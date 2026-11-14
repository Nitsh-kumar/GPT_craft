import { useState, useCallback, useRef, useEffect } from 'react';
import { CraftMode, Message, Model, ConversationResponse } from '../types';
import { chatService } from '../services/chatService';
import {
  appendMessageChunk,
  applyAgentSseEvent,
  markAbortedActions,
  markMessageComplete,
  markMessageInterrupted,
} from '../utils/chatReducers';

export const useChat = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [selectedMode, setSelectedMode] = useState<CraftMode>('standard');
  const [conversations, setConversations] = useState<ConversationResponse[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  
  const selectionRef = useRef(0);
  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesRef = useRef<Message[]>(messages);
  messagesRef.current = messages;

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const availableModels = await chatService.getModels();
        setModels(availableModels);
        if (availableModels.length > 0) {
          setSelectedModel(availableModels[0].id);
        }
      } catch (err) {
        setError('Unable to load available models. Please reload to retry.');
      }
    };
    fetchModels();
  }, []);

  const loadConversations = useCallback(async () => {
    try {
      const convs = await chatService.getConversations();
      setConversations(convs);
    } catch (err) {
      console.error('Failed to fetch conversations', err);
    }
  }, []);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const selectConversation = useCallback(async (id: string | null) => {
    const selection = ++selectionRef.current;
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setError(null);
    setCurrentConversationId(id);
    if (!id) {
      setMessages([]);
      setIsGenerating(false);
      return;
    }
    setIsGenerating(true);
    try {
      const history = await chatService.getHistory(id);
      const mapped: Message[] = history.map((msg) => ({
        id: msg.id.toString(),
        role: msg.role as 'user' | 'assistant',
        content: msg.content,
        timestamp: msg.created_at,
        modelUsed: msg.model_used || undefined,
        modeUsed: msg.mode_used || undefined,
        status: 'complete' as const,
      }));
      try {
        const pending = await chatService.getPendingApproval(id);
        if (pending && mapped.length > 0) {
          const lastMsg = mapped[mapped.length - 1];
          lastMsg.approvalRequired = pending;
        }
      } catch (e) {
        console.warn('Failed to load pending approval', e);
      }
      if (selectionRef.current === selection) setMessages(mapped);
    } catch (err) {
      console.error('Failed to load history', err);
      if (selectionRef.current === selection) setError('Failed to load conversation history');
    } finally {
      if (selectionRef.current === selection) setIsGenerating(false);
    }
  }, []);

  const deleteConversation = useCallback(async (id: string) => {
    try {
      await chatService.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id.toString() !== id));
      if (currentConversationId === id) {
        setCurrentConversationId(null);
        setMessages([]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to delete conversation');
    }
  }, [currentConversationId]);

  const sendMessage = useCallback(async (content: string, modeOverride?: CraftMode) => {
    if (!content.trim() || !selectedModel || abortControllerRef.current) return;

    const activeMode = modeOverride ?? selectedMode;

    const newUserMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
      mode: activeMode,
    };

    setMessages((prev) => [...prev, newUserMessage]);
    setIsGenerating(true);
    setError(null);

    const assistantMessageId = (Date.now() + 1).toString();
    const newAssistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      status: 'streaming',
      modelUsed: selectedModel,
      modeUsed: activeMode,
      timestamp: new Date().toISOString(),
      mode: activeMode,
      thoughts: [],
      actions: [],
    };

    setMessages((prev) => [...prev, newAssistantMessage]);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const history = [...messages, newUserMessage];

      const result = await chatService.streamMessage(
        currentConversationId,
        selectedModel,
        history,
        (chunk) => {
          if (controller.signal.aborted) return;
          setMessages((prev) =>
            prev.map((msg) => (msg.id === assistantMessageId ? appendMessageChunk(msg, chunk) : msg))
          );
        },
        controller.signal,
        activeMode,
        (event) => {
          if (controller.signal.aborted) return;
          setMessages((prev) =>
            prev.map((msg) => (msg.id === assistantMessageId ? applyAgentSseEvent(msg, event) : msg))
          );
        },
        (event) => {
          if (controller.signal.aborted) return;
          setCurrentConversationId(String(event.conversation_id));
          loadConversations();
        }
      );

      if (controller.signal.aborted) return;
      setMessages((prev) =>
        prev.map((msg) => (msg.id === assistantMessageId ? markMessageComplete(msg, result) : msg))
      );
      if (!currentConversationId && result.conversationId) {
        setCurrentConversationId(result.conversationId);
        loadConversations();
      }
      
    } catch (err: unknown) {
      setMessages((prev) =>
        prev.map((msg) => (msg.id === assistantMessageId ? markMessageInterrupted(msg) : msg))
      );
      if (err instanceof Error && err.name === 'AbortError') {
        console.log('Stream aborted by user');
      } else {
        setError(err instanceof Error ? err.message : 'Generation failed.');
      }
    } finally {
      if (abortControllerRef.current === controller) {
        setIsGenerating(false);
        abortControllerRef.current = null;
      }
    }
  }, [messages, selectedModel, selectedMode, currentConversationId, loadConversations]);

  const stopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsGenerating(false);
      setMessages((prev) => prev.map(markAbortedActions));
    }
  }, []);

  const handleApprovalDecision = useCallback(
    async (
      actionId: string,
      decision: 'approve' | 'modify' | 'reject',
      modifiedParams?: Record<string, unknown>,
      feedback?: string
    ) => {
      if (abortControllerRef.current) return;

      const targetMessage = messagesRef.current.find(
        (msg) => msg.approvalRequired?.actionId === actionId
      );
      const targetMessageId = targetMessage?.id ?? null;
      const pendingApproval = targetMessage?.approvalRequired;

      setIsGenerating(true);
      setError(null);
      const controller = new AbortController();
      abortControllerRef.current = controller;
      let streamStarted = false;

      try {
        const result = await chatService.submitApproval(
          actionId,
          decision,
          modifiedParams,
          feedback,
          (chunk) => {
            if (controller.signal.aborted || !targetMessageId) return;
            setMessages((prev) =>
              prev.map((msg) => (msg.id === targetMessageId ? appendMessageChunk(msg, chunk) : msg))
            );
          },
          (event) => {
            if (controller.signal.aborted || !targetMessageId) return;
            const defaultActionTier =
              pendingApproval && 'actionId' in event && event.actionId === pendingApproval.actionId
                ? pendingApproval.tier
                : 1;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === targetMessageId
                  ? applyAgentSseEvent(msg, event, { defaultActionTier })
                  : msg
              )
            );
          },
          controller.signal,
          () => {
            if (controller.signal.aborted) return;
            streamStarted = true;
            if (!targetMessageId) return;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === targetMessageId
                  ? { ...msg, approvalRequired: undefined, status: 'streaming' }
                  : msg
              )
            );
          }
        );

        if (controller.signal.aborted || !targetMessageId) return;
        setMessages((prev) =>
          prev.map((msg) => (msg.id === targetMessageId ? markMessageComplete(msg, result) : msg))
        );
      } catch (err: unknown) {
        if (targetMessageId) {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === targetMessageId
                ? markMessageInterrupted(
                    msg,
                    !streamStarted && pendingApproval
                      ? { preserveApproval: pendingApproval }
                      : undefined
                  )
                : msg
            )
          );
        }
        if (err instanceof Error && err.name === 'AbortError') {
          console.log('Approval stream aborted');
        } else {
          setError(err instanceof Error ? err.message : 'Error executing approval decision');
        }
      } finally {
        if (abortControllerRef.current === controller) {
          setIsGenerating(false);
          abortControllerRef.current = null;
        }
      }
    },
    []
  );

  const clearChat = useCallback(() => {
    ++selectionRef.current;
    setMessages([]);
    setError(null);
    setCurrentConversationId(null);
    stopGeneration();
  }, [stopGeneration]);

  useEffect(() => () => { abortControllerRef.current?.abort(); }, []);

  return {
    messages,
    isGenerating,
    isStreaming: isGenerating,
    error,
    models,
    selectedModel,
    selectedMode,
    conversations,
    currentConversationId,
    setSelectedModel,
    setSelectedMode,
    sendMessage,
    handleApprovalDecision,
    stopGeneration,
    clearChat,
    selectConversation,
    deleteConversation,
  };
};

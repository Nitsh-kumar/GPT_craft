import { useState, useCallback, useRef, useEffect } from 'react';
import { CraftMode, Message, Model } from '../types';
import { chatService } from '../services/chatService';

export const useChat = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [selectedMode, setSelectedMode] = useState<CraftMode>('standard');
  const [conversations, setConversations] = useState<any[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const availableModels = await chatService.getModels();
        setModels(availableModels);
        if (availableModels.length > 0) {
          setSelectedModel(availableModels[0].id);
        }
      } catch (err) {
        console.error('Failed to fetch models', err);
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
    setCurrentConversationId(id);
    if (!id) {
      setMessages([]);
      return;
    }
    setIsGenerating(true);
    try {
      const history = await chatService.getHistory(id);
      const mapped: Message[] = history.map((msg: any) => ({
        id: msg.id.toString(),
        role: msg.role as 'user' | 'assistant',
        content: msg.content,
        timestamp: msg.created_at
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
      setMessages(mapped);
    } catch (err) {
      console.error('Failed to load history', err);
      setError('Failed to load conversation history');
    } finally {
      setIsGenerating(false);
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
    if (!content.trim() || !selectedModel) return;

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
      timestamp: new Date().toISOString(),
      mode: activeMode,
      thoughts: [],
      actions: [],
    };

    setMessages((prev) => [...prev, newAssistantMessage]);

    abortControllerRef.current = new AbortController();

    try {
      const history = [...messages, newUserMessage];
      
      const result = await chatService.streamMessage(
        currentConversationId,
        selectedModel,
        history,
        (chunk) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: msg.content + chunk }
                : msg
            )
          );
        },
        abortControllerRef.current.signal,
        activeMode,
        (event) => {
          if (event.type === 'thought') {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? { ...msg, thoughts: [...(msg.thoughts || []), event.thought] }
                  : msg
              )
            );
          } else if (event.type === 'action_call') {
            setMessages((prev) =>
              prev.map((msg) => {
                if (msg.id !== assistantMessageId) return msg;
                const currentActions = msg.actions || [];
                const exists = currentActions.some((a) => a.actionId === event.actionId);
                if (exists) return msg;
                return {
                  ...msg,
                  actions: [
                    ...currentActions,
                    {
                      actionId: event.actionId,
                      tool: event.tool,
                      args: event.args,
                      tier: event.tier,
                    },
                  ],
                };
              })
            );
          } else if (event.type === 'action_result') {
            setMessages((prev) =>
              prev.map((msg) => {
                if (msg.id !== assistantMessageId) return msg;
                const currentActions = msg.actions || [];
                const idx = currentActions.findIndex((a) => a.actionId === event.actionId);
                if (idx >= 0) {
                  const updated = [...currentActions];
                  updated[idx] = { ...updated[idx], output: event.output };
                  return { ...msg, actions: updated };
                }
                return {
                  ...msg,
                  actions: [
                    ...currentActions,
                    {
                      actionId: event.actionId,
                      tool: event.tool,
                      args: {},
                      tier: 1,
                      output: event.output,
                    },
                  ],
                };
              })
            );
          } else if (event.type === 'approval_required') {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? {
                      ...msg,
                      approvalRequired: {
                        actionId: event.actionId,
                        tool: event.tool,
                        tier: event.tier,
                        parameters: event.parameters,
                        rationale: event.rationale,
                        diff: event.diff,
                      },
                    }
                  : msg
              )
            );
          }
        }
      );

      if (!currentConversationId && result.conversationId) {
        setCurrentConversationId(result.conversationId);
        loadConversations();
      }
      
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('Stream aborted by user');
      } else {
        setError(err.message || 'An error occurred while generating the response.');
      }
    } finally {
      setIsGenerating(false);
      abortControllerRef.current = null;
    }
  }, [messages, selectedModel, selectedMode, currentConversationId, loadConversations]);

  const stopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsGenerating(false);
    }
  }, []);

  const handleApprovalDecision = useCallback(
    async (
      actionId: string,
      decision: 'approve' | 'modify' | 'reject',
      modifiedParams?: Record<string, unknown>,
      feedback?: string
    ) => {
      setIsGenerating(true);
      setError(null);
      abortControllerRef.current = new AbortController();

      let targetMessageId: string | null = null;
      setMessages((prev) =>
        prev.map((msg) => {
          if (msg.approvalRequired?.actionId === actionId) {
            targetMessageId = msg.id;
            return { ...msg, approvalRequired: undefined };
          }
          return msg;
        })
      );

      try {
        await chatService.submitApproval(
          actionId,
          decision,
          modifiedParams,
          feedback,
          (chunk) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === targetMessageId
                  ? { ...msg, content: (msg.content || '') + chunk }
                  : msg
              )
            );
          },
          (event) => {
            if (event.type === 'action_result') {
              setMessages((prev) =>
                prev.map((msg) => {
                  if (msg.id !== targetMessageId) return msg;
                  const currentActions = msg.actions || [];
                  const idx = currentActions.findIndex((a) => a.actionId === event.actionId);
                  if (idx >= 0) {
                    const updated = [...currentActions];
                    updated[idx] = { ...updated[idx], output: event.output };
                    return { ...msg, actions: updated };
                  }
                  return {
                    ...msg,
                    actions: [
                      ...currentActions,
                      {
                        actionId: event.actionId,
                        tool: event.tool,
                        args: {},
                        tier: 2,
                        output: event.output,
                      },
                    ],
                  };
                })
              );
            } else if (event.type === 'approval_required') {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === targetMessageId
                    ? {
                        ...msg,
                        approvalRequired: {
                          actionId: event.actionId,
                          tool: event.tool,
                          tier: event.tier,
                          parameters: event.parameters,
                          rationale: event.rationale,
                          diff: event.diff,
                        },
                      }
                    : msg
                )
              );
            } else if (event.type === 'thought') {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === targetMessageId
                    ? { ...msg, thoughts: [...(msg.thoughts || []), event.thought] }
                    : msg
                )
              );
            }
          },
          abortControllerRef.current.signal
        );
      } catch (err: any) {
        if (err.name === 'AbortError') {
          console.log('Approval stream aborted');
        } else {
          setError(err.message || 'Error executing approval decision');
        }
      } finally {
        setIsGenerating(false);
        abortControllerRef.current = null;
      }
    },
    []
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    setError(null);
    setCurrentConversationId(null);
    stopGeneration();
  }, [stopGeneration]);

  return {
    messages,
    isGenerating,
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

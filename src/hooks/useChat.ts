import { useState, useCallback, useRef, useEffect } from 'react';
import { Message, Model } from '../types';
import { chatService } from '../services/chatService';

export const useChat = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
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
      const mapped = history.map((msg: any) => ({
        id: msg.id.toString(),
        role: msg.role as 'user' | 'assistant',
        content: msg.content,
        timestamp: msg.created_at
      }));
      setMessages(mapped);
    } catch (err) {
      console.error('Failed to load history', err);
      setError('Failed to load conversation history');
    } finally {
      setIsGenerating(false);
    }
  }, []);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || !selectedModel) return;

    const newUserMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
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
        abortControllerRef.current.signal
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
  }, [messages, selectedModel, currentConversationId, loadConversations]);

  const stopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsGenerating(false);
    }
  }, []);

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
    conversations,
    currentConversationId,
    setSelectedModel,
    sendMessage,
    stopGeneration,
    clearChat,
    selectConversation,
  };
};

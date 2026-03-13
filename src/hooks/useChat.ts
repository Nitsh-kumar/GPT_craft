import { useState, useCallback, useRef, useEffect } from 'react';
import { Message, Model } from '../types';
import { chatService } from '../services/chatService';

export const useChat = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
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

    // Create a new AbortController for this request
    abortControllerRef.current = new AbortController();

    try {
      // Pass the current messages + the new user message to the backend
      const history = [...messages, newUserMessage];
      
      await chatService.streamMessage(
        selectedModel,
        history,
        (chunk) => {
          // Use functional state update to prevent stale closures and excessive re-renders
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
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('Stream aborted by user');
      } else {
        // Handle specific errors like 429 Quota Exceeded or 401 Unauthorized
        setError(err.message || 'An error occurred while generating the response.');
      }
    } finally {
      setIsGenerating(false);
      abortControllerRef.current = null;
    }
  }, [messages, selectedModel]);

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
    stopGeneration();
  }, [stopGeneration]);

  return {
    messages,
    isGenerating,
    error,
    models,
    selectedModel,
    setSelectedModel,
    sendMessage,
    stopGeneration,
    clearChat,
  };
};

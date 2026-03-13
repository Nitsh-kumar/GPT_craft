import React, { useEffect } from 'react';
import { MainLayout } from '../components/layout/MainLayout';
import { MessageList } from '../components/chat/MessageList';
import { ChatInput } from '../components/chat/ChatInput';
import { ModelSelector } from '../components/chat/ModelSelector';
import { QuotaDisplay } from '../components/chat/QuotaDisplay';
import { useChat } from '../hooks/useChat';
import { useQuota } from '../hooks/useQuota';
import { Trash2, AlertTriangle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const ChatPage = () => {
  const { user } = useAuth();
  const {
    messages,
    isGenerating,
    error,
    models,
    selectedModel,
    setSelectedModel,
    sendMessage,
    stopGeneration,
    clearChat,
  } = useChat();

  const { quota, isLoading: isQuotaLoading, refreshQuota } = useQuota();

  // Refresh quota after every message generation completes
  useEffect(() => {
    if (!isGenerating && messages.length > 0) {
      refreshQuota();
    }
  }, [isGenerating, messages.length, refreshQuota]);

  const isQuotaExhausted = quota ? quota.requestsRemaining <= 0 || quota.tokensRemaining <= 0 : false;

  return (
    <MainLayout onNewChat={clearChat}>
      <div className="flex flex-col h-full relative">
        {/* Header Area */}
        <div className="flex items-center justify-between p-4 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 z-10 sticky top-0">
          <div className="flex items-center gap-4">
            <ModelSelector
              models={models}
              selectedModel={selectedModel}
              onSelect={setSelectedModel}
              userPlan={user?.plan || 'free'}
            />
            <div className="hidden md:block h-6 w-px bg-zinc-200 dark:bg-zinc-800 mx-2" />
            <QuotaDisplay quota={quota} isLoading={isQuotaLoading} />
          </div>
          
          <button
            onClick={clearChat}
            disabled={isGenerating || messages.length === 0}
            className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-zinc-600 dark:text-zinc-400 hover:text-red-600 dark:hover:text-red-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800"
            title="Clear conversation"
          >
            <Trash2 size={16} />
            <span className="hidden sm:inline">Clear Chat</span>
          </button>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 p-4 m-4 rounded-r-md flex items-start gap-3">
            <AlertTriangle className="text-red-500 shrink-0 mt-0.5" size={20} />
            <div>
              <h3 className="text-red-800 dark:text-red-200 font-medium text-sm">Error</h3>
              <p className="text-red-700 dark:text-red-300 text-sm mt-1">{error}</p>
            </div>
          </div>
        )}

        {/* Chat Area */}
        <MessageList messages={messages} isGenerating={isGenerating} />

        {/* Input Area */}
        <ChatInput
          onSend={sendMessage}
          onStop={stopGeneration}
          isGenerating={isGenerating}
          disabled={isQuotaExhausted}
        />
      </div>
    </MainLayout>
  );
};

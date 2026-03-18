import React, { useEffect } from 'react';
import { MainLayout } from '../components/layout/MainLayout';
import { MessageList } from '../components/chat/MessageList';
import { ChatInput } from '../components/chat/ChatInput';
import { QuotaDisplay } from '../components/chat/QuotaDisplay';
import { useChat } from '../hooks/useChat';
import { useQuota } from '../hooks/useQuota';
import { AlertTriangle } from 'lucide-react';
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

  useEffect(() => {
    if (!isGenerating && messages.length > 0) {
      refreshQuota();
    }
  }, [isGenerating, messages.length, refreshQuota]);

  const isQuotaExhausted = quota ? quota.requestsRemaining <= 0 || quota.tokensRemaining <= 0 : false;

  return (
    <MainLayout onNewChat={clearChat} onClearChat={clearChat}>
      <div className="flex flex-col h-full relative">
        {/* Header — quota on the right */}
        <div className="flex items-center justify-end p-4 border-b border-zinc-800/50 z-10 sticky top-0 bg-brand-dark/80 backdrop-blur-sm">
          <QuotaDisplay quota={quota} isLoading={isQuotaLoading} />
        </div>

        {/* Error Banner */}
        {error && (
          <div className="bg-red-900/20 border-l-4 border-red-500 p-4 m-4 rounded-r-md flex items-start gap-3">
            <AlertTriangle className="text-red-500 shrink-0 mt-0.5" size={20} />
            <div>
              <h3 className="text-red-200 font-medium text-sm">Error</h3>
              <p className="text-red-300 text-sm mt-1">{error}</p>
            </div>
          </div>
        )}

        {/* Chat Area */}
        <MessageList 
          messages={messages} 
          isGenerating={isGenerating} 
          userName={user?.name || user?.email || undefined}
        />

        {/* Input Area */}
        <ChatInput
          onSend={sendMessage}
          onStop={stopGeneration}
          isGenerating={isGenerating}
          disabled={isQuotaExhausted}
          models={models}
          selectedModel={selectedModel}
          setSelectedModel={setSelectedModel}
          userPlan={user?.plan || 'free'}
        />
      </div>
    </MainLayout>
  );
};

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
  } = useChat();

  const { quota, isLoading: isQuotaLoading, refreshQuota } = useQuota();

  useEffect(() => {
    if (!isGenerating && messages.length > 0) {
      refreshQuota();
    }
  }, [isGenerating, messages.length, refreshQuota]);

  const isQuotaExhausted = quota ? quota.requestsRemaining <= 0 || quota.tokensRemaining <= 0 : false;

  return (
    <MainLayout 
      onNewChat={() => selectConversation(null)} 
      onClearChat={clearChat}
      conversations={conversations}
      currentConversationId={currentConversationId}
      onSelectConversation={selectConversation}
      onDeleteConversation={deleteConversation}
    >
      <div className="flex flex-col h-full relative">
        {/* Header — usage on the right */}
        <div className="sticky top-0 z-10 flex h-12 items-center justify-end border-b border-line bg-canvas px-5">
          <QuotaDisplay quota={quota} isLoading={isQuotaLoading} />
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mx-auto mt-4 flex w-[calc(100%-2rem)] max-w-3xl items-start gap-3 rounded-xl border border-danger/30 bg-danger-soft p-4" data-testid="chat-error-banner" role="alert">
            <AlertTriangle className="mt-0.5 shrink-0 text-danger" size={18} />
            <div>
              <h3 className="text-sm font-medium text-ink">Something went wrong</h3>
              <p className="mt-1 text-sm text-ink-2">{error}</p>
            </div>
          </div>
        )}

        {/* Chat Area */}
        <MessageList 
          messages={messages} 
          isGenerating={isGenerating} 
          userName={user?.name || user?.email || undefined}
          selectedMode={selectedMode}
          selectedModelName={models.find(m => m.id === selectedModel)?.name}
          onQuickPrompt={(prompt, mode) => {
            if (mode) setSelectedMode(mode);
            sendMessage(prompt, mode);
          }}
          onApprovalDecision={handleApprovalDecision}
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
          selectedMode={selectedMode}
          setSelectedMode={setSelectedMode}
          userPlan={user?.plan || 'free'}
        />
      </div>
    </MainLayout>
  );
};

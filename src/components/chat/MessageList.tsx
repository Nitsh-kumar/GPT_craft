import React, { useRef, useEffect } from 'react';
import { Message } from '../../types';
import { MessageBubble } from './MessageBubble';
import { Loader2, Sparkles } from 'lucide-react';

interface MessageListProps {
  messages: Message[];
  isGenerating: boolean;
  userName?: string;
}

export const MessageList = ({ messages, isGenerating, userName }: MessageListProps) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isGenerating]);

  const firstName = userName?.split(' ')[0] || userName?.split('@')[0] || 'there';

  return (
    <div className="flex-1 overflow-y-auto scrollbar-hide py-8">
      <div className="max-w-4xl mx-auto flex flex-col min-h-full">
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center px-8">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles size={20} className="text-brand-cyan" />
              <span className="text-lg font-medium text-brand-cyan">
                Hi {firstName}
              </span>
            </div>
            <h2 className="text-3xl sm:text-4xl font-semibold text-zinc-200 tracking-tight">
              Where should we start?
            </h2>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {isGenerating && (
              <div className="flex items-center gap-3 px-8 py-4 animate-pulse">
                <div className="h-6 w-6 rounded-lg glass-card flex items-center justify-center">
                  <Loader2 size={12} className="animate-spin text-brand-cyan" />
                </div>
                <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-cyan-500/60">
                  Thinking...
                </span>
              </div>
            )}
            <div ref={messagesEndRef} className="h-32 shrink-0" />
          </>
        )}
      </div>
    </div>
  );
};

import React, { useRef, useEffect } from 'react';
import { Message } from '../../types';
import { MessageBubble } from './MessageBubble';
import { Loader2, Sparkles, Compass, Code2, Lightbulb } from 'lucide-react';

interface MessageListProps {
  messages: Message[];
  isGenerating: boolean;
  userName?: string;
  onQuickPrompt?: (prompt: string) => void;
}

const STARTER_CARDS = [
  {
    title: 'System Architecture',
    prompt: 'Design a scalable microservices architecture for a real-time AI chat app.',
    icon: <Compass size={16} className="text-brand-cyan" />,
  },
  {
    title: 'TypeScript Refactor',
    prompt: 'Write a clean React custom hook for Server-Sent Events (SSE) streaming.',
    icon: <Code2 size={16} className="text-emerald-400" />,
  },
  {
    title: 'Product Brainstorm',
    prompt: 'Give me 3 unique differentiator features for an AI coding assistant.',
    icon: <Lightbulb size={16} className="text-amber-400" />,
  },
];

export const MessageList = ({ messages, isGenerating, userName, onQuickPrompt }: MessageListProps) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const prevMessageCountRef = useRef(0);

  useEffect(() => {
    const currentCount = messages.length;
    if (currentCount > prevMessageCountRef.current) {
      if (containerRef.current) {
        containerRef.current.scrollTop = containerRef.current.scrollHeight;
      }
    }
    prevMessageCountRef.current = currentCount;
  }, [messages.length]);

  const firstName = userName?.split(' ')[0] || userName?.split('@')[0] || 'there';

  return (
    <div ref={containerRef} className="flex-1 overflow-y-auto scrollbar-hide py-8">
      <div className="max-w-4xl mx-auto flex flex-col min-h-full">
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center px-8">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles size={20} className="text-brand-cyan" />
              <span className="text-lg font-medium text-brand-cyan">
                Hi {firstName}
              </span>
            </div>
            <h2 className="text-3xl sm:text-4xl font-semibold text-zinc-200 tracking-tight mb-8">
              Where should we start?
            </h2>

            {onQuickPrompt && (
              <div className="grid sm:grid-cols-3 gap-3 max-w-2xl w-full text-left">
                {STARTER_CARDS.map((card, idx) => (
                  <button
                    key={idx}
                    type="button"
                    data-testid={`starter-card-${idx}`}
                    onClick={() => onQuickPrompt(card.prompt)}
                    className="p-4 rounded-2xl border border-zinc-800 bg-zinc-900/50 hover:bg-zinc-800/70 hover:border-brand-cyan/40 transition-all group"
                  >
                    <div className="flex items-center gap-2 mb-2 font-semibold text-xs text-zinc-200 group-hover:text-brand-cyan">
                      {card.icon}
                      <span>{card.title}</span>
                    </div>
                    <p className="text-xs text-zinc-400 line-clamp-2 leading-relaxed">
                      {card.prompt}
                    </p>
                  </button>
                ))}
              </div>
            )}
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
            <div ref={messagesEndRef} className="h-4 shrink-0" />
          </>
        )}
      </div>
    </div>
  );
};

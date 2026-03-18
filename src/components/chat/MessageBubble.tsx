import React from 'react';
import { Message } from '../../types';
import { cn } from '../../utils/cn';
import { User, Copy, Check } from 'lucide-react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MessageBubbleProps {
  message: Message;
}

export const MessageBubble = ({ message }: MessageBubbleProps) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = React.useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={cn(
        'group w-full flex flex-col px-4 py-6 transition-all animate-in',
        isUser ? 'items-end' : 'items-start'
      )}
    >
      <div className={cn(
        "max-w-[85%] md:max-w-[75%] flex flex-col gap-2 transition-all duration-300",
        isUser ? "items-end" : "items-start"
      )}>
        {/* Avatar/Header */}
        {!isUser && (
          <div className="flex items-center gap-2 mb-1 px-2">
            <div className="h-6 w-6 rounded-lg glass-card flex items-center justify-center overflow-hidden">
              <img src="/craft_logo.png" alt="AI" className="w-4 h-4 object-contain opacity-80" />
            </div>
          </div>
        )}

        {/* Message Content */}
        <div className={cn(
          "relative px-5 py-4 rounded-[2rem] shadow-xl transition-all duration-300",
          isUser 
            ? "bg-brand-cyan text-brand-dark rounded-tr-none font-medium shadow-cyan-500/10" 
            : "glass text-zinc-900 dark:text-zinc-100 rounded-tl-none border-zinc-200/50 dark:border-zinc-800/50"
        )}>
          <div className="markdown-body prose prose-sm dark:prose-invert max-w-none w-full leading-relaxed">
            <Markdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </Markdown>
          </div>
          
          {/* Action Buttons (Hover) */}
          {!isUser && message.content && (
            <div className="absolute right-2 -bottom-8 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-2">
              <button 
                onClick={handleCopy}
                className="p-1.5 rounded-lg glass-card text-zinc-500 hover:text-brand-cyan hover:border-brand-cyan/30 transition-all"
                title="Copy message"
              >
                {copied ? <Check size={14} /> : <Copy size={14} />}
              </button>
            </div>
          )}
        </div>

        {/* Timestamp/Status */}
        <div className={cn(
          "px-2 text-[10px] font-medium text-zinc-400 opacity-0 group-hover:opacity-100 transition-opacity",
          isUser ? "text-right" : "text-left"
        )}>
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </div>
  );
};

import React, { useState, useRef, useEffect } from 'react';
import { Send, Square } from 'lucide-react';
import { cn } from '../../utils/cn';

interface ChatInputProps {
  onSend: (message: string) => void;
  onStop: () => void;
  isGenerating: boolean;
  disabled?: boolean;
}

export const ChatInput = ({ onSend, onStop, isGenerating, disabled }: ChatInputProps) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (input.trim() && !isGenerating && !disabled) {
      onSend(input);
      setInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  return (
    <div className="absolute bottom-0 left-0 w-full bg-gradient-to-t from-white via-white dark:from-zinc-950 dark:via-zinc-950 to-transparent pt-6 pb-4 px-4 md:px-0">
      <div className="max-w-3xl mx-auto flex flex-col gap-3">
        <div className="relative flex w-full flex-grow flex-col rounded-2xl border border-black/10 bg-white shadow-[0_0_15px_rgba(0,0,0,0.1)] dark:border-white/10 dark:bg-zinc-900 dark:shadow-[0_0_15px_rgba(0,0,0,0.5)]">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={disabled ? "Quota exceeded. Please try again later." : "Send a message..."}
            disabled={disabled || isGenerating}
            className={cn(
              "m-0 w-full resize-none border-0 bg-transparent p-4 pr-12 focus:ring-0 focus-visible:ring-0 dark:bg-transparent py-4 text-zinc-900 dark:text-zinc-100",
              "max-h-52 overflow-y-auto"
            )}
            rows={1}
            style={{ minHeight: '56px' }}
          />
          
          <div className="absolute right-2 bottom-2">
            {isGenerating ? (
              <button
                onClick={onStop}
                className="p-2 rounded-lg bg-zinc-800 text-white hover:bg-zinc-700 transition-colors"
                title="Stop generation"
              >
                <Square size={16} className="fill-current" />
              </button>
            ) : (
              <button
                onClick={handleSend}
                disabled={!input.trim() || disabled}
                className="p-2 rounded-lg bg-cyan-600 text-white hover:bg-cyan-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title="Send message"
              >
                <Send size={16} />
              </button>
            )}
          </div>
        </div>
        <div className="text-center text-xs text-zinc-500 dark:text-zinc-400">
          AI can make mistakes. Consider verifying important information.
        </div>
      </div>
    </div>
  );
};

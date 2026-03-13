import React from 'react';
import { Message } from '../../types';
import { cn } from '../../utils/cn';
import { User, Bot } from 'lucide-react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MessageBubbleProps {
  message: Message;
}

export const MessageBubble = ({ message }: MessageBubbleProps) => {
  const isUser = message.role === 'user';

  return (
    <div
      className={cn(
        'group w-full text-zinc-800 dark:text-zinc-100 border-b border-black/10 dark:border-white/10',
        isUser ? 'bg-white dark:bg-zinc-950' : 'bg-zinc-50 dark:bg-zinc-900'
      )}
    >
      <div className="text-base gap-4 md:gap-6 m-auto md:max-w-2xl lg:max-w-3xl xl:max-w-4xl p-4 md:py-6 flex lg:px-0">
        <div className="w-8 flex flex-col relative items-end">
          <div
            className={cn(
              'relative h-8 w-8 rounded-sm text-white flex items-center justify-center',
              isUser ? 'bg-cyan-600 p-1' : 'bg-transparent'
            )}
          >
            {isUser ? <User size={20} /> : <img src="/craft_logo.png" alt="AI" className="w-full h-full object-contain" />}
          </div>
        </div>
        <div className="relative flex w-[calc(100%-50px)] flex-col gap-1 md:gap-3 lg:w-[calc(100%-115px)]">
          <div className="flex flex-grow flex-col gap-3">
            <div className="min-h-[20px] flex flex-col items-start gap-4 whitespace-pre-wrap break-words">
              <div className="markdown-body prose dark:prose-invert max-w-none w-full">
                <Markdown remarkPlugins={[remarkGfm]}>
                  {message.content}
                </Markdown>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

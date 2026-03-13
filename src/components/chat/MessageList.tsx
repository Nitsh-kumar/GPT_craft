import React, { useEffect, useRef } from 'react';
import { Message } from '../../types';
import { MessageBubble } from './MessageBubble';

interface MessageListProps {
  messages: Message[];
  isGenerating: boolean;
}

export const MessageList = ({ messages, isGenerating }: MessageListProps) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change or while generating
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isGenerating]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center h-full text-zinc-500 dark:text-zinc-400">
        <img src="/craft_logo.png" alt="GPTCraft Logo" className="w-16 h-16 object-contain mb-4" />
        <h2 className="text-xl font-semibold mb-2">How can I help you today?</h2>
        <p className="text-sm max-w-md text-center">
          Ask me anything. I can help you write code, draft emails, or answer questions.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto w-full">
      <div className="flex flex-col pb-32">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        <div ref={bottomRef} className="h-4" />
      </div>
    </div>
  );
};

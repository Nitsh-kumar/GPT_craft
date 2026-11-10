import React, { useRef, useEffect } from 'react';
import { Message, CraftMode } from '../../types';
import { MessageBubble } from './MessageBubble';
import { Compass, Code2, Lightbulb, Sparkles, Zap, ArrowUpRight, Cpu } from 'lucide-react';
import { cn } from '../../utils/cn';

interface MessageListProps {
  messages: Message[];
  isGenerating: boolean;
  userName?: string;
  selectedMode?: CraftMode;
  selectedModelName?: string;
  onQuickPrompt?: (prompt: string, mode?: CraftMode) => void;
}

interface WorkbenchCard {
  mode: CraftMode;
  title: string;
  category: string;
  prompt: string;
  tag: string;
  icon: React.ReactNode;
  accentColor: string;
  borderColor: string;
}

const WORKBENCH_CARDS: WorkbenchCard[] = [
  {
    mode: 'architect',
    title: 'Deep Architect',
    category: 'System & Schema Design',
    prompt: 'Design a fault-tolerant distributed architecture for high-concurrency real-time AI agents.',
    tag: 'Frontier Reasoning',
    icon: <Compass size={18} />,
    accentColor: 'text-blue-500 bg-blue-500/10',
    borderColor: 'hover:border-blue-500/40',
  },
  {
    mode: 'code',
    title: 'Code Craft',
    category: 'Full-Stack Engineering',
    prompt: 'Write a clean, production-grade custom React 19 hook for resilient Server-Sent Events (SSE).',
    tag: 'Typed & Optimized',
    icon: <Code2 size={18} />,
    accentColor: 'text-emerald-500 bg-emerald-500/10',
    borderColor: 'hover:border-emerald-500/40',
  },
  {
    mode: 'brainstorm',
    title: 'Brainstorm',
    category: 'Strategy & Ideation',
    prompt: 'Brainstorm 4 high-leverage wedge features that differentiate an AI developer platform.',
    tag: 'Divergent Synthesis',
    icon: <Lightbulb size={18} />,
    accentColor: 'text-amber-500 bg-amber-500/10',
    borderColor: 'hover:border-amber-500/40',
  },
  {
    mode: 'standard',
    title: 'Standard Craft',
    category: 'Fast Technical Synthesis',
    prompt: 'Break down vector embedding quantization trade-offs: scalar, product, and 1-bit RaBitQ.',
    tag: 'Instant LPU Speed',
    icon: <Sparkles size={18} />,
    accentColor: 'text-accent bg-accent-soft',
    borderColor: 'hover:border-accent/40',
  },
];

export const MessageList = ({
  messages,
  isGenerating,
  userName,
  selectedMode = 'standard',
  selectedModelName = 'Llama 3.3 70B',
  onQuickPrompt,
}: MessageListProps) => {
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

  const firstName = userName?.split(' ')[0] || userName?.split('@')[0] || 'Maker';
  const lastIsEmptyAssistant =
    messages.length > 0 && messages[messages.length - 1].role === 'assistant' && !messages[messages.length - 1].content;

  return (
    <div ref={containerRef} className="flex-1 overflow-y-auto">
      <div className="mx-auto flex min-h-full w-full max-w-4xl flex-col px-4 sm:px-6">
        {messages.length === 0 ? (
          <div className="flex flex-1 flex-col justify-center py-10 sm:py-16">
            {/* Studio Workbench Header */}
            <div className="mb-8">
              <div className="inline-flex items-center gap-2 rounded-full border border-line bg-sunken px-3 py-1 text-[11px] font-medium text-ink-3">
                <span className="flex h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
                <span className="font-mono text-ink tracking-tight font-semibold">GROQ LPU ACCELERATED</span>
                <span className="text-line-strong">/</span>
                <span>Active Model: <strong className="text-ink font-semibold">{selectedModelName}</strong></span>
              </div>

              <h1 className="mt-4 font-display text-3xl sm:text-4xl font-semibold tracking-[-0.03em] text-ink">
                Studio Workbench, <span className="text-accent">{firstName}</span>.
              </h1>
              <p className="mt-2 text-sm text-ink-3 max-w-xl">
                Select a specialized Craft Mode below or type directly to begin reasoning.
              </p>
            </div>

            {/* Interactive Craft Mode Workbench Cards */}
            {onQuickPrompt && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                {WORKBENCH_CARDS.map((card) => {
                  const isCurrentMode = selectedMode === card.mode;
                  return (
                    <button
                      key={card.mode}
                      type="button"
                      data-testid={`starter-card-${card.mode}`}
                      onClick={() => onQuickPrompt(card.prompt, card.mode)}
                      className={cn(
                        'group relative flex flex-col text-left p-4 rounded-xl border bg-raised transition-all duration-200 shadow-lift',
                        isCurrentMode ? 'border-accent ring-1 ring-accent/20' : 'border-line',
                        card.borderColor,
                        'hover:shadow-float active:translate-y-px'
                      )}
                    >
                      <div className="flex items-center justify-between w-full mb-2.5">
                        <div className="flex items-center gap-2">
                          <span className={cn('p-1.5 rounded-lg', card.accentColor)}>
                            {card.icon}
                          </span>
                          <div>
                            <span className="text-xs font-semibold text-ink font-display block leading-none">
                              {card.title}
                            </span>
                            <span className="text-[10px] text-ink-3 tracking-tight">
                              {card.category}
                            </span>
                          </div>
                        </div>

                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-md border border-line bg-sunken text-ink-3 group-hover:text-ink transition-colors">
                          {card.tag}
                        </span>
                      </div>

                      <p className="text-xs text-ink-2 leading-relaxed line-clamp-2 mt-1">
                        &ldquo;{card.prompt}&rdquo;
                      </p>

                      <div className="mt-3 flex items-center justify-between pt-2 border-t border-line/60 text-[11px] text-ink-3">
                        <span className="group-hover:text-accent font-medium transition-colors">Launch mode</span>
                        <ArrowUpRight size={14} className="group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-accent transition-transform duration-200" />
                      </div>
                    </button>
                  );
                })}
              </div>
            )}

            {/* Workbench telemetry footer */}
            <div className="mt-8 flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-line text-xs text-ink-3 font-mono">
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1.5">
                  <Zap size={13} className="text-accent" />
                  High-throughput LPU
                </span>
                <span className="flex items-center gap-1.5">
                  <Cpu size={13} className="text-ink-3" />
                  Mixture of Experts
                </span>
              </div>
              <span className="text-[11px]">⌘K or / to switch modes</span>
            </div>
          </div>
        ) : (
          <div className="py-6 sm:py-8 space-y-6">
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                modelName={selectedModelName}
                modeName={selectedMode}
              />
            ))}
            {isGenerating && (lastIsEmptyAssistant || messages[messages.length - 1]?.role === 'user') && (
              <div className="flex items-center gap-3 py-4 px-2" role="status" aria-live="polite">
                <div className="h-6 w-6 rounded-lg border border-line bg-surface flex items-center justify-center">
                  <Sparkles size={13} className="text-accent animate-pulse" />
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-mono font-medium text-ink">GPTCraft Engine</span>
                  <span className="text-xs text-ink-3">is formulating reasoning response…</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} className="h-4 shrink-0" />
          </div>
        )}
      </div>
    </div>
  );
};

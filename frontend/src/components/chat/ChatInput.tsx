import React, { useState, useRef, useEffect } from 'react';
import { ArrowUp, Square, ChevronDown, Lock, Cpu, Zap, Brain, Sparkles, Compass, Code2, Lightbulb, Check, Bot } from 'lucide-react';
import { cn } from '../../utils/cn';
import { CraftMode, Model, PlanType, UserPreferences } from '../../types';
import { memoryService, PREFERENCES_UPDATED_EVENT } from '../../services/memoryService';

interface ChatInputProps {
  onSend: (message: string) => void;
  onStop: () => void;
  isGenerating: boolean;
  disabled?: boolean;
  models: Model[];
  selectedModel: string;
  setSelectedModel: (modelId: string) => void;
  selectedMode: CraftMode;
  setSelectedMode: (mode: CraftMode) => void;
  userPlan: PlanType;
}

const planHierarchy: Record<PlanType, number> = { free: 0, super: 1, hyper: 2 };

const craftModes: { id: CraftMode; label: string; icon: React.ReactNode; badge?: string }[] = [
  { id: 'standard', label: 'Standard', icon: <Sparkles size={12} /> },
  { id: 'architect', label: 'Deep Architect', icon: <Compass size={12} /> },
  { id: 'code', label: 'Code Craft', icon: <Code2 size={12} /> },
  { id: 'brainstorm', label: 'Brainstorm', icon: <Lightbulb size={12} /> },
  { id: 'agent', label: 'Agent Studio', icon: <Bot size={12} />, badge: 'STUDIO' },
];

const getModelIcon = (modelId: string, size = 14) => {
  if (modelId.includes('70b')) return <Brain size={size} />;
  if (modelId.includes('8b')) return <Zap size={size} />;
  return <Cpu size={size} />;
};

export const ChatInput = ({ 
  onSend, 
  onStop, 
  isGenerating, 
  disabled,
  models,
  selectedModel,
  setSelectedModel,
  selectedMode,
  setSelectedMode,
  userPlan
}: ChatInputProps) => {
  const [input, setInput] = useState('');
  const [modelMenuOpen, setModelMenuOpen] = useState(false);
  const [memoryEnabled, setMemoryEnabled] = useState(true);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    memoryService
      .getPreferences()
      .then((prefs) => {
        if (active && typeof prefs.memoryEnabled === 'boolean') {
          setMemoryEnabled(prefs.memoryEnabled);
        }
      })
      .catch(() => {
        // Keep default on unauthenticated or offline init
      });

    const onPrefsUpdated = (e: Event) => {
      const customEvent = e as CustomEvent<UserPreferences>;
      if (customEvent.detail && typeof customEvent.detail.memoryEnabled === 'boolean') {
        setMemoryEnabled(customEvent.detail.memoryEnabled);
      }
    };
    window.addEventListener(PREFERENCES_UPDATED_EVENT, onPrefsUpdated);
    return () => {
      active = false;
      window.removeEventListener(PREFERENCES_UPDATED_EVENT, onPrefsUpdated);
    };
  }, []);

  const selected = models.find(m => m.id === selectedModel) || models[0];

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

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setModelMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div className="w-full bg-canvas px-4 pt-2 pb-4 sm:px-8">
      <div className="mx-auto max-w-3xl">
        <div
          className={cn(
            'w-full rounded-2xl border border-line-strong bg-raised shadow-lift transition-[border-color,box-shadow] duration-200',
            !disabled && 'focus-within:border-ember focus-within:shadow-float',
            disabled && 'cursor-not-allowed opacity-60'
          )}
        >
          <label htmlFor="chat-input" className="sr-only">Message</label>
          <textarea
            id="chat-input"
            ref={textareaRef}
            data-testid="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={disabled ? "You've used today's quota. Upgrade or come back tomorrow." : selectedMode === 'agent' ? 'Assign a workspace task or goal for Agent Studio…' : `Message ${selected?.name || 'GPTCraft'}…`}
            disabled={disabled || isGenerating}
            className="m-0 block max-h-52 w-full resize-none overflow-y-auto border-0 bg-transparent px-4 pt-4 pb-2 text-[0.95rem] leading-relaxed text-ink outline-none placeholder:text-ink-3 focus:ring-0 focus-visible:outline-none"
            rows={1}
            style={{ minHeight: '52px' }}
          />

          <div className="flex items-center justify-between gap-2 px-2.5 pb-2.5">
            <div className="flex min-w-0 items-center gap-1">
              {/* Model selector */}
              <div className="relative" ref={menuRef}>
                <button
                  type="button"
                  data-testid="model-selector-button"
                  aria-haspopup="listbox"
                  aria-expanded={modelMenuOpen}
                  onClick={() => setModelMenuOpen(!modelMenuOpen)}
                  className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-ink-2 transition-colors hover:bg-sunken hover:text-ink"
                >
                  <span className="text-ember">{getModelIcon(selected?.id || '', 14)}</span>
                  <span className="max-w-[9rem] truncate">{selected?.name || 'Model'}</span>
                  <ChevronDown size={12} className={cn('text-ink-3 transition-transform', modelMenuOpen && 'rotate-180')} />
                </button>

                {modelMenuOpen && (
                  <div className="absolute bottom-full left-0 z-50 mb-2 w-72 animate-in overflow-hidden rounded-xl border border-line bg-raised p-1.5 shadow-float" role="listbox">
                    <div className="px-2.5 pt-1.5 pb-2 text-xs font-medium text-ink-3">Model</div>
                    {models.map((model) => {
                      const isLocked = planHierarchy[model.requiredPlan] > planHierarchy[userPlan];
                      const isSelected = model.id === selectedModel;

                      return (
                        <button
                          key={model.id}
                          type="button"
                          role="option"
                          aria-selected={isSelected}
                          data-testid={`model-option-${model.id}`}
                          disabled={isLocked}
                          onClick={() => {
                            setSelectedModel(model.id);
                            setModelMenuOpen(false);
                          }}
                          className={cn(
                            'flex w-full items-start gap-3 rounded-lg px-2.5 py-2 text-left transition-colors',
                            isSelected ? 'bg-ember-soft' : 'hover:bg-sunken',
                            isLocked && 'cursor-not-allowed opacity-55 hover:bg-transparent'
                          )}
                        >
                          <span className={cn('mt-0.5', isSelected ? 'text-ember' : 'text-ink-3')}>{getModelIcon(model.id, 15)}</span>
                          <div className="min-w-0 flex-1">
                            <div className="text-sm font-medium text-ink">{model.name}</div>
                            <div className="truncate text-xs text-ink-3">
                              {isLocked ? `Requires ${model.requiredPlan} plan` : model.description}
                            </div>
                          </div>
                          {isLocked ? (
                            <Lock size={13} className="mt-1 shrink-0 text-ink-3" />
                          ) : (
                            isSelected && <Check size={14} className="mt-1 shrink-0 text-ember" />
                          )}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              <span className="mx-1 h-4 w-px shrink-0 bg-line" aria-hidden />

              {/* Craft Mode */}
              <div className="flex items-center gap-0.5 overflow-x-auto" role="group" aria-label="Craft Mode">
                {craftModes.map((m) => {
                  const active = selectedMode === m.id;
                  const isAgent = m.id === 'agent';
                  return (
                    <button
                      key={m.id}
                      type="button"
                      data-testid={`craft-mode-${m.id}`}
                      aria-pressed={active}
                      title={m.label}
                      onClick={() => setSelectedMode(m.id)}
                      className={cn(
                        'flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors',
                        isAgent
                          ? active
                            ? 'border border-accent/40 bg-accent-soft text-accent shadow-lift'
                            : 'border border-accent/25 bg-sunken text-ink-2 hover:border-accent/45 hover:bg-accent-soft hover:text-accent'
                          : active
                            ? 'bg-ember-soft text-ember'
                            : 'text-ink-3 hover:bg-sunken hover:text-ink'
                      )}
                    >
                      {m.icon}
                      <span className={cn(!active && !isAgent && 'max-md:hidden')}>{m.label}</span>
                      {m.badge && (
                        <span
                          data-testid="agent-mode-badge"
                          className={cn(
                            'rounded px-1 py-px font-mono text-[9px] font-semibold uppercase tracking-wider',
                            active ? 'bg-accent text-on-accent' : 'bg-accent-soft text-accent'
                          )}
                        >
                          {m.badge}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {isGenerating ? (
              <button
                onClick={onStop}
                data-testid="stop-button"
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-ink text-canvas transition-transform active:scale-95"
                title="Stop generating"
                aria-label="Stop generating"
              >
                <Square size={12} className="fill-current" />
              </button>
            ) : (
              <button
                onClick={handleSend}
                data-testid="send-button"
                disabled={!input.trim() || disabled}
                className={cn(
                  'flex h-9 w-9 shrink-0 items-center justify-center rounded-full transition-[background-color,transform] active:scale-95',
                  input.trim() && !disabled
                    ? 'bg-ember text-on-ember hover:bg-ember-hover'
                    : 'cursor-not-allowed bg-sunken text-ink-3'
                )}
                title="Send message"
                aria-label="Send message"
              >
                <ArrowUp size={17} strokeWidth={2.25} />
              </button>
            )}
          </div>
        </div>

        <div className="mt-2 flex items-center justify-between px-1 text-[11px] text-ink-3 font-mono">
          <span>Enter to send · Shift + Enter for new line</span>
          {memoryEnabled ? (
            <span className="flex items-center gap-1.5 max-sm:hidden" data-testid="memory-active-indicator">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-ember" />
              <span>Memory & Personalization Active</span>
            </span>
          ) : (
            <span className="max-sm:hidden" data-testid="memory-paused-indicator">⚡ Groq LPU Engine</span>
          )}
        </div>
      </div>
    </div>
  );
};
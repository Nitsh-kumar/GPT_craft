import React, { useState, useRef, useEffect } from 'react';
import { Send, Square, ChevronDown, Lock, Cpu, Zap, Brain } from 'lucide-react';
import { cn } from '../../utils/cn';
import { Model, PlanType } from '../../types';

interface ChatInputProps {
  onSend: (message: string) => void;
  onStop: () => void;
  isGenerating: boolean;
  disabled?: boolean;
  models: Model[];
  selectedModel: string;
  setSelectedModel: (modelId: string) => void;
  userPlan: PlanType;
}

const planHierarchy: Record<PlanType, number> = { free: 0, super: 1, hyper: 2 };

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
  userPlan
}: ChatInputProps) => {
  const [input, setInput] = useState('');
  const [modelMenuOpen, setModelMenuOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

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

  // Close dropdown on outside click
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
    <div className="w-full pt-2 pb-4 px-4">
      <div className="max-w-3xl mx-auto">
        <div className={cn(
          "w-full rounded-2xl border border-zinc-700/60 bg-zinc-900/80 transition-all duration-200",
          !disabled && "focus-within:border-brand-cyan/40 focus-within:shadow-[0_0_20px_rgba(0,210,211,0.06)]",
          disabled && "opacity-50 cursor-not-allowed"
        )}>
          {/* Input row */}
          <div className="relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={disabled ? "Quota exhausted" : `Ask ${selected?.name || 'GPTCraft'}...`}
              disabled={disabled || isGenerating}
              className="m-0 w-full resize-none border-0 bg-transparent px-4 py-3.5 pr-14 focus:ring-0 focus-visible:ring-0 text-sm text-zinc-100 placeholder:text-zinc-500 max-h-48 overflow-y-auto leading-relaxed outline-none"
              rows={1}
              style={{ minHeight: '44px' }}
            />
            
            {/* Send button inline */}
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              {isGenerating ? (
                <button
                  onClick={onStop}
                  className="flex items-center justify-center h-8 w-8 rounded-lg bg-zinc-700 text-zinc-300 hover:bg-zinc-600 hover:text-white transition-all active:scale-95"
                  title="Stop"
                >
                  <Square size={14} className="fill-current" />
                </button>
              ) : (
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || disabled}
                  className={cn(
                    "flex items-center justify-center h-8 w-8 rounded-lg transition-all active:scale-95",
                    input.trim() && !disabled 
                      ? "bg-brand-cyan text-brand-dark hover:bg-white" 
                      : "bg-zinc-800 text-zinc-600 cursor-not-allowed"
                  )}
                  title="Send"
                >
                  <Send size={15} />
                </button>
              )}
            </div>
          </div>

          {/* Bottom toolbar */}
          <div className="flex items-center justify-between px-3 pb-2.5 pt-0">
            {/* Model selector */}
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setModelMenuOpen(!modelMenuOpen)}
                className="flex items-center gap-1.5 px-2 py-1 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60 transition-all text-xs font-medium"
              >
                <span className="text-brand-cyan">{getModelIcon(selected?.id || '', 13)}</span>
                <span>{selected?.name || 'Model'}</span>
                <ChevronDown size={11} className={cn("transition-transform", modelMenuOpen && "rotate-180")} />
              </button>

              {modelMenuOpen && (
                <div className="absolute left-0 bottom-full mb-2 w-64 rounded-xl bg-zinc-900 border border-zinc-700/60 shadow-2xl z-50 overflow-hidden">
                  <div className="p-1.5">
                    <div className="px-2.5 py-1.5">
                      <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-zinc-500">Select Model</span>
                    </div>
                    {models.map((model) => {
                      const isLocked = planHierarchy[model.requiredPlan] > planHierarchy[userPlan];
                      const isSelected = model.id === selectedModel;
                      
                      return (
                        <button
                          key={model.id}
                          disabled={isLocked}
                          onClick={() => {
                            setSelectedModel(model.id);
                            setModelMenuOpen(false);
                          }}
                          className={cn(
                            "flex items-center gap-2.5 w-full px-2.5 py-2 rounded-lg transition-all text-left text-sm",
                            isSelected ? "bg-brand-cyan/10 text-brand-cyan" : "text-zinc-300 hover:bg-zinc-800",
                            isLocked && "opacity-40 cursor-not-allowed"
                          )}
                        >
                          <span className={cn(isSelected ? "text-brand-cyan" : "text-zinc-500")}>
                            {getModelIcon(model.id, 14)}
                          </span>
                          <div className="flex-1 min-w-0">
                            <div className="font-semibold text-xs">{model.name}</div>
                            <div className="text-[10px] text-zinc-500 truncate">{model.description}</div>
                          </div>
                          {isLocked && <Lock size={11} className="text-zinc-500 shrink-0" />}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="mt-2 text-center text-[10px] text-zinc-600 uppercase tracking-widest">
          GPTCraft Premium AI • Intelligently Crafted
        </div>
      </div>
    </div>
  );
};

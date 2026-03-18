import React, { useState, useRef, useEffect } from 'react';
import { Model, PlanType } from '../../types';
import { ChevronDown, Lock, Cpu, Zap, Brain, Sparkles } from 'lucide-react';
import { cn } from '../../utils/cn';

interface ModelSelectorProps {
  models: Model[];
  selectedModel: string;
  onSelect: (modelId: string) => void;
  userPlan: PlanType;
  variant?: 'default' | 'compact';
}

const planHierarchy: Record<PlanType, number> = { free: 0, super: 1, hyper: 2 };

const getModelIcon = (modelId: string) => {
  if (modelId.includes('70b') || modelId.includes('opus')) return <Brain size={16} />;
  if (modelId.includes('8b') || modelId.includes('3.5')) return <Zap size={16} />;
  return <Cpu size={16} />;
};

export const ModelSelector = ({ models, selectedModel, onSelect, userPlan, variant = 'default' }: ModelSelectorProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const selected = models.find(m => m.id === selectedModel) || models[0];

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (models.length === 0) return null;

  const isCompact = variant === 'compact';

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex items-center gap-2 transition-all group",
          isCompact 
            ? "px-3 py-2 rounded-2xl hover:bg-white/10 dark:hover:bg-zinc-800/40" 
            : "glass-card px-4 py-2 rounded-2xl hover:bg-white/10 dark:hover:bg-zinc-800/50 border-zinc-200/50 dark:border-zinc-800/50"
        )}
      >
        <div className="text-brand-cyan group-hover:scale-110 transition-transform">
          {getModelIcon(selected.id)}
        </div>
        {isCompact ? (
          <span className="text-xs font-bold text-zinc-400 hidden sm:inline max-w-[80px] truncate">
            {selected.name}
          </span>
        ) : (
          <div className="flex flex-col items-start leading-tight">
            <span className="text-sm font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
              {selected.name}
            </span>
            <span className="text-[10px] font-medium text-zinc-500 uppercase tracking-wider">
              Groq powered
            </span>
          </div>
        )}
        <ChevronDown size={isCompact ? 12 : 14} className={cn("text-zinc-500 transition-transform duration-300", isOpen && "rotate-180")} />
      </button>

      {isOpen && (
        <div className={cn(
          "absolute mt-3 w-72 origin-top-left rounded-3xl shadow-2xl z-50 overflow-hidden animate-in border border-zinc-700/50",
          "bg-zinc-900",
          isCompact ? "left-0 bottom-full mb-4 mt-0" : "left-0"
        )}>
          <div className="p-2 flex flex-col gap-1">
            <div className="px-3 py-2">
              <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-zinc-500/80">
                Select AI Model
              </span>
            </div>
            {models.map((model) => {
              const isLocked = planHierarchy[model.requiredPlan] > planHierarchy[userPlan];
              const isSelected = model.id === selectedModel;
              
              return (
                <button
                  key={model.id}
                  disabled={isLocked}
                  onClick={() => {
                    onSelect(model.id);
                    setIsOpen(false);
                  }}
                  className={cn(
                    "flex items-start gap-3 w-full p-3 rounded-2xl transition-all text-left group",
                    isSelected ? "bg-brand-cyan/15 border border-brand-cyan/30" : "hover:bg-zinc-800 border border-transparent",
                    isLocked && "opacity-50 grayscale"
                  )}
                >
                  <div className={cn(
                    "mt-1 p-2 rounded-xl transition-colors",
                    isSelected ? "bg-brand-cyan text-brand-dark" : "bg-zinc-100 dark:bg-zinc-800 text-zinc-500 group-hover:text-brand-cyan"
                  )}>
                    {getModelIcon(model.id)}
                  </div>
                  <div className="flex-1 flex flex-col leading-snug">
                    <div className="flex items-center justify-between">
                      <span className={cn("text-sm font-bold", isSelected ? "text-brand-cyan" : "text-zinc-900 dark:text-zinc-100")}>
                        {model.name}
                      </span>
                      {isLocked && <Lock size={12} className="text-zinc-500" />}
                    </div>
                    <span className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5 line-clamp-1">
                      {model.description}
                    </span>
                    {isLocked && (
                      <span className="text-[10px] font-bold text-cyan-600 dark:text-cyan-400 mt-1 uppercase">
                        Requires {model.requiredPlan}
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

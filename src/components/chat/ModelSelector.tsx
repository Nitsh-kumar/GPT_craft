import React from 'react';
import { Model, PlanType } from '../../types';
import { ChevronDown } from 'lucide-react';

interface ModelSelectorProps {
  models: Model[];
  selectedModel: string;
  onSelect: (modelId: string) => void;
  userPlan: PlanType;
}

const planHierarchy: Record<PlanType, number> = { free: 0, super: 1, hyper: 2 };

export const ModelSelector = ({ models, selectedModel, onSelect, userPlan }: ModelSelectorProps) => {
  if (models.length === 0) return null;

  return (
    <div className="relative inline-block text-left">
      <select
        value={selectedModel}
        onChange={(e) => onSelect(e.target.value)}
        className="appearance-none bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 py-2 pl-4 pr-10 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 sm:text-sm font-medium"
      >
        {models.map((model) => {
          const isLocked = planHierarchy[model.requiredPlan] > planHierarchy[userPlan];
          return (
            <option key={model.id} value={model.id} disabled={isLocked}>
              {model.name} {isLocked ? `(Requires ${model.requiredPlan.toUpperCase()})` : ''}
            </option>
          );
        })}
      </select>
      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-zinc-500">
        <ChevronDown size={16} />
      </div>
    </div>
  );
};

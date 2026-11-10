import React from 'react';
import { Monitor, Moon, Sun } from 'lucide-react';
import { ThemePreference, useTheme } from '../../context/ThemeContext';
import { cn } from '../../utils/cn';

const OPTIONS: { id: ThemePreference; label: string; icon: React.ReactNode }[] = [
  { id: 'light', label: 'Light', icon: <Sun size={14} strokeWidth={2} /> },
  { id: 'dark', label: 'Dark', icon: <Moon size={14} strokeWidth={2} /> },
  { id: 'system', label: 'System', icon: <Monitor size={14} strokeWidth={2} /> },
];

/** Segmented Light / Dark / System control. */
export const ThemeSwitcher = ({ className, showLabels = false }: { className?: string; showLabels?: boolean }) => {
  const { preference, setTheme } = useTheme();

  return (
    <div
      role="radiogroup"
      aria-label="Colour theme"
      data-testid="theme-switcher"
      className={cn('inline-flex items-center gap-0.5 rounded-full border border-line bg-sunken p-0.5', className)}
    >
      {OPTIONS.map((o) => {
        const active = preference === o.id;
        return (
          <button
            key={o.id}
            type="button"
            role="radio"
            aria-checked={active}
            aria-label={`${o.label} theme`}
            title={`${o.label} theme`}
            data-testid={`theme-${o.id}`}
            onClick={(e) => setTheme(o.id, { x: e.clientX, y: e.clientY })}
            className={cn(
              'flex h-7 items-center justify-center gap-1.5 rounded-full text-xs font-medium transition-colors duration-200',
              showLabels ? 'flex-1 px-2.5' : 'w-8',
              active ? 'bg-raised text-ink shadow-lift' : 'text-ink-3 hover:text-ink'
            )}
          >
            {o.icon}
            {showLabels && <span>{o.label}</span>}
          </button>
        );
      })}
    </div>
  );
};

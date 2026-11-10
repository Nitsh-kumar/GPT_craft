import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';

type Theme = 'light' | 'dark';
export type ThemePreference = Theme | 'system';

interface ThemeContextType {
  /** The resolved theme currently applied to the document. */
  theme: Theme;
  /** What the user picked: light, dark, or follow the OS. */
  preference: ThemePreference;
  toggleTheme: (origin?: { x: number; y: number }) => void;
  setTheme: (theme: ThemePreference, origin?: { x: number; y: number }) => void;
}

const STORAGE_KEY = 'gptcraft-theme';
const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const systemTheme = (): Theme =>
  window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';

const readPreference = (): ThemePreference => {
  const saved = localStorage.getItem(STORAGE_KEY);
  return saved === 'light' || saved === 'dark' || saved === 'system' ? saved : 'system';
};

const applyClass = (theme: Theme) => {
  document.documentElement.classList.toggle('dark', theme === 'dark');
};

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [preference, setPreference] = useState<ThemePreference>(readPreference);
  const [system, setSystem] = useState<Theme>(systemTheme);
  const theme: Theme = preference === 'system' ? system : preference;

  // Follow OS changes while in "system" mode
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => setSystem(mq.matches ? 'dark' : 'light');
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, []);

  useEffect(() => {
    applyClass(theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, preference);
  }, [preference]);

  const setTheme = useCallback(
    (next: ThemePreference, origin?: { x: number; y: number }) => {
      const nextResolved: Theme = next === 'system' ? systemTheme() : next;
      const doc = document as Document & { startViewTransition?: (cb: () => void) => unknown };
      const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const changes = nextResolved !== (document.documentElement.classList.contains('dark') ? 'dark' : 'light');

      if (!changes || reduced || !doc.startViewTransition) {
        setPreference(next);
        return;
      }

      // Ink-spread reveal from the control that was pressed
      const x = origin?.x ?? window.innerWidth / 2;
      const y = origin?.y ?? window.innerHeight / 2;
      const r = Math.hypot(Math.max(x, window.innerWidth - x), Math.max(y, window.innerHeight - y));
      const rootStyle = document.documentElement.style;
      rootStyle.setProperty('--reveal-x', `${x}px`);
      rootStyle.setProperty('--reveal-y', `${y}px`);
      rootStyle.setProperty('--reveal-r', `${r}px`);
      doc.startViewTransition(() => {
        applyClass(nextResolved);
        setPreference(next);
      });
    },
    []
  );

  const toggleTheme = useCallback(
    (origin?: { x: number; y: number }) => setTheme(theme === 'dark' ? 'light' : 'dark', origin),
    [theme, setTheme]
  );

  return (
    <ThemeContext.Provider value={{ theme, preference, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

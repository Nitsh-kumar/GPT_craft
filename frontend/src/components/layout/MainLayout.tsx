import React, { ReactNode, useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { LogOut, Plus, Trash2, Menu, X, ArrowUpRight, Brain } from 'lucide-react';
import { Link } from 'react-router-dom';
import { ThemeSwitcher } from './ThemeSwitcher';
import { PersonalizationModal } from '../chat/PersonalizationModal';
import { cn } from '../../utils/cn';

interface MainLayoutProps {
  children: ReactNode;
  onNewChat?: () => void;
  onClearChat?: () => void;
  conversations?: any[];
  currentConversationId?: string | null;
  onSelectConversation?: (id: string | null) => void;
  onDeleteConversation?: (id: string) => void;
}

export const MainLayout = ({
  children,
  onNewChat,
  conversations = [],
  currentConversationId = null,
  onSelectConversation,
  onDeleteConversation,
}: MainLayoutProps) => {
  const { user, logout } = useAuth();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [personalizationOpen, setPersonalizationOpen] = useState(false);

  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setDrawerOpen(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [drawerOpen]);

  const displayName = user?.name || user?.email?.split('@')[0] || 'You';
  const initial = displayName.charAt(0).toUpperCase();

  const sidebar = (
    <>
      <div className="flex items-center justify-between px-5 pt-5 pb-4">
        <Link to="/chat" className="flex items-center gap-2.5 rounded-lg" onClick={() => setDrawerOpen(false)}>
          <img src="/craft_logo.png" alt="" className="h-7 w-7 object-contain" />
          <span className="font-display text-[1.35rem] font-bold leading-none tracking-tight text-ink">GPTCraft</span>
        </Link>
        <button
          type="button"
          onClick={() => setDrawerOpen(false)}
          className="rounded-lg p-1.5 text-ink-3 hover:bg-sunken hover:text-ink md:hidden"
          aria-label="Close menu"
        >
          <X size={18} />
        </button>
      </div>

      <div className="px-3 pb-3">
        <button
          onClick={() => {
            onNewChat?.();
            setDrawerOpen(false);
          }}
          data-testid="new-conversation-button"
          className="flex w-full items-center gap-2.5 rounded-xl border border-line bg-raised px-3.5 py-2.5 text-sm font-medium text-ink shadow-lift transition-colors hover:border-line-strong active:translate-y-px"
        >
          <span className="flex h-5 w-5 items-center justify-center rounded-md bg-ember text-on-ember">
            <Plus size={14} strokeWidth={2.5} />
          </span>
          New conversation
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 pb-4" aria-label="Conversation history">
        <h2 className="px-2.5 pt-3 pb-2 text-xs font-medium text-ink-3">Recent</h2>

        {conversations.length === 0 && (
          <p className="px-2.5 py-2 text-sm leading-relaxed text-ink-3">
            Your conversations will appear here.
          </p>
        )}

        <ul className="space-y-px">
          {conversations.map((conv) => {
            const isActive = currentConversationId === conv.id.toString();
            return (
              <li key={conv.id} className="group/h relative flex items-center">
                <button
                  onClick={() => {
                    onSelectConversation?.(conv.id.toString());
                    setDrawerOpen(false);
                  }}
                  data-testid={`conversation-item-${conv.id}`}
                  aria-current={isActive ? 'page' : undefined}
                  className={cn(
                    'w-full truncate rounded-lg py-2 pr-9 pl-2.5 text-left text-sm transition-colors',
                    isActive
                      ? 'bg-raised font-medium text-ink shadow-lift'
                      : 'text-ink-2 hover:bg-sunken hover:text-ink'
                  )}
                >
                  {conv.title}
                </button>
                {onDeleteConversation && (
                  <button
                    type="button"
                    data-testid={`delete-conversation-${conv.id}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteConversation(conv.id.toString());
                    }}
                    className="absolute right-1.5 rounded-md p-1.5 text-ink-3 opacity-0 transition-opacity hover:bg-danger-soft hover:text-danger focus-visible:opacity-100 group-hover/h:opacity-100"
                    title="Delete conversation"
                    aria-label={`Delete ${conv.title}`}
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="space-y-3 border-t border-line p-3">
        <button
          type="button"
          onClick={() => {
            setPersonalizationOpen(true);
            setDrawerOpen(false);
          }}
          data-testid="personalization-button"
          className="flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 text-xs font-medium text-ink-2 transition-colors hover:bg-sunken hover:text-ink"
        >
          <Brain size={15} className="text-ember" />
          <span>Personalization & Memory</span>
        </button>

        <div className="flex items-center justify-between px-1">
          <span className="text-xs font-medium text-ink-3">Appearance</span>
          <ThemeSwitcher />
        </div>

        <div className="flex items-center gap-3 rounded-xl p-2">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-ink font-display text-sm font-semibold text-canvas">
            {initial}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium leading-tight text-ink" data-testid="sidebar-user-name">
              {displayName}
            </div>
            <Link
              to="/subscription"
              data-testid="manage-subscription-link"
              className="group/plan mt-0.5 inline-flex items-center gap-1 text-xs text-ink-3 hover:text-ember"
              title="Manage subscription"
            >
              <span className="capitalize" data-testid="sidebar-user-plan">{user?.plan || 'free'}</span>
              <span>plan</span>
              <ArrowUpRight size={12} className="opacity-70" />
            </Link>
          </div>
          <button
            type="button"
            onClick={() => {
              setPersonalizationOpen(true);
              setDrawerOpen(false);
            }}
            data-testid="user-personalization-button"
            className="rounded-lg p-2 text-ink-3 transition-colors hover:bg-sunken hover:text-ember"
            title="Personalization & Memory"
            aria-label="Personalization & Memory"
          >
            <Brain size={17} />
          </button>
          <button
            onClick={logout}
            data-testid="logout-button"
            className="rounded-lg p-2 text-ink-3 transition-colors hover:bg-danger-soft hover:text-danger"
            title="Log out"
            aria-label="Log out"
          >
            <LogOut size={17} />
          </button>
        </div>
      </div>
    </>
  );

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-canvas font-sans text-ink">
      {/* Desktop sidebar */}
      <aside className="relative z-30 hidden w-[17.5rem] shrink-0 flex-col border-r border-line bg-surface md:flex">
        {sidebar}
      </aside>

      {/* Mobile drawer */}
      <div
        className={cn(
          'fixed inset-0 z-50 md:hidden',
          drawerOpen ? 'pointer-events-auto' : 'pointer-events-none'
        )}
        aria-hidden={!drawerOpen}
      >
        <div
          className={cn('absolute inset-0 bg-black/40 transition-opacity duration-300', drawerOpen ? 'opacity-100' : 'opacity-0')}
          onClick={() => setDrawerOpen(false)}
        />
        <aside
          className={cn(
            'absolute inset-y-0 left-0 flex w-[85%] max-w-[19rem] flex-col bg-surface shadow-float transition-transform duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]',
            drawerOpen ? 'translate-x-0' : '-translate-x-full'
          )}
        >
          {sidebar}
        </aside>
      </div>

      <main className="relative flex min-w-0 flex-1 flex-col">
        {/* Mobile header */}
        <header className="sticky top-0 z-40 flex items-center justify-between border-b border-line bg-canvas px-3 py-2.5 md:hidden">
          <button
            type="button"
            onClick={() => setDrawerOpen(true)}
            className="rounded-lg p-2 text-ink-2 hover:bg-sunken"
            aria-label="Open menu"
          >
            <Menu size={20} />
          </button>
          <Link to="/chat" className="flex items-center gap-2">
            <img src="/craft_logo.png" alt="" className="h-6 w-6 object-contain" />
            <span className="font-display text-lg font-bold tracking-tight text-ink">GPTCraft</span>
          </Link>
          <button onClick={onNewChat} className="rounded-lg p-2 text-ink-2 hover:bg-sunken" title="New chat" aria-label="New chat">
            <Plus size={20} />
          </button>
        </header>

        <div className="relative flex flex-1 flex-col overflow-hidden">{children}</div>
      </main>

      <PersonalizationModal
        isOpen={personalizationOpen}
        onClose={() => setPersonalizationOpen(false)}
      />
    </div>
  );
};

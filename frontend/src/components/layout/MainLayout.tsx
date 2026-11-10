import React, { ReactNode } from 'react';
import { useAuth } from '../../context/AuthContext';
import { LogOut, User as UserIcon, MessageSquare, Plus, ShieldCheck, Trash2 } from 'lucide-react';
import { Link } from 'react-router-dom';

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

  return (
    <div className="flex h-screen w-full bg-zinc-50 dark:bg-brand-dark text-zinc-900 dark:text-zinc-100 overflow-hidden font-sans">
      {/* Sidebar */}
      <aside className="w-72 border-r border-zinc-200/50 dark:border-zinc-800/50 glass flex flex-col hidden md:flex z-30 relative">
        <div className="absolute top-0 -left-20 w-40 h-screen bg-brand-cyan/5 blur-[100px] pointer-events-none" />
        
        <Link to="/chat" className="p-6 flex items-center gap-3 group">
          <div className="p-2 rounded-xl bg-brand-cyan/10 group-hover:bg-brand-cyan/20 transition-colors">
            <img src="/craft_logo.png" alt="GPTCraft" className="w-7 h-7 object-contain group-hover:scale-110 transition-transform" />
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-xl tracking-tight leading-none text-glow-cyan">GPTCraft</span>
            <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 mt-1">Version 2.0</span>
          </div>
        </Link>
        
        <div className="p-6">
          <button 
            onClick={onNewChat}
            data-testid="new-conversation-button"
            className="w-full flex items-center justify-center gap-2 bg-brand-cyan text-brand-dark px-4 py-3 rounded-2xl hover:bg-white transition-all font-bold text-sm shadow-xl shadow-brand-cyan/10 active:scale-95"
          >
            <Plus size={18} />
            New Conversation
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto px-4 pb-4 space-y-2">
          <div className="px-4 py-2">
            <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-[0.2em]">Recent History</span>
          </div>
          
          {conversations.length === 0 && (
            <div className="px-4 py-2 text-sm text-zinc-500">No recent conversations</div>
          )}
          
          {conversations.map((conv) => {
            const isActive = currentConversationId === conv.id.toString();
            return (
              <div key={conv.id} className="relative group/h flex items-center">
                <button 
                  onClick={() => onSelectConversation?.(conv.id.toString())}
                  data-testid={`conversation-item-${conv.id}`}
                  className={`w-full text-left px-4 py-3 pr-10 rounded-2xl border flex items-center gap-3 text-sm font-medium transition-colors ${
                    isActive 
                      ? 'glass-card border-brand-cyan/30 text-brand-cyan' 
                      : 'border-transparent text-zinc-400 hover:bg-white/5 hover:text-zinc-200'
                  }`}
                >
                  <MessageSquare size={16} className="shrink-0" />
                  <span className="truncate flex-1">{conv.title}</span>
                </button>
                {onDeleteConversation && (
                  <button
                    type="button"
                    data-testid={`delete-conversation-${conv.id}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteConversation(conv.id.toString());
                    }}
                    className="absolute right-2 p-1.5 text-zinc-500 hover:text-red-400 rounded-lg opacity-0 group-hover/h:opacity-100 transition-opacity"
                    title="Delete conversation"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            );
          })}
        </div>

        <div className="p-6 border-t border-zinc-200/50 dark:border-zinc-800/50">
          <div className="flex items-center justify-between p-3 rounded-2xl glass-card">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-10 h-10 rounded-xl bg-gradient-cyan flex items-center justify-center text-brand-dark shrink-0 shadow-lg">
                <UserIcon size={20} />
              </div>
              <div className="flex flex-col min-w-0">
                <div className="text-sm font-bold truncate leading-tight" data-testid="sidebar-user-name">
                  {user?.name || user?.email?.split('@')[0]}
                </div>
                <Link 
                  to="/subscription" 
                  data-testid="manage-subscription-link"
                  className="flex items-center gap-1.5 mt-0.5 group/plan cursor-pointer"
                  title="Manage subscription"
                >
                  <div className="h-1.5 w-1.5 rounded-full bg-brand-cyan animate-pulse" />
                  <span className="text-[10px] font-black uppercase tracking-widest text-brand-cyan group-hover/plan:text-white transition-colors" data-testid="sidebar-user-plan">
                    {user?.plan || 'Free'}
                  </span>
                  <ShieldCheck size={10} className="text-brand-cyan/50 group-hover/plan:text-white transition-colors" />
                </Link>
              </div>
            </div>
            <button 
              onClick={logout}
              data-testid="logout-button"
              className="p-2 text-zinc-500 hover:text-red-500 hover:bg-red-500/10 rounded-xl transition-all"
              title="Logout"
            >
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 relative">
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-brand-cyan/5 blur-[120px] pointer-events-none" />
        
        {/* Mobile Header */}
        <header className="md:hidden p-4 border-b border-zinc-200/50 dark:border-zinc-800/50 flex items-center justify-between glass sticky top-0 z-40">
          <Link to="/chat" className="flex items-center gap-2">
            <img src="/craft_logo.png" alt="GPTCraft" className="w-8 h-8 object-contain" />
            <span className="font-bold text-xl tracking-tight text-glow-cyan">GPTCraft</span>
          </Link>
          <div className="flex items-center gap-2">
            <button onClick={onNewChat} className="p-2.5 rounded-xl bg-brand-cyan/10 text-brand-cyan" title="New Chat">
              <Plus size={20} />
            </button>
            <button onClick={logout} className="p-2.5 rounded-xl bg-zinc-100 dark:bg-zinc-800 text-zinc-500" title="Logout">
              <LogOut size={20} />
            </button>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-hidden relative flex flex-col">
          {children}
        </div>
      </main>
    </div>
  );
};

import React, { ReactNode } from 'react';
import { useAuth } from '../../context/AuthContext';
import { LogOut, User as UserIcon, MessageSquare, Plus } from 'lucide-react';
import { Link } from 'react-router-dom';
import { cn } from '../../utils/cn';

interface MainLayoutProps {
  children: ReactNode;
  onNewChat?: () => void;
}

export const MainLayout = ({ children, onNewChat }: MainLayoutProps) => {
  const { user, logout } = useAuth();

  return (
    <div className="flex h-screen w-full bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100">
      {/* Sidebar */}
      <aside className="w-64 border-r border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex flex-col hidden md:flex">
        <Link to="/chat" className="p-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center gap-2 hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors">
          <img src="/craft_logo.png" alt="GPTCraft Logo" className="w-8 h-8 object-contain" />
          <span className="font-semibold text-lg tracking-tight">GPTCraft</span>
        </Link>
        
        <div className="p-4">
          <button 
            onClick={onNewChat}
            className="w-full flex items-center gap-2 bg-cyan-600 text-white px-4 py-2.5 rounded-lg hover:bg-cyan-700 transition-colors font-medium text-sm shadow-sm"
          >
            <Plus size={18} />
            New Chat
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto px-4 pb-4">
          <div className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">
            Recent Chats
          </div>
          <button className="w-full text-left px-3 py-2 rounded-md bg-zinc-100 dark:bg-zinc-800 flex items-center gap-2 text-sm">
            <MessageSquare size={16} />
            <span className="truncate">Current Conversation</span>
          </button>
        </div>

        <div className="p-4 border-t border-zinc-200 dark:border-zinc-800">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-zinc-200 dark:bg-zinc-700 flex items-center justify-center">
                <UserIcon size={16} />
              </div>
              <div className="flex flex-col">
                <div className="text-sm truncate max-w-[120px] leading-tight">
                  {user?.name || user?.email}
                </div>
                <div className="text-[10px] font-bold uppercase tracking-wider text-cyan-600 dark:text-cyan-400 mt-0.5">
                  {user?.plan || 'Free'} Plan
                </div>
              </div>
            </div>
            <button 
              onClick={logout}
              className="p-2 text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors"
              title="Logout"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Mobile Header */}
        <header className="md:hidden p-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between bg-white dark:bg-zinc-900">
          <Link to="/chat" className="flex items-center gap-2">
            <img src="/craft_logo.png" alt="GPTCraft Logo" className="w-8 h-8 object-contain" />
            <span className="font-semibold text-lg tracking-tight">GPTCraft</span>
          </Link>
          <div className="flex items-center gap-1">
            <button onClick={onNewChat} className="p-2 text-zinc-600 dark:text-zinc-300" title="New Chat">
              <Plus size={20} />
            </button>
            <button onClick={logout} className="p-2 text-zinc-600 dark:text-zinc-300" title="Logout">
              <LogOut size={20} />
            </button>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-hidden relative">
          {children}
        </div>
      </main>
    </div>
  );
};

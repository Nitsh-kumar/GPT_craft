import React, { useState, useEffect } from 'react';
import { X, Brain, Sliders, Trash2, Plus, Check, Loader2, Sparkles, AlertCircle } from 'lucide-react';
import { memoryService } from '../../services/memoryService';
import { UserMemoryItem, MemoryCategory } from '../../types';
import { cn } from '../../utils/cn';

interface PersonalizationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onPreferencesUpdated?: () => void;
}

const getErrorMessage = (err: unknown, fallback: string): string => {
  if (err instanceof Error && err.message) {
    return err.message;
  }
  return fallback;
};

export const PersonalizationModal: React.FC<PersonalizationModalProps> = ({
  isOpen,
  onClose,
  onPreferencesUpdated,
}) => {
  const [activeTab, setActiveTab] = useState<'instructions' | 'memories'>('instructions');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Custom Instructions state
  const [profileText, setProfileText] = useState('');
  const [styleText, setStyleText] = useState('');
  const [memoryEnabled, setMemoryEnabled] = useState(true);

  // Memories state
  const [memories, setMemories] = useState<UserMemoryItem[]>([]);
  const [newMemoryContent, setNewMemoryContent] = useState('');
  const [newMemoryCategory, setNewMemoryCategory] = useState<MemoryCategory>('general');
  const [addingMemory, setAddingMemory] = useState(false);

  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Load preferences and memories when modal opens
  useEffect(() => {
    if (!isOpen) return;
    loadData();
  }, [isOpen]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [prefs, memList] = await Promise.all([
        memoryService.getPreferences(),
        memoryService.getMemories(),
      ]);
      setProfileText(prefs.customInstructionsProfile || '');
      setStyleText(prefs.customInstructionsStyle || '');
      setMemoryEnabled(prefs.memoryEnabled ?? true);
      setMemories(memList.memories || []);
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to load personalization data'));
    } finally {
      setLoading(false);
    }
  };

  const handleSaveInstructions = async () => {
    setSaving(true);
    setError(null);
    setSaveSuccess(false);
    try {
      await memoryService.updatePreferences({
        customInstructionsProfile: profileText,
        customInstructionsStyle: styleText,
        memoryEnabled: memoryEnabled,
      });
      setSaveSuccess(true);
      onPreferencesUpdated?.();
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to save custom instructions'));
    } finally {
      setSaving(false);
    }
  };

  const handleToggleMemory = async () => {
    const updated = !memoryEnabled;
    setMemoryEnabled(updated);
    try {
      await memoryService.updatePreferences({ memoryEnabled: updated });
      onPreferencesUpdated?.();
    } catch (err: unknown) {
      setMemoryEnabled(!updated);
      setError(getErrorMessage(err, 'Failed to update memory setting'));
    }
  };

  const handleAddMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMemoryContent.trim()) return;

    setAddingMemory(true);
    setError(null);
    try {
      const item = await memoryService.addMemory(newMemoryContent.trim(), newMemoryCategory);
      setMemories((prev) => [item, ...prev]);
      setNewMemoryContent('');
      onPreferencesUpdated?.();
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to add memory'));
    } finally {
      setAddingMemory(false);
    }
  };

  const handleDeleteMemory = async (id: number) => {
    try {
      await memoryService.deleteMemory(id);
      setMemories((prev) => prev.filter((m) => m.id !== id));
      onPreferencesUpdated?.();
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to delete memory'));
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm('Are you sure you want to clear all remembered facts? This cannot be undone.')) {
      return;
    }
    try {
      await memoryService.clearAllMemories();
      setMemories([]);
      onPreferencesUpdated?.();
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to clear memories'));
    }
  };

  const addPreset = (target: 'profile' | 'style', text: string) => {
    if (target === 'profile') {
      setProfileText((prev) => (prev ? `${prev.trim()}, ${text}` : text));
    } else {
      setStyleText((prev) => (prev ? `${prev.trim()}, ${text}` : text));
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="personalization-modal-title">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-ink/40 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal Dialog */}
      <div className="relative flex max-h-[90vh] w-full max-w-2xl flex-col rounded-2xl border border-line bg-surface shadow-float">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-line px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-ember-soft text-ember">
              <Brain size={20} />
            </div>
            <div>
              <h2 id="personalization-modal-title" className="font-display text-lg font-bold text-ink">Personalization & Memory</h2>
              <p className="text-xs text-ink-3">Customize how GPTCraft responds and manage what it knows</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-ink-3 transition-colors hover:bg-sunken hover:text-ink"
            aria-label="Close dialog"
          >
            <X size={18} />
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-line px-6 pt-2">
          <button
            onClick={() => setActiveTab('instructions')}
            data-testid="tab-instructions"
            className={cn(
              'flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors',
              activeTab === 'instructions'
                ? 'border-ember text-ember'
                : 'border-transparent text-ink-3 hover:text-ink'
            )}
          >
            <Sliders size={16} />
            Custom Instructions
          </button>
          <button
            onClick={() => setActiveTab('memories')}
            data-testid="tab-memories"
            className={cn(
              'flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors',
              activeTab === 'memories'
                ? 'border-ember text-ember'
                : 'border-transparent text-ink-3 hover:text-ink'
            )}
          >
            <Sparkles size={16} />
            Remembered Facts ({memories.length})
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {error && (
            <div className="mb-4 flex items-center gap-2.5 rounded-xl border border-danger/20 bg-danger-soft p-3 text-sm text-danger">
              <AlertCircle size={16} className="shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {loading ? (
            <div className="flex h-48 items-center justify-center">
              <Loader2 size={24} className="animate-spin text-ember" />
            </div>
          ) : activeTab === 'instructions' ? (
            /* TAB 1: Custom Instructions */
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-semibold text-ink">
                  What would you like GPTCraft to know about you?
                </label>
                <p className="mt-0.5 text-xs text-ink-3">
                  Share your role, technical background, primary programming languages, or project context.
                </p>
                <textarea
                  rows={4}
                  data-testid="profile-instructions-input"
                  value={profileText}
                  onChange={(e) => setProfileText(e.target.value)}
                  placeholder="e.g., I am a Senior Full-Stack Engineer working with FastAPI, React 19, and PostgreSQL. I prefer clean modular architecture."
                  className="mt-2.5 w-full rounded-xl border border-line bg-canvas p-3 text-sm text-ink placeholder:text-ink-3 focus:border-ember focus:outline-none focus:ring-1 focus:ring-ember"
                />
                <div className="mt-2 flex flex-wrap gap-1.5">
                  <span className="self-center text-[11px] font-medium text-ink-3">Quick Presets:</span>
                  {['Senior Software Engineer', 'Python & React Stack', 'Fast-Paced Startup', 'Student / Learner'].map(
                    (preset) => (
                      <button
                        key={preset}
                        type="button"
                        onClick={() => addPreset('profile', preset)}
                        className="rounded-md border border-line bg-raised px-2 py-0.5 text-xs text-ink-2 hover:border-line-strong hover:text-ink"
                      >
                        + {preset}
                      </button>
                    )
                  )}
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold text-ink">
                  How would you like GPTCraft to respond?
                </label>
                <p className="mt-0.5 text-xs text-ink-3">
                  Specify tone, formatting preferences, code verbosity, and level of explanation.
                </p>
                <textarea
                  rows={4}
                  data-testid="style-instructions-input"
                  value={styleText}
                  onChange={(e) => setStyleText(e.target.value)}
                  placeholder="e.g., Be concise, direct, and code-first. Omit polite filler phrases. Always include clean TypeScript interfaces and handle edge cases."
                  className="mt-2.5 w-full rounded-xl border border-line bg-canvas p-3 text-sm text-ink placeholder:text-ink-3 focus:border-ember focus:outline-none focus:ring-1 focus:ring-ember"
                />
                <div className="mt-2 flex flex-wrap gap-1.5">
                  <span className="self-center text-[11px] font-medium text-ink-3">Quick Presets:</span>
                  {['Concise & Code-First', 'Explain Trade-offs & Architecture', 'Zero Pleasantries', 'Step-by-Step Pedagogical'].map(
                    (preset) => (
                      <button
                        key={preset}
                        type="button"
                        onClick={() => addPreset('style', preset)}
                        className="rounded-md border border-line bg-raised px-2 py-0.5 text-xs text-ink-2 hover:border-line-strong hover:text-ink"
                      >
                        + {preset}
                      </button>
                    )
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between border-t border-line pt-4">
                <div className="text-xs text-ink-3">
                  {saveSuccess && (
                    <span className="flex items-center gap-1.5 font-medium text-ember">
                      <Check size={14} /> Saved successfully!
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  data-testid="save-instructions-button"
                  onClick={handleSaveInstructions}
                  disabled={saving}
                  className="flex items-center gap-2 rounded-xl bg-ember px-5 py-2.5 text-sm font-medium text-on-ember shadow-lift transition-all hover:brightness-105 active:translate-y-px disabled:opacity-50"
                >
                  {saving ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
                  Save Instructions
                </button>
              </div>
            </div>
          ) : (
            /* TAB 2: Remembered Memories */
            <div className="space-y-5">
              {/* Master Memory Toggle */}
              <div className="flex items-center justify-between rounded-xl border border-line bg-canvas p-3.5">
                <div>
                  <div className="text-sm font-semibold text-ink">Persistent Memory Active</div>
                  <div className="text-xs text-ink-3">
                    Allow GPTCraft to recall facts and dynamically tailor responses across conversations
                  </div>
                </div>
                <button
                  type="button"
                  data-testid="memory-toggle-button"
                  onClick={handleToggleMemory}
                  aria-pressed={memoryEnabled}
                  className={cn(
                    'relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none',
                    memoryEnabled ? 'bg-ember' : 'bg-line-strong'
                  )}
                >
                  <span
                    className={cn(
                      'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-surface shadow-lift ring-0 transition duration-200 ease-in-out',
                      memoryEnabled ? 'translate-x-5' : 'translate-x-0'
                    )}
                  />
                </button>
              </div>

              {/* Add Memory Form */}
              <form onSubmit={handleAddMemory} className="flex gap-2">
                <input
                  type="text"
                  data-testid="new-memory-input"
                  value={newMemoryContent}
                  onChange={(e) => setNewMemoryContent(e.target.value)}
                  placeholder="Add a new memory (e.g., Prefers Tailwind v4 with Vite)"
                  className="flex-1 rounded-xl border border-line bg-canvas px-3 py-2 text-sm text-ink placeholder:text-ink-3 focus:border-ember focus:outline-none focus:ring-1 focus:ring-ember"
                />
                <select
                  value={newMemoryCategory}
                  onChange={(e) => setNewMemoryCategory(e.target.value as MemoryCategory)}
                  className="rounded-xl border border-line bg-canvas px-3 py-2 text-xs font-medium text-ink focus:border-ember focus:outline-none"
                >
                  <option value="general">General</option>
                  <option value="tech_stack">Tech Stack</option>
                  <option value="project">Project</option>
                  <option value="preference">Preference</option>
                </select>
                <button
                  type="submit"
                  data-testid="add-memory-button"
                  disabled={addingMemory || !newMemoryContent.trim()}
                  className="flex items-center gap-1.5 rounded-xl bg-ink px-4 py-2 text-sm font-medium text-canvas transition-colors hover:bg-ink-2 disabled:opacity-50"
                >
                  {addingMemory ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                  Add
                </button>
              </form>

              {/* Memory List */}
              <div className="space-y-2">
                {memories.length === 0 ? (
                  <div className="rounded-xl border border-line/60 bg-sunken/40 py-8 text-center">
                    <Sparkles size={24} className="mx-auto text-ink-3" />
                    <p className="mt-2 text-sm font-medium text-ink-2">
                      No memories saved yet
                    </p>
                    <p className="mt-0.5 text-xs text-ink-3">
                      Memories are learned automatically during conversation or added manually above.
                    </p>
                  </div>
                ) : (
                  memories.map((mem) => (
                    <div
                      key={mem.id}
                      className="group flex items-center justify-between rounded-xl border border-line bg-canvas p-3 transition-colors hover:border-line-strong"
                    >
                      <div className="min-w-0 flex-1 pr-3">
                        <div className="flex items-center gap-2">
                          <span
                            className={cn(
                              'rounded-md px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider',
                              mem.category === 'tech_stack' || mem.category === 'preference'
                                ? 'bg-ember-soft text-ember'
                                : 'bg-sunken text-ink-2'
                            )}
                          >
                            {mem.category.replace('_', ' ')}
                          </span>
                        </div>
                        <p className="mt-1 text-sm text-ink">{mem.content}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleDeleteMemory(mem.id)}
                        className="rounded-lg p-1.5 text-ink-3 opacity-0 transition-opacity hover:bg-danger-soft hover:text-danger focus-visible:opacity-100 group-hover:opacity-100"
                        title="Delete memory"
                        aria-label="Delete memory"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  ))
                )}
              </div>

              {/* Clear All Footer */}
              {memories.length > 0 && (
                <div className="flex justify-end border-t border-line pt-3">
                  <button
                    type="button"
                    onClick={handleClearAll}
                    className="flex items-center gap-1.5 text-xs font-medium text-danger hover:underline"
                  >
                    <Trash2 size={13} />
                    Clear all memories
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

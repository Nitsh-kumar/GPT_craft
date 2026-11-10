import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { PlanType } from '../types';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Check, Sparkles, Zap, Crown, Loader2 } from 'lucide-react';

interface PlanSpec {
  id: PlanType;
  title: string;
  price: string;
  period: string;
  description: string;
  features: string[];
  icon: React.ReactNode;
  highlight?: boolean;
}

const PLANS: PlanSpec[] = [
  {
    id: 'free',
    title: 'Free',
    price: '$0',
    period: '/mo',
    description: 'Essential AI reasoning for everyday exploration.',
    features: [
      'Llama 3 8B & Gemma 2 9B',
      '50 requests / day',
      '5,000 daily tokens',
      'All 4 Craft Modes',
    ],
    icon: <Sparkles className="text-zinc-400" size={20} />,
  },
  {
    id: 'super',
    title: 'Super',
    price: '$15',
    period: '/mo',
    description: 'High-throughput Mixture-of-Experts for builders.',
    features: [
      'Everything in Free',
      'Unlocks Mixtral 8x7B',
      '500 requests / day',
      '50,000 daily tokens',
    ],
    icon: <Zap className="text-brand-cyan" size={20} />,
    highlight: true,
  },
  {
    id: 'hyper',
    title: 'Hyper',
    price: '$39',
    period: '/mo',
    description: 'Maximum frontier intelligence and 70B scale.',
    features: [
      'Everything in Super',
      'Unlocks Llama 3.3 70B',
      '5,000 requests / day',
      '500,000 daily tokens',
    ],
    icon: <Crown className="text-amber-400" size={20} />,
  },
];

export const SubscriptionPage = () => {
  const { user, upgradePlan } = useAuth();
  const navigate = useNavigate();
  const [updatingPlan, setUpdatingPlan] = useState<PlanType | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const currentPlan: PlanType = (user?.plan as PlanType) || 'free';

  const handleSelectPlan = async (planId: PlanType) => {
    if (planId === currentPlan) return;
    setUpdatingPlan(planId);
    setStatusMsg(null);
    try {
      await upgradePlan(planId);
      setStatusMsg(`Successfully switched to the ${planId.toUpperCase()} tier!`);
    } catch (err: any) {
      setStatusMsg(err.message || 'Failed to update subscription plan.');
    } finally {
      setUpdatingPlan(null);
    }
  };

  return (
    <div className="min-h-screen bg-brand-dark text-zinc-100 p-6 md:p-12">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-10">
          <Link
            to="/chat"
            data-testid="back-to-chat-link"
            className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-brand-cyan transition-colors"
          >
            <ArrowLeft size={16} />
            Back to Chat
          </Link>
          <div className="text-xs uppercase tracking-widest text-zinc-500">
            Active Plan:{' '}
            <span className="text-brand-cyan font-bold" data-testid="active-plan-badge">
              {currentPlan.toUpperCase()}
            </span>
          </div>
        </div>

        <div className="text-center mb-12">
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-3">
            Manage Your GPTCraft Tier
          </h1>
          <p className="text-zinc-400 max-w-xl mx-auto text-sm">
            Unlock larger reasoning models (Mixtral 8x7B and Llama 3.3 70B) and expand your daily token and request quotas immediately.
          </p>
          {statusMsg && (
            <div
              data-testid="subscription-status-banner"
              className="mt-6 inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-cyan/15 border border-brand-cyan/40 text-brand-cyan text-sm font-medium"
            >
              <Check size={16} />
              <span>{statusMsg}</span>
              <button
                onClick={() => navigate('/chat')}
                className="ml-3 underline text-xs hover:text-white"
              >
                Return to Chat
              </button>
            </div>
          )}
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {PLANS.map((plan) => {
            const isCurrent = currentPlan === plan.id;
            const isBusy = updatingPlan === plan.id;

            return (
              <div
                key={plan.id}
                data-testid={`plan-card-${plan.id}`}
                className={`p-8 rounded-3xl border flex flex-col justify-between transition-all ${
                  plan.highlight
                    ? 'border-brand-cyan/60 bg-zinc-900/80 shadow-2xl shadow-brand-cyan/10'
                    : 'border-zinc-800 bg-zinc-900/40'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="p-2.5 rounded-xl bg-black/50 border border-zinc-800">
                      {plan.icon}
                    </div>
                    {isCurrent && (
                      <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                        Current Tier
                      </span>
                    )}
                  </div>
                  <h2 className="text-xl font-bold text-white mb-1">{plan.title}</h2>
                  <p className="text-xs text-zinc-400 mb-6">{plan.description}</p>
                  <div className="mb-6">
                    <span className="text-4xl font-bold text-white">{plan.price}</span>
                    <span className="text-zinc-500 text-sm">{plan.period}</span>
                  </div>
                  <ul className="space-y-3 mb-8">
                    {plan.features.map((feat, i) => (
                      <li key={i} className="flex items-center gap-2.5 text-xs text-zinc-300">
                        <Check size={15} className="text-brand-cyan shrink-0" />
                        <span>{feat}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <button
                  type="button"
                  data-testid={`select-plan-${plan.id}`}
                  disabled={isCurrent || updatingPlan !== null}
                  onClick={() => handleSelectPlan(plan.id)}
                  className={`w-full py-3 px-4 rounded-xl text-xs font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 ${
                    isCurrent
                      ? 'bg-zinc-800 text-zinc-500 cursor-default'
                      : 'bg-brand-cyan text-brand-dark hover:bg-white cursor-pointer'
                  }`}
                >
                  {isBusy ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : isCurrent ? (
                    'Active Plan'
                  ) : (
                    `Switch to ${plan.title}`
                  )}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

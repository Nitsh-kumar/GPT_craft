import React from 'react';
import { useAuth } from '../context/AuthContext';
import { PlanType } from '../types';
import { Link } from 'react-router-dom';
import { ArrowLeft, Check, Sparkles, Zap, Crown } from 'lucide-react';
import { ThemeSwitcher } from '../components/layout/ThemeSwitcher';

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
      'GPT-OSS 20B',
      '50 requests / day',
      '5,000 daily tokens',
      'All 4 Craft Modes',
    ],
    icon: <Sparkles className="text-ink-3" size={20} />,
  },
  {
    id: 'super',
    title: 'Super',
    price: '$15',
    period: '/mo',
    description: 'High-throughput Mixture-of-Experts for builders.',
    features: [
      'Everything in Free',
      'Higher daily allowance',
      '500 requests / day',
      '50,000 daily tokens',
    ],
    icon: <Zap className="text-ember" size={20} />,
    highlight: true,
  },
  {
    id: 'hyper',
    title: 'Hyper',
    price: '$39',
    period: '/mo',
    description: 'Larger models and a higher daily allowance.',
    features: [
      'Everything in Super',
      'Unlocks GPT-OSS 120B',
      '5,000 requests / day',
      '500,000 daily tokens',
    ],
    icon: <Crown className="text-warn" size={20} />,
  },
];

export const SubscriptionPage = () => {
  const { user } = useAuth();

  const currentPlan: PlanType = (user?.plan as PlanType) || 'free';


  return (
    <div className="min-h-screen bg-canvas text-ink p-6 md:p-12">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-10">
          <Link
            to="/chat"
            data-testid="back-to-chat-link"
            className="inline-flex items-center gap-2 text-sm text-ink-2 hover:text-ember transition-colors"
          >
            <ArrowLeft size={16} />
            Back to Chat
          </Link>
          <div className="flex items-center gap-4">
            <div className="text-xs uppercase tracking-widest text-ink-3">
            Active Plan:{' '}
            <span className="text-ember font-bold" data-testid="active-plan-badge">
              {currentPlan.toUpperCase()}
            </span>
            </div>
            <ThemeSwitcher />
          </div>
        </div>

        <div className="text-center mb-12">
          <h1 className="font-serif text-3xl md:text-4xl font-medium tracking-tight text-ink mb-3">
            Manage Your GPTCraft Tier
          </h1>
          <p className="text-ink-2 max-w-xl mx-auto text-sm">
            Paid plan changes are not available yet. Your current plan and usage allowance remain in place.
          </p>

        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {PLANS.map((plan) => {
            const isCurrent = currentPlan === plan.id;


            return (
              <div
                key={plan.id}
                data-testid={`plan-card-${plan.id}`}
                className={`p-8 rounded-3xl border flex flex-col justify-between transition-all ${
                  plan.highlight
                    ? 'border-ember bg-raised shadow-float'
                    : 'border-line bg-surface shadow-lift'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="p-2.5 rounded-xl bg-sunken border border-line">
                      {plan.icon}
                    </div>
                    {isCurrent && (
                      <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-sunken text-ok border border-line">
                        Current Tier
                      </span>
                    )}
                  </div>
                  <h2 className="font-serif text-xl font-medium tracking-tight text-ink mb-1">{plan.title}</h2>
                  <p className="text-xs text-ink-2 mb-6">{plan.description}</p>
                  <div className="mb-6">
                    <span className="text-4xl font-semibold text-ink">{plan.price}</span>
                    <span className="text-ink-3 text-sm">{plan.period}</span>
                  </div>
                  <ul className="space-y-3 mb-8">
                    {plan.features.map((feat, i) => (
                      <li key={i} className="flex items-center gap-2.5 text-xs text-ink-2">
                        <Check size={15} className="text-ember shrink-0" />
                        <span>{feat}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <button
                  type="button"
                  data-testid={`select-plan-${plan.id}`}
                  disabled={true}
                  className={`w-full py-3 px-4 rounded-xl text-xs font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 ${
                    isCurrent
                      ? 'bg-sunken text-ink-3 cursor-default'
                      : 'bg-ember text-on-ember hover:bg-ember-hover cursor-pointer'
                  }`}
                >
                  {isCurrent ? (
                    'Active Plan'
                  ) : (
                    'Coming soon'
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

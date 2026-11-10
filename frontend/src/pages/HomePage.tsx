import React, { Suspense } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'motion/react';
import { Bot, Zap, Shield, Sparkles, ArrowRight, MessageSquare, Code, Cpu, Check } from 'lucide-react';

const Spline = React.lazy(() => import('@splinetool/react-spline'));

const fadeIn = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5 }
};

const staggerContainer = {
  animate: {
    transition: {
      staggerChildren: 0.1
    }
  }
};

export const HomePage = () => {
  return (
    <div className="min-h-screen bg-black text-zinc-50 overflow-hidden font-sans selection:bg-cyan-500/30 relative">
      {/* Content Wrapper */}
      <div className="relative z-20">
        
        {/* Navigation */}
        <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/10 bg-black/50 backdrop-blur-md">
          <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <img src="/craft_logo.png" alt="GPTCraft Logo" className="w-8 object-contain" />
              <span className="font-semibold text-lg tracking-tight text-white ml-2">GPTCraft</span>
            </div>
            <div className="flex items-center gap-4">
              <Link 
                to="/login" 
                className="text-sm font-medium text-zinc-300 hover:text-white transition-colors"
              >
                Sign in
              </Link>
              <Link 
                to="/register" 
                className="text-sm font-medium bg-white text-black px-4 py-2 rounded-full hover:scale-105 transition-transform shadow-lg"
              >
                Get Started
              </Link>
            </div>
          </div>
        </nav>

        {/* Hero Section */}
        <main className="pt-32 pb-16 px-6 relative min-h-[90vh] flex items-center justify-center overflow-hidden">
          <div className="max-w-7xl mx-auto w-full relative z-10 grid lg:grid-cols-2 gap-12 items-center">
            
            {/* Left Content */}
            <motion.div
              initial="initial"
              animate="animate"
              variants={staggerContainer}
              className="flex flex-col items-center lg:items-start text-center lg:text-left space-y-8"
            >
              <motion.div variants={fadeIn} className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#00D2FF]/10 text-[#00D2FF] text-sm font-medium mb-4 border border-[#00D2FF]/20 backdrop-blur-sm">
                <Sparkles size={14} />
                <span>Powered by Advanced AI Models</span>
              </motion.div>
              
              <motion.h1 variants={fadeIn} className="text-5xl lg:text-6xl xl:text-7xl font-bold tracking-tight leading-[1.1] text-white">
                Your Intelligent <br />
                <span className="text-aurora">
                  Thinking Partner
                </span>
              </motion.h1>
              
              <motion.p variants={fadeIn} className="text-lg md:text-xl text-zinc-300 max-w-xl leading-relaxed">
                Experience the next generation of conversational AI. Write code, draft emails, analyze data, and solve complex problems with a custom-built interface.
              </motion.p>
              
              <motion.div variants={fadeIn} className="flex flex-col sm:flex-row items-center gap-4 pt-4 w-full lg:w-auto">
                <Link 
                  to="/register" 
                  className="w-full sm:w-auto flex items-center justify-center gap-2 bg-[#2E3192] text-white px-8 py-4 rounded-full text-lg font-medium hover:bg-[#1a1b52] hover:shadow-xl hover:shadow-[#00D2FF]/20 transition-all group border border-[#2E3192] hover:border-[#00D2FF]/50"
                >
                  Start Chatting Free
                  <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
                </Link>
                <Link 
                  to="/login" 
                  className="w-full sm:w-auto flex items-center justify-center gap-2 bg-white/5 text-white border border-white/10 px-8 py-4 rounded-full text-lg font-medium hover:bg-white/10 backdrop-blur-sm transition-all"
                >
                  Sign In
                </Link>
              </motion.div>
            </motion.div>

            {/* Right Content - Spline 3D Model */}
            <motion.div 
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 1, delay: 0.2 }}
              className="relative w-full h-[400px] lg:h-[600px] flex items-center justify-center overflow-hidden rounded-2xl"
            >
              {/* Fallback glow while loading */}
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[80%] h-[80%] bg-cyan-500/20 blur-[100px] rounded-full z-0 pointer-events-none"></div>
              
              <div className="absolute inset-0 z-10 flex items-center justify-center pointer-events-auto">
                <Suspense fallback={
                  <div className="flex flex-col items-center justify-center h-full w-full text-cyan-400/50">
                    <div className="w-10 h-10 border-4 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin mb-4"></div>
                    <span className="text-sm font-medium animate-pulse">Loading 3D Experience...</span>
                  </div>
                }>
                  <div className="w-full h-full flex items-center justify-center">
                    <Spline 
                      scene="https://prod.spline.design/hbSm8HI-9WHa1IUM/scene.splinecode" 
                      className="w-full h-full"
                    />
                  </div>
                </Suspense>
              </div>
            </motion.div>

          </div>
        </main>

        {/* Features Section */}
        <section className="py-24 bg-black/80 backdrop-blur-xl border-t border-white/10 relative z-20">
          <div className="max-w-7xl mx-auto px-6">
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-4xl font-bold mb-4 text-white">Built for Power Users</h2>
              <p className="text-zinc-400 max-w-2xl mx-auto">Everything you need to interact with advanced language models efficiently.</p>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
              <FeatureCard 
                icon={<Zap className="text-amber-400" />}
                title="Real-time Streaming"
                description="Watch responses appear instantly token-by-token. No waiting for long generations to finish."
              />
              <FeatureCard 
                icon={<Shield className="text-emerald-400" />}
                title="Secure & Private"
                description="Enterprise-grade security with JWT authentication. Your data and API keys stay protected."
              />
              <FeatureCard 
                icon={<Cpu className="text-cyan-400" />}
                title="Multiple Models"
                description="Switch seamlessly between GPT-4, Claude 3, and other leading models based on your needs."
              />
              <FeatureCard 
                icon={<MessageSquare className="text-blue-400" />}
                title="Context Aware"
                description="Maintains conversation history perfectly so the AI remembers what you discussed earlier."
              />
              <FeatureCard 
                icon={<Code className="text-pink-400" />}
                title="Code Highlighting"
                description="Beautiful syntax highlighting for dozens of programming languages with copy support."
              />
              <FeatureCard 
                icon={<Sparkles className="text-purple-400" />}
                title="Quota Management"
                description="Built-in tracking for tokens and requests so you never unexpectedly hit your API limits."
              />
            </div>
          </div>
        </section>
        
        {/* Pricing Section */}
        <section className="py-24 bg-black/95 backdrop-blur-xl border-t border-white/10 relative z-20">
          <div className="max-w-7xl mx-auto px-6">
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-4xl font-bold mb-4 text-white">Simple, Transparent Pricing</h2>
              <p className="text-zinc-400 max-w-2xl mx-auto">Choose the plan that fits your needs. Upgrade anytime.</p>
            </div>

            <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
              <PricingCard 
                title="Free"
                price="$0"
                description="Perfect for getting started and casual use."
                features={['GPT-3.5 Turbo', '50 requests / day', '100,000 tokens', 'Standard support']}
                buttonText="Get Started"
                isPopular={false}
              />
              <PricingCard 
                title="Super"
                price="$15"
                period="/mo"
                description="For professionals who need more power."
                features={['Everything in Free', 'Access to GPT-4', '500 requests / day', '1,000,000 tokens', 'Priority support']}
                buttonText="Upgrade to Super"
                isPopular={true}
              />
              <PricingCard 
                title="Hyper"
                price="$39"
                period="/mo"
                description="Unlimited potential for power users."
                features={['Everything in Super', 'Access to Claude 3 Opus', '5,000 requests / day', '10,000,000 tokens', '24/7 Dedicated support']}
                buttonText="Upgrade to Hyper"
                isPopular={false}
              />
            </div>
          </div>
        </section>
        
        {/* Footer */}
        <footer className="py-8 text-center text-zinc-500 text-sm border-t border-white/10 bg-black relative z-20">
          <p>© {new Date().getFullYear()} GPTCraft. All rights reserved.</p>
        </footer>
      </div>
    </div>
  );
};

const FeatureCard = ({ icon, title, description }: { icon: React.ReactNode, title: string, description: string }) => {
  return (
    <motion.div 
      whileHover={{ y: -5 }}
      className="p-6 rounded-2xl bg-zinc-900/50 border border-white/10 hover:border-white/20 hover:bg-zinc-900/80 transition-all backdrop-blur-sm"
    >
      <div className="w-12 h-12 rounded-xl bg-black border border-white/10 flex items-center justify-center mb-4 shadow-sm">
        {icon}
      </div>
      <h3 className="text-xl font-semibold mb-2 text-white">{title}</h3>
      <p className="text-zinc-400 leading-relaxed">{description}</p>
    </motion.div>
  );
};

const PricingCard = ({ title, price, period = '', description, features, buttonText, isPopular }: any) => {
  return (
    <motion.div 
      whileHover={{ y: -5 }}
      className={`relative p-8 rounded-3xl border ${isPopular ? 'border-[#00D2FF] shadow-2xl shadow-[#00D2FF]/20 bg-zinc-900/80' : 'border-white/10 bg-zinc-900/40'} flex flex-col backdrop-blur-sm`}
    >
      {isPopular && (
        <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-gradient-to-r from-[#00D2FF] to-[#2E3192] text-white px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider">
          Most Popular
        </div>
      )}
      <div className="mb-8">
        <h3 className="text-xl font-bold mb-2 text-white">{title}</h3>
        <p className="text-zinc-400 text-sm h-10">{description}</p>
      </div>
      <div className="mb-8">
        <span className="text-4xl font-bold text-white">{price}</span>
        <span className="text-zinc-400">{period}</span>
      </div>
      <ul className="space-y-4 mb-8 flex-1">
        {features.map((feature: string, i: number) => (
          <li key={i} className="flex items-start gap-3 text-sm">
            <Check size={18} className="text-emerald-400 shrink-0" />
            <span className="text-zinc-300">{feature}</span>
          </li>
        ))}
      </ul>
      <Link 
        to="/register" 
        className={`w-full py-3 px-4 rounded-xl font-medium text-center transition-colors ${
          isPopular 
            ? 'bg-[#2E3192] text-white hover:bg-[#1a1b52] border border-[#2E3192] hover:border-[#00D2FF]/50' 
            : 'bg-white/10 text-white hover:bg-white/20'
        }`}
      >
        {buttonText}
      </Link>
    </motion.div>
  );
};

const UserIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-cyan-600 dark:text-cyan-400">
    <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path>
    <circle cx="12" cy="7" r="4"></circle>
  </svg>
);

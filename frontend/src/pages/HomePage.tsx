import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'motion/react';
import { 
  Zap, 
  Shield, 
  Sparkles, 
  ArrowRight, 
  MessageSquare, 
  FileText, 
  Sliders, 
  Check,
  Sun,
  Moon
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { NeuralCoreVisualizer } from '../components/landing/NeuralCoreVisualizer';

const fadeIn = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.45, ease: [0.16, 1, 0.3, 1] }
};

const staggerContainer = {
  animate: {
    transition: {
      staggerChildren: 0.08
    }
  }
};

export const HomePage: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black text-zinc-900 dark:text-zinc-50 overflow-hidden font-sans selection:bg-cyan-500/30 selection:text-cyan-900 dark:selection:text-cyan-100 relative transition-colors duration-300">
      {/* Seamless atmospheric lighting mesh - dynamically spans wide displays */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-[1720px] h-[600px] xl:h-[750px] bg-gradient-to-b from-cyan-200/50 via-blue-100/30 to-transparent dark:from-cyan-950/30 dark:via-blue-950/15 dark:to-transparent blur-3xl pointer-events-none transition-colors duration-500" />
      <div className="absolute top-[850px] -left-36 w-80 sm:w-[550px] xl:w-[750px] h-[550px] xl:h-[750px] bg-cyan-500/5 dark:bg-cyan-900/10 rounded-full blur-[150px] pointer-events-none transition-colors duration-500" />
      <div className="absolute top-[1650px] -right-36 w-80 sm:w-[550px] xl:w-[750px] h-[550px] xl:h-[750px] bg-indigo-500/5 dark:bg-indigo-950/15 rounded-full blur-[150px] pointer-events-none transition-colors duration-500" />

      {/* Content Wrapper */}
      <div className="relative z-20">
        
        {/* Navigation - Wide responsive container with center links & theme switch */}
        <header className="fixed top-0 left-0 right-0 z-50 border-b border-zinc-200/80 dark:border-white/5 bg-white/75 dark:bg-black/60 backdrop-blur-xl transition-colors duration-300">
          <div className="max-w-[1720px] mx-auto px-5 sm:px-8 md:px-12 lg:px-16 xl:px-20 h-16 sm:h-20 flex items-center justify-between">
            {/* Left Brand */}
            <Link to="/" className="flex items-center gap-2.5 group">
              <img 
                src="/craft_logo.png" 
                alt="GPTCraft Logo" 
                width={34} 
                height={34} 
                className="w-8 h-8 sm:w-9 sm:h-9 object-contain transition-transform group-hover:scale-105" 
              />
              <span className="font-display font-bold text-xl sm:text-2xl tracking-tight text-zinc-900 dark:text-white transition-colors">GPTCraft</span>
            </Link>

            {/* Center Navigation Links (Hidden on small mobile, visible on tablet+) */}
            <nav className="hidden md:flex items-center gap-8">
              <a 
                href="#features" 
                className="text-sm font-medium text-zinc-600 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-white transition-colors"
              >
                Features
              </a>
              <a 
                href="#pricing" 
                className="text-sm font-medium text-zinc-600 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-white transition-colors"
              >
                Pricing
              </a>
            </nav>

            {/* Right Action Cluster */}
            <div className="flex items-center gap-2.5 sm:gap-4">
              {/* Theme Toggle Button */}
              <button
                type="button"
                onClick={(e) => toggleTheme({ x: e.clientX, y: e.clientY })}
                aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
                title={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
                className="p-2 sm:p-2.5 rounded-full border border-zinc-200/90 dark:border-white/10 bg-zinc-100/80 dark:bg-white/5 text-zinc-700 dark:text-zinc-200 hover:text-cyan-600 dark:hover:text-cyan-400 hover:border-cyan-500/40 transition-all cursor-pointer shadow-sm active:scale-95"
              >
                {theme === 'dark' ? (
                  <Sun size={18} className="transition-transform hover:rotate-45" />
                ) : (
                  <Moon size={18} className="transition-transform hover:-rotate-12" />
                )}
              </button>

              <Link 
                to="/login" 
                className="text-sm sm:text-base font-medium text-zinc-600 hover:text-zinc-900 dark:text-zinc-300 dark:hover:text-white transition-colors px-3 py-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-white/5"
              >
                Sign in
              </Link>
              <Link 
                to="/register" 
                className="font-display text-xs sm:text-sm font-semibold bg-zinc-900 hover:bg-zinc-800 text-white dark:bg-white dark:text-black dark:hover:bg-zinc-200 px-4 sm:px-5 py-2 sm:py-2.5 rounded-full transition-all shadow-sm active:scale-95"
              >
                Get Started
              </Link>
            </div>
          </div>
        </header>

        {/* Hero Section - Scaled across mobile, desktop, 2K, and ultrawide viewports */}
        <main className="pt-28 pb-16 sm:pt-32 sm:pb-20 lg:pt-36 xl:pt-40 px-5 sm:px-8 md:px-12 lg:px-16 xl:px-20 relative min-h-[85vh] lg:min-h-[92vh] flex items-center justify-center">
          <div className="max-w-[1720px] mx-auto w-full relative z-10 grid lg:grid-cols-12 gap-8 lg:gap-10 xl:gap-16 2xl:gap-24 items-center">
            
            {/* Left Content Column */}
            <motion.div
              initial="initial"
              animate="animate"
              variants={staggerContainer}
              className="lg:col-span-7 xl:col-span-6 flex flex-col items-center lg:items-start text-center lg:text-left space-y-6 sm:space-y-8"
            >
              <motion.h1 
                variants={fadeIn} 
                className="font-display text-4xl sm:text-5xl md:text-6xl lg:text-6xl xl:text-7xl 2xl:text-8xl font-bold tracking-[-0.035em] leading-[1.05] text-zinc-900 dark:text-white transition-colors"
              >
                Your Intelligent <br />
                <span className="text-cyan-600 dark:text-cyan-400 font-extrabold tracking-[-0.035em] transition-colors">Thinking Partner</span>
              </motion.h1>
              
              <motion.p 
                variants={fadeIn} 
                className="text-base sm:text-lg md:text-xl xl:text-2xl text-zinc-600 dark:text-zinc-300 max-w-xl xl:max-w-2xl leading-relaxed font-normal transition-colors"
              >
                Experience an intuitive companion for your thoughts, writing, and daily work. Brainstorm ideas, draft content, and find clear answers with natural, effortless conversations.
              </motion.p>
              
              <motion.div variants={fadeIn} className="flex flex-col sm:flex-row items-center gap-3.5 sm:gap-4 pt-2 sm:pt-4 w-full lg:w-auto">
                <Link 
                  to="/register" 
                  className="w-full sm:w-auto flex items-center justify-center gap-2.5 bg-cyan-500 dark:bg-cyan-400 hover:bg-cyan-400 dark:hover:bg-cyan-300 text-black px-7 py-3.5 sm:px-8 sm:py-4 xl:px-9 xl:py-4.5 rounded-full text-sm sm:text-base xl:text-lg font-semibold font-display shadow-lg shadow-cyan-500/20 hover:shadow-cyan-400/30 transition-all group"
                >
                  Start Chatting Free
                  <ArrowRight size={19} className="group-hover:translate-x-1 transition-transform" />
                </Link>
                <Link 
                  to="/login" 
                  className="w-full sm:w-auto flex items-center justify-center gap-2 bg-white/80 dark:bg-white/5 text-zinc-900 dark:text-white border border-zinc-200/90 dark:border-white/10 px-7 py-3.5 sm:px-8 sm:py-4 xl:px-9 xl:py-4.5 rounded-full text-sm sm:text-base xl:text-lg font-medium hover:bg-zinc-100 dark:hover:bg-white/10 hover:border-zinc-300 dark:hover:border-white/20 backdrop-blur-sm transition-all shadow-sm dark:shadow-none"
                >
                  Sign In
                </Link>
              </motion.div>

              {/* Value Assurances */}
              <motion.div 
                variants={fadeIn} 
                className="pt-2 sm:pt-4 flex flex-wrap items-center justify-center lg:justify-start gap-4 sm:gap-6 xl:gap-8 text-xs sm:text-sm text-zinc-500 dark:text-zinc-400"
              >
                <div className="flex items-center gap-2">
                  <Shield size={16} className="text-emerald-500 dark:text-emerald-400" />
                  <span>Private by default</span>
                </div>
                <div className="flex items-center gap-2">
                  <Zap size={16} className="text-cyan-500 dark:text-cyan-400" />
                  <span>Instant responses</span>
                </div>
                <div className="flex items-center gap-2">
                  <Sparkles size={16} className="text-purple-500 dark:text-purple-400" />
                  <span>Always available</span>
                </div>
              </motion.div>
            </motion.div>

            {/* Right Content Column - Proportional 3D Canvas across all screen sizes */}
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
              className="lg:col-span-5 xl:col-span-6 flex items-center justify-center relative w-full"
            >
              <NeuralCoreVisualizer />
            </motion.div>

          </div>
        </main>

        {/* Subtle Gradient Transition Divider */}
        <div className="relative w-full max-w-[1720px] mx-auto px-5 sm:px-8 md:px-12 lg:px-16 xl:px-20">
          <div className="h-px bg-gradient-to-r from-transparent via-zinc-200 dark:via-white/10 to-transparent transition-colors" />
        </div>

        {/* Features Section - Wide layout with display typography */}
        <section id="features" className="py-20 sm:py-28 xl:py-32 relative z-20">
          <div className="max-w-[1720px] mx-auto px-5 sm:px-8 md:px-12 lg:px-16 xl:px-20">
            <div className="max-w-3xl mb-14 sm:mb-18 xl:mb-20 text-center lg:text-left">
              <h2 className="font-display text-3xl sm:text-4xl md:text-5xl xl:text-6xl font-bold mb-3 sm:mb-4 text-zinc-900 dark:text-white tracking-[-0.03em] transition-colors">Designed for Clearer Thinking</h2>
              <p className="text-zinc-600 dark:text-zinc-400 text-base sm:text-lg xl:text-xl leading-relaxed transition-colors">
                Everything you need to think creatively, organize complex ideas, and get high-quality work done faster.
              </p>
            </div>

            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5 sm:gap-6 xl:gap-8">
              <FeatureCard 
                icon={<Zap size={22} className="text-amber-500 dark:text-amber-400" />}
                title="Instant Conversations"
                description="Responses appear naturally as thoughts form. Enjoy a fast, uninterrupted creative flow without waiting."
              />
              <FeatureCard 
                icon={<Shield size={22} className="text-emerald-500 dark:text-emerald-400" />}
                title="Private & Protected"
                description="Your conversations, ideas, and drafts remain completely confidential and strictly protected."
              />
              <FeatureCard 
                icon={<Sliders size={22} className="text-cyan-500 dark:text-cyan-400" />}
                title="Adaptive Intelligence"
                description="Tailor conversations to match your immediate task—whether in-depth analysis, concise answers, or brainstorming."
              />
              <FeatureCard 
                icon={<MessageSquare size={22} className="text-blue-500 dark:text-blue-400" />}
                title="Continuous Memory"
                description="Easily pick up previous conversations. Important background context stays with you across sessions."
              />
              <FeatureCard 
                icon={<FileText size={22} className="text-pink-500 dark:text-pink-400" />}
                title="Clean Formatting"
                description="Beautiful readability for documents, structured lists, and code snippets, ready to copy and share."
              />
              <FeatureCard 
                icon={<Sparkles size={22} className="text-purple-500 dark:text-purple-400" />}
                title="Clear Usage Visibility"
                description="Simple, transparent daily limits with no surprises so you always know your active capacity."
              />
            </div>
          </div>
        </section>

        {/* Subtle Gradient Transition Divider */}
        <div className="relative w-full max-w-[1720px] mx-auto px-5 sm:px-8 md:px-12 lg:px-16 xl:px-20">
          <div className="h-px bg-gradient-to-r from-transparent via-zinc-200 dark:via-white/10 to-transparent transition-colors" />
        </div>
        
        {/* Pricing Section - Proportional grid across wider viewports */}
        <section id="pricing" className="py-20 sm:py-28 xl:py-32 relative z-20">
          <div className="max-w-[1720px] mx-auto px-5 sm:px-8 md:px-12 lg:px-16 xl:px-20">
            <div className="text-center mb-14 sm:mb-18 xl:mb-20">
              <h2 className="font-display text-3xl sm:text-4xl md:text-5xl xl:text-6xl font-bold mb-3 sm:mb-4 text-zinc-900 dark:text-white tracking-[-0.03em] transition-colors">Simple, Transparent Pricing</h2>
              <p className="text-zinc-600 dark:text-zinc-400 max-w-xl mx-auto text-sm sm:text-base xl:text-lg transition-colors">
                Choose the plan that fits your personal or professional creative workflow. Upgrade or downgrade anytime.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6 lg:gap-8 xl:gap-10 max-w-6xl xl:max-w-7xl mx-auto items-stretch">
              <PricingCard 
                title="Free"
                price="$0"
                description="Perfect for casual daily exploration and everyday questions."
                features={['Standard intelligence', '50 messages / day', 'Standard response speed', 'Community support']}
                buttonText="Get Started"
                isPopular={false}
              />
              <PricingCard 
                title="Super"
                price="$15"
                period="/mo"
                description="For professionals who need deeper reasoning and expanded limits."
                features={['Everything in Free', 'Advanced reasoning models', '500 messages / day', 'Faster response speed', 'Priority support']}
                buttonText="Upgrade to Super"
                isPopular={true}
              />
              <PricingCard 
                title="Hyper"
                price="$39"
                period="/mo"
                description="Highest capacity for power users with demanding daily workflows."
                features={['Everything in Super', 'Highest-tier intelligence', '5,000 messages / day', 'Fastest response times', 'Dedicated 24/7 support']}
                buttonText="Upgrade to Hyper"
                isPopular={false}
              />
            </div>
          </div>
        </section>
        
        {/* Footer */}
        <footer className="py-12 text-center text-zinc-500 text-xs sm:text-sm border-t border-zinc-200/80 dark:border-white/5 bg-zinc-100/60 dark:bg-black/40 relative z-20 transition-colors">
          <p>© {new Date().getFullYear()} GPTCraft. Thoughtful conversational AI.</p>
        </footer>
      </div>
    </div>
  );
};

const FeatureCard = ({ icon, title, description }: { icon: React.ReactNode, title: string, description: string }) => {
  return (
    <div className="group relative p-6 sm:p-7 xl:p-8 rounded-2xl bg-white/70 dark:bg-zinc-900/30 border border-zinc-200/80 dark:border-white/[0.08] hover:border-cyan-500/40 hover:bg-white dark:hover:bg-zinc-900/60 transition-all duration-300 overflow-hidden flex flex-col justify-between shadow-sm dark:shadow-none">
      {/* Top subtle specular highlight */}
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-zinc-200/80 dark:via-white/10 to-transparent group-hover:via-cyan-500/40 dark:group-hover:via-cyan-400/30 transition-colors" />
      
      <div>
        <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-xl bg-zinc-100/90 dark:bg-white/[0.03] border border-zinc-200/80 dark:border-white/10 flex items-center justify-center mb-5 group-hover:border-zinc-300 dark:group-hover:border-white/20 transition-colors">
          {icon}
        </div>
        <h3 className="font-display text-lg sm:text-xl font-semibold mb-2 sm:mb-2.5 text-zinc-900 dark:text-white tracking-[-0.02em] transition-colors">{title}</h3>
        <p className="text-zinc-600 dark:text-zinc-400 text-xs sm:text-sm xl:text-base leading-relaxed transition-colors">{description}</p>
      </div>
    </div>
  );
};

interface PricingCardProps {
  title: string;
  price: string;
  period?: string;
  description: string;
  features: string[];
  buttonText: string;
  isPopular?: boolean;
}

const PricingCard: React.FC<PricingCardProps> = ({ 
  title, 
  price, 
  period = '', 
  description, 
  features, 
  buttonText, 
  isPopular 
}) => {
  return (
    <div 
      className={`relative p-7 sm:p-8 xl:p-9 rounded-3xl border ${
        isPopular 
          ? 'border-cyan-500/50 dark:border-cyan-400/40 bg-cyan-50/30 dark:bg-zinc-900/60 shadow-xl shadow-cyan-500/10 dark:shadow-[0_0_50px_-12px_rgba(6,182,212,0.22)]' 
          : 'border-zinc-200/80 dark:border-white/[0.08] bg-white/70 dark:bg-zinc-900/30 hover:border-zinc-300 dark:hover:border-white/20 hover:bg-white dark:hover:bg-zinc-900/50 shadow-sm dark:shadow-none'
      } flex flex-col transition-all duration-300 overflow-hidden`}
    >
      {/* Top subtle specular highlight */}
      <div 
        className={`absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent ${
          isPopular ? 'via-cyan-500/60 dark:via-cyan-400/50' : 'via-zinc-200/80 dark:via-white/10'
        } to-transparent`} 
      />

      {isPopular && (
        <div className="font-display absolute -top-3.5 left-1/2 -translate-x-1/2 bg-gradient-to-r from-cyan-400 to-teal-400 text-black px-4 py-1 rounded-full text-xs font-bold uppercase tracking-wider shadow-md shadow-cyan-500/20">
          Most Popular
        </div>
      )}
      <div className="mb-6">
        <h3 className="font-display text-xl sm:text-2xl font-bold mb-2 text-zinc-900 dark:text-white tracking-[-0.02em] transition-colors">{title}</h3>
        <p className="text-zinc-600 dark:text-zinc-400 text-sm xl:text-base min-h-[44px] leading-relaxed transition-colors">{description}</p>
      </div>
      <div className="mb-6 pb-6 border-b border-zinc-200/80 dark:border-white/10 transition-colors">
        <span className="font-display text-3xl sm:text-4xl xl:text-5xl font-extrabold text-zinc-900 dark:text-white tracking-tight transition-colors">{price}</span>
        {period && <span className="text-zinc-500 dark:text-zinc-400 text-sm xl:text-base ml-1 transition-colors">{period}</span>}
      </div>
      <ul className="space-y-3.5 mb-8 flex-1">
        {features.map((feature, i) => (
          <li key={i} className="flex items-start gap-3 text-sm xl:text-base">
            <Check size={17} className="text-emerald-500 dark:text-emerald-400 shrink-0 mt-0.5" />
            <span className="text-zinc-700 dark:text-zinc-300 text-xs sm:text-sm xl:text-base transition-colors">{feature}</span>
          </li>
        ))}
      </ul>
      <Link 
        to="/register" 
        className={`font-display w-full py-3.5 px-4 rounded-xl font-semibold text-sm xl:text-base text-center transition-all ${
          isPopular 
            ? 'bg-cyan-500 hover:bg-cyan-400 dark:bg-cyan-400 dark:hover:bg-cyan-300 text-black shadow-lg shadow-cyan-500/20' 
            : 'bg-zinc-900 hover:bg-zinc-800 text-white dark:bg-white/10 dark:hover:bg-white/15 dark:text-white shadow-sm dark:shadow-none'
        }`}
      >
        {buttonText}
      </Link>
    </div>
  );
};

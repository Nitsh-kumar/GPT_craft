import { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { supabase } from '../lib/supabase';
import { Loader2 } from 'lucide-react';
import { ThemeSwitcher } from '../components/layout/ThemeSwitcher';

export const AuthSuccess = () => {
  const [searchParams] = useSearchParams();
  const { user, isAuthenticated, loginWithToken } = useAuth();
  const navigate = useNavigate();
  const [authError, setAuthError] = useState<string | null>(null);
  const navigatedRef = useRef(false);

  // 1. If user is authenticated in context, navigate to /chat immediately
  useEffect(() => {
    if ((isAuthenticated || user) && !navigatedRef.current) {
      navigatedRef.current = true;
      navigate('/chat', { replace: true });
    }
  }, [isAuthenticated, user, navigate]);

  // 2. Main OAuth redirect processor
  useEffect(() => {
    if (navigatedRef.current) return;

    const doNavigate = (to: string) => {
      if (!navigatedRef.current) {
        navigatedRef.current = true;
        navigate(to, { replace: true });
      }
    };

    const handleAuthRedirect = async () => {
      try {
        // Parse hash fragment for OAuth implicit flow or error params
        const rawHash = window.location.hash.startsWith('#')
          ? window.location.hash.substring(1)
          : window.location.hash;
        const hashParams = new URLSearchParams(rawHash);

        // Check for any OAuth errors in search params or hash fragment
        const oauthError =
          searchParams.get('error') ||
          hashParams.get('error') ||
          hashParams.get('error_code');
        const oauthErrorDesc =
          searchParams.get('error_description') ||
          hashParams.get('error_description') ||
          searchParams.get('details') ||
          hashParams.get('details');

        if (oauthError) {
          const details = oauthErrorDesc ? `&details=${encodeURIComponent(oauthErrorDesc)}` : '';
          doNavigate(`/login?error=${encodeURIComponent(oauthError)}${details}`);
          return;
        }

        // Check for explicit token
        const explicitToken = searchParams.get('token') || hashParams.get('access_token');
        if (explicitToken) {
          await loginWithToken(explicitToken);
          doNavigate('/chat');
          return;
        }

        // Handle PKCE code exchange
        const authCode = searchParams.get('code');
        if (authCode) {
          const { data, error: exchangeError } = await supabase.auth.exchangeCodeForSession(authCode);
          if (exchangeError) throw exchangeError;
          if (data.session?.access_token) {
            await loginWithToken(data.session.access_token);
            doNavigate('/chat');
            return;
          }
        }

        // Check active Supabase session
        const { data: { session }, error: sessionError } = await supabase.auth.getSession();
        if (sessionError) throw sessionError;

        if (session?.access_token) {
          await loginWithToken(session.access_token);
          doNavigate('/chat');
          return;
        }

        // Check stored token in localStorage
        const storedToken = localStorage.getItem('accessToken');
        if (storedToken) {
          await loginWithToken(storedToken);
          doNavigate('/chat');
          return;
        }

        // Listen for Supabase onAuthStateChange if session exchange is in-flight
        const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, currentSession) => {
          if (currentSession?.access_token && !navigatedRef.current) {
            subscription.unsubscribe();
            await loginWithToken(currentSession.access_token);
            doNavigate('/chat');
          }
        });

        // Fallback timeout to prevent permanent spinner
        const timer = setTimeout(() => {
          if (!navigatedRef.current) {
            subscription.unsubscribe();
            const tokenCheck = localStorage.getItem('accessToken');
            if (tokenCheck) {
              doNavigate('/chat');
            } else {
              doNavigate('/login');
            }
          }
        }, 3000);

        return () => {
          clearTimeout(timer);
          subscription.unsubscribe();
        };
      } catch (err: any) {
        console.error('Failed to complete authentication', err);
        setAuthError(err.message || 'Authentication failed');
        doNavigate(`/login?error=session_creation_failed&details=${encodeURIComponent(err.message || '')}`);
      }
    };

    handleAuthRedirect();
  }, [searchParams, loginWithToken, navigate]);

  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center">
      <div className="fixed top-4 right-4 z-50">
        <ThemeSwitcher />
      </div>
      <div className="text-center space-y-4">
        <Loader2 className="w-12 h-12 text-ember animate-spin mx-auto" />
        <h2 className="font-serif text-xl font-medium tracking-tight text-ink">Authenticating...</h2>
        <p className="text-ink-3">
          {authError ? `Error: ${authError}` : 'Please wait while we complete your sign in.'}
        </p>
      </div>
    </div>
  );
};

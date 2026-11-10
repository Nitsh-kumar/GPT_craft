import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { setAuthToken } from '../services/api';
import { Loader2 } from 'lucide-react';

export const AuthSuccess = () => {
  const [searchParams] = useSearchParams();
  const { loginWithToken } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const token = searchParams.get('token');
    const error = searchParams.get('error');
    const details = searchParams.get('details');

    if (token) {
      localStorage.setItem('accessToken', token);
      setAuthToken(token);
      loginWithToken(token).then(() => {
        navigate('/chat');
      }).catch((err) => {
        console.error('Failed to login with token', err);
        navigate(`/login?error=session_creation_failed&details=${encodeURIComponent(err.message)}`);
      });
    } else if (error) {
      navigate(`/login?error=${error}${details ? `&details=${encodeURIComponent(details)}` : ''}`);
    } else {
      navigate('/login');
    }
  }, [searchParams, loginWithToken, navigate]);

  return (
    <div className="min-h-screen bg-black flex items-center justify-center">
      <div className="text-center space-y-4">
        <Loader2 className="w-12 h-12 text-cyan-500 animate-spin mx-auto" />
        <h2 className="text-xl font-medium text-white">Authenticating...</h2>
        <p className="text-zinc-500">Please wait while we complete your sign in.</p>
      </div>
    </div>
  );
};

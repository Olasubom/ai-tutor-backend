import { GoogleLogin } from '@react-oauth/google';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { getOnboardingStatus, loginWithGoogle } from '@/api/auth';
import { useAuthStore, getRedirectForRole } from '@/stores/authStore';
import { useToastStore } from '@/components/ui/Toast';
import axios from 'axios';

interface GoogleSignInButtonProps {
  /** Where new Google students go after first sign-in when onboarding is incomplete */
  registerRedirect?: string;
}

const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;

export function GoogleSignInButton({ registerRedirect = '/onboarding/step1' }: GoogleSignInButtonProps) {
  const navigate = useNavigate();
  const authLogin = useAuthStore((s) => s.login);
  const setOnboardingComplete = useAuthStore((s) => s.setOnboardingComplete);
  const toast = useToastStore((s) => s.add);

  const handleCredential = async (credential: string) => {
    try {
      const tokenResponse = await loginWithGoogle(credential);
      authLogin(tokenResponse);

      if (tokenResponse.role === 'student') {
        try {
          const status = await getOnboardingStatus();
          if (status.is_complete) {
            setOnboardingComplete(tokenResponse.user_id);
            navigate('/student/dashboard');
          } else {
            navigate(registerRedirect);
          }
        } catch {
          navigate(registerRedirect);
        }
        return;
      }

      navigate(getRedirectForRole(tokenResponse.role));
    } catch (e) {
      if (axios.isAxiosError(e)) {
        const detail = e.response?.data?.detail;
        if (typeof detail === 'string') {
          toast(detail, 'error');
          return;
        }
      }
      toast(e instanceof Error ? e.message : 'Google sign-in failed.', 'error');
    }
  };

  if (!clientId) {
    return (
      <Button
        variant="secondary"
        fullWidth
        type="button"
        onClick={() =>
          toast(
            'Add VITE_GOOGLE_CLIENT_ID to frontend/.env — create an OAuth Client ID at console.cloud.google.com',
            'info',
          )
        }
      >
        Continue with Google
      </Button>
    );
  }

  return (
    <div className="flex w-full justify-center [&>div]:w-full [&_iframe]:!w-full">
      <GoogleLogin
        onSuccess={(res) => {
          if (res.credential) handleCredential(res.credential);
        }}
        onError={() => toast('Google sign-in was cancelled or failed', 'error')}
        theme="outline"
        size="large"
        text="continue_with"
        shape="rectangular"
        width="384"
      />
    </div>
  );
}

import { GoogleLogin } from '@react-oauth/google';
import { Button } from '@/components/ui/Button';
import { loginWithGoogle } from '@/api/auth';
import { useAuthStore, getRedirectForRole } from '@/stores/authStore';
import { useToastStore } from '@/components/ui/Toast';
import { useNavigate } from 'react-router-dom';

interface GoogleSignInButtonProps {
  /** Where new Google students go after first sign-in */
  registerRedirect?: string;
}

const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;

export function GoogleSignInButton({ registerRedirect }: GoogleSignInButtonProps) {
  const navigate = useNavigate();
  const authLogin = useAuthStore((s) => s.login);
  const toast = useToastStore((s) => s.add);

  const handleCredential = async (credential: string) => {
    try {
      const result = await loginWithGoogle(credential);
      authLogin(result.user, result.token);
      if (result.user.role === 'student' && !result.user.onboarding_complete && registerRedirect) {
        navigate(registerRedirect);
      } else {
        navigate(getRedirectForRole(result.user.role));
      }
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Google sign-in failed', 'error');
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

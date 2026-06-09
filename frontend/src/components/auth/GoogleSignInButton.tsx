import { GoogleLogin } from '@react-oauth/google';
import { Button } from '@/components/ui/Button';
import { loginWithGoogle } from '@/api/auth';
import { useToastStore } from '@/components/ui/Toast';

interface GoogleSignInButtonProps {
  /** Where new Google students go after first sign-in */
  registerRedirect?: string;
}

const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;

export function GoogleSignInButton({ registerRedirect: _registerRedirect }: GoogleSignInButtonProps) {
  const toast = useToastStore((s) => s.add);

  const handleCredential = async (_credential: string) => {
    try {
      await loginWithGoogle(_credential);
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Google sign-in is not configured on the backend.', 'error');
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

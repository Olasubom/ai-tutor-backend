import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { AuthSidePanel } from '@/components/auth/AuthSidePanel';
import { GoogleSignInButton } from '@/components/auth/GoogleSignInButton';
import { login } from '@/api/auth';
import { syncOnboardingComplete } from '@/api/onboarding';
import { useAuthStore, getRedirectForRole } from '@/stores/authStore';
import { learnerIdFromUser } from '@/lib/utils';
import { useToastStore } from '@/components/ui/Toast';

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(6),
});

type FormData = z.infer<typeof schema>;

export default function Login() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const authLogin = useAuthStore((s) => s.login);
  const toast = useToastStore((s) => s.add);

  useEffect(() => {
    if (params.get('expired')) {
      toast('Session expired. Please sign in again.', 'warning');
    }
  }, [params, toast]);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    try {
      const result = await login(data.email, data.password);
      let user = result.user;
      if (user.role === 'student') {
        const learnerId = user.learner_id ?? learnerIdFromUser(user.user_id);
        const complete = await syncOnboardingComplete(learnerId);
        if (complete) user = { ...user, onboarding_complete: true };
      }
      authLogin(user, result.token);
      navigate(user.role === 'student' && !user.onboarding_complete ? '/onboarding/step1' : getRedirectForRole(user.role));
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Login failed', 'error');
    }
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          <h1 className="text-[28px] font-extrabold tracking-tight">Welcome back</h1>
          <p className="mt-2 text-text-secondary">Log in to continue your learning journey.</p>
          <div className="mt-8">
            <GoogleSignInButton />
          </div>
          <div className="my-6 flex items-center gap-3 text-[11px] font-semibold uppercase tracking-wide text-text-muted">
            <div className="h-px flex-1 bg-border" />
            OR EMAIL
            <div className="h-px flex-1 bg-border" />
          </div>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input label="Email address" type="email" error={errors.email?.message} {...register('email')} />
            <div>
              <div className="mb-1.5 flex justify-between">
                <label className="text-[14px] font-medium">Password</label>
                <a href="#" className="text-[13px] text-primary">
                  Forgot?
                </a>
              </div>
              <Input type="password" error={errors.password?.message} {...register('password')} />
            </div>
            <Button type="submit" fullWidth disabled={isSubmitting}>
              Sign in
            </Button>
          </form>
          <p className="mt-6 text-center text-[14px] text-text-muted">
            Don&apos;t have an account?{' '}
            <Link to="/register" className="font-semibold text-primary">
              Sign up
            </Link>
          </p>
        </div>
      </div>
      <AuthSidePanel panel="login" />
    </div>
  );
}

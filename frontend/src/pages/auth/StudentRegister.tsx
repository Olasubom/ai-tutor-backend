import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate } from 'react-router-dom';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { AuthSidePanel } from '@/components/auth/AuthSidePanel';
import { GoogleSignInButton } from '@/components/auth/GoogleSignInButton';
import { registerStudent } from '@/api/auth';
import { useAuthStore } from '@/stores/authStore';
import { useToastStore } from '@/components/ui/Toast';

const schema = z
  .object({
    name: z.string().min(2),
    email: z.string().email(),
    password: z.string().min(8),
    confirm: z.string(),
  })
  .refine((d) => d.password === d.confirm, { message: 'Passwords must match', path: ['confirm'] });

type FormData = z.infer<typeof schema>;

export default function StudentRegister() {
  const navigate = useNavigate();
  const authLogin = useAuthStore((s) => s.login);
  const toast = useToastStore((s) => s.add);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    try {
      const result = await registerStudent({ name: data.name, email: data.email, password: data.password });
      authLogin(result.user, result.token);
      navigate('/onboarding/step1');
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Registration failed', 'error');
    }
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          <h1 className="text-[28px] font-extrabold tracking-tight">Create your student account</h1>
          <p className="mt-2 text-text-secondary">Start your personalized learning journey today.</p>

          <div className="mt-8">
            <GoogleSignInButton registerRedirect="/onboarding/step1" />
          </div>

          <div className="my-6 flex items-center gap-3 text-[11px] font-semibold uppercase tracking-wide text-text-muted">
            <div className="h-px flex-1 bg-border" />
            OR EMAIL
            <div className="h-px flex-1 bg-border" />
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input label="Full Name" error={errors.name?.message} {...register('name')} />
            <Input label="Email address" type="email" error={errors.email?.message} {...register('email')} />
            <Input label="Password" type="password" error={errors.password?.message} {...register('password')} />
            <Input label="Confirm Password" type="password" error={errors.confirm?.message} {...register('confirm')} />
            <Button type="submit" fullWidth disabled={isSubmitting}>
              Create Account
            </Button>
          </form>

          <p className="mt-4 text-center text-[12px] text-text-muted">
            By creating an account you agree to our Terms of Service.
          </p>
          <p className="mt-4 text-center text-[14px] text-text-muted">
            Already have an account?{' '}
            <Link to="/login" className="font-semibold text-primary">
              Sign in
            </Link>
          </p>
        </div>
      </div>

      <AuthSidePanel panel="student_register" />
    </div>
  );
}

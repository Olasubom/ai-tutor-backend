import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate } from 'react-router-dom';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { adminLogin, parseAdminLoginError } from '@/api/auth';
import { useAuthStore } from '@/stores/authStore';
import { useToastStore } from '@/components/ui/Toast';

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(1, 'Password is required'),
});

type FormData = z.infer<typeof schema>;

export default function AdminLogin() {
  const navigate = useNavigate();
  const authLogin = useAuthStore((s) => s.login);
  const toast = useToastStore((s) => s.add);
  const [formError, setFormError] = useState<{ message: string; showStudentLink?: boolean } | null>(null);
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const adminEmail = watch('email');

  const onSubmit = async (data: FormData) => {
    setFormError(null);
    try {
      const tokenResponse = await adminLogin(data.email, data.password);
      authLogin(tokenResponse);
      navigate('/admin');
    } catch (e) {
      const parsed = parseAdminLoginError(e);
      if (parsed.kind === 'not_admin') {
        setFormError({ message: parsed.message, showStudentLink: true });
        return;
      }
      if (parsed.kind === 'network' || parsed.kind === 'credentials' || parsed.kind === 'pending') {
        setFormError({ message: parsed.message });
        return;
      }
      toast(parsed.message, 'error');
    }
  };

  return (
    <div className="page-grid flex min-h-screen items-center justify-center px-6 py-12">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8 shadow-card">
        <h1 className="text-[28px] font-extrabold tracking-tight">Admin sign in</h1>
        <p className="mt-2 text-text-secondary">Platform administration access only.</p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input label="Admin email" type="email" error={errors.email?.message} {...register('email')} />
          <div>
            <Input label="Password" type="password" error={errors.password?.message} {...register('password')} />
            <p className="mt-2 text-right text-[13px]">
              <Link
                to="/admin/forgot-password"
                state={{ email: adminEmail?.trim() }}
                className="text-primary hover:underline"
                onClick={(e) => {
                  if (!adminEmail?.trim()) {
                    e.preventDefault();
                    setFormError({
                      message: 'Enter your admin email above first, then click Forgot password.',
                    });
                  }
                }}
              >
                Forgot password?
              </Link>
            </p>
          </div>
          {formError && (
            <div className="rounded-lg border border-error/30 bg-error-container px-4 py-3 text-[14px] text-error">
              {formError.message}
              {formError.showStudentLink && (
                <p className="mt-2">
                  <Link to="/login" className="font-semibold text-primary hover:underline">
                    Go to Student / Lecturer login
                  </Link>
                </p>
              )}
            </div>
          )}
          <Button type="submit" fullWidth disabled={isSubmitting}>
            {isSubmitting ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>

        <p className="mt-6 text-center text-[14px] text-text-muted">
          <Link to="/login" className="text-primary">
            Student / Lecturer login
          </Link>
        </p>
      </div>
    </div>
  );
}

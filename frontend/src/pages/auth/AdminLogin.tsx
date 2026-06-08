import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate } from 'react-router-dom';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { adminLogin } from '@/api/auth';
import { useAuthStore } from '@/stores/authStore';
import { useToastStore } from '@/components/ui/Toast';

const schema = z.object({
  email: z.string().email(),
  secret: z.string().min(1, 'Admin secret is required'),
});

type FormData = z.infer<typeof schema>;

export default function AdminLogin() {
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
      const result = await adminLogin(data.email, data.secret);
      authLogin(result.user, result.token);
      navigate('/admin');
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Login failed', 'error');
    }
  };

  return (
    <div className="page-grid flex min-h-screen items-center justify-center px-6 py-12">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8 shadow-card">
        <h1 className="text-[28px] font-extrabold tracking-tight">Admin sign in</h1>
        <p className="mt-2 text-text-secondary">Platform administration access only.</p>

        <form onSubmit={handleSubmit(onSubmit)} className="mt-8 space-y-4">
          <Input label="Admin email" type="email" error={errors.email?.message} {...register('email')} />
          <Input
            label="Admin secret"
            type="password"
            placeholder="From VITE_ADMIN_SECRET"
            error={errors.secret?.message}
            {...register('secret')}
          />
          <Button type="submit" fullWidth disabled={isSubmitting}>
            Sign in
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

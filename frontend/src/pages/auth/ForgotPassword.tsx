import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate } from 'react-router-dom';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { requestPasswordResetCode, resetPasswordWithCode } from '@/api/auth';
import { useToastStore } from '@/components/ui/Toast';

const emailSchema = z.object({
  email: z.string().email('Enter a valid email'),
});

const resetSchema = z
  .object({
    code: z.string().length(6, 'Enter the 6-digit code'),
    password: z.string().min(8, 'At least 8 characters'),
    confirm: z.string(),
  })
  .refine((d) => d.password === d.confirm, { message: 'Passwords must match', path: ['confirm'] });

type EmailForm = z.infer<typeof emailSchema>;
type ResetForm = z.infer<typeof resetSchema>;

export default function ForgotPassword() {
  const navigate = useNavigate();
  const toast = useToastStore((s) => s.add);
  const [step, setStep] = useState<'email' | 'reset'>('email');
  const [email, setEmail] = useState('');
  const [devCode, setDevCode] = useState<string | null>(null);
  const [emailSent, setEmailSent] = useState(false);
  const [sending, setSending] = useState(false);

  const emailForm = useForm<EmailForm>({ resolver: zodResolver(emailSchema) });
  const resetForm = useForm<ResetForm>({ resolver: zodResolver(resetSchema) });

  const sendCode = async (data: EmailForm) => {
    setSending(true);
    try {
      const result = await requestPasswordResetCode(data.email);
      setEmail(data.email);
      setDevCode(result.devCode ?? null);
      setEmailSent(result.emailSent ?? false);
      setStep('reset');
      toast(result.message, 'success');
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Could not send code', 'error');
    } finally {
      setSending(false);
    }
  };

  const onReset = async (data: ResetForm) => {
    try {
      await resetPasswordWithCode(email, data.code, data.password);
      toast('Password updated. You can sign in now.', 'success');
      navigate('/login');
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Reset failed', 'error');
    }
  };

  return (
    <div className="page-grid flex min-h-screen items-center justify-center px-6 py-12">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8 shadow-card">
        <h1 className="text-[28px] font-extrabold tracking-tight">Reset password</h1>
        <p className="mt-2 text-text-secondary">
          {step === 'email'
            ? 'Enter your email and we will send a verification code.'
            : 'Enter the code from your email and choose a new password.'}
        </p>

        {step === 'email' ? (
          <form onSubmit={emailForm.handleSubmit(sendCode)} className="mt-8 space-y-4">
            <Input
              label="Email address"
              type="email"
              error={emailForm.formState.errors.email?.message}
              {...emailForm.register('email')}
            />
            <Button type="submit" fullWidth disabled={sending}>
              {sending ? 'Sending…' : 'Send verification code'}
            </Button>
          </form>
        ) : (
          <>
            {emailSent && (
              <p className="mt-4 text-[14px] text-text-secondary">
                Check your inbox (and spam folder) for a 6-digit code from AITutor.
              </p>
            )}
            {devCode && !emailSent && (
              <div className="mt-4 rounded-lg border border-warning/40 bg-warning-container/20 p-3 text-[13px] text-text-secondary">
                <strong className="text-text-primary">SMTP not configured:</strong> add Gmail settings to{' '}
                <code className="text-[12px]">agency/.env</code>. Your code is{' '}
                <span className="font-mono text-[15px] font-bold text-primary">{devCode}</span>
              </div>
            )}
            <form onSubmit={resetForm.handleSubmit(onReset)} className="mt-6 space-y-4">
              <Input
                label="Verification code"
                placeholder="6-digit code"
                maxLength={6}
                error={resetForm.formState.errors.code?.message}
                {...resetForm.register('code')}
              />
              <Input
                label="New password"
                type="password"
                error={resetForm.formState.errors.password?.message}
                {...resetForm.register('password')}
              />
              <Input
                label="Confirm password"
                type="password"
                error={resetForm.formState.errors.confirm?.message}
                {...resetForm.register('confirm')}
              />
              <Button type="submit" fullWidth disabled={resetForm.formState.isSubmitting}>
                Reset password
              </Button>
              <Button
                type="button"
                variant="ghost"
                fullWidth
                onClick={() => {
                  setStep('email');
                  setDevCode(null);
                  setEmailSent(false);
                }}
              >
                Use a different email
              </Button>
            </form>
          </>
        )}

        <p className="mt-6 text-center text-[14px] text-text-muted">
          <Link to="/login" className="text-primary">
            Back to sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

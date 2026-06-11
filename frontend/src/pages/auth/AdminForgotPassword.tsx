import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import {
  requestAdminPasswordResetCode,
  resetAdminPasswordWithCode,
  verifyAdminResetCode,
} from '@/api/auth';
import { useToastStore } from '@/components/ui/Toast';

const codeSchema = z.object({
  code: z.string().length(6, 'Enter the 6-digit verification code'),
});

const passwordSchema = z
  .object({
    password: z.string().min(8, 'At least 8 characters'),
    confirm: z.string(),
  })
  .refine((d) => d.password === d.confirm, { message: 'Passwords must match', path: ['confirm'] });

type CodeForm = z.infer<typeof codeSchema>;
type PasswordForm = z.infer<typeof passwordSchema>;

type Step = 'sending' | 'code' | 'password';

export default function AdminForgotPassword() {
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToastStore((s) => s.add);
  const email = ((location.state as { email?: string } | null)?.email ?? '').trim().toLowerCase();

  const [step, setStep] = useState<Step>('sending');
  const [maskedEmail, setMaskedEmail] = useState('');
  const [verifiedCode, setVerifiedCode] = useState('');
  const [sendError, setSendError] = useState('');
  const [resending, setResending] = useState(false);

  const codeForm = useForm<CodeForm>({ resolver: zodResolver(codeSchema) });
  const passwordForm = useForm<PasswordForm>({ resolver: zodResolver(passwordSchema) });

  const sendCode = async () => {
    if (!email) return;
    setSendError('');
    try {
      const result = await requestAdminPasswordResetCode(email);
      setMaskedEmail(result.masked_email);
      setStep('code');
      toast(result.message, 'success');
    } catch (e) {
      if (axios.isAxiosError(e)) {
        const detail = e.response?.data?.detail;
        setSendError(typeof detail === 'string' ? detail : 'Could not send verification code.');
      } else {
        setSendError('Could not send verification code.');
      }
      setStep('code');
    }
  };

  useEffect(() => {
    if (!email) return;
    void sendCode();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [email]);

  const onVerifyCode = async (data: CodeForm) => {
    try {
      await verifyAdminResetCode(email, data.code);
      setVerifiedCode(data.code);
      setStep('password');
    } catch (e) {
      if (axios.isAxiosError(e)) {
        const detail = e.response?.data?.detail;
        toast(typeof detail === 'string' ? detail : 'Invalid verification code', 'error');
      } else {
        toast('Invalid verification code', 'error');
      }
    }
  };

  const onResetPassword = async (data: PasswordForm) => {
    try {
      await resetAdminPasswordWithCode(email, verifiedCode, data.password);
      toast('Admin password updated. You can sign in now.', 'success');
      navigate('/admin/login', { replace: true });
    } catch (e) {
      if (axios.isAxiosError(e)) {
        const detail = e.response?.data?.detail;
        toast(typeof detail === 'string' ? detail : 'Reset failed', 'error');
      } else {
        toast('Reset failed', 'error');
      }
    }
  };

  if (!email) {
    return (
      <div className="page-grid flex min-h-screen items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8 shadow-card text-center">
          <h1 className="text-[24px] font-extrabold">Admin password reset</h1>
          <p className="mt-3 text-[14px] text-text-secondary">
            Enter your admin email on the sign-in page, then click Forgot password.
          </p>
          <Button type="button" className="mt-6" fullWidth onClick={() => navigate('/admin/login')}>
            Back to admin sign in
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-grid flex min-h-screen items-center justify-center px-6 py-12">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8 shadow-card">
        <h1 className="text-[28px] font-extrabold tracking-tight">Reset admin password</h1>
        <p className="mt-2 text-text-secondary">
          {step === 'sending' && 'Sending a verification code to your registered admin email…'}
          {step === 'code' &&
            (maskedEmail
              ? `Enter the 6-digit code sent to ${maskedEmail}.`
              : 'Enter the 6-digit verification code from your email.')}
          {step === 'password' && 'Choose a new admin password.'}
        </p>

        {sendError && step === 'code' && (
          <div className="mt-4 rounded-lg border border-error/30 bg-error-container px-4 py-3 text-[14px] text-error">
            {sendError}
            <Button type="button" variant="secondary" className="mt-3" fullWidth disabled={resending} onClick={async () => {
              setResending(true);
              setStep('sending');
              await sendCode();
              setResending(false);
            }}>
              {resending ? 'Sending…' : 'Resend code'}
            </Button>
          </div>
        )}

        {step === 'sending' && !sendError && (
          <div className="mt-8 text-center text-[14px] text-text-muted">Sending verification code…</div>
        )}

        {step === 'code' && (
          <form onSubmit={codeForm.handleSubmit(onVerifyCode)} className="mt-8 space-y-4">
            <Input
              label="Verification code"
              placeholder="6-digit code"
              maxLength={6}
              inputMode="numeric"
              autoComplete="one-time-code"
              error={codeForm.formState.errors.code?.message}
              {...codeForm.register('code')}
            />
            <Button type="submit" fullWidth disabled={codeForm.formState.isSubmitting}>
              Continue
            </Button>
            <Button
              type="button"
              variant="ghost"
              fullWidth
              disabled={resending}
              onClick={async () => {
                setResending(true);
                await sendCode();
                setResending(false);
              }}
            >
              {resending ? 'Sending…' : 'Resend code'}
            </Button>
          </form>
        )}

        {step === 'password' && (
          <form onSubmit={passwordForm.handleSubmit(onResetPassword)} className="mt-8 space-y-4">
            <Input
              label="New password"
              type="password"
              error={passwordForm.formState.errors.password?.message}
              {...passwordForm.register('password')}
            />
            <Input
              label="Confirm password"
              type="password"
              error={passwordForm.formState.errors.confirm?.message}
              {...passwordForm.register('confirm')}
            />
            <Button type="submit" fullWidth disabled={passwordForm.formState.isSubmitting}>
              Reset password
            </Button>
          </form>
        )}

        <p className="mt-6 text-center text-[14px] text-text-muted">
          <Link to="/admin/login" className="text-primary">
            Back to admin sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

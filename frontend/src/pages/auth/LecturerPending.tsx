import { Link, useLocation } from 'react-router-dom';
import { Clock } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

export default function LecturerPending() {
  const location = useLocation();
  const email = (location.state as { email?: string } | null)?.email;

  return (
    <div className="page-grid flex min-h-screen items-center justify-center p-6">
      <Card className="max-w-md p-8 text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-warning/10 text-warning">
          <Clock className="h-7 w-7" />
        </div>
        <h1 className="mt-6 text-[24px] font-extrabold">Account pending approval</h1>
        <p className="mt-3 text-text-secondary">
          Your lecturer registration has been submitted. A platform administrator will verify your staff ID and activate
          your account.
        </p>
        {email && (
          <p className="mt-2 text-[14px] text-text-muted">
            We&apos;ll notify <span className="font-semibold text-text-primary">{email}</span> once approved.
          </p>
        )}
        <p className="mt-4 text-[13px] text-text-muted">
          You cannot sign in until your account is approved. This usually takes 1–2 business days.
        </p>
        <Link to="/login" className="mt-8 inline-block">
          <Button fullWidth>Back to Sign in</Button>
        </Link>
      </Card>
    </div>
  );
}

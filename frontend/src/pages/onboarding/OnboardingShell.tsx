import { Link, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { useAuth } from '@/hooks/useAuth';

const steps = [
  { path: '/onboarding/step1', label: 'Academic Profile' },
  { path: '/onboarding/step2', label: 'Curriculum Focus' },
  { path: '/onboarding/step3', label: 'Knowledge Assessment' },
  { path: '/onboarding/step4', label: 'Study Preferences' },
];

export default function OnboardingShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const current = steps.findIndex((s) => location.pathname.startsWith(s.path));

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="page-grid flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-[620px] rounded-2xl border border-border bg-card p-8 shadow-card">
        <div className="mb-4 flex items-center justify-between">
          <span className="label-caps text-text-muted">STEP {Math.max(1, current + 1)} OF 4</span>
          <span className="label-caps text-primary">{steps[Math.max(0, current)]?.label}</span>
        </div>
        <div className="mb-8 flex gap-2">
          {steps.map((_, i) => (
            <div
              key={i}
              className={cn(
                'h-1.5 flex-1 rounded-full',
                i < current ? 'bg-teal' : i === current ? 'bg-primary' : 'bg-border',
              )}
            />
          ))}
        </div>
        <Outlet />
        <div className="mt-8 flex items-center justify-between">
          {current > 0 ? (
            <Button variant="ghost" onClick={() => navigate(steps[current - 1].path)}>
              Back
            </Button>
          ) : (
            <Link to="/login" className="text-[14px] text-text-muted">
              Cancel
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

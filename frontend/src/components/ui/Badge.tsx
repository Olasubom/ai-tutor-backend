import { cn } from '@/lib/utils';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'teal' | 'primary' | 'warning' | 'error' | 'muted';
  className?: string;
}

export function Badge({ children, variant = 'default', className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide',
        variant === 'default' && 'bg-card-hover text-text-secondary',
        variant === 'teal' && 'bg-teal-container/30 text-teal',
        variant === 'primary' && 'bg-primary/10 text-primary',
        variant === 'warning' && 'bg-warning-container text-warning',
        variant === 'error' && 'bg-error-container text-error',
        variant === 'muted' && 'bg-card-hover text-text-muted',
        className,
      )}
    >
      {children}
    </span>
  );
}

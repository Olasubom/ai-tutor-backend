import { cn, masteryStatus } from '@/lib/utils';

interface ProgressBarProps {
  value: number;
  className?: string;
  autoColor?: boolean;
}

export function ProgressBar({ value, className, autoColor = true }: ProgressBarProps) {
  const status = masteryStatus(value);
  const fill =
    autoColor && status === 'mastered'
      ? 'bg-teal'
      : autoColor && status === 'in_progress'
        ? 'bg-warning'
        : autoColor
          ? 'bg-error'
          : 'bg-primary';

  return (
    <div className={cn('h-[5px] w-full overflow-hidden rounded-full bg-border', className)}>
      <div
        className={cn('h-full rounded-full transition-all', fill)}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}

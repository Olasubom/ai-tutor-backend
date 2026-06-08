import { cn } from '@/lib/utils';

interface SubjectPillProps {
  label: string;
  selected?: boolean;
  onClick?: () => void;
}

export function SubjectPill({ label, selected, onClick }: SubjectPillProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'rounded-full border px-3 py-1.5 text-[13px] font-medium transition-colors',
        selected
          ? 'border-primary bg-primary/10 text-primary'
          : 'border-border bg-card text-text-secondary hover:border-primary/40',
      )}
    >
      {label}
    </button>
  );
}

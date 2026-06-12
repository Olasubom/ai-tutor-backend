import { cn } from '@/lib/utils';

interface SemesterBadgeProps {
  semester: string | null | undefined;
  size?: 'sm' | 'md';
}

const CONFIG: Record<string, { label: string; bg: string; text: string; border: string }> = {
  First: {
    label: '1st Semester',
    bg: 'bg-blue-50',
    text: 'text-blue-700',
    border: 'border-blue-200',
  },
  Second: {
    label: '2nd Semester',
    bg: 'bg-purple-50',
    text: 'text-purple-700',
    border: 'border-purple-200',
  },
  Both: {
    label: 'Full Year',
    bg: 'bg-green-50',
    text: 'text-green-700',
    border: 'border-green-200',
  },
};

export function SemesterBadge({ semester, size = 'sm' }: SemesterBadgeProps) {
  if (!semester) return null;

  const style = CONFIG[semester] ?? {
    label: semester,
    bg: 'bg-gray-50',
    text: 'text-gray-600',
    border: 'border-gray-200',
  };

  const sizeClasses = size === 'sm' ? 'text-[10px] px-2 py-0.5' : 'text-xs px-2.5 py-1';

  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center rounded-full border font-semibold uppercase tracking-wide',
        style.bg,
        style.text,
        style.border,
        sizeClasses,
      )}
    >
      {style.label}
    </span>
  );
}

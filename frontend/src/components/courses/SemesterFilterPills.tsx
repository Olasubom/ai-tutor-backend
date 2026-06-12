import { SEMESTER_FILTER_OPTIONS, type SemesterFilter } from '@/lib/courseSemester';
import { cn } from '@/lib/utils';

interface SemesterFilterPillsProps {
  value: SemesterFilter;
  onChange: (value: SemesterFilter) => void;
}

export function SemesterFilterPills({ value, onChange }: SemesterFilterPillsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {SEMESTER_FILTER_OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={cn(
            'rounded-full border px-3 py-1.5 text-[12px] font-semibold transition-all',
            value === option.value
              ? 'border-primary bg-primary text-white'
              : 'border-border bg-card text-text-secondary hover:border-primary/40',
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

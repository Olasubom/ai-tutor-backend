import { Check } from 'lucide-react';
import { SemesterBadge } from '@/components/ui/SemesterBadge';
import { cn } from '@/lib/utils';
import type { UniversityCourse } from '@/types';

interface CourseSelectItemProps {
  course: UniversityCourse;
  selected: boolean;
  onClick: () => void;
}

export function CourseSelectItem({ course, selected, onClick }: CourseSelectItemProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex w-full items-center justify-between rounded-xl border px-4 py-3 text-left transition-all',
        selected ? 'border-primary bg-primary/5' : 'border-border bg-card hover:border-primary/30',
      )}
    >
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
        <span className="text-[14px] font-semibold">{course.course_code}</span>
        <span className="truncate text-[14px] text-text-secondary">{course.course_title}</span>
      </div>
      <div className="ml-3 flex shrink-0 items-center gap-2">
        <SemesterBadge semester={course.semester} />
        {selected && <Check className="h-4 w-4 text-primary" />}
      </div>
    </button>
  );
}

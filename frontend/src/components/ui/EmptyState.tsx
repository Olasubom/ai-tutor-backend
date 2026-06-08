import type { LucideIcon } from 'lucide-react';
import { Button } from './Button';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-border bg-card px-6 py-16 text-center">
      <Icon className="mb-4 h-12 w-12 text-gray-300 dark:text-gray-600" />
      <h3 className="text-[16px] font-semibold text-gray-500 dark:text-gray-400">{title}</h3>
      {description && <p className="mt-2 max-w-md text-[14px] text-gray-400">{description}</p>}
      {action && (
        <Button className="mt-4 px-3 py-1.5 text-[13px]" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
}

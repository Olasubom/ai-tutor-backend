import { cn } from '@/lib/utils';

interface Tab {
  id: string;
  label: string;
}

interface TabsProps {
  tabs: Tab[];
  active: string;
  onChange: (id: string) => void;
  className?: string;
}

export function Tabs({ tabs, active, onChange, className }: TabsProps) {
  return (
    <div className={cn('flex flex-wrap gap-2', className)}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={cn(
            'rounded-full px-4 py-1.5 text-[13px] font-semibold transition-colors',
            active === tab.id
              ? 'bg-text-primary text-page'
              : 'border border-border bg-card text-text-secondary hover:bg-card-hover',
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

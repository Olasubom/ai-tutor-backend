import { cn } from '@/lib/utils';
import type { HTMLAttributes } from 'react';

export function Card({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'rounded-xl border border-border bg-card p-8 shadow-card transition-colors hover:border-border/80',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

import { cn } from '@/lib/utils';
import type { SelectHTMLAttributes } from 'react';
import { forwardRef } from 'react';

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: { value: string; label: string }[];
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, error, options, id, ...props }, ref) => (
    <div className="w-full">
      {label && (
        <label htmlFor={id} className="mb-1.5 block text-[14px] font-medium text-text-primary">
          {label}
        </label>
      )}
      <select
        ref={ref}
        id={id}
        className={cn(
          'w-full rounded-lg border border-border bg-input px-3 py-2 text-[14px] text-text-primary focus:outline-none focus:ring-2 focus:ring-primary',
          error && 'border-error',
          className,
        )}
        {...props}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {error && <p className="mt-1 text-[12px] text-error">{error}</p>}
    </div>
  ),
);
Select.displayName = 'Select';

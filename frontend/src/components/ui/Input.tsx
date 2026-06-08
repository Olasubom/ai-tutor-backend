import { cn } from '@/lib/utils';
import type { InputHTMLAttributes } from 'react';
import { forwardRef } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, id, ...props }, ref) => (
    <div className="w-full">
      {label && (
        <label htmlFor={id} className="mb-1.5 block text-[14px] font-medium text-text-primary">
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={id}
        className={cn(
          'w-full rounded-lg border border-border bg-input px-3 py-2 text-[14px] text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary',
          error && 'border-error',
          className,
        )}
        {...props}
      />
      {error && <p className="mt-1 text-[12px] text-error">{error}</p>}
    </div>
  ),
);
Input.displayName = 'Input';

import { create } from 'zustand';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';

interface ToastItem {
  id: string;
  message: string;
  type: 'error' | 'success' | 'info' | 'warning';
}

interface ToastState {
  toasts: ToastItem[];
  add: (message: string, type?: ToastItem['type']) => void;
  remove: (id: string) => void;
}

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  add: (message, type = 'info') => {
    const id = Math.random().toString(36).slice(2);
    set((s) => ({ toasts: [...s.toasts, { id, message, type }] }));
    setTimeout(() => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })), 4000);
  },
  remove: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

export function ToastContainer() {
  const { toasts, remove } = useToastStore();
  return (
    <div className="fixed bottom-4 right-4 z-[9999] flex flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={cn(
            'flex min-w-[280px] items-start gap-3 rounded-lg border px-4 py-3 shadow-lg',
            t.type === 'error' && 'border-error bg-error-container text-error',
            t.type === 'success' && 'border-teal bg-teal-container/20 text-teal',
            t.type === 'warning' && 'border-warning bg-warning-container text-warning',
            t.type === 'info' && 'border-border bg-card text-text-primary',
          )}
        >
          <p className="flex-1 text-[14px]">{t.message}</p>
          <button type="button" onClick={() => remove(t.id)}>
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  );
}

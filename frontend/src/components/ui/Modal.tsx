import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  className?: string;
}

export function Modal({ open, onClose, title, children, className }: ModalProps) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className={cn('w-full max-w-lg rounded-xl border border-border bg-card p-6 shadow-lg', className)}>
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-[18px] font-bold text-text-primary">{title}</h3>
          <button type="button" onClick={onClose} className="text-text-muted hover:text-text-primary">
            <X className="h-5 w-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

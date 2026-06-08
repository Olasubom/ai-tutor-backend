import { useRef, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface TiltCardProps {
  children: ReactNode;
  className?: string;
  maxTilt?: number;
}

export function TiltCard({ children, className, maxTilt = 12 }: TiltCardProps) {
  const ref = useRef<HTMLDivElement>(null);

  const onMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const px = (x / rect.width - 0.5) * 2;
    const py = (y / rect.height - 0.5) * 2;
    el.style.transform = `perspective(1000px) rotateX(${-py * maxTilt}deg) rotateY(${px * maxTilt}deg) scale3d(1.02, 1.02, 1.02)`;
  };

  const onLeave = () => {
    const el = ref.current;
    if (!el) return;
    el.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)';
  };

  return (
    <div className={cn('relative', className)} style={{ perspective: '1000px' }}>
      <div
        ref={ref}
        onMouseMove={onMove}
        onMouseLeave={onLeave}
        className="transition-transform duration-200 ease-out will-change-transform"
        style={{ transformStyle: 'preserve-3d' }}
      >
        {children}
      </div>
    </div>
  );
}

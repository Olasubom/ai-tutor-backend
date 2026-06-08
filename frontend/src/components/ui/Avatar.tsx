import { cn } from '@/lib/utils';

interface AvatarProps {
  name?: string;
  src?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function Avatar({ name, src, size = 'md', className }: AvatarProps) {
  const initials = name
    ?.split(' ')
    .map((n) => n[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();
  const sizes = { sm: 'h-8 w-8 text-xs', md: 'h-10 w-10 text-sm', lg: 'h-12 w-12 text-base' };
  return (
    <div
      className={cn(
        'flex shrink-0 items-center justify-center rounded-full bg-primary font-bold text-white',
        sizes[size],
        className,
      )}
    >
      {src ? <img src={src} alt={name} className="h-full w-full rounded-full object-cover" /> : initials}
    </div>
  );
}

import { Moon, Sun } from 'lucide-react';
import { useThemeStore } from '@/stores/themeStore';
import { cn } from '@/lib/utils';

export function Toggle({
  checked,
  onChange,
  className,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  className?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={cn(
        'relative h-7 w-12 rounded-full transition-colors',
        checked ? 'bg-primary' : 'bg-border',
        className,
      )}
    >
      <span
        className={cn(
          'absolute top-0.5 h-6 w-6 rounded-full bg-white shadow transition-transform',
          checked ? 'left-[22px]' : 'left-0.5',
        )}
      />
    </button>
  );
}

export function ThemeToggle({ className }: { className?: string }) {
  const { theme, toggleTheme } = useThemeStore();
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label="Toggle theme"
      className={cn(
        'relative flex h-8 w-14 items-center rounded-full p-1 transition-colors',
        isDark ? 'bg-primary' : 'bg-border',
        className,
      )}
    >
      <span
        className={cn(
          'flex h-6 w-6 items-center justify-center rounded-full bg-white shadow transition-transform',
          isDark ? 'translate-x-6' : 'translate-x-0',
        )}
      >
        {isDark ? <Moon className="h-3.5 w-3.5 text-primary" /> : <Sun className="h-3.5 w-3.5 text-warning" />}
      </span>
    </button>
  );
}

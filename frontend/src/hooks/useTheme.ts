import { useThemeStore } from '@/stores/themeStore';

export function useTheme() {
  const { theme, setTheme, toggleTheme, init } = useThemeStore();
  return { theme, setTheme, toggleTheme, init, isDark: theme === 'dark' };
}

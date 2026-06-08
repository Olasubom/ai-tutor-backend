import { create } from 'zustand';

type Theme = 'light' | 'dark';

interface ThemeState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  init: () => void;
}

function applyTheme(theme: Theme) {
  const root = document.documentElement;
  if (theme === 'dark') root.classList.add('dark');
  else root.classList.remove('dark');
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  theme: 'light',
  setTheme: (theme) => {
    localStorage.setItem('theme', theme);
    applyTheme(theme);
    set({ theme });
  },
  toggleTheme: () => {
    const next = get().theme === 'light' ? 'dark' : 'light';
    get().setTheme(next);
  },
  init: () => {
    const stored = (localStorage.getItem('theme') as Theme | null) ?? 'light';
    applyTheme(stored);
    set({ theme: stored });
  },
}));

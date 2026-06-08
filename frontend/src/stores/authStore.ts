import { create } from 'zustand';
import type { AuthUser, UserRole } from '@/types';
import { learnerIdFromUser } from '@/lib/utils';

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  login: (user: AuthUser, token: string) => void;
  logout: () => void;
  init: () => void;
  updateUser: (patch: Partial<AuthUser>) => void;
}

const STORAGE_KEY = 'aitutor_auth';

function persist(token: string | null, user: AuthUser | null) {
  if (token && user) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ token, user }));
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  isAuthenticated: false,
  login: (user, token) => {
    const enriched: AuthUser = {
      ...user,
      learner_id: user.role === 'student' ? learnerIdFromUser(user.user_id) : user.learner_id,
    };
    persist(token, enriched);
    set({ token, user: enriched, isAuthenticated: true });
  },
  logout: () => {
    persist(null, null);
    set({ token: null, user: null, isAuthenticated: false });
  },
  init: () => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    try {
      const { token, user } = JSON.parse(raw) as { token: string; user: AuthUser };
      set({ token, user, isAuthenticated: true });
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    }
  },
  updateUser: (patch) =>
    set((s) => {
      if (!s.user) return s;
      const user = { ...s.user, ...patch };
      persist(s.token, user);
      return { user };
    }),
}));

export function getRedirectForRole(role: UserRole): string {
  switch (role) {
    case 'student':
      return '/student/dashboard';
    case 'lecturer':
      return '/lecturer/dashboard';
    case 'admin':
      return '/admin';
    default:
      return '/';
  }
}

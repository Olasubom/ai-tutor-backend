import { create } from 'zustand';
import type { UserRole } from '@/types';

const TOKEN_KEY = 'ai_tutor_token';
const USER_KEY = 'ai_tutor_user';

export interface TokenResponse {
  access_token: string;
  token_type: string;
  role: UserRole;
  user_id: string;
  name: string;
  email: string;
}

const ONBOARDING_KEY = 'ai_tutor_onboarding_complete';

interface AuthState {
  token: string | null;
  user_id: string | null;
  name: string | null;
  email: string | null;
  role: UserRole | null;
  isAuthenticated: boolean;
  onboardingComplete: boolean;
  login: (data: TokenResponse) => void;
  logout: () => void;
  hydrate: () => void;
  setOnboardingComplete: (userId: string) => void;
  isOnboardingComplete: (userId: string) => boolean;
}

function parseJwtExp(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1] ?? '')) as { exp?: number };
    return payload.exp ?? null;
  } catch {
    return null;
  }
}

function persist(token: string | null, user: TokenResponse | null) {
  if (token && user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    // legacy keys for gradual migration
    localStorage.setItem(
      'aitutor_auth',
      JSON.stringify({
        token,
        user: {
          user_id: user.user_id,
          role: user.role,
          name: user.name,
          email: user.email,
          learner_id: user.user_id,
        },
      }),
    );
  } else {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem('aitutor_auth');
    localStorage.removeItem('at_access');
    localStorage.removeItem('at_refresh');
    localStorage.removeItem('at_user');
  }
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: null,
  user_id: null,
  name: null,
  email: null,
  role: null,
  isAuthenticated: false,
  onboardingComplete: false,
  login: (data) => {
    persist(data.access_token, data);
    set({
      token: data.access_token,
      user_id: data.user_id,
      name: data.name,
      email: data.email,
      role: data.role,
      isAuthenticated: true,
      onboardingComplete: get().isOnboardingComplete(data.user_id),
    });
  },
  logout: () => {
    persist(null, null);
    set({
      token: null,
      user_id: null,
      name: null,
      email: null,
      role: null,
      isAuthenticated: false,
      onboardingComplete: false,
    });
  },
  hydrate: () => {
    const token =
      localStorage.getItem(TOKEN_KEY) ||
      localStorage.getItem('at_access') ||
      (() => {
        try {
          const legacy = JSON.parse(localStorage.getItem('aitutor_auth') ?? 'null') as { token?: string } | null;
          return legacy?.token ?? null;
        } catch {
          return null;
        }
      })();
    const raw =
      localStorage.getItem(USER_KEY) ||
      localStorage.getItem('at_user') ||
      (() => {
        try {
          const legacy = JSON.parse(localStorage.getItem('aitutor_auth') ?? 'null') as {
            user?: TokenResponse;
          } | null;
          return legacy?.user ? JSON.stringify(legacy.user) : null;
        } catch {
          return null;
        }
      })();
    if (!token || !raw) return;
    const exp = parseJwtExp(token);
    if (exp && exp * 1000 < Date.now()) {
      persist(null, null);
      return;
    }
    try {
      const user = JSON.parse(raw) as TokenResponse;
      set({
        token,
        user_id: user.user_id,
        name: user.name,
        email: user.email,
        role: user.role,
        isAuthenticated: true,
        onboardingComplete: get().isOnboardingComplete(user.user_id),
      });
    } catch {
      persist(null, null);
    }
  },
  setOnboardingComplete: (userId) => {
    localStorage.setItem(ONBOARDING_KEY, userId);
    set({ onboardingComplete: true });
  },
  isOnboardingComplete: (userId) => localStorage.getItem(ONBOARDING_KEY) === userId,
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

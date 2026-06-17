import { useAuthStore, type TokenResponse } from '@/stores/authStore';

export function useAuth() {
  const store = useAuthStore();
  const user_id = store.user_id ?? '';
  const name = store.name ?? '';
  return {
    user: user_id
      ? {
          user_id,
          name,
          email: store.email ?? '',
          role: store.role ?? 'student',
          learner_id: user_id,
        }
      : null,
    token: store.token,
    isAuthenticated: store.isAuthenticated,
    login: store.login,
    logout: () => {
      store.logout();
      window.location.href = '/login';
    },
    updateUser: (patch: { name?: string }) => {
      if (patch.name) {
        useAuthStore.setState({ name: patch.name });
        const raw = localStorage.getItem('ai_tutor_user');
        if (raw) {
          try {
            const user = JSON.parse(raw) as TokenResponse;
            localStorage.setItem('ai_tutor_user', JSON.stringify({ ...user, name: patch.name }));
          } catch {
            /* ignore */
          }
        }
      }
    },
    user_id,
    learnerId: user_id,
    name,
    email: store.email,
    role: store.role,
  };
}

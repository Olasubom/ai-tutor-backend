import { useAuthStore } from '@/stores/authStore';

export function useAuth() {
  const store = useAuthStore();
  const user_id = store.user_id ?? '';
  return {
    user: store.user_id
      ? {
          user_id: store.user_id,
          name: store.name ?? '',
          email: store.email ?? '',
          role: store.role ?? 'student',
          learner_id: store.user_id,
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
            const user = JSON.parse(raw);
            localStorage.setItem('ai_tutor_user', JSON.stringify({ ...user, name: patch.name }));
          } catch {
            /* ignore */
          }
        }
      }
    },
    user_id,
    learnerId: user_id,
    name: store.name,
    email: store.email,
    role: store.role,
  };
}

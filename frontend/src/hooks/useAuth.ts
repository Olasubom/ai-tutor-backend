import { useAuthStore } from '@/stores/authStore';

export function useAuth() {
  const { user, token, isAuthenticated, login, logout, updateUser } = useAuthStore();
  const learnerId = user?.learner_id ?? (user ? `learner_${user.user_id}` : '');
  return { user, token, isAuthenticated, login, logout, updateUser, learnerId };
}

import { useToastStore } from '@/components/ui/Toast';

const SESSION_EXPIRED_TOAST_KEY = 'at_session_expired_toast';

let sessionExpiredToastShown = false;

export function showSessionExpiredToast(): void {
  if (sessionExpiredToastShown || sessionStorage.getItem(SESSION_EXPIRED_TOAST_KEY) === '1') return;
  sessionExpiredToastShown = true;
  sessionStorage.setItem(SESSION_EXPIRED_TOAST_KEY, '1');
  useToastStore.getState().add('Session expired. Please sign in again.', 'warning');
  setTimeout(() => {
    sessionExpiredToastShown = false;
    sessionStorage.removeItem(SESSION_EXPIRED_TOAST_KEY);
  }, 5000);
}

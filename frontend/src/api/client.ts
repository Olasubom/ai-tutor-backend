import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { useToastStore } from '@/components/ui/Toast';
import { useAuthStore } from '@/stores/authStore';
import { showSessionExpiredToast } from '@/utils/sessionExpiredToast';

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 120000,
});

function getApiKey(): string {
  const fromEnv = import.meta.env.VITE_API_KEY as string | undefined;
  const fromStorage = localStorage.getItem('aitutor_api_key');
  return fromStorage || fromEnv || 'change_me';
}

function getDevToken(): string {
  const fromEnv = import.meta.env.VITE_DEV_TOKEN as string | undefined;
  const fromStorage = localStorage.getItem('aitutor_dev_token');
  return fromStorage || fromEnv || 'dev-secret';
}

function isAuthPage(): boolean {
  const currentPath = window.location.pathname;
  return currentPath === '/login' || currentPath.startsWith('/register');
}

let sessionExpiredHandled = false;

export function handleSessionExpired(): void {
  if (sessionExpiredHandled || isAuthPage()) return;
  sessionExpiredHandled = true;
  useAuthStore.getState().logout();
  window.location.href = '/login?expired=1';
}

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const { token } = useAuthStore.getState();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  if (config.headers['X-Skip-Api-Key'] !== 'true') {
    config.headers['X-API-Key'] = getApiKey();
  }

  if (config.headers['X-Use-Dev-Token'] === 'true') {
    config.headers['X-Dev-Token'] = getDevToken();
    delete config.headers['X-Use-Dev-Token'];
  }

  delete config.headers['X-Skip-Api-Key'];
  return config;
});

apiClient.interceptors.response.use(
  (res) => res,
  async (error: AxiosError<{ detail?: string | { detail?: string } }>) => {
    const toast = useToastStore.getState().add;
    const requestUrl = error.config?.url ?? '';

    if (error.response?.status === 401) {
      const hadToken = Boolean(useAuthStore.getState().token);
      const isAuthEndpoint =
        requestUrl.includes('/auth/login') ||
        requestUrl.includes('/auth/register') ||
        requestUrl.includes('/auth/google');

      if (hadToken && !isAuthEndpoint) {
        useAuthStore.getState().logout();
        if (!isAuthPage()) {
          showSessionExpiredToast();
          handleSessionExpired();
        }
      }
      return Promise.reject(error);
    }

    if (error.response?.status === 403) {
      const detail = error.response.data?.detail;
      toast(typeof detail === 'string' ? detail : 'Access denied.', 'warning');
    } else if (error.response?.status === 500) {
      toast('Server error. Please try again.', 'error');
    } else if (!error.response) {
      toast('Cannot connect to server. Check that the backend is running.', 'error');
    } else if (error.response?.status !== 404) {
      const detail = error.response.data?.detail;
      const msg = typeof detail === 'string' ? detail : detail?.detail ?? 'Something went wrong. Please try again.';
      toast(msg, 'error');
    }
    return Promise.reject(error);
  },
);

export function setApiCredentials(apiKey: string, devToken?: string) {
  localStorage.setItem('aitutor_api_key', apiKey);
  if (devToken) localStorage.setItem('aitutor_dev_token', devToken);
}

export function getApiBaseUrl(): string {
  return baseURL;
}

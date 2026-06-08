import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { useToastStore } from '@/components/ui/Toast';

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

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('aitutor_auth');
  if (token) {
    try {
      const parsed = JSON.parse(token) as { token?: string };
      if (parsed.token) {
        const payload = JSON.parse(atob(parsed.token.split('.')[1] ?? '')) as { exp?: number };
        if (payload.exp && payload.exp * 1000 < Date.now()) {
          localStorage.removeItem('aitutor_auth');
          window.location.href = '/login?expired=1';
          return config;
        }
        config.headers.Authorization = `Bearer ${parsed.token}`;
      }
    } catch {
      /* ignore */
    }
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
    if (error.response?.status === 401) {
      localStorage.removeItem('aitutor_auth');
      window.location.href = '/login?expired=1';
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

import axios from 'axios';
import { apiClient, getApiBaseUrl } from './client';
import type { TokenResponse } from '@/stores/authStore';

export async function login(email: string, password: string): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>('/auth/login', { email, password });
  return data;
}

export async function registerStudent(body: {
  email: string;
  name: string;
  password: string;
  department?: string;
  college?: string;
  academic_level?: string;
  institution?: string;
}): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>('/auth/register/student', body);
  return data;
}

export async function registerLecturer(body: {
  email: string;
  name: string;
  password: string;
  nuc_staff_id: string;
  college: string;
  department: string;
}): Promise<{ message: string }> {
  const { data } = await apiClient.post<{ message: string }>('/auth/register/lecturer', body, {
    validateStatus: (s) => s === 202 || s < 300,
  });
  return data;
}

export async function getMe() {
  const { data } = await apiClient.get('/auth/me');
  return data;
}

export async function patchProfile(body: Record<string, string>) {
  const { data } = await apiClient.patch('/auth/profile', body);
  return data;
}

export async function getOnboardingStatus() {
  const { data } = await apiClient.get<{ is_complete: boolean; missing_steps: string[] }>(
    '/auth/onboarding/status',
  );
  return data;
}

export async function completeOnboarding(body: Record<string, unknown>) {
  const { data } = await apiClient.post('/auth/onboarding/complete', body);
  return data;
}

export async function requestPasswordResetCode(email: string) {
  const { data } = await apiClient.post<{ message: string; dev_code?: string; email_sent?: boolean }>(
    '/auth/forgot-password',
    { email },
  );
  return { message: data.message, devCode: data.dev_code, emailSent: data.email_sent ?? false };
}

export async function resetPasswordWithCode(email: string, code: string, newPassword: string) {
  await apiClient.post('/auth/reset-password', { email, code, new_password: newPassword });
}

export async function requestAdminPasswordResetCode(email: string) {
  const { data } = await apiClient.post<{
    message: string;
    email_sent: boolean;
    masked_email: string;
  }>('/auth/admin/forgot-password', { email });
  return data;
}

export async function verifyAdminResetCode(email: string, code: string) {
  await apiClient.post('/auth/admin/verify-reset-code', { email, code });
}

export async function resetAdminPasswordWithCode(email: string, code: string, newPassword: string) {
  await apiClient.post('/auth/admin/reset-password', { email, code, new_password: newPassword });
}

export async function loginWithGoogle(credential: string): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>('/auth/google', { credential });
  return data;
}

export async function adminLogin(email: string, password: string): Promise<TokenResponse> {
  try {
    const data = await login(email, password);
    if (data.role !== 'admin') {
      throw new Error('ADMIN_ROLE_REQUIRED');
    }
    return data;
  } catch (e) {
    if (axios.isAxiosError(e)) {
      const detail = e.response?.data?.detail;
      const status = e.response?.status;
      if (!e.response) {
        throw new Error(`Cannot reach server. Is the backend running at ${getApiBaseUrl()}?`);
      }
      if (status === 401) {
        throw new Error('Incorrect email or password');
      }
      if (status === 403 && typeof detail === 'string') {
        if (detail.toLowerCase().includes('pending')) {
          throw new Error('Account pending approval');
        }
        if (detail.toLowerCase().includes('disabled')) {
          throw new Error('Account disabled.');
        }
      }
    }
    if (e instanceof Error && e.message === 'ADMIN_ROLE_REQUIRED') {
      throw e;
    }
    throw e instanceof Error ? e : new Error('Login failed');
  }
}

export type AdminLoginErrorKind = 'credentials' | 'not_admin' | 'pending' | 'network' | 'other';

export function parseAdminLoginError(error: unknown): { kind: AdminLoginErrorKind; message: string } {
  if (!(error instanceof Error)) {
    return { kind: 'other', message: 'Login failed' };
  }
  if (error.message === 'ADMIN_ROLE_REQUIRED') {
    return {
      kind: 'not_admin',
      message: 'This account does not have admin access. Use Student / Lecturer login instead.',
    };
  }
  if (error.message.startsWith('Cannot reach server')) {
    return { kind: 'network', message: error.message };
  }
  if (error.message === 'Incorrect email or password') {
    return { kind: 'credentials', message: error.message };
  }
  if (error.message === 'Account pending approval') {
    return { kind: 'pending', message: error.message };
  }
  return { kind: 'other', message: error.message };
}

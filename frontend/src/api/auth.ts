import { apiClient } from './client';
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

export async function loginWithGoogle(_credential: string) {
  throw new Error('Google sign-in requires backend OAuth configuration.');
}

export async function adminLogin(email: string, password: string): Promise<TokenResponse> {
  const data = await login(email, password);
  if (data.role !== 'admin') {
    throw new Error('Not authorized. Admin role required.');
  }
  return data;
}

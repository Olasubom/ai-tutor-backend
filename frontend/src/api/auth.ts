import { localPlatform } from './localPlatform';
import type { AuthUser } from '@/types';

export async function login(email: string, password: string) {
  const result = localPlatform.login(email, password);
  if (!result) throw new Error('Invalid email or password.');
  return result;
}

export async function loginWithGoogle(credential: string) {
  return localPlatform.loginWithGoogle(credential);
}

export async function registerStudent(data: { name: string; email: string; password: string }) {
  return localPlatform.registerStudent(data);
}

export async function registerLecturer(data: {
  name: string;
  email: string;
  staff_id: string;
  faculty_id: string;
  department_id: string;
  password: string;
}) {
  return localPlatform.registerLecturer(data);
}

export async function adminLogin(email: string, secret: string) {
  const result = localPlatform.adminLogin(email, secret);
  if (!result) throw new Error('Invalid admin credentials.');
  return result;
}

export async function refreshToken(): Promise<{ token: string; user: AuthUser } | null> {
  const raw = localStorage.getItem('aitutor_auth');
  if (!raw) return null;
  try {
    const { user } = JSON.parse(raw) as { token: string; user: AuthUser };
    const token = `aitutor.${btoa(JSON.stringify({ ...user, exp: Date.now() + 7 * 24 * 60 * 60 * 1000 }))}`;
    return { token, user };
  } catch {
    return null;
  }
}

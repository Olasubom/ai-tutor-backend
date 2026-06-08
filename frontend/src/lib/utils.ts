import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(value: string | Date): string {
  const d = typeof value === 'string' ? new Date(value) : value;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function formatTime(value: string | Date): string {
  const d = typeof value === 'string' ? new Date(value) : value;
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

export function masteryStatus(pct: number): 'mastered' | 'in_progress' | 'review' {
  if (pct >= 80) return 'mastered';
  if (pct >= 50) return 'in_progress';
  return 'review';
}

export function masteryColor(pct: number): string {
  const s = masteryStatus(pct);
  if (s === 'mastered') return 'text-teal';
  if (s === 'in_progress') return 'text-warning';
  return 'text-error';
}

export function generateId(prefix = 'id'): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

export function learnerIdFromUser(userId: string): string {
  return `learner_${userId}`;
}

import { apiClient } from './client';
import type { LearnerTask } from '@/types';

export async function getLearnerTasks(learnerId: string): Promise<LearnerTask[]> {
  const { data } = await apiClient.get<LearnerTask[]>(`/tutor/tasks/${learnerId}`);
  return data ?? [];
}

export async function createTask(
  learnerId: string,
  body: { text: string; due_date: string; priority?: string; course?: string },
) {
  const { data } = await apiClient.post(`/tutor/tasks/${learnerId}`, body);
  return data;
}

export async function completeTask(learnerId: string, taskId: string) {
  const { data } = await apiClient.patch(`/tutor/tasks/${learnerId}/${taskId}/complete`);
  return data;
}

export async function deleteTask(learnerId: string, taskId: string) {
  await apiClient.delete(`/tutor/tasks/${learnerId}/${taskId}`);
}

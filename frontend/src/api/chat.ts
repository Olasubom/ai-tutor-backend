import { apiClient } from './client';
import type { TutorChatRequest, TutorChatResponse } from '@/types';

export async function sendChatMessage(payload: TutorChatRequest): Promise<TutorChatResponse> {
  const { data } = await apiClient.post<TutorChatResponse>('/tutor/chat', payload);
  return data;
}

export async function checkTutorHealth(): Promise<{ status: string; service: string }> {
  const { data } = await apiClient.get('/tutor/health');
  return data;
}

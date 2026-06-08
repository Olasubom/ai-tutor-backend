import { apiClient } from './client';

export interface ChatSession {
  session_id: string;
  subject: string;
  started_at: string;
  ended_at: string;
  message_count: number;
  topics_covered: string[];
  summary: string;
}

export async function getSessions(learnerId: string) {
  const { data } = await apiClient.get<ChatSession[]>(`/sessions/${learnerId}`);
  return data;
}

export async function getSessionMessages(learnerId: string, sessionId: string) {
  const { data } = await apiClient.get<Array<{ role: string; content: string; timestamp: string }>>(
    `/sessions/${learnerId}/${sessionId}/messages`,
  );
  return data;
}

import { apiClient, getApiBaseUrl } from './client';
import { useAuthStore } from '@/stores/authStore';
import type { TutorChatRequest, TutorChatResponse } from '@/types';

export async function sendChatMessage(payload: TutorChatRequest): Promise<TutorChatResponse> {
  const { data } = await apiClient.post<TutorChatResponse>('/tutor/chat', payload);
  return data;
}

function streamHeaders(): Record<string, string> {
  const apiKey =
    localStorage.getItem('aitutor_api_key') || (import.meta.env.VITE_API_KEY as string) || 'change_me';
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-API-Key': apiKey,
  };
  const { token } = useAuthStore.getState();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

export async function streamChatMessage(
  payload: TutorChatRequest,
  handlers: {
    onDelta: (chunk: string) => void;
    onDone: (fullResponse: string, sessionId?: string) => void;
    onError: (message: string) => void;
  },
): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/tutor/chat?stream=true`, {
    method: 'POST',
    headers: streamHeaders(),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(err || `Stream failed (${response.status})`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response stream available');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      try {
        const data = JSON.parse(line.slice(6)) as {
          delta?: string;
          done?: boolean;
          full_response?: string;
          session_id?: string;
          type?: string;
          content?: string;
          detail?: string;
        };
        if (data.type === 'error' || data.detail) {
          handlers.onError(data.detail ?? 'Stream error');
          continue;
        }
        if (data.delta) handlers.onDelta(data.delta);
        if (data.type === 'delta' && data.content) handlers.onDelta(data.content);
        if (data.done) {
          handlers.onDone(data.full_response ?? '', data.session_id);
        }
      } catch {
        /* skip malformed chunks */
      }
    }
  }
}

export async function checkTutorHealth(): Promise<{ status: string; service: string }> {
  const { data } = await apiClient.get('/tutor/health');
  return data;
}

import { apiClient } from './client';
import type { ContentItem, TutorRecommendRequest, TutorRecommendResponse } from '@/types';

export async function getRecommendations(
  payload: TutorRecommendRequest,
): Promise<TutorRecommendResponse> {
  const { data } = await apiClient.post<TutorRecommendResponse>('/tutor/recommend', payload);
  return data;
}

export async function getContentItems(params?: {
  topic?: string;
  modality?: string;
  source_type?: string;
  source_origin?: string;
  limit?: number;
}): Promise<{ count: number; items: ContentItem[] }> {
  const { data } = await apiClient.get('/tutor/content-items', {
    params,
    headers: { 'X-Use-Dev-Token': 'true' },
  });
  return data;
}

export async function ingestSources(body: {
  source: string;
  topics?: string[];
  max_per_topic?: number;
}) {
  const { data } = await apiClient.post('/tutor/ingest-sources', body, {
    headers: { 'X-Use-Dev-Token': 'true' },
  });
  return data;
}

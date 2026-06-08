import { apiClient } from './client';

export async function recordEngagement(
  learnerId: string,
  eventType: string,
  metadata: Record<string, unknown> = {},
) {
  const { data } = await apiClient.post(`/engagement/${learnerId}`, {
    event_type: eventType,
    metadata,
  });
  return data;
}

export async function getHeatmap(learnerId: string, period: '7d' | '30d' | 'all' = 'all') {
  const { data } = await apiClient.get<Array<{ date: string; count: number }>>(
    `/engagement/${learnerId}/heatmap`,
    { params: { period } },
  );
  return data;
}

export async function getEngagementMetrics(learnerId: string, period: '7d' | '30d' | 'all' = '7d') {
  const { data } = await apiClient.get<
    Array<{ date: string; study_time: number; questions_answered: number }>
  >(`/engagement/${learnerId}`, { params: { period } });
  return data;
}

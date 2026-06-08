import { apiClient } from './client';

export interface MemoryProfile {
  strengths: string[];
  weak_areas: string[];
  study_habits: {
    preferred_time: string;
    avg_session_length_minutes: number;
    sessions_per_week: number;
    preferred_content_type: string;
  };
  recent_session_summaries: string[];
  total_interactions: number;
  last_active: string;
}

export async function getMemoryProfile(learnerId: string) {
  const { data } = await apiClient.get<MemoryProfile>(`/memory-profile/${learnerId}`);
  return data;
}

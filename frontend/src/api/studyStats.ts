import { apiClient } from './client';

export interface StudyStatsResponse {
  weekly_goal_hours: number;
  completed_hours: number;
  percent: number;
  message: string;
}

export async function getStudyStats(): Promise<StudyStatsResponse> {
  const { data } = await apiClient.get<StudyStatsResponse>('/tutor/study-stats');
  return data;
}

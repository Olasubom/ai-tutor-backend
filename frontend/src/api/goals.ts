import { apiClient } from './client';

export interface LearningGoal {
  goal_id: string;
  topic: string;
  target_mastery: number;
  target_date: string;
  current_mastery: number;
  progress_percentage: number;
  days_remaining: number;
  on_track: boolean;
}

export async function getGoals(learnerId: string) {
  const { data } = await apiClient.get<LearningGoal[]>(`/goals/${learnerId}`);
  return data;
}

export async function createGoal(
  learnerId: string,
  body: { topic: string; target_mastery: number; target_date: string },
) {
  const { data } = await apiClient.post(`/goals/${learnerId}`, body);
  return data;
}

export async function deleteGoal(learnerId: string, goalId: string) {
  await apiClient.delete(`/goals/${learnerId}/${goalId}`);
}

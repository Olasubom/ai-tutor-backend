import { apiClient } from './client';
import type { LearnerProfileResponse } from '@/types';

export async function getLearnerProfile(learnerId: string): Promise<LearnerProfileResponse> {
  const { data } = await apiClient.get<LearnerProfileResponse>(`/tutor/profile/${learnerId}`);
  return data;
}

export async function resetLearnerState(learnerId: string) {
  const { data } = await apiClient.delete(`/tutor/reset-learner/${learnerId}`, {
    headers: { 'X-Use-Dev-Token': 'true' },
  });
  return data;
}

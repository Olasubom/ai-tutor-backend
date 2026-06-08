import { apiClient } from './client';

export interface AtRiskStudent {
  learner_id: string;
  name: string;
  department: string;
  level: string;
  risk_factors: string[];
  severity: 'low' | 'medium' | 'high';
  last_active: string;
  suggested_action: string;
}

export async function getAtRiskStudents(lecturerId: string) {
  const { data } = await apiClient.get<AtRiskStudent[]>(`/at-risk/${lecturerId}`);
  return data;
}

export async function dismissAtRiskAlert(lecturerId: string, learnerId: string) {
  await apiClient.patch(`/at-risk/${lecturerId}/${learnerId}/dismiss`);
}

export async function sendResourceToStudent(body: {
  lecturer_id: string;
  learner_id: string;
  resource_url: string;
  note?: string;
}) {
  await apiClient.post('/lecturer/send-resource', body);
}

import { apiClient } from './client';

export async function patchProfile(body: {
  learner_id: string;
  full_name?: string;
  field_of_study?: string;
  institution?: string;
  department_id?: string;
  academic_level?: string;
}) {
  const { data } = await apiClient.patch<{ ok: boolean }>('/auth/profile', body);
  return data;
}

import { apiClient, getApiBaseUrl } from './client';

export interface CurriculumModule {
  module_number?: number;
  step?: number;
  content_item_id?: string;
  item_id?: string;
  title?: string;
  description?: string;
  objective?: string;
  topic?: string;
  module_type?: string;
  estimated_minutes?: number;
  modality?: string;
  bloom_level?: string;
  source_type?: string;
  source_url?: string;
  status?: 'not_started' | 'in_progress' | 'completed' | 'locked';
  percent_complete?: number;
}

export interface CurriculumResponse {
  learner_id: string;
  course_id: string;
  course_code: string;
  course_title: string;
  modules: CurriculumModule[];
  source?: 'lecturer_materials' | 'external_supplemental' | null;
  status: 'generated' | 'not_generated' | 'not_found' | 'not_enrolled';
  message?: string;
}

export async function fetchCurriculum(
  learnerId: string,
  courseId: string,
): Promise<CurriculumResponse> {
  const { data } = await apiClient.get<CurriculumResponse>(`/tutor/curriculum/${learnerId}`, {
    params: { course_id: courseId },
  });
  return data;
}

export async function requestCurriculumUpdate(
  learnerId: string,
  courseId: string,
): Promise<{ message: string; status: string }> {
  const { data } = await apiClient.post<{ message: string; status: string }>(
    '/tutor/curriculum/request-update',
    { learner_id: learnerId, course_id: courseId },
  );
  return data;
}

export async function updateModuleProgress(
  learnerId: string,
  contentItemId: string,
  percentComplete: number,
  status: 'in_progress' | 'completed',
): Promise<void> {
  await apiClient.post('/tutor/module-progress', {
    learner_id: learnerId,
    content_item_id: contentItemId,
    percent_complete: percentComplete,
    status,
  });
}

export function resolveModuleUrl(sourceUrl?: string | null): string {
  if (!sourceUrl) return '';
  if (sourceUrl.startsWith('http://') || sourceUrl.startsWith('https://')) return sourceUrl;
  return `${getApiBaseUrl()}${sourceUrl.startsWith('/') ? sourceUrl : `/${sourceUrl}`}`;
}

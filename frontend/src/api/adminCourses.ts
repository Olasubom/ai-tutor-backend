import { apiClient } from './client';
import type { UniversityCourse } from '@/types';

export async function fetchAdminCourses(departmentId: string, level: string): Promise<UniversityCourse[]> {
  const { data } = await apiClient.get<UniversityCourse[]>('/admin/courses', {
    params: { department_id: departmentId, level },
  });
  return data ?? [];
}

export async function syncCourseToBackend(course: UniversityCourse): Promise<void> {
  await apiClient.post('/admin/courses/sync', course);
}

export async function deleteCourseFromBackend(courseId: string): Promise<void> {
  await apiClient.delete(`/admin/courses/${courseId}`);
}

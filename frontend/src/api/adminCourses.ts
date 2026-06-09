import { apiClient } from './client';
import type { UniversityCourse } from '@/types';

function mapCourse(c: Record<string, unknown>): UniversityCourse {
  return {
    id: String(c.id),
    department_id: String(c.department_id),
    course_code: String(c.course_code),
    course_title: String(c.course_title),
    level: String(c.level),
    units: Number(c.credit_units ?? 0),
    semester: (c.semester as UniversityCourse['semester']) ?? 'First',
    type: (c.course_type as UniversityCourse['type']) ?? 'Compulsory',
    description: c.description ? String(c.description) : undefined,
  };
}

export async function fetchAdminCourses(departmentId: string, level: string): Promise<UniversityCourse[]> {
  const { data } = await apiClient.get<Record<string, unknown>[]>('/admin/courses', {
    params: { department_id: departmentId, level },
  });
  return (data ?? []).map(mapCourse);
}

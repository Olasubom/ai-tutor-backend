import { apiClient } from './client';
import type { UniversityCourse } from '@/types';
import { normalizeCourseLevel } from '@/lib/courseLevel';
import { normalizeSemester } from '@/lib/courseSemester';

function mapCourse(c: Record<string, unknown>): UniversityCourse {
  return {
    id: String(c.id),
    department_id: String(c.department_id),
    course_code: String(c.course_code),
    course_title: String(c.course_title),
    level: String(c.level),
    units: Number(c.credit_units ?? 0),
    semester: normalizeSemester(c.semester ? String(c.semester) : undefined),
    type: (c.course_type as UniversityCourse['type']) ?? 'Compulsory',
    description: c.description ? String(c.description) : undefined,
  };
}

export async function fetchAdminCourses(departmentId: string, level: string): Promise<UniversityCourse[]> {
  const normalizedLevel = normalizeCourseLevel(level) ?? level;
  const { data } = await apiClient.get<Record<string, unknown>[]>('/admin/courses', {
    params: { department_id: departmentId, level: normalizedLevel },
  });
  return (data ?? []).map(mapCourse);
}

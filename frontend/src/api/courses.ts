import { apiClient } from './client';
import type { College, Department, UniversityCourse } from '@/types';

export async function fetchColleges(): Promise<College[]> {
  const { data } = await apiClient.get<College[]>('/admin/colleges');
  return data ?? [];
}

export async function fetchDepartments(collegeId?: string): Promise<Department[]> {
  const { data } = await apiClient.get<Department[]>('/admin/departments', {
    params: collegeId ? { college_id: collegeId } : undefined,
  });
  return data ?? [];
}

export async function fetchCourses(departmentId?: string, level?: string): Promise<UniversityCourse[]> {
  const { data } = await apiClient.get<Array<Record<string, unknown>>>('/admin/courses', {
    params: {
      ...(departmentId ? { department_id: departmentId } : {}),
      ...(level ? { level } : {}),
    },
  });
  return (data ?? []).map((c) => ({
    id: String(c.id),
    department_id: String(c.department_id),
    course_code: String(c.course_code),
    course_title: String(c.course_title),
    level: String(c.level),
    units: Number(c.credit_units ?? c.units ?? 0),
    semester: (c.semester as UniversityCourse['semester']) ?? 'First',
    type: (c.course_type as UniversityCourse['type']) ?? 'Compulsory',
    description: c.description ? String(c.description) : undefined,
  }));
}

export async function createDepartment(data: { name: string; college_id: string }) {
  const { createDepartment: create } = await import('./admin');
  return create({ name: data.name, college_id: data.college_id });
}

export async function removeDepartment(id: string) {
  const { deleteDepartment } = await import('./admin');
  return deleteDepartment(id);
}

export async function createCourse(data: Omit<UniversityCourse, 'id'>) {
  const { createCourse: create } = await import('./admin');
  return create({
    course_code: data.course_code,
    course_title: data.course_title,
    department_id: data.department_id,
    level: data.level,
    credit_units: data.units,
    semester: data.semester,
    course_type: data.type,
    description: data.description,
  });
}

export async function updateCourse(id: string, data: Omit<UniversityCourse, 'id'>) {
  const { updateCourse: update } = await import('./admin');
  return update(id, {
    course_code: data.course_code,
    course_title: data.course_title,
    level: data.level,
    credit_units: data.units,
    semester: data.semester,
    course_type: data.type,
    description: data.description,
  });
}

export async function removeCourse(id: string) {
  const { deleteCourse } = await import('./admin');
  return deleteCourse(id);
}

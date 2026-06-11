import { apiClient } from './client';
import type { College, Department, NucIdRecord, UniversityCourse } from '@/types';

export async function listColleges(): Promise<College[]> {
  const { data } = await apiClient.get<College[]>('/admin/colleges');
  return data ?? [];
}

export async function createCollege(name: string): Promise<College> {
  const { data } = await apiClient.post<College>('/admin/colleges', { name });
  return data;
}

export async function deleteCollege(id: string): Promise<void> {
  await apiClient.delete(`/admin/colleges/${id}`);
}

export async function listDepartments(collegeId?: string): Promise<Department[]> {
  const { data } = await apiClient.get<Department[]>('/admin/departments', {
    params: collegeId ? { college_id: collegeId } : undefined,
  });
  return data ?? [];
}

export async function createDepartment(body: { name: string; college_id: string }): Promise<Department> {
  const { data } = await apiClient.post<Department>('/admin/departments', body);
  return data;
}

export async function deleteDepartment(id: string): Promise<void> {
  await apiClient.delete(`/admin/departments/${id}`);
}

export async function listCourses(departmentId?: string, level?: string): Promise<UniversityCourse[]> {
  const { data } = await apiClient.get<Array<Record<string, unknown>>>('/admin/courses', {
    params: {
      ...(departmentId ? { department_id: departmentId } : {}),
      ...(level ? { level } : {}),
    },
  });
  return (data ?? []).map(mapCourse);
}

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

export async function createCourse(body: {
  course_code: string;
  course_title: string;
  department_id: string;
  level: string;
  credit_units: number;
  semester: string;
  course_type: string;
  description?: string;
}): Promise<UniversityCourse> {
  const { data } = await apiClient.post<Record<string, unknown>>('/admin/courses', body);
  return mapCourse(data);
}

export async function updateCourse(
  id: string,
  body: Partial<{
    course_code: string;
    course_title: string;
    level: string;
    credit_units: number;
    semester: string;
    course_type: string;
    description: string;
  }>,
): Promise<UniversityCourse> {
  const { data } = await apiClient.put<Record<string, unknown>>(`/admin/courses/${id}`, body);
  return mapCourse(data);
}

export async function deleteCourse(id: string): Promise<void> {
  await apiClient.delete(`/admin/courses/${id}`);
}

export async function bulkImportCourses(file: File): Promise<{ imported: number }> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await apiClient.post<{ imported: number }>('/admin/courses/bulk-import', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function listNucIds(): Promise<NucIdRecord[]> {
  const { data } = await apiClient.get<NucIdRecord[]>('/admin/nuc-ids');
  return data ?? [];
}

export async function createNucId(body: {
  nuc_staff_id: string;
  label?: string;
  college: string;
  department: string;
}): Promise<NucIdRecord> {
  const { data } = await apiClient.post<NucIdRecord>('/admin/nuc-ids', body);
  return data;
}

export async function revokeNucId(id: string): Promise<void> {
  await apiClient.patch(`/admin/nuc-ids/${id}/revoke`);
}

export async function deleteNucId(id: string): Promise<void> {
  await apiClient.delete(`/admin/nuc-ids/${id}`);
}

export async function listPendingLecturers() {
  const { data } = await apiClient.get('/admin/lecturers/pending');
  return data as Array<{
    id: string;
    name: string;
    email: string;
    nuc_staff_id: string;
    college: string;
    department: string;
    created_at: string;
  }>;
}

export async function approveLecturer(id: string): Promise<void> {
  await apiClient.patch(`/admin/lecturers/${id}/approve`);
}

export async function rejectLecturer(id: string): Promise<void> {
  await apiClient.patch(`/admin/lecturers/${id}/reject`);
}

export async function listStudents(params?: { department?: string; college?: string; level?: string }) {
  const { data } = await apiClient.get<AdminStudent[]>('/admin/students', { params });
  return data ?? [];
}

export async function suspendStudent(id: string): Promise<void> {
  await apiClient.patch(`/admin/students/${id}/suspend`);
}

export async function deleteStudent(id: string): Promise<void> {
  await apiClient.delete(`/admin/students/${id}`);
}

export interface AdminStudent {
  user_id: string;
  name: string;
  email: string;
  department?: string | null;
  college?: string | null;
  academic_level?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AdminLecturer {
  user_id: string;
  name: string;
  email: string;
  nuc_staff_id?: string | null;
  college?: string | null;
  department?: string | null;
  lecturer_status?: string | null;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export async function listLecturers(status?: string): Promise<AdminLecturer[]> {
  const { data } = await apiClient.get<AdminLecturer[]>('/admin/lecturers', {
    params: status ? { status } : undefined,
  });
  return data ?? [];
}

export async function deleteLecturer(id: string): Promise<void> {
  await apiClient.delete(`/admin/lecturers/${id}`);
}

// ——— Compatibility aliases for admin Dashboard ———

import { localPlatform } from './localPlatform';
import type { AuthUser, Testimonial } from '@/types';
import { apiClient as client } from './client';

export const getColleges = listColleges;
export const addCollege = async (name: string) => {
  await createCollege(name);
};
export const removeCollege = deleteCollege;
export const updateCollege = async (_id: string, _name: string) => {
  /* College rename not supported by API yet */
};
export const getNucIds = listNucIds;
export const addNucId = async (body: {
  staff_id: string;
  label?: string;
  college_id?: string;
  department_id?: string;
  college?: string;
  department?: string;
}) => {
  const colleges = await listColleges();
  const depts = await listDepartments();
  const college =
    body.college ??
    colleges.find((c) => c.id === body.college_id)?.name ??
    '';
  const department =
    body.department ?? depts.find((d) => d.id === body.department_id)?.name ?? '';
  return createNucId({
    nuc_staff_id: body.staff_id,
    label: body.label,
    college,
    department,
  });
};
export const getPendingLecturers = listPendingLecturers;
export const getLecturers = async (): Promise<AuthUser[]> => localPlatform.getLecturers();
export const getTestimonials = async (): Promise<Testimonial[]> => localPlatform.getTestimonials();
export const saveTestimonial = (t: Testimonial) => localPlatform.saveTestimonial(t);
export async function getSystemHealth() {
  const { data } = await client.get('/readyz');
  return data as { status: string; checks?: Record<string, boolean> };
}

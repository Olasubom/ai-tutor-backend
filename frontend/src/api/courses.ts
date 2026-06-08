import { localPlatform } from './localPlatform';
import { deleteCourseFromBackend, syncCourseToBackend } from './adminCourses';
import type { Department, Faculty, UniversityCourse } from '@/types';

export function fetchFaculties(): Faculty[] {
  return localPlatform.getFaculties();
}

export function fetchDepartments(): Department[] {
  return localPlatform.getDepartments();
}

export function fetchCourses(departmentId?: string, level?: string): UniversityCourse[] {
  return localPlatform.getCourses(departmentId, level);
}

export function createDepartment(data: { name: string; faculty_id: string }) {
  localPlatform.saveDepartment(data);
}

export function updateDepartment(id: string, data: { name: string; faculty_id: string }) {
  localPlatform.saveDepartment({ ...data, id });
}

export function removeDepartment(id: string) {
  localPlatform.deleteDepartment(id);
}

export function createCourse(data: Omit<UniversityCourse, 'id'>) {
  const course = localPlatform.saveCourse(data);
  syncCourseToBackend(course).catch(() => {});
  return course;
}

export function updateCourse(id: string, data: Omit<UniversityCourse, 'id'>) {
  const course = localPlatform.saveCourse({ ...data, id });
  syncCourseToBackend(course).catch(() => {});
  return course;
}

export function removeCourse(id: string) {
  localPlatform.deleteCourse(id);
  deleteCourseFromBackend(id).catch(() => {});
}

export function createFaculty(name: string) {
  localPlatform.saveFaculty(name);
}

export function removeFaculty(id: string) {
  localPlatform.deleteFaculty(id);
}

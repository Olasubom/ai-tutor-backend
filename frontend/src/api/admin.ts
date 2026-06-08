import { localPlatform } from './localPlatform';
import { apiClient } from './client';
import type { AuthUser, NucIdRecord, Testimonial, TestimonialPanel } from '@/types';

export function getStudents(): AuthUser[] {
  return localPlatform.getStudents();
}

export function getLecturers(): AuthUser[] {
  return localPlatform.getLecturers();
}

export function getPendingLecturers(): AuthUser[] {
  return localPlatform.getLecturers().filter((l) => l.status === 'pending_verification');
}

export function approveLecturer(userId: string) {
  localPlatform.approveLecturer(userId);
}

export function rejectLecturer(userId: string) {
  localPlatform.rejectLecturer(userId);
}

export function getNucIds(): NucIdRecord[] {
  return localPlatform.getNucIds();
}

export function addNucId(data: {
  staff_id: string;
  label?: string;
  faculty_id: string;
  department_id: string;
}) {
  localPlatform.saveNucId(data);
}

export function revokeNucId(id: string) {
  localPlatform.revokeNucId(id);
}

export function deleteNucId(id: string) {
  localPlatform.deleteNucId(id);
}

export function getTestimonials(): Testimonial[] {
  return localPlatform.getTestimonials();
}

export function getTestimonialForPanel(panel: TestimonialPanel): Testimonial {
  return localPlatform.getTestimonialForPanel(panel);
}

export function saveTestimonial(data: Omit<Testimonial, 'id'> & { id?: string }) {
  localPlatform.saveTestimonial(data);
}

export function getFaculties() {
  return localPlatform.getFaculties();
}

export function addFaculty(name: string) {
  localPlatform.saveFaculty(name);
}

export function updateFaculty(id: string, name: string) {
  localPlatform.saveFaculty(name, id);
}

export function removeFaculty(id: string) {
  localPlatform.deleteFaculty(id);
}

export async function getSystemHealth() {
  const [readyz, dbHealth] = await Promise.allSettled([
    apiClient.get('/readyz'),
    apiClient.get('/tutor/db-health', { headers: { 'X-Use-Dev-Token': 'true' } }),
  ]);
  return {
    readyz: readyz.status === 'fulfilled' ? readyz.value.data : null,
    dbHealth: dbHealth.status === 'fulfilled' ? dbHealth.value.data : null,
  };
}

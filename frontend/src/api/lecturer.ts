import { apiClient } from './client';
import {
  getCourseAnalyticsOverview,
  getCourseStudentAnalytics,
  listLecturerManagedCourses,
} from './lecturerDashboard';

export async function ensureLecturerProfile(
  lecturerId: string,
  body: { name: string; department_id: string; college_id?: string },
) {
  const { data } = await apiClient.post(`/lecturer/ensure/${lecturerId}`, body);
  return data;
}

export async function getLecturerStudents(lecturerId: string) {
  const { data } = await apiClient.get(`/lecturer/students/${lecturerId}`);
  return data;
}

export async function getLecturerClassOverview(_departmentName?: string) {
  const courses = await listLecturerManagedCourses();
  if (!courses.length) return [];

  const overview = await getCourseAnalyticsOverview(courses[0].id);
  const students = await getCourseStudentAnalytics(courses[0].id);

  return students.map((s) => ({
    student: {
      user_id: s.student_id,
      name: s.name,
      email: s.email,
      learner_id: s.student_id,
    },
    mastery: Math.round(s.overall_mastery),
    subjects: Object.entries(s.topic_mastery ?? {}).map(([topic, mastery]) => ({ topic, mastery })),
    overview,
  }));
}

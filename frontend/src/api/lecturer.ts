import { apiClient } from './client';
import { localPlatform } from './localPlatform';
import { getKnowledgeState } from './knowledge';

export async function ensureLecturerProfile(
  lecturerId: string,
  body: { name: string; department_id: string; faculty_id?: string },
) {
  const { data } = await apiClient.post(`/lecturer/ensure/${lecturerId}`, body);
  return data;
}

export async function getLecturerStudents(lecturerId: string) {
  const { data } = await apiClient.get(`/lecturer/students/${lecturerId}`);
  return data;
}

export async function getLecturerClassOverview(departmentId?: string) {
  const students = localPlatform.getStudents();
  const filtered = departmentId
    ? students.filter((s) => {
        const onboarding = localPlatform.getOnboarding(s.user_id);
        return onboarding?.departmentId === departmentId;
      })
    : students;

  const rows = await Promise.all(
    filtered.slice(0, 20).map(async (s) => {
      const learnerId = s.learner_id ?? `learner_${s.user_id}`;
      try {
        const knowledge = await getKnowledgeState(learnerId);
        const avg =
          knowledge.subjects.length > 0
            ? Math.round(
                knowledge.subjects.reduce((a, b) => a + b.mastery, 0) / knowledge.subjects.length,
              )
            : 0;
        return { student: s, mastery: avg, subjects: knowledge.subjects };
      } catch {
        return { student: s, mastery: 0, subjects: [] };
      }
    }),
  );

  return rows;
}

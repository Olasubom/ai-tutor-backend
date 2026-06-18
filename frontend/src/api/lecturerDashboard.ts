import { apiClient } from './client';

export interface LecturerManagedCourse {
  id: string;
  code: string;
  title: string;
  description?: string | null;
  department_id: string;
  level: string;
  credit_units?: number;
  semester?: string;
  lecturer_id?: string | null;
  is_active?: boolean;
}

export interface LinkedMaterial {
  id: string;
  title: string;
  file_type?: string;
  original_name?: string;
  status?: string;
  link_id?: string;
}

export interface CourseModule {
  id: string;
  course_id: string;
  title: string;
  description?: string | null;
  order: number;
  bloom_level?: string | null;
  materials?: LinkedMaterial[];
  created_at?: string;
}

export interface CourseDetail extends LecturerManagedCourse {
  modules: CourseModule[];
}

export interface AnalyticsOverview {
  course_id: string;
  course_title: string;
  total_students: number;
  avg_mastery: number;
  students_at_risk: number;
  modules_completion_rate: Array<{ module_title: string; completion_rate: number; avg_score: number }>;
  most_struggled_topics: string[];
  active_this_week: number;
}

export interface StudentAnalyticsRow {
  student_id: string;
  name: string;
  email: string;
  overall_mastery: number;
  modules_completed: number;
  quiz_average?: number | null;
  quiz_count?: number;
  last_active?: string | null;
  status: 'on_track' | 'at_risk' | 'inactive';
  topic_mastery?: Record<string, number>;
}

export interface CourseMaterialItem {
  id: string;
  title: string;
  description?: string | null;
  source_type?: string | null;
  module_order?: number | null;
  status?: string | null;
  embedding_status?: string;
  created_at?: string | null;
}

export interface AiQuizSummaryRow {
  topic: string;
  type: string;
  attempts: number;
  avg_score: number;
  pass_rate: number;
}

export interface GradeRow {
  id: string | null;
  student_id: string;
  student_name?: string;
  student_email?: string;
  course_id: string;
  ca_score?: number | null;
  exam_score?: number | null;
  total_score?: number | null;
  grade_letter?: string | null;
  grade_point?: number | null;
  remark?: string | null;
  comment?: string | null;
  quiz_avg?: number | null;
  quiz_count?: number | null;
}

export interface LecturerQuiz {
  id: string;
  module_id: string;
  title: string;
  description?: string | null;
  bloom_level?: string | null;
  is_published: boolean;
  max_attempts: number;
  created_at?: string;
  questions?: QuizQuestion[];
  pending_review_count?: number;
}

export interface CourseAnnouncement {
  id: string;
  course_id: string;
  lecturer_id: string;
  title: string;
  body: string;
  is_pinned: boolean;
  created_at: string;
}

export interface QuizQuestion {
  id: string;
  text: string;
  difficulty: string;
  approved: boolean;
  ai_generated: boolean;
  options: Array<{ id: string; text: string; is_correct?: boolean }>;
}

export async function listLecturerManagedCourses(): Promise<LecturerManagedCourse[]> {
  const { data } = await apiClient.get<LecturerManagedCourse[]>('/lecturer/courses');
  return data;
}

export async function getLecturerCourse(courseId: string): Promise<CourseDetail> {
  const { data } = await apiClient.get<CourseDetail>(`/lecturer/courses/${courseId}`);
  return data;
}

export async function createLecturerCourse(body: {
  code: string;
  title: string;
  description?: string;
  level: string;
}): Promise<LecturerManagedCourse> {
  const { data } = await apiClient.post<LecturerManagedCourse>('/lecturer/courses', body);
  return data;
}

export async function addCourseModule(
  courseId: string,
  body: { title: string; description?: string; order: number; bloom_level?: string },
): Promise<CourseModule> {
  const { data } = await apiClient.post<CourseModule>(`/lecturer/courses/${courseId}/modules`, body);
  return data;
}

export async function deleteCourseModule(courseId: string, moduleId: string): Promise<void> {
  await apiClient.delete(`/lecturer/courses/${courseId}/modules/${moduleId}`);
}

export async function linkModuleMaterial(moduleId: string, materialId: string): Promise<void> {
  await apiClient.post(`/lecturer/modules/${moduleId}/materials/${materialId}`);
}

export async function unlinkModuleMaterial(moduleId: string, materialId: string): Promise<void> {
  await apiClient.delete(`/lecturer/modules/${moduleId}/materials/${materialId}`);
}

export async function getCourseAnalyticsOverview(courseId: string): Promise<AnalyticsOverview> {
  const { data } = await apiClient.get<AnalyticsOverview>(
    `/lecturer/courses/${courseId}/analytics/overview`,
  );
  return data;
}

export async function getCourseStudentAnalytics(courseId: string): Promise<StudentAnalyticsRow[]> {
  const { data } = await apiClient.get<StudentAnalyticsRow[]>(
    `/lecturer/courses/${courseId}/analytics/students`,
  );
  return data;
}

export async function listCourseGrades(courseId: string): Promise<GradeRow[]> {
  const { data } = await apiClient.get<GradeRow[]>(`/lecturer/courses/${courseId}/grades`);
  return data;
}

export async function submitGrade(
  courseId: string,
  body: { student_id: string; ca_score?: number; exam_score?: number; comment?: string },
): Promise<GradeRow> {
  const { data } = await apiClient.post<GradeRow>(`/lecturer/courses/${courseId}/grades`, body);
  return data;
}

export async function listModuleQuizzes(moduleId: string): Promise<LecturerQuiz[]> {
  const { data } = await apiClient.get<LecturerQuiz[]>(`/lecturer/modules/${moduleId}/quizzes`);
  return data;
}

export async function createModuleQuiz(
  moduleId: string,
  body: { title: string; description?: string; max_attempts?: number },
): Promise<LecturerQuiz> {
  const { data } = await apiClient.post<LecturerQuiz>(`/lecturer/modules/${moduleId}/quizzes`, body);
  return data;
}

export async function getQuizDetail(quizId: string): Promise<LecturerQuiz> {
  const { data } = await apiClient.get<LecturerQuiz>(`/lecturer/quizzes/${quizId}`);
  return data;
}

export async function publishQuiz(quizId: string): Promise<LecturerQuiz> {
  const { data } = await apiClient.post<LecturerQuiz>(`/lecturer/quizzes/${quizId}/publish`);
  return data;
}

export async function approveQuizQuestion(questionId: string): Promise<QuizQuestion> {
  const { data } = await apiClient.post<QuizQuestion>(`/lecturer/questions/${questionId}/approve`);
  return data;
}

export async function rejectQuizQuestion(questionId: string): Promise<void> {
  await apiClient.post(`/lecturer/questions/${questionId}/reject`);
}

export async function generateQuizQuestions(
  quizId: string,
  body: { topic?: string; count?: number; difficulty?: string },
): Promise<QuizQuestion[]> {
  const { data } = await apiClient.post<QuizQuestion[]>(
    `/lecturer/quizzes/${quizId}/generate-questions`,
    body,
  );
  return data;
}

export async function addQuizQuestion(
  quizId: string,
  body: {
    text: string;
    options: Array<{ text: string; is_correct: boolean }>;
    explanation?: string;
  },
): Promise<QuizQuestion> {
  const { data } = await apiClient.post<QuizQuestion>(`/lecturer/quizzes/${quizId}/questions`, body);
  return data;
}

export async function listCourseAnnouncements(courseId: string): Promise<CourseAnnouncement[]> {
  const { data } = await apiClient.get<CourseAnnouncement[]>(`/lecturer/courses/${courseId}/announcements`);
  return data;
}

export async function createCourseAnnouncement(
  courseId: string,
  body: { title: string; body: string; is_pinned?: boolean },
): Promise<CourseAnnouncement> {
  const { data } = await apiClient.post<CourseAnnouncement>(`/lecturer/courses/${courseId}/announcements`, body);
  return data;
}

export async function updateCourseAnnouncement(
  announcementId: string,
  body: { title?: string; body?: string; is_pinned?: boolean },
): Promise<CourseAnnouncement> {
  const { data } = await apiClient.put<CourseAnnouncement>(`/lecturer/announcements/${announcementId}`, body);
  return data;
}

export async function deleteCourseAnnouncement(announcementId: string): Promise<void> {
  await apiClient.delete(`/lecturer/announcements/${announcementId}`);
}

export async function getCourseMaterials(courseId: string): Promise<CourseMaterialItem[]> {
  const { data } = await apiClient.get<CourseMaterialItem[]>(`/lecturer/courses/${courseId}/materials`);
  return data;
}

export async function getCourseAiQuizResults(courseId: string): Promise<AiQuizSummaryRow[]> {
  const { data } = await apiClient.get<AiQuizSummaryRow[]>(`/lecturer/courses/${courseId}/ai-quiz-results`);
  return data;
}

export async function lecturerAiChat(body: { message: string; course_id?: string }) {
  const { data } = await apiClient.post<{ message: string; context_used: boolean }>('/lecturer/ai-chat', body);
  return data;
}

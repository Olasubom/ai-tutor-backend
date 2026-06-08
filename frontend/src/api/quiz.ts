import { apiClient } from './client';

export interface QuizQuestion {
  question_id: string;
  question_text: string;
  options: string[];
  difficulty: 'easy' | 'medium' | 'hard';
}

export interface QuizGenerateResponse {
  quiz_id: string;
  topic: string;
  questions: QuizQuestion[];
}

export interface QuizSubmitResponse {
  quiz_id: string;
  topic: string;
  score: number;
  total: number;
  percentage: number;
  time_taken_seconds: number;
  results: Array<{
    question_id: string;
    question_text: string;
    selected_option: number;
    correct_option: number;
    is_correct: boolean;
    explanation: string;
  }>;
  mastery_update: {
    topic: string;
    previous_mastery: number;
    new_mastery: number;
    bkt_params: { p_l0: number; p_t: number; p_s: number; p_g: number };
  };
  recommendation_triggered: boolean;
}

export async function generateQuiz(learnerId: string, topic: string, numQuestions = 5) {
  const { data } = await apiClient.post<QuizGenerateResponse>('/quiz/generate', {
    learner_id: learnerId,
    topic,
    num_questions: numQuestions,
  });
  return data;
}

export async function submitQuiz(
  learnerId: string,
  quizId: string,
  responses: Array<{ question_id: string; selected_option: number; time_taken_seconds: number }>,
) {
  const { data } = await apiClient.post<QuizSubmitResponse>('/quiz/submit', {
    learner_id: learnerId,
    quiz_id: quizId,
    responses,
  });
  return data;
}

export async function getReviewDue(learnerId: string) {
  const { data } = await apiClient.get<Array<{
    topic: string;
    due_date: string;
    days_overdue: number;
    current_mastery: number;
    suggested_question_count: number;
  }>>(`/quiz/review-due/${learnerId}`);
  return data;
}

export async function getBktState(learnerId: string, topic: string) {
  const { data } = await apiClient.get(`/quiz/bkt/${learnerId}/${encodeURIComponent(topic)}`);
  return data;
}

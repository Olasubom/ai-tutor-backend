import { apiClient } from './client';
import type { Recommendation } from '@/types';

export type ModuleSessionStage = 'onboarding' | 'explanation' | 'tasks' | 'quiz' | 'completed';

export interface OnboardingOption {
  id: string;
  label: string;
  description?: string;
}

export interface ModuleSessionOnboardingFields {
  onboarding_step?: 'style' | 'level' | 'style_custom_input';
  options?: OnboardingOption[];
  question?: string;
  awaiting_custom_text?: boolean;
}

export interface ModuleSessionState {
  sessionId: string;
  stage: ModuleSessionStage;
  courseCode: string;
  moduleTitle: string;
  pdfUrl?: string | null;
  contentItemId: string;
  courseId?: string;
}

export interface MixedQuizMcq {
  id: string;
  type: 'mcq';
  question: string;
  options: string[];
  correct_index: number;
  explanation?: string;
}

export interface MixedQuizShortAnswer {
  id: string;
  type: 'short_answer';
  question: string;
  model_answer: string;
  key_points: string[];
}

export interface MixedQuizData {
  mcq: MixedQuizMcq[];
  short_answer: MixedQuizShortAnswer[];
}

export interface StartModuleSessionResponse extends ModuleSessionOnboardingFields {
  session_id: string;
  stage: ModuleSessionStage;
  explanation_progress: number;
  message: string;
  pdf_url?: string | null;
  total_chunks?: number;
  total_topics?: number;
  tasks?: Recommendation[];
  quiz_id?: string;
  quiz_data?: MixedQuizData;
  redirect_to_quiz?: boolean;
  topic?: string;
}

export interface ContinueModuleSessionResponse extends ModuleSessionOnboardingFields {
  stage: ModuleSessionStage;
  message: string;
  explanation_progress?: number;
  total_chunks?: number;
  total_topics?: number;
  tasks?: Recommendation[];
  quiz_id?: string;
  quiz_data?: MixedQuizData;
  redirect_to_quiz?: boolean;
  topic?: string;
  next_action?: string;
  is_comprehension_check?: boolean;
  score?: number;
}

export async function startModuleSession(contentItemId: string): Promise<StartModuleSessionResponse> {
  const { data } = await apiClient.post<StartModuleSessionResponse>('/tutor/module-session/start', {
    content_item_id: contentItemId,
  });
  return data;
}

export async function continueModuleSession(
  sessionId: string,
  message?: string,
  selectedOptionId?: string,
): Promise<ContinueModuleSessionResponse> {
  const { data } = await apiClient.post<ContinueModuleSessionResponse>('/tutor/module-session/continue', {
    session_id: sessionId,
    message: message ?? '',
    selected_option_id: selectedOptionId,
  });
  return data;
}

export async function completeModuleSession(sessionId: string): Promise<{
  message: string;
  stage: string;
  next_module?: {
    content_item_id: string;
    title: string;
    module_number: number;
  } | null;
}> {
  const { data } = await apiClient.post<{
    message: string;
    stage: string;
    next_module?: {
      content_item_id: string;
      title: string;
      module_number: number;
    } | null;
  }>('/tutor/module-session/complete', { session_id: sessionId });
  return data;
}

export async function getEmbeddingStatus(uploadId: string): Promise<{
  content_item_id: string;
  embedding_status: string;
  has_extracted_text: boolean;
}> {
  const { data } = await apiClient.get(`/upload/material/${uploadId}/embedding-status`);
  return data;
}

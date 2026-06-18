import { apiClient } from './client';
import type { Recommendation } from '@/types';

export type ModuleSessionStage = 'onboarding' | 'explanation' | 'tasks' | 'quiz' | 'completed';

export interface ModuleSessionState {
  sessionId: string;
  stage: ModuleSessionStage;
  courseCode: string;
  moduleTitle: string;
  pdfUrl?: string | null;
  contentItemId: string;
  courseId?: string;
}

export interface StartModuleSessionResponse {
  session_id: string;
  stage: ModuleSessionStage;
  explanation_progress: number;
  message: string;
  pdf_url?: string | null;
  total_chunks?: number;
  tasks?: Recommendation[];
  quiz_id?: string;
  redirect_to_quiz?: boolean;
  topic?: string;
}

export interface ContinueModuleSessionResponse {
  stage: ModuleSessionStage;
  message: string;
  explanation_progress?: number;
  total_chunks?: number;
  tasks?: Recommendation[];
  quiz_id?: string;
  redirect_to_quiz?: boolean;
  topic?: string;
  next_action?: string;
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
): Promise<ContinueModuleSessionResponse> {
  const { data } = await apiClient.post<ContinueModuleSessionResponse>('/tutor/module-session/continue', {
    session_id: sessionId,
    message: message ?? '',
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

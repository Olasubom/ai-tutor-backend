import { apiClient } from './client';

export interface OnboardingStepResponse {
  ok: boolean;
  completed_steps: number[];
}

export interface OnboardingStatusResponse {
  completed_steps: number[];
  is_complete: boolean;
}

export async function onboardingStep1(body: {
  learner_id: string;
  full_name: string;
  field_of_study: string;
  institution: string;
  proficiency_level: string;
}) {
  const { data } = await apiClient.post<OnboardingStepResponse>('/auth/onboarding/step1', body);
  return data;
}

export async function onboardingStep2(body: {
  learner_id: string;
  department_id: string;
  level: string;
  selected_course_ids: string[];
  additional_subjects: string[];
}) {
  const { data } = await apiClient.post<OnboardingStepResponse>('/auth/onboarding/step2', body);
  return data;
}

export async function onboardingStep4(body: {
  learner_id: string;
  weekly_hours: number;
  content_formats: string[];
  primary_objective: string;
}) {
  const { data } = await apiClient.post<OnboardingStepResponse>('/auth/onboarding/step4', body);
  return data;
}

export async function getOnboardingStatus(learnerId: string) {
  const { data } = await apiClient.get<OnboardingStatusResponse>(`/auth/onboarding/status/${learnerId}`);
  return data;
}

export async function syncOnboardingComplete(learnerId: string): Promise<boolean> {
  try {
    const status = await getOnboardingStatus(learnerId);
    return status.is_complete;
  } catch {
    return false;
  }
}

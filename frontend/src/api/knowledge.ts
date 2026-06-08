import { apiClient } from './client';
import type { KnowledgeStateSummary } from '@/types';

export async function getKnowledgeState(learnerId: string) {
  const { data } = await apiClient.get<{
    learner_id: string;
    subjects: Array<{ topic: string; mastery: number; attempts: number }>;
    summary: KnowledgeStateSummary;
  }>(`/tutor/knowledge/${learnerId}`);
  return {
    subjects: data.subjects ?? [],
    summary: data.summary ?? {},
  };
}

export async function getMasteryTrajectory(learnerId: string) {
  const { data } = await apiClient.get<Array<{ date: string; overall_mastery: number }>>(
    `/tutor/knowledge/trajectory/${learnerId}`,
  );
  return data;
}

const PROFICIENCY_MAP: Record<string, string> = {
  none: 'no_knowledge',
  no_knowledge: 'no_knowledge',
  familiar: 'familiar',
  comfortable: 'comfortable',
  proficient: 'proficient',
};

export async function seedKnowledge(
  learnerId: string,
  assessments: Array<{ topic: string; proficiency: string }>,
) {
  const normalized = assessments.map((a) => ({
    topic: a.topic,
    proficiency: PROFICIENCY_MAP[a.proficiency] ?? a.proficiency,
  }));
  const { data } = await apiClient.post<{ seeded: number; completed_steps: number[] }>(
    '/tutor/knowledge/seed',
    { learner_id: learnerId, assessments: normalized },
  );
  return data;
}

export async function patchTopicMastery(learnerId: string, topic: string, proficiency: string) {
  const { data } = await apiClient.patch(`/tutor/knowledge/${learnerId}/${encodeURIComponent(topic)}`, {
    proficiency,
  });
  return data;
}

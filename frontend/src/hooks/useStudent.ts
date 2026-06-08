import { useQuery } from '@tanstack/react-query';
import { getLearnerProfile } from '@/api/student';
import { getKnowledgeState } from '@/api/knowledge';
import { getLearnerTasks } from '@/api/tasks';

export function useLearnerProfile(learnerId: string) {
  return useQuery({
    queryKey: ['profile', learnerId],
    queryFn: () => getLearnerProfile(learnerId),
    enabled: !!learnerId,
  });
}

export function useKnowledge(learnerId: string) {
  return useQuery({
    queryKey: ['knowledge', learnerId],
    queryFn: () => getKnowledgeState(learnerId),
    enabled: !!learnerId,
  });
}

export function useTasks(learnerId: string) {
  return useQuery({
    queryKey: ['tasks', learnerId],
    queryFn: () => getLearnerTasks(learnerId),
    enabled: !!learnerId,
  });
}

import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GraduationCap } from 'lucide-react';
import { localPlatform } from '@/api/localPlatform';
import { seedKnowledge } from '@/api/knowledge';
import { getRecommendations } from '@/api/recommendations';
import { getLearnerTasks } from '@/api/tasks';
import { useAuthStore } from '@/stores/authStore';

const steps = ['Seeding knowledge model', 'Generating curriculum path', 'Preparing your first session'];
const SEEDED_KEY = 'onboarding_knowledge_seeded';

export default function GeneratingModel() {
  const navigate = useNavigate();
  const [done, setDone] = useState(0);
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    const run = async () => {
      const { user, updateUser } = useAuthStore.getState();
      const learnerId = user?.learner_id ?? (user ? `learner_${user.user_id}` : '');
      const onboarding = JSON.parse(sessionStorage.getItem('onboarding_all') ?? '{}');

      if (user) {
        localPlatform.saveOnboarding(user.user_id, onboarding);
        updateUser({ onboarding_complete: true });

        const alreadySeeded = sessionStorage.getItem(SEEDED_KEY) === learnerId;
        if (onboarding.knowledgeRatings && learnerId && !alreadySeeded) {
          const assessments = Object.entries(onboarding.knowledgeRatings as Record<string, string>).map(
            ([topic, proficiency]) => ({ topic, proficiency }),
          );
          await seedKnowledge(learnerId, assessments);
          sessionStorage.setItem(SEEDED_KEY, learnerId);
        }
        setDone(1);

        if (learnerId) {
          await getRecommendations({ learner_id: learnerId, message: 'onboarding first recommendations', limit: 6 });
        }
        setDone(2);

        if (learnerId) {
          await getLearnerTasks(learnerId);
        }
        setDone(3);
      }

      navigate('/student/dashboard', { replace: true });
    };

    run().catch(() => navigate('/student/dashboard', { replace: true }));
  }, [navigate]);

  return (
    <div className="page-grid flex min-h-screen flex-col items-center justify-center p-6 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-primary text-white">
        <GraduationCap className="h-7 w-7 animate-pulse" />
      </div>
      <h1 className="mt-6 text-[24px] font-extrabold">Building your personalized knowledge model...</h1>
      <p className="mt-2 max-w-md text-text-secondary">
        We are analyzing your inputs and configuring your adaptive curriculum.
      </p>
      <ul className="mt-8 space-y-3 text-left">
        {steps.map((s, i) => (
          <li key={s} className={i < done ? 'text-teal' : 'text-text-muted'}>
            {i < done ? '✓' : '○'} {s}
          </li>
        ))}
      </ul>
    </div>
  );
}

import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GraduationCap } from 'lucide-react';
import { completeOnboarding } from '@/api/auth';
import { getRecommendations } from '@/api/recommendations';
import { useAuthStore } from '@/stores/authStore';
import { Button } from '@/components/ui/Button';

const steps = ['Setting up your profile…', 'Preparing your recommendations…'];

export default function GeneratingModel() {
  const navigate = useNavigate();
  const [done, setDone] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const startedRef = useRef(false);

  const run = async () => {
    setError(null);
    const { user_id, name } = useAuthStore.getState();
    if (!user_id) {
      setError('Not signed in. Please log in again.');
      return;
    }

    const onboarding = JSON.parse(sessionStorage.getItem('onboarding_all') ?? '{}') as {
      name?: string;
      department?: string;
      college?: string;
      level?: string;
      institution?: string;
      courses?: string[];
      knowledgeRatings?: Record<string, string>;
      weeklyHours?: number;
      contentFormats?: string[];
      primaryObjective?: string;
    };

    const subjectRatings = Object.entries(onboarding.knowledgeRatings ?? {}).map(([topic, proficiency]) => ({
      topic,
      proficiency,
    }));

    const displayName = (onboarding.name ?? name ?? 'Student').trim();

    await completeOnboarding({
      name: displayName,
      department: onboarding.department ?? '',
      college: onboarding.college ?? '',
      academic_level: onboarding.level ?? '200-300',
      institution: onboarding.institution ?? '',
      selected_course_ids: onboarding.courses ?? [],
      subject_ratings: subjectRatings,
      weekly_hours: onboarding.weeklyHours ?? 20,
      content_formats: onboarding.contentFormats ?? [],
      primary_objective: onboarding.primaryObjective ?? 'Academic Excellence',
    });
    setDone(1);

    if (displayName) {
      useAuthStore.setState({ name: displayName });
      const raw = localStorage.getItem('ai_tutor_user');
      if (raw) {
        try {
          const user = JSON.parse(raw);
          localStorage.setItem('ai_tutor_user', JSON.stringify({ ...user, name: displayName }));
        } catch {
          /* ignore */
        }
      }
    }

    const events = subjectRatings.map(({ topic, proficiency }) => ({
      topic,
      correct: proficiency === 'comfortable' || proficiency === 'proficient',
    }));

    await getRecommendations({ learner_id: user_id, message: 'initial recommendations', events });
    setDone(2);

    useAuthStore.getState().setOnboardingComplete(user_id);
    sessionStorage.removeItem('onboarding_step1');
    sessionStorage.removeItem('onboarding_step2');
    sessionStorage.removeItem('onboarding_step3');
    sessionStorage.removeItem('onboarding_all');
    navigate('/student/dashboard', { replace: true });
  };

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    run().catch((e) => {
      setError(e instanceof Error ? e.message : 'Setup failed. Please try again.');
    });
  }, []);

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
      {error && (
        <div className="mt-8 max-w-md">
          <p className="text-error">{error}</p>
          <Button className="mt-4" onClick={() => run()}>
            Retry
          </Button>
        </div>
      )}
    </div>
  );
}

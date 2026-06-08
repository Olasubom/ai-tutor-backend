import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { BookOpen } from 'lucide-react';

const RATINGS = [
  { id: 'no_knowledge', label: 'No Knowledge' },
  { id: 'familiar', label: 'Familiar' },
  { id: 'comfortable', label: 'Comfortable' },
  { id: 'proficient', label: 'Proficient' },
];

export default function Step3KnowledgeAssessment() {
  const navigate = useNavigate();
  const topics = useMemo(() => {
    const raw = sessionStorage.getItem('onboarding_step2');
    if (!raw) return [];
    const data = JSON.parse(raw) as { topics?: string[] };
    return data.topics ?? [];
  }, []);

  const [ratings, setRatings] = useState<Record<string, string>>(
    Object.fromEntries(topics.map((t) => [t, 'familiar'])),
  );

  if (topics.length === 0) {
    return (
      <>
        <h2 className="text-[24px] font-extrabold">Knowledge Assessment</h2>
        <p className="mt-4 text-text-secondary">No courses selected yet. Go back and choose courses, or continue without assessment topics.</p>
        <div className="mt-8 flex justify-end">
          <Button onClick={() => navigate('/onboarding/step4')}>Skip to Preferences →</Button>
        </div>
      </>
    );
  }

  return (
    <>
      <h2 className="text-[24px] font-extrabold">Knowledge Assessment</h2>
      <p className="mt-2 text-text-secondary">
        Rate your current proficiency in each subject to seed your knowledge model.
      </p>

      <div className="mt-6 space-y-4">
        {topics.map((topic) => (
          <div key={topic} className="rounded-xl border border-border p-5">
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <BookOpen className="h-5 w-5" />
              </div>
              <div className="flex-1">
                <div className="font-bold text-text-primary">{topic}</div>
                <p className="text-[13px] text-text-muted">How would you rate your experience?</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {RATINGS.map((r) => (
                    <button
                      key={r.id}
                      type="button"
                      onClick={() => setRatings((prev) => ({ ...prev, [topic]: r.id }))}
                      className={cn(
                        'rounded-full border px-3 py-1.5 text-[12px] font-semibold',
                        ratings[topic] === r.id
                          ? 'border-primary text-primary'
                          : 'border-border text-text-muted',
                      )}
                    >
                      {r.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 flex justify-end">
        <Button
          onClick={() => {
            sessionStorage.setItem('onboarding_step3', JSON.stringify({ knowledgeRatings: ratings }));
            navigate('/onboarding/step4');
          }}
        >
          Continue to Model Generation →
        </Button>
      </div>
    </>
  );
}

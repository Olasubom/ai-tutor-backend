import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { cn } from '@/lib/utils';
import { BookOpen, Brain, GraduationCap, TrendingUp } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { onboardingStep1 } from '@/api/onboarding';
import { useToastStore } from '@/components/ui/Toast';

const levels = [
  { id: 'foundation', icon: BookOpen, title: '100 Level — Foundation', desc: 'First year. Building core concepts and fundamentals in your field.' },
  { id: 'developing', icon: TrendingUp, title: '200-300 Level — Developing', desc: 'Intermediate years. Applying concepts and deepening subject understanding.' },
  { id: 'advanced', icon: Brain, title: '400 Level — Advanced', desc: 'Final year. Complex problem-solving and independent research focus.' },
  { id: 'postgraduate', icon: GraduationCap, title: 'Postgraduate / Self-Study', desc: 'Beyond undergraduate. Specialized mastery and research-level work.' },
];

export default function Step1Profile() {
  const navigate = useNavigate();
  const { learnerId } = useAuth();
  const toast = useToastStore((s) => s.add);
  const [level, setLevel] = useState('developing');
  const [name, setName] = useState('');
  const [field, setField] = useState('');
  const [institution, setInstitution] = useState('');
  const [saving, setSaving] = useState(false);

  const continueNext = async () => {
    if (!name.trim() || !field.trim()) {
      toast('Please fill in your name and field of study.', 'warning');
      return;
    }
    setSaving(true);
    try {
      sessionStorage.setItem('onboarding_step1', JSON.stringify({ name, field, institution, level }));
      if (learnerId) {
        await onboardingStep1({
          learner_id: learnerId,
          full_name: name,
          field_of_study: field,
          institution,
          proficiency_level: level,
        });
      }
      navigate('/onboarding/step2');
    } catch {
      toast('Failed to save profile. Check that the backend is running.', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <h2 className="text-[24px] font-extrabold">Create your academic profile</h2>
      <p className="mt-2 text-text-secondary">Tell us about yourself so we can tailor your curriculum.</p>
      <div className="mt-6 space-y-4">
        <Input label="Full Name" value={name} onChange={(e) => setName(e.target.value)} />
        <div className="grid gap-4 sm:grid-cols-2">
          <Input label="Primary Field of Study" placeholder="e.g. Computer Science" value={field} onChange={(e) => setField(e.target.value)} />
          <Input label="Institution / Organization" value={institution} onChange={(e) => setInstitution(e.target.value)} />
        </div>
        <div className="border-t border-border pt-4">
          <h3 className="font-bold">Your Academic Standing</h3>
          <p className="mt-1 text-[13px] text-text-secondary">
            Select the level that best describes where you currently are in your studies. This helps the AI set the right
            starting point for your personalized curriculum.
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {levels.map((l) => (
              <button
                key={l.id}
                type="button"
                onClick={() => setLevel(l.id)}
                className={cn(
                  'rounded-xl border p-5 text-left',
                  level === l.id ? 'border-2 border-primary bg-primary/5' : 'border-border',
                )}
              >
                <l.icon className="mb-2 h-5 w-5 text-primary" />
                <div className="font-bold">{l.title}</div>
                <p className="mt-1 text-[13px] text-text-secondary">{l.desc}</p>
              </button>
            ))}
          </div>
        </div>
      </div>
      <div className="mt-8 flex justify-end">
        <Button onClick={continueNext} disabled={saving}>
          Continue →
        </Button>
      </div>
    </>
  );
}

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { FileText, Gamepad2, Layers, Video } from 'lucide-react';

const FORMATS = [
  { id: 'video', icon: Video, title: 'Video Lectures', desc: 'Visual explanations and demonstrations.' },
  { id: 'text', icon: FileText, title: 'Written Material', desc: 'Articles, notes, and textbooks.' },
  { id: 'interactive', icon: Gamepad2, title: 'Interactive Quizzes', desc: 'Hands-on practice and drills.' },
  { id: 'mixed', icon: Layers, title: 'Mixed Approach', desc: 'Balanced blend of all formats.' },
];

const OBJECTIVES = [
  'Professional Certification',
  'Academic Excellence',
  'Skill Acquisition & Hobby',
];

export default function Step4StudyPreferences() {
  const navigate = useNavigate();
  const [hours, setHours] = useState(20);
  const [formats, setFormats] = useState<string[]>(['video', 'interactive']);
  const [objective, setObjective] = useState(OBJECTIVES[1]);

  const toggleFormat = (id: string) => {
    setFormats((prev) => (prev.includes(id) ? prev.filter((f) => f !== id) : [...prev, id]));
  };

  const finish = () => {
    const step1 = JSON.parse(sessionStorage.getItem('onboarding_step1') ?? '{}');
    const step2 = JSON.parse(sessionStorage.getItem('onboarding_step2') ?? '{}');
    const step3 = JSON.parse(sessionStorage.getItem('onboarding_step3') ?? '{}');
    sessionStorage.setItem(
      'onboarding_all',
      JSON.stringify({
        ...step1,
        ...step2,
        ...step3,
        weeklyHours: hours,
        contentFormats: formats,
        primaryObjective: objective,
      }),
    );
    navigate('/onboarding/generating');
  };

  return (
    <>
      <h2 className="text-[24px] font-extrabold">Study Preferences</h2>
      <p className="mt-2 text-text-secondary">Customize your learning environment.</p>

      <div className="mt-6 space-y-6">
        <div>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold">Weekly Commitment</h3>
              <p className="text-[13px] text-text-muted">How many hours can you dedicate per week?</p>
            </div>
            <span className="text-[28px] font-extrabold text-primary">{hours} hrs</span>
          </div>
          <input
            type="range"
            min={1}
            max={40}
            value={hours}
            onChange={(e) => setHours(Number(e.target.value))}
            className="mt-3 w-full accent-primary"
          />
          <div className="flex justify-between text-[12px] text-text-muted">
            <span>1 hr</span>
            <span>40 hrs</span>
          </div>
        </div>

        <div>
          <h3 className="font-bold">Preferred Content Formats</h3>
          <p className="text-[13px] text-text-muted">Select all that apply.</p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {FORMATS.map((f) => (
              <button
                key={f.id}
                type="button"
                onClick={() => toggleFormat(f.id)}
                className={cn(
                  'rounded-xl border p-4 text-left',
                  formats.includes(f.id) ? 'border-2 border-primary bg-primary/5' : 'border-border',
                )}
              >
                <f.icon className="mb-2 h-5 w-5 text-primary" />
                <div className="font-bold">{f.title}</div>
                <p className="mt-1 text-[12px] text-text-muted">{f.desc}</p>
              </button>
            ))}
          </div>
        </div>

        <div>
          <h3 className="font-bold">Primary Objective</h3>
          <div className="mt-3 space-y-2">
            {OBJECTIVES.map((o) => (
              <button
                key={o}
                type="button"
                onClick={() => setObjective(o)}
                className={cn(
                  'flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left text-[14px]',
                  objective === o ? 'border-2 border-primary bg-primary/5' : 'border-border',
                )}
              >
                <span
                  className={cn(
                    'h-4 w-4 rounded-full border-2',
                    objective === o ? 'border-primary bg-primary' : 'border-border',
                  )}
                />
                {o}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-8 flex justify-end">
        <Button onClick={finish}>Finish Setup →</Button>
      </div>
    </>
  );
}

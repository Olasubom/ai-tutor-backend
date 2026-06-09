import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { cn } from '@/lib/utils';
import { BookOpen, Brain, GraduationCap, TrendingUp } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { fetchColleges, fetchDepartments } from '@/api/courses';
import { useToastStore } from '@/components/ui/Toast';

const levels = [
  { id: '100', icon: BookOpen, title: '100 Level — Foundation', desc: 'First year. Building core concepts and fundamentals.' },
  { id: '200-300', icon: TrendingUp, title: '200–300 Level — Developing', desc: 'Intermediate years. Applying concepts and deepening understanding.' },
  { id: '400', icon: Brain, title: '400 Level — Advanced', desc: 'Final year. Complex problem-solving and research focus.' },
  { id: 'postgrad', icon: GraduationCap, title: 'Postgraduate / Self-Study', desc: 'Beyond undergraduate. Specialized mastery and research.' },
];

export default function Step1Profile() {
  const navigate = useNavigate();
  const { name: authName } = useAuth();
  const toast = useToastStore((s) => s.add);
  const [level, setLevel] = useState('200-300');
  const [name, setName] = useState(authName ?? '');
  const [institution, setInstitution] = useState('');
  const [collegeId, setCollegeId] = useState('');
  const [departmentId, setDepartmentId] = useState('');

  const { data: colleges = [] } = useQuery({ queryKey: ['colleges'], queryFn: fetchColleges });
  const activeCollegeId = collegeId || colleges[0]?.id || '';
  const { data: departments = [] } = useQuery({
    queryKey: ['departments', activeCollegeId],
    queryFn: () => fetchDepartments(activeCollegeId),
    enabled: !!activeCollegeId,
  });

  const continueNext = () => {
    if (!name.trim() || !departmentId) {
      toast('Please fill in your name and select your department.', 'warning');
      return;
    }
    const college = colleges.find((c) => c.id === activeCollegeId);
    const department = departments.find((d) => d.id === departmentId);
    sessionStorage.setItem(
      'onboarding_step1',
      JSON.stringify({
        name,
        institution,
        level,
        collegeId: activeCollegeId,
        college: college?.name ?? '',
        departmentId,
        department: department?.name ?? '',
      }),
    );
    navigate('/onboarding/step2');
  };

  return (
    <>
      <h2 className="text-[24px] font-extrabold">Create your academic profile</h2>
      <p className="mt-2 text-text-secondary">Tell us about yourself so we can tailor your curriculum.</p>
      <div className="mt-6 space-y-4">
        <Input label="Full Name" value={name} onChange={(e) => setName(e.target.value)} />
        <Input label="Institution / Organization" value={institution} onChange={(e) => setInstitution(e.target.value)} />

        <Select
          label="College"
          value={activeCollegeId}
          onChange={(e) => {
            setCollegeId(e.target.value);
            setDepartmentId('');
          }}
          options={[
            { value: '', label: 'Select your college…' },
            ...colleges.map((c) => ({ value: c.id, label: c.name })),
          ]}
        />

        <Select
          label="Department"
          value={departmentId}
          onChange={(e) => setDepartmentId(e.target.value)}
          options={[
            { value: '', label: 'Select department…' },
            ...departments.map((d) => ({ value: d.id, label: d.name })),
          ]}
        />

        <div className="border-t border-border pt-4">
          <h3 className="font-bold">Your Academic Standing</h3>
          <p className="mt-1 text-[13px] text-text-secondary">
            Select the level that best describes where you currently are in your studies.
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
        <Button onClick={continueNext}>Continue →</Button>
      </div>
    </>
  );
}

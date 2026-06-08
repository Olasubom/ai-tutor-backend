import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { SubjectPill } from '@/components/onboarding/SubjectPill';
import { fetchDepartments } from '@/api/courses';
import { fetchAdminCourses } from '@/api/adminCourses';
import { onboardingStep2 } from '@/api/onboarding';
import { useAuth } from '@/hooks/useAuth';
import { useToastStore } from '@/components/ui/Toast';
import { cn } from '@/lib/utils';

const LEVELS = ['100', '200', '300', '400', '500'];

export default function Step2CurriculumFocus() {
  const navigate = useNavigate();
  const { learnerId } = useAuth();
  const toast = useToastStore((s) => s.add);
  const departments = useMemo(() => fetchDepartments(), []);
  const [departmentId, setDepartmentId] = useState(departments[0]?.id ?? '');
  const [level, setLevel] = useState('200');
  const [selectedCourses, setSelectedCourses] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [showNoCourseWarning, setShowNoCourseWarning] = useState(false);

  const { data: courses = [], isLoading } = useQuery({
    queryKey: ['admin-courses', departmentId, level],
    queryFn: () => fetchAdminCourses(departmentId, level),
    enabled: !!departmentId && !!level,
  });

  const toggleCourse = (code: string) => {
    setSelectedCourses((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code],
    );
  };

  const selectAll = () => setSelectedCourses(courses.map((c) => c.course_code));

  const persistAndNavigate = async () => {
    setSaving(true);
    try {
      sessionStorage.setItem(
        'onboarding_step2',
        JSON.stringify({ departmentId, level, courses: selectedCourses, topics: selectedCourses }),
      );
      if (learnerId) {
        await onboardingStep2({
          learner_id: learnerId,
          department_id: departmentId,
          level,
          selected_course_ids: selectedCourses,
          additional_subjects: [],
        });
      }
      navigate('/onboarding/step3');
    } catch {
      toast('Failed to save curriculum focus.', 'error');
    } finally {
      setSaving(false);
    }
  };

  const continueNext = () => {
    if (courses.length > 0 && selectedCourses.length === 0) return;
    if (courses.length === 0 || selectedCourses.length === 0) {
      setShowNoCourseWarning(true);
      return;
    }
    persistAndNavigate();
  };

  const canContinue = courses.length === 0 || selectedCourses.length > 0;

  return (
    <>
      <h2 className="text-[24px] font-extrabold">Curriculum Focus</h2>
      <p className="mt-2 text-text-secondary">Select the subjects you&apos;d like to prioritize.</p>

      <div className="mt-6 space-y-5">
        <div>
          <span className="label-caps text-text-muted">Select your department</span>
          <Select
            className="mt-2"
            value={departmentId}
            onChange={(e) => {
              setDepartmentId(e.target.value);
              setSelectedCourses([]);
            }}
            options={departments.map((d) => ({ value: d.id, label: d.name }))}
          />
        </div>

        <div>
          <span className="label-caps text-text-muted">Select your level</span>
          <div className="mt-2 flex flex-wrap gap-2">
            {LEVELS.map((l) => (
              <button
                key={l}
                type="button"
                onClick={() => {
                  setLevel(l);
                  setSelectedCourses([]);
                }}
                className={cn(
                  'rounded-full px-4 py-1.5 text-[13px] font-semibold',
                  level === l ? 'bg-primary text-white' : 'border border-border text-text-secondary',
                )}
              >
                {l} Level
              </button>
            ))}
          </div>
        </div>

        <div>
          {courses.length > 0 && (
            <div className="mb-2 flex items-center justify-between">
              <span className="label-caps text-text-muted">Your courses this level</span>
              <button type="button" onClick={selectAll} className="text-[13px] font-semibold text-primary">
                Select All
              </button>
            </div>
          )}
          <div className="mt-2 flex flex-wrap gap-2">
            {isLoading ? (
              <p className="text-[14px] text-text-muted">Loading courses...</p>
            ) : courses.length === 0 ? (
              <p className="text-[14px] text-text-secondary">
                No courses have been added for this department and level yet. Please check back later or contact your
                department administrator.
              </p>
            ) : (
              courses.map((c) => (
                <SubjectPill
                  key={c.id}
                  label={`${c.course_code} · ${c.course_title}`}
                  selected={selectedCourses.includes(c.course_code)}
                  onClick={() => toggleCourse(c.course_code)}
                />
              ))
            )}
          </div>
        </div>
      </div>

      {showNoCourseWarning && (
        <div className="mt-6 rounded-xl border border-warning/40 bg-warning-container/20 p-4">
          <p className="text-[14px] text-text-secondary">
            You have not selected any courses. You can add them later from Settings.
          </p>
          <Button className="mt-3" onClick={persistAndNavigate} disabled={saving}>
            Continue Anyway
          </Button>
        </div>
      )}

      <div className="mt-8 flex justify-end">
        <Button onClick={continueNext} disabled={saving || !canContinue}>
          Continue →
        </Button>
      </div>
    </>
  );
}

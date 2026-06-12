import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { CourseSelectItem } from '@/components/courses/CourseSelectItem';
import { SemesterFilterPills } from '@/components/courses/SemesterFilterPills';
import { fetchAdminCourses } from '@/api/adminCourses';
import { COURSE_LEVEL_OPTIONS } from '@/lib/courseLevel';
import { filterCoursesBySemester, type SemesterFilter } from '@/lib/courseSemester';
import { useToastStore } from '@/components/ui/Toast';
import { cn } from '@/lib/utils';

const LEVELS = COURSE_LEVEL_OPTIONS.map((opt) => opt.value);

export default function Step2CurriculumFocus() {
  const navigate = useNavigate();
  const toast = useToastStore((s) => s.add);
  const step1 = useMemo(() => {
    try {
      return JSON.parse(sessionStorage.getItem('onboarding_step1') ?? '{}') as {
        departmentId?: string;
        department?: string;
      };
    } catch {
      return {};
    }
  }, []);

  const departmentId = step1.departmentId ?? '';
  const [level, setLevel] = useState('200');
  const [selectedCourses, setSelectedCourses] = useState<string[]>([]);
  const [showNoCourseWarning, setShowNoCourseWarning] = useState(false);
  const [semesterFilter, setSemesterFilter] = useState<SemesterFilter>('All');

  const { data: courses = [], isLoading } = useQuery({
    queryKey: ['admin-courses', departmentId, level],
    queryFn: () => fetchAdminCourses(departmentId, level),
    enabled: !!departmentId && !!level,
  });
  const filteredCourses = filterCoursesBySemester(courses, semesterFilter);

  const toggleCourse = (id: string) => {
    setSelectedCourses((prev) => (prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]));
  };

  const selectAll = () => setSelectedCourses(filteredCourses.map((c) => c.id));

  const persistAndNavigate = () => {
    sessionStorage.setItem(
      'onboarding_step2',
      JSON.stringify({
        departmentId,
        department: step1.department,
        level,
        courses: selectedCourses,
        courseTitles: courses.filter((c) => selectedCourses.includes(c.id)).map((c) => c.course_title),
      }),
    );
    navigate('/onboarding/step3');
  };

  const continueNext = () => {
    if (!departmentId) {
      toast('Complete step 1 first — select your department.', 'warning');
      navigate('/onboarding/step1');
      return;
    }
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
      <p className="mt-2 text-text-secondary">
        Department: <strong>{step1.department || '—'}</strong>. Select courses for your level.
      </p>

      <div className="mt-6 space-y-5">
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
          <SemesterFilterPills value={semesterFilter} onChange={setSemesterFilter} />
          <div className="mt-3 space-y-2">
            {isLoading ? (
              <p className="text-[14px] text-text-muted">Loading courses...</p>
            ) : filteredCourses.length === 0 ? (
              <p className="text-[14px] text-text-secondary">
                No courses have been added for this department and level yet. Please check back later or contact your
                college administrator.
              </p>
            ) : (
              filteredCourses.map((c) => (
                <CourseSelectItem
                  key={c.id}
                  course={c}
                  selected={selectedCourses.includes(c.id)}
                  onClick={() => toggleCourse(c.id)}
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
          <Button className="mt-3" onClick={persistAndNavigate}>
            Continue Anyway
          </Button>
        </div>
      )}

      <div className="mt-8 flex justify-end">
        <Button onClick={continueNext} disabled={!canContinue}>
          Continue →
        </Button>
      </div>
    </>
  );
}

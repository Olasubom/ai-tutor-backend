import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { X } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Tabs } from '@/components/ui/Tabs';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Modal } from '@/components/ui/Modal';
import { Toggle } from '@/components/ui/Toggle';
import { SubjectPill } from '@/components/onboarding/SubjectPill';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/hooks/useAuth';
import { useToastStore } from '@/components/ui/Toast';
import { patchProfile } from '@/api/profile';
import { getMe } from '@/api/auth';
import { onboardingStep2, onboardingStep4 } from '@/api/onboarding';
import { fetchDepartments } from '@/api/courses';
import { fetchAdminCourses } from '@/api/adminCourses';
import {
  getNotificationPreferences,
  patchNotificationPreferences,
  type NotificationPreferences,
} from '@/api/notifications';
import { BookOpen, FileText, Gamepad2, Layers, Video } from 'lucide-react';
import { cn } from '@/lib/utils';

const FORMATS = [
  { id: 'video', icon: Video, title: 'Video Lectures' },
  { id: 'text', icon: FileText, title: 'Written Material' },
  { id: 'interactive', icon: Gamepad2, title: 'Interactive Quizzes' },
  { id: 'mixed', icon: Layers, title: 'Mixed Approach' },
];

const OBJECTIVES = ['Professional Certification', 'Academic Excellence', 'Skill Acquisition & Hobby'];
const LEVELS = ['100', '200', '300', '400', '500'];
const ACADEMIC_LEVELS = [
  { value: 'foundation', label: '100 Level' },
  { value: 'developing', label: '200-300 Level' },
  { value: 'advanced', label: '400 Level' },
  { value: 'postgraduate', label: 'Postgraduate' },
];

export default function Settings() {
  const [tab, setTab] = useState('profile');
  const { user, learnerId, updateUser } = useAuth();
  const toast = useToastStore((s) => s.add);
  const qc = useQueryClient();
  const meQ = useQuery({ queryKey: ['auth-me'], queryFn: getMe, enabled: !!user });

  const [fullName, setFullName] = useState('');
  const [department, setDepartment] = useState('');
  const [college, setCollege] = useState('');
  const [institution, setInstitution] = useState('');
  const [academicLevel, setAcademicLevel] = useState('developing');
  const [enrolled, setEnrolled] = useState<string[]>([]);
  const [hours, setHours] = useState(20);
  const [formats, setFormats] = useState<string[]>(['video']);
  const [objective, setObjective] = useState(OBJECTIVES[1]);
  const [courseModal, setCourseModal] = useState(false);
  const [pickerDept, setPickerDept] = useState('');
  const [pickerLevel, setPickerLevel] = useState('200');
  const [pickerSelected, setPickerSelected] = useState<string[]>([]);

  const departmentsQ = useQuery({ queryKey: ['departments-settings'], queryFn: () => fetchDepartments() });
  const departments = departmentsQ.data ?? [];
  const coursesQ = useQuery({
    queryKey: ['admin-courses-settings', pickerDept, pickerLevel],
    queryFn: () => fetchAdminCourses(pickerDept, pickerLevel),
    enabled: courseModal && !!pickerDept,
  });

  const prefsQ = useQuery({
    queryKey: ['notification-prefs', learnerId],
    queryFn: () => getNotificationPreferences(learnerId),
    enabled: !!learnerId && tab === 'notifications',
  });
  const [prefs, setPrefs] = useState<NotificationPreferences | null>(null);

  useEffect(() => {
    if (prefsQ.data) setPrefs(prefsQ.data);
  }, [prefsQ.data]);

  useEffect(() => {
    const profile = meQ.data;
    if (!profile) return;
    setFullName(profile.name ?? '');
    setDepartment(profile.department ?? '');
    setCollege(profile.college ?? '');
    setInstitution(profile.institution ?? '');
    setAcademicLevel(profile.academic_level ?? 'developing');
    setEnrolled(profile.courses ?? []);
    const prefs = profile.preferences ?? {};
    setHours(Number(prefs.weekly_hours ?? 20));
    setFormats((prefs.content_formats as string[]) ?? ['video']);
    setObjective(String(prefs.primary_objective ?? OBJECTIVES[1]));
    const deptMatch = departments.find((d) => d.name === profile.department);
    if (deptMatch) setPickerDept(deptMatch.id);
  }, [meQ.data, departments]);

  const saveProfile = async () => {
    try {
      await patchProfile({
        full_name: fullName,
        department,
        college,
        institution,
        academic_level: academicLevel,
      });
      updateUser({ name: fullName });
      toast('Profile updated', 'success');
      qc.invalidateQueries({ queryKey: ['auth-me'] });
    } catch {
      toast('Failed to update profile', 'error');
    }
  };

  const saveCourses = async (ids: string[]) => {
    setEnrolled(ids);
    try {
      await onboardingStep2({
        learner_id: learnerId,
        department_id: pickerDept || departments.find((d) => d.name === department)?.id || '',
        level: pickerLevel,
        selected_course_ids: ids,
        additional_subjects: [],
      });
      toast('Courses updated', 'success');
      qc.invalidateQueries({ queryKey: ['auth-me'] });
    } catch {
      toast('Failed to update courses', 'error');
    }
  };

  const savePreferences = async () => {
    try {
      await onboardingStep4({
        learner_id: learnerId,
        weekly_hours: hours,
        content_formats: formats,
        primary_objective: objective,
      });
      toast('Preferences saved. AI will update your recommendations.', 'success');
      qc.invalidateQueries({ queryKey: ['auth-me'] });
    } catch {
      toast('Failed to save preferences', 'error');
    }
  };

  const togglePref = async (key: keyof NotificationPreferences, value: boolean) => {
    const next = { ...(prefs ?? prefsQ.data!), [key]: value };
    setPrefs(next);
    await patchNotificationPreferences(learnerId, { [key]: value });
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
      <Card className="h-fit p-4">
        <Tabs
          active={tab}
          onChange={setTab}
          tabs={[
            { id: 'profile', label: 'Profile' },
            { id: 'courses', label: 'My Courses' },
            { id: 'preferences', label: 'Study Preferences' },
            { id: 'notifications', label: 'Notifications' },
          ]}
        />
      </Card>
      <Card className="p-6">
        {tab === 'profile' && (
          <div className="space-y-4">
            <h2 className="text-[18px] font-bold">Profile</h2>
            <Input label="Full Name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
            <div>
              <Input label="Email" value={user?.email ?? ''} disabled />
              <p className="mt-1 text-[12px] text-text-muted">Contact support to change</p>
            </div>
            <Input label="Department" value={department} onChange={(e) => setDepartment(e.target.value)} />
            <Input label="Institution" value={institution} onChange={(e) => setInstitution(e.target.value)} />
            <Input label="College" value={college} onChange={(e) => setCollege(e.target.value)} />
            <Select
              label="Academic Level"
              value={academicLevel}
              onChange={(e) => setAcademicLevel(e.target.value)}
              options={ACADEMIC_LEVELS}
            />
            <Button onClick={saveProfile}>Save Changes</Button>
          </div>
        )}

        {tab === 'courses' && (
          <div className="space-y-4">
            <h2 className="text-[18px] font-bold">Enrolled Courses</h2>
            <p className="text-[14px] text-text-secondary">
              These are the courses the AI uses to personalize your recommendations and study plan.
            </p>
            {enrolled.length === 0 ? (
              <EmptyState
                icon={BookOpen}
                title="No courses enrolled"
                description="Add courses from your department to personalize your learning path."
                action={{ label: 'Add Courses', onClick: () => setCourseModal(true) }}
              />
            ) : (
              <div className="flex flex-wrap gap-2">
                {enrolled.map((code) => (
                  <span
                    key={code}
                    className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 text-[13px]"
                  >
                    {code}
                    <button
                      type="button"
                      onClick={() => saveCourses(enrolled.filter((c) => c !== code))}
                      className="text-text-muted hover:text-error"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
            <Button variant="secondary" onClick={() => { setPickerSelected(enrolled); setCourseModal(true); }}>
              Add More Courses
            </Button>
          </div>
        )}

        {tab === 'preferences' && (
          <div className="space-y-6">
            <h2 className="text-[18px] font-bold">Study Preferences</h2>
            <div>
              <div className="flex items-center justify-between">
                <span className="font-semibold">Weekly Study Commitment</span>
                <span className="text-[28px] font-extrabold text-primary">{hours} hrs/week</span>
              </div>
              <input type="range" min={1} max={40} value={hours} onChange={(e) => setHours(Number(e.target.value))} className="mt-3 w-full accent-primary" />
            </div>
            <div>
              <h3 className="font-semibold">Preferred Content Type</h3>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                {FORMATS.map((f) => (
                  <button
                    key={f.id}
                    type="button"
                    onClick={() => setFormats((p) => (p.includes(f.id) ? p.filter((x) => x !== f.id) : [...p, f.id]))}
                    className={cn('rounded-xl border p-4 text-left', formats.includes(f.id) ? 'border-2 border-primary bg-primary/5' : 'border-border')}
                  >
                    <f.icon className="mb-2 h-5 w-5 text-primary" />
                    <div className="font-bold">{f.title}</div>
                  </button>
                ))}
              </div>
            </div>
            <div>
              <h3 className="font-semibold">Primary Learning Goal</h3>
              <div className="mt-3 space-y-2">
                {OBJECTIVES.map((o) => (
                  <button
                    key={o}
                    type="button"
                    onClick={() => setObjective(o)}
                    className={cn('flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left text-[14px]', objective === o ? 'border-2 border-primary bg-primary/5' : 'border-border')}
                  >
                    <span className={cn('h-4 w-4 rounded-full border-2', objective === o ? 'border-primary bg-primary' : 'border-border')} />
                    {o}
                  </button>
                ))}
              </div>
            </div>
            <Button onClick={savePreferences}>Save Preferences</Button>
          </div>
        )}

        {tab === 'notifications' && prefs && (
          <div className="space-y-4">
            <h2 className="text-[18px] font-bold">Notifications</h2>
            {(
              [
                ['study_reminders', 'Study reminders'],
                ['new_recommendation_alerts', 'New recommendation alerts'],
                ['weekly_progress_email', 'Weekly progress report email'],
                ['task_due_alerts', 'Task due date alerts'],
                ['mastery_drop_alerts', 'AI-detected knowledge drop alerts'],
              ] as const
            ).map(([key, label]) => (
              <div key={key} className="flex items-center justify-between border-b border-border py-3">
                <span className="text-[14px]">{label}</span>
                <Toggle checked={prefs[key]} onChange={(v) => togglePref(key, v)} />
              </div>
            ))}
          </div>
        )}
      </Card>

      <Modal open={courseModal} onClose={() => setCourseModal(false)} title="Add Courses">
        <div className="space-y-4">
          <Select
            label="Department"
            value={pickerDept}
            onChange={(e) => setPickerDept(e.target.value)}
            options={departments.map((d) => ({ value: d.id, label: d.name }))}
          />
          <Select label="Level" value={pickerLevel} onChange={(e) => setPickerLevel(e.target.value)} options={LEVELS.map((l) => ({ value: l, label: `${l} Level` }))} />
          <div className="flex flex-wrap gap-2">
            {(coursesQ.data ?? []).length === 0 ? (
              <p className="text-[14px] text-text-muted">No courses available for this department and level.</p>
            ) : (
              coursesQ.data!.map((c) => (
                <SubjectPill
                  key={c.id}
                  label={`${c.course_code} · ${c.course_title}`}
                  selected={pickerSelected.includes(c.course_code)}
                  onClick={() =>
                    setPickerSelected((p) =>
                      p.includes(c.course_code) ? p.filter((x) => x !== c.course_code) : [...p, c.course_code],
                    )
                  }
                />
              ))
            )}
          </div>
          <Button
            onClick={() => {
              saveCourses(pickerSelected);
              setCourseModal(false);
            }}
          >
            Save Courses
          </Button>
        </div>
      </Modal>
    </div>
  );
}

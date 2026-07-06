import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BookOpen, Users } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { Skeleton } from '@/components/ui/Skeleton';
import { StatCard } from '@/components/ui/StatCard';
import { getMe } from '@/api/auth';
import {
  getCourseAnalyticsOverview,
  getCourseStudentAnalytics,
  listLecturerManagedCourses,
} from '@/api/lecturerDashboard';
import { useAuth } from '@/hooks/useAuth';
import { useAuthStore } from '@/stores/authStore';

const HONORIFICS = new Set(['mr', 'mr.', 'mrs', 'mrs.', 'ms', 'ms.', 'dr', 'dr.', 'prof', 'prof.', 'engr', 'engr.']);

function firstNameFrom(fullName?: string | null): string {
  if (!fullName?.trim()) return '';
  const parts = fullName.trim().split(/\s+/);
  for (const part of parts) {
    if (!HONORIFICS.has(part.toLowerCase())) return part;
  }
  return parts[parts.length - 1] ?? '';
}

export default function LecturerDashboard() {
  const { user } = useAuth();
  const [courseId, setCourseId] = useState('');

  const profileQ = useQuery({
    queryKey: ['lecturer-me'],
    queryFn: getMe,
    enabled: !!user,
  });

  useEffect(() => {
    const profileName = profileQ.data?.name?.trim();
    if (!profileName) return;
    const store = useAuthStore.getState();
    if (store.name === profileName) return;
    useAuthStore.setState({ name: profileName });
    const raw = localStorage.getItem('ai_tutor_user');
    if (raw) {
      try {
        const stored = JSON.parse(raw) as { name?: string };
        localStorage.setItem('ai_tutor_user', JSON.stringify({ ...stored, name: profileName }));
      } catch {
        /* ignore */
      }
    }
  }, [profileQ.data?.name]);

  const coursesQ = useQuery({
    queryKey: ['lecturer-managed-courses'],
    queryFn: listLecturerManagedCourses,
    enabled: !!user,
  });

  const activeCourseId = courseId || coursesQ.data?.[0]?.id || '';

  const overviewQ = useQuery({
    queryKey: ['lecturer-analytics-overview', activeCourseId],
    queryFn: () => getCourseAnalyticsOverview(activeCourseId),
    enabled: !!activeCourseId,
  });

  const studentsQ = useQuery({
    queryKey: ['lecturer-analytics-students', activeCourseId],
    queryFn: () => getCourseStudentAnalytics(activeCourseId),
    enabled: !!activeCourseId,
  });

  const aggregated = useMemo(() => {
    const ovs = overviewQ.data;
    if (!ovs) return { students: 0, avgMastery: 0, atRisk: 0 };
    return {
      students: ovs.total_students,
      avgMastery: Math.round(ovs.avg_mastery),
      atRisk: ovs.students_at_risk,
    };
  }, [overviewQ.data]);

  const fullName =
    profileQ.data?.name?.trim() ||
    user?.name?.trim() ||
    profileQ.data?.email?.split('@')[0] ||
    '';
  const displayName = firstNameFrom(fullName) || 'Lecturer';

  return (
    <div className="space-y-6">
      <div>
        <Badge variant="muted">LECTURER PORTAL</Badge>
        <h1 className="mt-2 text-[28px] font-extrabold tracking-tight">
          Welcome{displayName ? `, ${displayName}` : ''}.
        </h1>
        <p className="text-text-secondary">
          {profileQ.data?.department
            ? `${profileQ.data.department} — live analytics from enrolled students.`
            : 'Monitor student progress across your courses.'}
        </p>
      </div>

      {coursesQ.data && coursesQ.data.length > 1 && (
        <select
          className="max-w-md rounded-lg border border-border bg-input px-3 py-2 text-[14px]"
          value={activeCourseId}
          onChange={(e) => {
            setCourseId(e.target.value);
            localStorage.setItem('lecturerActiveCourseId', e.target.value);
          }}
        >
          {coursesQ.data.map((c) => (
            <option key={c.id} value={c.id}>
              {c.code} — {c.title}
            </option>
          ))}
        </select>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard
          label="Students"
          value={overviewQ.isLoading ? '…' : String(aggregated.students)}
          trend={activeCourseId ? 'Enrolled in selected course' : 'Select a course'}
        />
        <StatCard
          label="Avg. Mastery"
          value={overviewQ.isLoading ? '…' : `${aggregated.avgMastery}%`}
          trend="BKT profile average"
        />
        <StatCard
          label="At risk"
          value={overviewQ.isLoading ? '…' : String(aggregated.atRisk)}
          trend="Mastery below 40%"
        />
      </div>

      {overviewQ.data && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card className="p-4">
            <div className="text-[13px] text-text-muted">Active this week</div>
            <div className="text-[24px] font-bold">{overviewQ.data.active_this_week}</div>
          </Card>
          <Card className="p-4">
            <div className="text-[13px] text-text-muted">Struggled topics</div>
            <div className="mt-1 text-[14px]">
              {overviewQ.data.most_struggled_topics.length
                ? overviewQ.data.most_struggled_topics.join(', ')
                : 'None yet'}
            </div>
            <div className="mt-1 text-[12px] text-text-muted">2+ quiz attempts and mastery below 40%</div>
          </Card>
        </div>
      )}

      <Card className="p-6">
        <div className="mb-4 flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-primary" />
          <h2 className="text-[18px] font-bold">Your courses</h2>
        </div>
        {coursesQ.isLoading ? (
          <Skeleton className="h-24" />
        ) : !coursesQ.data?.length ? (
          <p className="text-text-secondary">
            No courses in your department yet. Use the Courses page to create one, or ask admin to run lecturer
            backfill.
          </p>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {coursesQ.data.map((course) => (
              <div key={course.id} className="rounded-xl border border-border p-4">
                <div className="font-bold">{course.code}</div>
                <p className="mt-1 text-[14px] text-text-secondary">{course.title}</p>
                <p className="mt-1 text-[12px] text-text-muted">Level {course.level}</p>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card className="p-6">
        <div className="mb-4 flex items-center gap-2">
          <Users className="h-5 w-5 text-primary" />
          <h2 className="text-[18px] font-bold">Student mastery</h2>
        </div>
        {studentsQ.isLoading ? (
          <Skeleton className="h-24" />
        ) : !studentsQ.data?.length ? (
          <p className="text-text-secondary">
            No enrolled students for this course. Students are enrolled when they select courses during onboarding.
          </p>
        ) : (
          <div className="space-y-4">
            {studentsQ.data.map((row) => (
              <div key={row.student_id}>
                <div className="mb-1 flex justify-between text-[14px]">
                  <span className="font-medium">
                    {row.name}{' '}
                    <span className="text-[12px] text-text-muted">({row.status.replace('_', ' ')})</span>
                  </span>
                  <span className="text-text-muted">{Math.round(row.overall_mastery)}%</span>
                </div>
                <ProgressBar value={Math.round(row.overall_mastery)} />
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

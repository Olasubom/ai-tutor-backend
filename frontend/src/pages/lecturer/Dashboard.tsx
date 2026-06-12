import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BookOpen, Users } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { Skeleton } from '@/components/ui/Skeleton';
import { StatCard } from '@/components/ui/StatCard';
import { SemesterBadge } from '@/components/ui/SemesterBadge';
import { getMe } from '@/api/auth';
import { getLecturerClassOverview } from '@/api/lecturer';
import { fetchCourses, fetchDepartments } from '@/api/courses';
import { useAuth } from '@/hooks/useAuth';

export default function LecturerDashboard() {
  const { user } = useAuth();
  const profileQ = useQuery({ queryKey: ['lecturer-me'], queryFn: getMe, enabled: !!user });

  const { data, isLoading } = useQuery({
    queryKey: ['lecturer-overview', profileQ.data?.department],
    queryFn: () => getLecturerClassOverview(profileQ.data?.department),
    enabled: !!user,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });

  const departmentsQ = useQuery({
    queryKey: ['lecturer-departments'],
    queryFn: () => fetchDepartments(),
    enabled: !!user,
  });

  const departmentId = useMemo(() => {
    const deptName = profileQ.data?.department;
    if (!deptName) return '';
    return departmentsQ.data?.find((d) => d.name === deptName)?.id ?? '';
  }, [departmentsQ.data, profileQ.data?.department]);

  const coursesQ = useQuery({
    queryKey: ['lecturer-dept-courses', departmentId],
    queryFn: () => fetchCourses(departmentId),
    enabled: !!departmentId,
  });

  const avgMastery =
    data && data.length > 0 ? Math.round(data.reduce((a, r) => a + r.mastery, 0) / data.length) : 0;

  return (
    <div className="space-y-6">
      <div>
        <Badge variant="muted">LECTURER PORTAL</Badge>
        <h1 className="mt-2 text-[28px] font-extrabold tracking-tight">Welcome, {user?.name?.split(' ')[0]}.</h1>
        <p className="text-text-secondary">
          {profileQ.data?.department
            ? `${profileQ.data.department} — class overview and student mastery.`
            : 'Monitor student progress in your department.'}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Students" value={String(data?.length ?? 0)} trend="In your department" />
        <StatCard label="Avg. Mastery" value={`${avgMastery}%`} trend="Across enrolled students" />
        <StatCard
          label="Staff ID"
          value={profileQ.data?.nuc_staff_id ?? '—'}
          trend={<span className="text-teal">Verified lecturer</span>}
        />
      </div>

      <Card className="p-6">
        <div className="mb-4 flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-primary" />
          <h2 className="text-[18px] font-bold">Department courses</h2>
        </div>
        {coursesQ.isLoading ? (
          <Skeleton className="h-24" />
        ) : !coursesQ.data?.length ? (
          <p className="text-text-secondary">No courses listed for your department yet.</p>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {coursesQ.data.map((course) => (
              <div key={course.id} className="rounded-xl border border-border p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[16px] font-bold">{course.course_code}</span>
                      <SemesterBadge semester={course.semester} size="md" />
                    </div>
                    <p className="mt-1 text-[14px] text-text-secondary">{course.course_title}</p>
                    <p className="mt-1 text-[12px] text-text-muted">
                      Level {course.level} · {course.units} credit units
                    </p>
                  </div>
                </div>
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
        {isLoading ? (
          <Skeleton className="h-24" />
        ) : !data?.length ? (
          <p className="text-text-secondary">No students enrolled in your department yet.</p>
        ) : (
          <div className="space-y-4">
            {data.map((row) => (
              <div key={row.student.user_id}>
                <div className="mb-1 flex justify-between text-[14px]">
                  <span className="font-medium">{row.student.name}</span>
                  <span className="text-text-muted">{row.mastery}%</span>
                </div>
                <ProgressBar value={row.mastery} />
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

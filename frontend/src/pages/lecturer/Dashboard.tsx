import { useQuery } from '@tanstack/react-query';
import { Users } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { Skeleton } from '@/components/ui/Skeleton';
import { StatCard } from '@/components/ui/StatCard';
import { getLecturerClassOverview } from '@/api/lecturer';
import { fetchDepartments } from '@/api/courses';
import { useAuth } from '@/hooks/useAuth';

export default function LecturerDashboard() {
  const { user } = useAuth();
  const department = fetchDepartments().find((d) => d.id === user?.department_id);

  const { data, isLoading } = useQuery({
    queryKey: ['lecturer-overview', user?.department_id],
    queryFn: () => getLecturerClassOverview(user?.department_id),
    enabled: !!user,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });

  const avgMastery =
    data && data.length > 0
      ? Math.round(data.reduce((a, r) => a + r.mastery, 0) / data.length)
      : 0;

  return (
    <div className="space-y-6">
      <div>
        <Badge variant="muted">LECTURER PORTAL</Badge>
        <h1 className="mt-2 text-[28px] font-extrabold tracking-tight">Welcome, {user?.name?.split(' ')[0]}.</h1>
        <p className="text-text-secondary">
          {department ? `${department.name} — class overview and student mastery.` : 'Monitor student progress in your department.'}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Students" value={String(data?.length ?? 0)} trend="In your department" />
        <StatCard label="Avg. Mastery" value={`${avgMastery}%`} trend="Across enrolled students" />
        <StatCard
          label="Staff ID"
          value={user?.staff_id ?? '—'}
          trend={<span className="text-teal">Verified lecturer</span>}
        />
      </div>

      <Card className="p-6">
        <div className="mb-4 flex items-center gap-2">
          <Users className="h-5 w-5 text-primary" />
          <h2 className="text-[18px] font-bold">Student mastery overview</h2>
        </div>

        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-14" />
            ))}
          </div>
        ) : !data?.length ? (
          <p className="text-[14px] text-text-muted">
            No students enrolled in your department yet. Students appear here after they complete onboarding.
          </p>
        ) : (
          <div className="divide-y divide-border">
            {data.map((row) => (
              <div key={row.student.user_id} className="flex items-center gap-4 py-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-[14px] font-bold text-primary">
                  {row.student.name
                    .split(' ')
                    .map((n) => n[0])
                    .join('')
                    .slice(0, 2)
                    .toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="font-semibold text-text-primary">{row.student.name}</div>
                  <div className="text-[13px] text-text-muted">{row.student.email}</div>
                </div>
                <div className="w-40">
                  <div className="mb-1 flex justify-between text-[12px]">
                    <span className="text-text-muted">Mastery</span>
                    <span className="font-bold">{row.mastery}%</span>
                  </div>
                  <ProgressBar value={row.mastery} />
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

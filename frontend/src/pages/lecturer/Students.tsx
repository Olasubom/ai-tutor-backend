import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Users } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { Skeleton } from '@/components/ui/Skeleton';
import {
  getCourseStudentAnalytics,
  listLecturerManagedCourses,
} from '@/api/lecturerDashboard';

export default function LecturerStudents() {
  const [courseId, setCourseId] = useState('');

  const coursesQ = useQuery({
    queryKey: ['lecturer-managed-courses'],
    queryFn: listLecturerManagedCourses,
  });

  const activeCourseId = courseId || coursesQ.data?.[0]?.id || '';

  const studentsQ = useQuery({
    queryKey: ['lecturer-analytics-students', activeCourseId],
    queryFn: () => getCourseStudentAnalytics(activeCourseId),
    enabled: !!activeCourseId,
  });

  return (
    <div className="space-y-6">
      <div>
        <Badge variant="muted">STUDENTS</Badge>
        <h1 className="mt-2 text-[28px] font-extrabold">Enrolled Students</h1>
        <p className="text-text-secondary">Per-student mastery and activity for your courses.</p>
      </div>

      <select
        className="max-w-md rounded-lg border border-border bg-input px-3 py-2 text-[14px]"
        value={activeCourseId}
        onChange={(e) => setCourseId(e.target.value)}
      >
        {(coursesQ.data ?? []).map((c) => (
          <option key={c.id} value={c.id}>
            {c.code} — {c.title}
          </option>
        ))}
      </select>

      <Card className="p-6">
        <div className="mb-4 flex items-center gap-2">
          <Users className="h-5 w-5 text-primary" />
          <h2 className="text-[18px] font-bold">Roster</h2>
        </div>
        {studentsQ.isLoading ? (
          <Skeleton className="h-24" />
        ) : !studentsQ.data?.length ? (
          <p className="text-text-secondary">No students enrolled in this course yet.</p>
        ) : (
          <div className="space-y-4">
            {studentsQ.data.map((row) => (
              <div key={row.student_id} className="rounded-xl border border-border p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="font-semibold">{row.name}</div>
                    <div className="text-[13px] text-text-muted">{row.email}</div>
                  </div>
                  <Badge variant={row.status === 'at_risk' ? 'error' : row.status === 'inactive' ? 'muted' : 'teal'}>
                    {row.status.replace('_', ' ')}
                  </Badge>
                </div>
                <div className="mt-3 flex justify-between text-[13px] text-text-muted">
                  <span>Mastery {Math.round(row.overall_mastery)}%</span>
                  <span>Modules done: {row.modules_completed}</span>
                  {row.quiz_average != null && <span>Quiz avg: {row.quiz_average}%</span>}
                </div>
                <ProgressBar className="mt-2" value={Math.round(row.overall_mastery)} />
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

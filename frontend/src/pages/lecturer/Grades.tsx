import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { GraduationCap } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Skeleton } from '@/components/ui/Skeleton';
import {
  getCourseStudentAnalytics,
  listLecturerManagedCourses,
  type GradeRow,
  listCourseGrades,
  submitGrade,
} from '@/api/lecturerDashboard';
import { useToastStore } from '@/components/ui/Toast';

type DraftScores = Record<string, { ca: string; exam: string }>;

export default function LecturerGrades() {
  const toast = useToastStore((s) => s.add);
  const qc = useQueryClient();
  const [courseId, setCourseId] = useState('');
  const [drafts, setDrafts] = useState<DraftScores>({});

  const coursesQ = useQuery({
    queryKey: ['lecturer-managed-courses'],
    queryFn: listLecturerManagedCourses,
  });

  const activeCourseId = courseId || coursesQ.data?.[0]?.id || '';

  const studentsQ = useQuery({
    queryKey: ['lecturer-course-students', activeCourseId],
    queryFn: () => getCourseStudentAnalytics(activeCourseId),
    enabled: !!activeCourseId,
  });

  const gradesQ = useQuery({
    queryKey: ['lecturer-course-grades', activeCourseId],
    queryFn: () => listCourseGrades(activeCourseId),
    enabled: !!activeCourseId,
  });

  const gradeByStudent = useMemo(() => {
    const map: Record<string, GradeRow> = {};
    for (const g of gradesQ.data ?? []) {
      map[g.student_id] = g;
    }
    return map;
  }, [gradesQ.data]);

  const saveMut = useMutation({
    mutationFn: (studentId: string) => {
      const d = drafts[studentId] ?? {};
      const existing = gradeByStudent[studentId];
      return submitGrade(activeCourseId, {
        student_id: studentId,
        ca_score: d.ca !== undefined && d.ca !== '' ? parseFloat(d.ca) : existing?.ca_score ?? undefined,
        exam_score:
          d.exam !== undefined && d.exam !== '' ? parseFloat(d.exam) : existing?.exam_score ?? undefined,
      });
    },
    onSuccess: async () => {
      toast('Grade saved', 'success');
      await qc.invalidateQueries({ queryKey: ['lecturer-course-grades', activeCourseId] });
    },
    onError: () => toast('Could not save grade', 'error'),
  });

  const setDraft = (studentId: string, field: 'ca' | 'exam', value: string) => {
    setDrafts((prev) => ({
      ...prev,
      [studentId]: { ...prev[studentId], [field]: value },
    }));
  };

  return (
    <div className="space-y-6">
      <div>
        <Badge variant="muted">GRADES</Badge>
        <h1 className="mt-2 text-[28px] font-extrabold">Course Grades</h1>
        <p className="text-text-secondary">Enter CA and exam scores. Totals and grade letters are computed automatically.</p>
      </div>

      <Card className="p-4">
        <label className="text-[13px] font-semibold text-text-muted">Course</label>
        <select
          className="mt-2 w-full max-w-md rounded-lg border border-border bg-input px-3 py-2 text-[14px]"
          value={activeCourseId}
          onChange={(e) => setCourseId(e.target.value)}
        >
          {(coursesQ.data ?? []).map((c) => (
            <option key={c.id} value={c.id}>
              {c.code} — {c.title}
            </option>
          ))}
        </select>
      </Card>

      <Card className="overflow-x-auto p-0">
        {studentsQ.isLoading || gradesQ.isLoading ? (
          <div className="p-6">
            <Skeleton className="h-24" />
          </div>
        ) : !studentsQ.data?.length ? (
          <p className="p-6 text-text-secondary">No enrolled students for this course yet.</p>
        ) : (
          <table className="w-full min-w-[720px] text-left text-[14px]">
            <thead className="border-b border-border bg-card-hover text-[12px] uppercase text-text-muted">
              <tr>
                <th className="px-4 py-3">Student</th>
                <th className="px-4 py-3">CA (/40)</th>
                <th className="px-4 py-3">Exam (/60)</th>
                <th className="px-4 py-3">AI Quiz Avg</th>
                <th className="px-4 py-3">Quizzes Taken</th>
                <th className="px-4 py-3">Total</th>
                <th className="px-4 py-3">Grade</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {studentsQ.data.map((s) => {
                const g = gradeByStudent[s.student_id];
                const draft = drafts[s.student_id] ?? {};
                return (
                  <tr key={s.student_id} className="border-b border-border">
                    <td className="px-4 py-3">
                      <div className="font-medium">{s.name}</div>
                      <div className="text-[12px] text-text-muted">{s.email}</div>
                    </td>
                    <td className="px-4 py-3">
                      <Input
                        className="w-20"
                        type="number"
                        min={0}
                        max={40}
                        placeholder={g?.ca_score != null ? String(g.ca_score) : '0'}
                        value={draft.ca ?? ''}
                        onChange={(e) => setDraft(s.student_id, 'ca', e.target.value)}
                      />
                    </td>
                    <td className="px-4 py-3">
                      <Input
                        className="w-20"
                        type="number"
                        min={0}
                        max={60}
                        placeholder={g?.exam_score != null ? String(g.exam_score) : '0'}
                        value={draft.exam ?? ''}
                        onChange={(e) => setDraft(s.student_id, 'exam', e.target.value)}
                      />
                    </td>
                    <td className="px-4 py-3">
                      {s.quiz_average != null ? (
                        <span className={`font-medium ${s.quiz_average >= 60 ? 'text-teal' : 'text-error'}`}>
                          {Math.round(s.quiz_average)}%
                        </span>
                      ) : (
                        <span className="text-text-muted">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-text-secondary">{s.quiz_count ?? 0}</td>
                    <td className="px-4 py-3">{g?.total_score != null ? `${g.total_score}%` : '—'}</td>
                    <td className="px-4 py-3">
                      {g?.grade_letter ? (
                        <span className="inline-flex items-center gap-1">
                          <GraduationCap className="h-4 w-4 text-primary" />
                          {g.grade_letter} ({g.grade_point})
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <Button
                        variant="secondary"
                        disabled={saveMut.isPending}
                        onClick={() => saveMut.mutate(s.student_id)}
                      >
                        Save
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

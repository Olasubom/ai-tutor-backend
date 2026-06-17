import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, ClipboardList, Sparkles, X } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Skeleton } from '@/components/ui/Skeleton';
import {
  approveQuizQuestion,
  createModuleQuiz,
  generateQuizQuestions,
  getLecturerCourse,
  getQuizDetail,
  getCourseAiQuizResults,
  listLecturerManagedCourses,
  listModuleQuizzes,
  publishQuiz,
  rejectQuizQuestion,
  type LecturerQuiz,
  type QuizQuestion,
} from '@/api/lecturerDashboard';
import { useToastStore } from '@/components/ui/Toast';
import { cn } from '@/lib/utils';

export default function LecturerQuizzes() {
  const toast = useToastStore((s) => s.add);
  const qc = useQueryClient();
  const [courseId, setCourseId] = useState('');
  const [moduleId, setModuleId] = useState('');
  const [quizTitle, setQuizTitle] = useState('');
  const [expandedQuizId, setExpandedQuizId] = useState<string | null>(null);
  const [rejectTarget, setRejectTarget] = useState<QuizQuestion | null>(null);

  const coursesQ = useQuery({
    queryKey: ['lecturer-managed-courses'],
    queryFn: listLecturerManagedCourses,
  });

  const activeCourseId = courseId || coursesQ.data?.[0]?.id || '';
  const detailQ = useQuery({
    queryKey: ['lecturer-course-detail', activeCourseId],
    queryFn: () => getLecturerCourse(activeCourseId),
    enabled: !!activeCourseId,
  });

  const modules = detailQ.data?.modules ?? [];
  const activeModuleId = moduleId || modules[0]?.id || '';

  const quizzesQ = useQuery({
    queryKey: ['lecturer-module-quizzes', activeModuleId],
    queryFn: () => listModuleQuizzes(activeModuleId),
    enabled: !!activeModuleId,
  });

  const aiQuizQ = useQuery({
    queryKey: ['lecturer-ai-quiz-results', activeCourseId],
    queryFn: () => getCourseAiQuizResults(activeCourseId),
    enabled: !!activeCourseId,
  });

  const quizDetailQ = useQuery({
    queryKey: ['lecturer-quiz-detail', expandedQuizId],
    queryFn: () => getQuizDetail(expandedQuizId!),
    enabled: !!expandedQuizId,
  });

  const patchQuizDetail = (updater: (prev: LecturerQuiz) => LecturerQuiz) => {
    if (!expandedQuizId) return;
    qc.setQueryData(['lecturer-quiz-detail', expandedQuizId], (prev: LecturerQuiz | undefined) => {
      if (!prev) return prev;
      return updater(prev);
    });
  };

  const createMut = useMutation({
    mutationFn: () => createModuleQuiz(activeModuleId, { title: quizTitle || 'Module Quiz' }),
    onSuccess: async (quiz) => {
      toast('Quiz created', 'success');
      setQuizTitle('');
      setExpandedQuizId(quiz.id);
      await qc.invalidateQueries({ queryKey: ['lecturer-module-quizzes', activeModuleId] });
    },
    onError: () => toast('Could not create quiz', 'error'),
  });

  const publishMut = useMutation({
    mutationFn: (quizId: string) => publishQuiz(quizId),
    onSuccess: async () => {
      toast('Quiz published', 'success');
      await qc.invalidateQueries({ queryKey: ['lecturer-module-quizzes', activeModuleId] });
      if (expandedQuizId) await qc.invalidateQueries({ queryKey: ['lecturer-quiz-detail', expandedQuizId] });
    },
    onError: () => toast('Could not publish quiz', 'error'),
  });

  const genMut = useMutation({
    mutationFn: (quizId: string) =>
      generateQuizQuestions(quizId, {
        topic: modules.find((m) => m.id === activeModuleId)?.title,
        count: 5,
        difficulty: 'medium',
      }),
    onSuccess: (created, quizId) => {
      toast('AI questions generated (pending approval)', 'success');
      setExpandedQuizId(quizId);
      const pendingAdded = created.filter((q) => q.ai_generated && !q.approved).length;
      qc.setQueryData(
        ['lecturer-module-quizzes', activeModuleId],
        (prev: LecturerQuiz[] | undefined) =>
          (prev ?? []).map((quiz) =>
            quiz.id === quizId
              ? { ...quiz, pending_review_count: (quiz.pending_review_count ?? 0) + pendingAdded }
              : quiz,
          ),
      );
      qc.setQueryData(['lecturer-quiz-detail', quizId], (prev: LecturerQuiz | undefined) => {
        const base = prev ?? { id: quizId, module_id: activeModuleId, title: '', is_published: false, max_attempts: 3 };
        const merged = [...(base.questions ?? [])];
        for (const q of created) {
          if (!merged.some((x) => x.id === q.id)) merged.push(q);
        }
        return {
          ...base,
          questions: merged,
          pending_review_count: merged.filter((q) => q.ai_generated && !q.approved).length,
        };
      });
    },
    onError: () => toast('Could not generate questions', 'error'),
  });

  const approveMut = useMutation({
    mutationFn: (questionId: string) => approveQuizQuestion(questionId),
    onSuccess: (updated) => {
      patchQuizDetail((prev) => ({
        ...prev,
        questions: (prev.questions ?? []).map((q) => (q.id === updated.id ? updated : q)),
        pending_review_count: (prev.questions ?? []).filter(
          (q) => q.id !== updated.id && q.ai_generated && !q.approved,
        ).length,
      }));
      qc.setQueryData(
        ['lecturer-module-quizzes', activeModuleId],
        (prev: LecturerQuiz[] | undefined) =>
          (prev ?? []).map((quiz) =>
            quiz.id === expandedQuizId
              ? { ...quiz, pending_review_count: Math.max(0, (quiz.pending_review_count ?? 0) - 1) }
              : quiz,
          ),
      );
      toast('Question approved', 'success');
    },
    onError: () => toast('Could not approve question', 'error'),
  });

  const rejectMut = useMutation({
    mutationFn: (questionId: string) => rejectQuizQuestion(questionId),
    onSuccess: (_, questionId) => {
      const wasPending = rejectTarget?.ai_generated && !rejectTarget?.approved;
      patchQuizDetail((prev) => ({
        ...prev,
        questions: (prev.questions ?? []).filter((q) => q.id !== questionId),
        pending_review_count: (prev.questions ?? []).filter(
          (q) => q.id !== questionId && q.ai_generated && !q.approved,
        ).length,
      }));
      if (wasPending) {
        qc.setQueryData(
          ['lecturer-module-quizzes', activeModuleId],
          (prev: LecturerQuiz[] | undefined) =>
            (prev ?? []).map((quiz) =>
              quiz.id === expandedQuizId
                ? { ...quiz, pending_review_count: Math.max(0, (quiz.pending_review_count ?? 0) - 1) }
                : quiz,
            ),
        );
      }
      toast('Question rejected', 'success');
      setRejectTarget(null);
    },
    onError: () => toast('Could not reject question', 'error'),
  });

  const toggleQuiz = (quizId: string) => {
    setExpandedQuizId((prev) => (prev === quizId ? null : quizId));
  };

  return (
    <div className="space-y-6">
      <div>
        <Badge variant="muted">QUIZZES</Badge>
        <h1 className="mt-2 text-[28px] font-extrabold">Assessments</h1>
        <p className="text-text-secondary">Create, generate, review, and publish module quizzes for enrolled students.</p>
      </div>

      <Card className="grid gap-4 p-4 md:grid-cols-2">
        <div>
          <label className="text-[13px] font-semibold text-text-muted">Course</label>
          <select
            className="mt-2 w-full rounded-lg border border-border bg-input px-3 py-2 text-[14px]"
            value={activeCourseId}
            onChange={(e) => {
              setCourseId(e.target.value);
              setModuleId('');
              setExpandedQuizId(null);
            }}
          >
            {(coursesQ.data ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.code} — {c.title}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-[13px] font-semibold text-text-muted">Module</label>
          <select
            className="mt-2 w-full rounded-lg border border-border bg-input px-3 py-2 text-[14px]"
            value={activeModuleId}
            onChange={(e) => {
              setModuleId(e.target.value);
              setExpandedQuizId(null);
            }}
          >
            {modules.map((m) => (
              <option key={m.id} value={m.id}>
                {m.order}. {m.title}
              </option>
            ))}
          </select>
        </div>
      </Card>

      <Card className="flex flex-wrap items-end gap-3 p-4">
        <Input
          className="max-w-sm"
          placeholder="Quiz title"
          value={quizTitle}
          onChange={(e) => setQuizTitle(e.target.value)}
        />
        <Button disabled={!activeModuleId || createMut.isPending} onClick={() => createMut.mutate()}>
          Create Quiz
        </Button>
      </Card>

      <Card className="p-6">
        <div className="mb-4 flex items-center gap-2">
          <ClipboardList className="h-5 w-5 text-primary" />
          <h2 className="text-[18px] font-bold">Quizzes for this module</h2>
        </div>
        {quizzesQ.isLoading ? (
          <Skeleton className="h-20" />
        ) : !quizzesQ.data?.length ? (
          <p className="text-text-secondary">No quizzes yet.</p>
        ) : (
          <div className="space-y-3">
            {quizzesQ.data.map((q) => {
              const expanded = expandedQuizId === q.id;
              const detail = expanded ? quizDetailQ.data : undefined;
              const pending =
                expanded && detail
                  ? (detail.questions ?? []).filter((x) => x.ai_generated && !x.approved).length
                  : (q.pending_review_count ?? 0);

              return (
                <div key={q.id} className="rounded-xl border border-border">
                  <div className="flex flex-wrap items-center justify-between gap-3 p-4">
                    <button type="button" className="text-left" onClick={() => toggleQuiz(q.id)}>
                      <div className="font-semibold">{q.title}</div>
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-[13px] text-text-muted">
                        {q.is_published ? (
                          <Badge variant="teal">Published</Badge>
                        ) : (
                          <Badge variant="warning">Draft</Badge>
                        )}
                        {pending > 0 && (
                          <Badge variant="warning">{pending} pending review</Badge>
                        )}
                      </div>
                    </button>
                    <div className="flex gap-2">
                      <Button variant="secondary" disabled={genMut.isPending} onClick={() => genMut.mutate(q.id)}>
                        <Sparkles className="mr-1 h-4 w-4" /> AI Generate
                      </Button>
                      {!q.is_published && (
                        <Button
                          disabled={publishMut.isPending || pending > 0}
                          title={
                            pending > 0
                              ? `${pending} AI question(s) must be approved before publishing`
                              : undefined
                          }
                          onClick={() => {
                            if (pending > 0) {
                              toast('Approve all AI-generated questions before publishing', 'error');
                              if (!expanded) setExpandedQuizId(q.id);
                              return;
                            }
                            publishMut.mutate(q.id);
                          }}
                        >
                          Publish
                        </Button>
                      )}
                    </div>
                  </div>

                  {expanded && (
                    <div className="border-t border-border px-4 pb-4">
                      {quizDetailQ.isLoading ? (
                        <Skeleton className="mt-4 h-24" />
                      ) : !(detail?.questions?.length ?? 0) ? (
                        <p className="mt-4 text-[14px] text-text-secondary">
                          No questions yet. Use AI Generate or add questions manually.
                        </p>
                      ) : (
                        <div className="mt-4 space-y-3">
                          {pending > 0 && (
                            <p className="rounded-lg border border-warning/40 bg-warning-container/20 px-3 py-2 text-[13px] text-text-secondary">
                              {pending} AI-generated question(s) need approval before you can publish this quiz.
                            </p>
                          )}
                          {detail!.questions!.map((question, idx) => (
                            <QuestionRow
                              key={question.id}
                              index={idx + 1}
                              question={question}
                              onApprove={() => approveMut.mutate(question.id)}
                              onReject={() => setRejectTarget(question)}
                              busy={approveMut.isPending || rejectMut.isPending}
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {(aiQuizQ.data?.length ?? 0) > 0 && (
        <Card className="p-6">
          <h3 className="mb-3 text-[15px] font-bold">
            AI Quiz Results{' '}
            <span className="text-xs font-normal text-text-muted">from student module sessions</span>
          </h3>
          <div className="space-y-2">
            {aiQuizQ.data!.map((q) => (
              <div
                key={q.topic}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border p-3"
              >
                <div>
                  <p className="text-sm font-medium">{q.topic}</p>
                  <p className="text-xs text-text-muted">
                    {q.attempts} attempt{q.attempts !== 1 ? 's' : ''}
                  </p>
                </div>
                <div className="flex gap-4 text-sm">
                  <span>
                    Avg: <strong>{q.avg_score}%</strong>
                  </span>
                  <span>
                    Pass rate:{' '}
                    <strong className={q.pass_rate >= 60 ? 'text-teal' : 'text-error'}>{q.pass_rate}%</strong>
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {rejectTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <Card className="w-full max-w-md p-6">
            <h3 className="text-[18px] font-bold">Reject question?</h3>
            <p className="mt-2 text-[14px] text-text-secondary">
              This will permanently delete the AI-generated question:
            </p>
            <p className="mt-2 text-[14px] font-medium">&ldquo;{rejectTarget.text}&rdquo;</p>
            <div className="mt-6 flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setRejectTarget(null)}>
                Cancel
              </Button>
              <Button
                variant="secondary"
                disabled={rejectMut.isPending}
                onClick={() => rejectMut.mutate(rejectTarget.id)}
              >
                Reject &amp; Delete
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

function QuestionRow({
  question,
  index,
  onApprove,
  onReject,
  busy,
}: {
  question: QuizQuestion;
  index: number;
  onApprove: () => void;
  onReject: () => void;
  busy: boolean;
}) {
  const pending = question.ai_generated && !question.approved;

  return (
    <div className={cn('rounded-lg border border-border p-4', pending && 'border-warning/50 bg-warning-container/10')}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[12px] font-bold text-text-muted">Q{index}</span>
            {pending && <Badge variant="warning">Pending Review</Badge>}
            {question.ai_generated && question.approved && (
              <Badge variant="muted">AI generated</Badge>
            )}
          </div>
          <p className="mt-2 text-[14px] font-medium">{question.text}</p>
          <ul className="mt-2 space-y-1">
            {question.options.map((opt) => (
              <li
                key={opt.id}
                className={cn(
                  'text-[13px] text-text-secondary',
                  opt.is_correct && 'font-semibold text-teal',
                )}
              >
                {opt.is_correct ? '✓ ' : '○ '}
                {opt.text}
              </li>
            ))}
          </ul>
        </div>
        {pending && (
          <div className="flex shrink-0 gap-2">
            <Button className="px-3 py-1.5 text-[13px]" disabled={busy} onClick={onApprove}>
              <Check className="mr-1 h-3.5 w-3.5" /> Approve
            </Button>
            <Button className="px-3 py-1.5 text-[13px]" variant="ghost" disabled={busy} onClick={onReject}>
              <X className="mr-1 h-3.5 w-3.5" /> Reject
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

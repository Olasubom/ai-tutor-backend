import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Clock, RefreshCw } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/hooks/useAuth';
import { completeTask, createTask, getLearnerTasks } from '@/api/tasks';
import { getReviewDue } from '@/api/quiz';
import { useToastStore } from '@/components/ui/Toast';
import { ClipboardList } from 'lucide-react';

export default function Tasks() {
  const { learnerId } = useAuth();
  const qc = useQueryClient();
  const toast = useToastStore((s) => s.add);
  const [newText, setNewText] = useState('');

  const tasks = useQuery({ queryKey: ['tasks', learnerId], queryFn: () => getLearnerTasks(learnerId), enabled: !!learnerId });
  const reviews = useQuery({ queryKey: ['review-due', learnerId], queryFn: () => getReviewDue(learnerId), enabled: !!learnerId });

  const complete = useMutation({
    mutationFn: (taskId: string) => completeTask(learnerId, taskId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tasks', learnerId] });
      toast('Task completed', 'success');
    },
  });

  const add = useMutation({
    mutationFn: () =>
      createTask(learnerId, {
        text: newText,
        due_date: new Date(Date.now() + 86400000 * 3).toISOString().split('T')[0],
        priority: 'medium',
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tasks', learnerId] });
      setNewText('');
      toast('Task added', 'success');
    },
  });

  if (tasks.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-48" />
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    );
  }

  const pending = (tasks.data ?? []).filter((t) => t.status !== 'completed');
  const reviewList = reviews.data ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-[28px] font-extrabold">Tasks</h1>
        <p className="text-text-secondary">Your AI-generated study plan and review schedule.</p>
      </div>

      {reviewList.length > 0 && (
        <section className="space-y-3">
          <div className="flex items-center gap-2 font-bold">
            <RefreshCw className="h-4 w-4 text-primary" /> Review Due
          </div>
          <p className="text-[14px] text-text-secondary">
            The AI recommends reviewing these topics based on your learning history.
          </p>
          {reviewList.map((r) => (
            <Card key={r.topic} className="flex flex-wrap items-center justify-between gap-3 bg-card-hover/50 p-4">
              <div className="flex items-center gap-3">
                <Clock className="h-4 w-4 text-primary" />
                <div>
                  <div className="font-semibold">{r.topic}</div>
                  <div className="text-[13px] text-text-muted">
                    {r.days_overdue > 0 ? `${r.days_overdue} days overdue` : 'Due today'}
                  </div>
                </div>
              </div>
              <Badge variant="teal">{Math.round(r.current_mastery * 100)}% mastery</Badge>
              <Link to={`/student/quiz/${encodeURIComponent(r.topic)}`}>
                <Button className="px-3 py-1.5 text-[13px]">Start Review</Button>
              </Link>
            </Card>
          ))}
        </section>
      )}

      <section className="space-y-3">
        <h2 className="font-bold">Due Today</h2>
        {pending.length === 0 ? (
          <EmptyState
            icon={ClipboardList}
            title="No tasks yet"
            description="The AI will generate your study plan after your first quiz."
          />
        ) : (
          pending.map((t) => {
            const id = t.task_id ?? t.id ?? '';
            return (
              <Card key={id} className="flex items-center gap-4 p-4">
                <input
                  type="checkbox"
                  className="h-5 w-5 rounded border-border"
                  onChange={() => complete.mutate(id)}
                />
                <div className="flex-1">
                  <div className="font-medium">{t.title ?? t.text}</div>
                  {t.course && <div className="text-[13px] text-text-muted">{t.course}</div>}
                </div>
                {t.priority && <Badge variant={t.priority === 'urgent' ? 'error' : 'muted'}>{t.priority}</Badge>}
              </Card>
            );
          })
        )}
      </section>

      <div className="flex gap-2">
        <input
          className="flex-1 rounded-lg border border-border bg-input px-4 py-2 text-[14px]"
          placeholder="Add a task..."
          value={newText}
          onChange={(e) => setNewText(e.target.value)}
        />
        <Button disabled={!newText.trim()} onClick={() => add.mutate()}>
          Add task
        </Button>
      </div>
    </div>
  );
}

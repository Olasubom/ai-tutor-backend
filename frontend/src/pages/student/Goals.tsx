import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Target } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { Skeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/hooks/useAuth';
import { createGoal, deleteGoal, getGoals } from '@/api/goals';
import { useToastStore } from '@/components/ui/Toast';

export default function Goals() {
  const { learnerId } = useAuth();
  const qc = useQueryClient();
  const toast = useToastStore((s) => s.add);
  const [open, setOpen] = useState(false);
  const [topic, setTopic] = useState('');
  const [target, setTarget] = useState(80);
  const [date, setDate] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['goals', learnerId],
    queryFn: () => getGoals(learnerId),
    enabled: !!learnerId,
  });

  const add = useMutation({
    mutationFn: () =>
      createGoal(learnerId, {
        topic,
        target_mastery: target / 100,
        target_date: date || new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0],
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['goals', learnerId] });
      setOpen(false);
      toast('Goal set. Study tasks updated.', 'success');
    },
  });

  const remove = useMutation({
    mutationFn: (goalId: string) => deleteGoal(learnerId, goalId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['goals', learnerId] }),
  });

  if (isLoading) return <Skeleton className="h-64 w-full" />;

  const goals = data ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-[28px] font-extrabold">Learning Goals</h1>
        <Button onClick={() => setOpen(true)}>Set New Goal</Button>
      </div>

      {goals.length === 0 ? (
        <EmptyState
          icon={Target}
          title="No goals set yet"
          description="Set a mastery target for a subject to get a personalized study plan."
          action={{ label: 'Set Your First Goal', onClick: () => setOpen(true) }}
        />
      ) : (
        <div className="space-y-4">
          {goals.map((g) => (
            <Card key={g.goal_id} className="p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="text-[18px] font-bold">{g.topic}</div>
                  <div className="text-[14px] text-text-secondary">
                    Reach {Math.round(g.target_mastery * 100)}% mastery
                  </div>
                </div>
                <Badge variant={g.on_track ? 'teal' : 'warning'}>{g.on_track ? 'On Track' : 'Behind Schedule'}</Badge>
                <Badge variant="muted">{g.days_remaining} days left</Badge>
              </div>
              <div className="mt-4">
                <div className="mb-1 flex justify-between text-[13px]">
                  <span>{Math.round(g.current_mastery * 100)}%</span>
                  <span>{Math.round(g.target_mastery * 100)}%</span>
                </div>
                <ProgressBar value={g.progress_percentage} autoColor={false} />
              </div>
              <div className="mt-4 flex gap-3">
                <Link to={`/student/quiz/${encodeURIComponent(g.topic)}`} className="text-[14px] font-semibold text-primary">
                  Take Quiz
                </Link>
                <button
                  type="button"
                  className="text-[14px] text-text-muted hover:text-error"
                  onClick={() => remove.mutate(g.goal_id)}
                >
                  Delete Goal
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal open={open} onClose={() => setOpen(false)} title="Set New Goal">
        <div className="space-y-4">
          <Input label="Topic" value={topic} onChange={(e) => setTopic(e.target.value)} />
          <div>
            <label className="text-[13px] font-medium">Target mastery: {target}%</label>
            <input
              type="range"
              min={50}
              max={100}
              value={target}
              onChange={(e) => setTarget(Number(e.target.value))}
              className="mt-2 w-full"
            />
          </div>
          <Input label="Target date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          <Button disabled={!topic.trim() || add.isPending} onClick={() => add.mutate()}>
            Set Goal →
          </Button>
        </div>
      </Modal>
    </div>
  );
}

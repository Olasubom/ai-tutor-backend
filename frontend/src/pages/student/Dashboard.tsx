import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { BarChart2, CheckSquare, Flame } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { StatCard } from '@/components/ui/StatCard';
import { StatCardSkeleton, Skeleton } from '@/components/ui/Skeleton';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/hooks/useAuth';
import { useLearnerProfile, useKnowledge, useTasks } from '@/hooks/useStudent';
import { getHeatmap } from '@/api/engagement';
import { completeTask } from '@/api/tasks';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useToastStore } from '@/components/ui/Toast';

export default function Dashboard() {
  const navigate = useNavigate();
  const { user, learnerId } = useAuth();
  const qc = useQueryClient();
  const toast = useToastStore((s) => s.add);
  const profile = useLearnerProfile(learnerId);
  const knowledge = useKnowledge(learnerId);
  const tasks = useTasks(learnerId);
  const heatmap = useQuery({
    queryKey: ['heatmap', learnerId, '7d'],
    queryFn: () => getHeatmap(learnerId, '7d'),
    enabled: !!learnerId,
  });

  const complete = useMutation({
    mutationFn: (taskId: string) => completeTask(learnerId, taskId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tasks', learnerId] });
      toast('Task completed', 'success');
    },
  });

  const loading = profile.isLoading || knowledge.isLoading || tasks.isLoading;

  if (loading) {
    return (
      <div className="space-y-6">
        <StatCardSkeleton />
        <div className="grid gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <StatCardSkeleton key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (profile.isError) {
    return (
      <Card className="p-8 text-center">
        <p className="text-text-secondary">Failed to load dashboard.</p>
        <Button className="mt-4" onClick={() => profile.refetch()}>
          Retry
        </Button>
      </Card>
    );
  }

  const p = profile.data?.profile;
  const subjects = [...(knowledge.data?.subjects ?? [])].sort((a, b) => a.mastery - b.mastery);
  const topThree = [...subjects].sort((a, b) => b.mastery - a.mastery).slice(0, 3);
  const mastery = p?.overall_mastery_percentage ?? 0;
  const pendingTasks = (tasks.data ?? []).filter((t) => t.status !== 'completed' && !(t as { done?: boolean }).done);
  const weekData = heatmap.data ?? [];
  const hasActivity = weekData.some((d) => d.count > 0);

  const subtitle =
    mastery > 0
      ? `You are at ${mastery}% overall mastery. Keep going.`
      : 'Complete your first session to get started.';

  return (
    <div className="page-grid -m-6 space-y-6 p-6">
      <Card className="flex flex-col justify-between gap-6 lg:flex-row">
        <div>
          <h1 className="text-[28px] font-extrabold tracking-tight">Welcome back, {user?.name?.split(' ')[0]}.</h1>
          <p className="mt-2 max-w-xl text-text-secondary">{subtitle}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {profile.isLoading ? (
              <Skeleton className="h-6 w-24" />
            ) : (
              <>
                <Badge variant="muted">
                  <Flame className="mr-1 inline h-3 w-3" /> {p?.current_streak ?? 0} Day Streak
                </Badge>
                <Badge variant="teal">{mastery}% Avg Mastery</Badge>
                <Badge variant="muted">{pendingTasks.length} Tasks Pending</Badge>
              </>
            )}
          </div>
        </div>
        {topThree.length > 0 && (
          <div className="w-full max-w-xs rounded-xl border border-border bg-card p-4 lg:w-72">
            <div className="text-[12px] uppercase text-text-muted">Top Subjects</div>
            <div className="mt-4 space-y-3">
              {topThree.map((s) => (
                <div key={s.topic}>
                  <div className="mb-1 flex justify-between text-[12px]">
                    <span className="truncate">{s.topic}</span>
                    <span>{s.mastery}%</span>
                  </div>
                  <ProgressBar value={s.mastery} />
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Learning Hours" value={String(p?.total_study_hours ?? 0)} />
        <StatCard label="Modules Completed" value={String(p?.modules_completed ?? 0)} />
        <StatCard label="Current Streak" value={String(p?.current_streak ?? 0)} />
        <StatCard label="Global Mastery" value={mastery > 0 ? `${mastery}%` : '--'} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <h3 className="font-bold">Topic Mastery</h3>
          <div className="mt-4 space-y-4">
            {subjects.length === 0 ? (
              <EmptyState
                icon={BarChart2}
                title="No mastery data yet"
                description="Complete your first quiz to see your topic mastery levels."
                action={{ label: 'Go to Curriculum', onClick: () => navigate('/student/curriculum') }}
              />
            ) : (
              subjects.slice(0, 6).map((s) => (
                <div key={s.topic}>
                  <div className="mb-1 flex justify-between text-[13px]">
                    <span>{s.topic}</span>
                    <span>{s.mastery}%</span>
                  </div>
                  <ProgressBar value={s.mastery} />
                </div>
              ))
            )}
          </div>
        </Card>

        <Card className="p-6">
          <h3 className="font-bold">Weekly Activity</h3>
          {heatmap.isLoading ? (
            <Skeleton className="mt-4 h-24 w-full" />
          ) : hasActivity ? (
            <div className="mt-4 flex h-24 items-end gap-2">
              {weekData.map((d) => (
                <div key={d.date} className="flex flex-1 flex-col items-center gap-1">
                  <div className="w-full rounded bg-primary/20" style={{ height: `${Math.max(4, d.count * 10)}px`, opacity: d.count > 0 ? 1 : 0.3 }} />
                  <span className="text-[10px] text-text-muted">{d.date.slice(8)}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-4 text-[14px] text-text-secondary">
              Study activity will appear here after your first session.
            </p>
          )}
        </Card>
      </div>

      <Card className="p-6">
        <h3 className="font-bold">Up Next</h3>
        <div className="mt-4 space-y-3">
          {pendingTasks.length === 0 ? (
            <EmptyState
              icon={CheckSquare}
              title="No tasks yet"
              description="Chat with the AI Tutor to generate your first study plan."
              action={{ label: 'Start a Session', onClick: () => navigate('/student/ai-assistant') }}
            />
          ) : (
            pendingTasks.slice(0, 4).map((t) => {
              const id = t.task_id ?? t.id ?? '';
              return (
                <label key={id} className="flex items-center gap-3 text-[14px]">
                  <input type="checkbox" onChange={() => complete.mutate(id)} />
                  <span>{t.title ?? t.text}</span>
                </label>
              );
            })
          )}
        </div>
      </Card>
    </div>
  );
}

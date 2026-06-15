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
import { getMasteryBarColor, getMasteryLabel, getGlobalMasteryDescriptor } from '@/lib/masteryLabels';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useToastStore } from '@/components/ui/Toast';
import { cn } from '@/lib/utils';

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
  const modulesCompleted = p?.modules_completed ?? 0;

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
        <Card className="p-6">
          <div className="mb-4 flex items-center gap-1">
            <span className="text-xs font-semibold uppercase tracking-wide text-gray-400">Knowledge Mastery</span>
            <div className="group relative">
              <svg
                className="h-3.5 w-3.5 cursor-help text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <div
                className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-64 -translate-x-1/2 rounded-lg bg-gray-900 p-3 text-xs text-white opacity-0 shadow-xl transition-opacity group-hover:opacity-100"
              >
                <p className="mb-1 font-semibold">What is Knowledge Mastery?</p>
                <p className="leading-relaxed text-gray-300">
                  This is your AI-estimated probability of knowing your enrolled topics. It is seeded from your
                  onboarding self-assessment and updates automatically after every quiz. It is not a course completion
                  score.
                </p>
                <div className="absolute left-1/2 top-full -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
              </div>
            </div>
          </div>
          <div className="stat-number text-text-primary">{mastery > 0 ? `${mastery}%` : '--'}</div>
          {mastery > 0 && (
            <p className="mt-1 text-xs text-gray-400">{getGlobalMasteryDescriptor(mastery)}</p>
          )}
          {modulesCompleted === 0 && (
            <p className="mt-1 text-xs text-blue-500">Seeded from your onboarding assessment. Take a quiz to update it.</p>
          )}
        </Card>
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
              subjects.slice(0, 6).map((s) => {
                const status = getMasteryLabel(s.mastery);
                return (
                  <div key={s.topic}>
                    <div className="mb-1 flex items-center justify-between text-[13px]">
                      <span>{s.topic}</span>
                      <div className="flex items-center gap-2">
                        <span className={cn('text-xs font-semibold', status.color)}>{status.label}</span>
                        <span className="font-bold text-gray-800">{s.mastery}%</span>
                      </div>
                    </div>
                    <div className="h-[5px] w-full overflow-hidden rounded-full bg-border">
                      <div
                        className={cn('h-full rounded-full transition-all', getMasteryBarColor(s.mastery))}
                        style={{ width: `${s.mastery}%` }}
                      />
                    </div>
                  </div>
                );
              })
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

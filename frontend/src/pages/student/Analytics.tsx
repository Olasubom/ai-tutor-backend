import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/ui/Card';
import { StatCard } from '@/components/ui/StatCard';
import { Skeleton } from '@/components/ui/Skeleton';
import { BarChart } from '@/components/ui/BarChart';
import { LineChart } from '@/components/ui/LineChart';
import { useAuth } from '@/hooks/useAuth';
import { useLearnerProfile, useKnowledge } from '@/hooks/useStudent';
import { getHeatmap, getEngagementMetrics } from '@/api/engagement';
import { getMasteryTrajectory } from '@/api/knowledge';
import { cn } from '@/lib/utils';

type Period = '7d' | '30d' | 'all';

export default function Analytics() {
  const { learnerId } = useAuth();
  const [period, setPeriod] = useState<Period>('7d');
  const profile = useLearnerProfile(learnerId);
  const knowledge = useKnowledge(learnerId);

  const heatmap = useQuery({
    queryKey: ['heatmap', learnerId, period],
    queryFn: () => getHeatmap(learnerId, period === 'all' ? 'all' : period),
    enabled: !!learnerId,
  });

  const metrics = useQuery({
    queryKey: ['engagement-metrics', learnerId, period],
    queryFn: () => getEngagementMetrics(learnerId, period === 'all' ? '30d' : period),
    enabled: !!learnerId,
  });

  const trajectory = useQuery({
    queryKey: ['trajectory', learnerId],
    queryFn: () => getMasteryTrajectory(learnerId),
    enabled: !!learnerId,
  });

  const loading = profile.isLoading || knowledge.isLoading || heatmap.isLoading;

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      </div>
    );
  }

  const p = profile.data?.profile;
  const barData = (heatmap.data ?? []).slice(-7).map((d) => ({
    name: d.date.slice(5),
    count: d.count,
  }));
  const lineData = (metrics.data ?? []).map((d) => ({
    name: d.date.slice(5),
    study: d.study_time,
    questions: d.questions_answered,
  }));
  const trajData = (trajectory.data ?? []).map((d) => ({
    name: d.date.slice(5),
    v: Math.round(d.overall_mastery * 100),
  }));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-[28px] font-extrabold">Mastery Analytics</h1>
        <div className="flex gap-2">
          {(['7d', '30d', 'all'] as Period[]).map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setPeriod(p)}
              className={cn(
                'rounded-full border px-4 py-1.5 text-[13px] font-semibold uppercase',
                period === p ? 'border-primary bg-primary text-white' : 'border-border',
              )}
            >
              {p === 'all' ? 'All Time' : p}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Study Hours" value={String(p?.total_study_hours ?? 0)} />
        <StatCard label="Modules Mastered" value={String(p?.modules_completed ?? 0)} />
        <StatCard label="Streak" value={String(p?.current_streak ?? 0)} />
        <StatCard label="Global Mastery" value={`${p?.overall_mastery_percentage ?? 0}%`} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <h3 className="font-bold">Daily Activity</h3>
          <BarChart data={barData} dataKey="count" xKey="name" />
        </Card>
        <Card className="p-6">
          <h3 className="font-bold">Output vs Effort</h3>
          <LineChart data={lineData} dataKey="study" />
        </Card>
      </div>

      <Card className="p-6">
        <h3 className="mb-4 font-bold">30-Day Mastery Trajectory</h3>
        <LineChart data={trajData} dataKey="v" />
      </Card>

      <Card className="overflow-x-auto p-6">
        <h3 className="mb-4 font-bold">Subject Comparison</h3>
        <table className="w-full text-left text-[14px]">
          <thead>
            <tr className="text-text-muted">
              <th className="pb-2">Subject</th>
              <th className="pb-2">Mastery</th>
              <th className="pb-2">Attempts</th>
            </tr>
          </thead>
          <tbody>
            {(knowledge.data?.subjects ?? []).map((s) => (
              <tr key={s.topic} className="border-t border-border">
                <td className="py-3 font-medium">{s.topic}</td>
                <td className="py-3">{s.mastery}%</td>
                <td className="py-3">{s.attempts}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckCircle2, Lock, Play } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { Tabs } from '@/components/ui/Tabs';
import { Skeleton } from '@/components/ui/Skeleton';
import { getRecommendations } from '@/api/recommendations';
import { useKnowledge } from '@/hooks/useStudent';
import { useAuth } from '@/hooks/useAuth';
import { useToastStore } from '@/components/ui/Toast';
import { cn } from '@/lib/utils';

export default function Curriculum() {
  const { learnerId } = useAuth();
  const navigate = useNavigate();
  const toast = useToastStore((s) => s.add);
  const qc = useQueryClient();
  const [tab, setTab] = useState('all');
  const knowledge = useKnowledge(learnerId);
  const recs = useQuery({
    queryKey: ['curriculum', learnerId],
    queryFn: () => getRecommendations({ learner_id: learnerId, limit: 6 }),
    enabled: !!learnerId,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });

  const refresh = useMutation({
    mutationFn: () => getRecommendations({ learner_id: learnerId, message: 'refresh curriculum path', limit: 6 }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['curriculum', learnerId] });
      qc.invalidateQueries({ queryKey: ['knowledge', learnerId] });
      toast('Curriculum updated based on your latest mastery data.', 'success');
    },
    onError: () => toast('Failed to update curriculum', 'error'),
  });

  const path = recs.data?.adaptive_path ?? [];
  const masteryMap = Object.fromEntries(
    (knowledge.data?.subjects ?? []).map((s) => [s.topic, s.mastery]),
  );
  const subject = knowledge.data?.subjects[0]?.topic ?? 'Your Curriculum';

  const filteredPath = path.filter((step) => {
    if (tab === 'all') return true;
    const type = String(step.type ?? step.module_type ?? '').toLowerCase();
    if (tab === 'core') return type === 'core' || type === 'compulsory';
    if (tab === 'electives') return type === 'elective';
    if (tab === 'assessments') return type === 'assessment' || type === 'quiz';
    return false;
  });

  if (knowledge.isLoading || recs.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-32" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <Badge variant="muted">CURRICULUM</Badge>
          <h1 className="mt-2 text-[28px] font-extrabold">{subject}</h1>
          <p className="text-text-secondary">Adaptive path generated from your mastery model.</p>
        </div>
        <Button variant="secondary" disabled={refresh.isPending} onClick={() => refresh.mutate()}>
          {refresh.isPending ? 'Updating...' : 'Request AI Update'}
        </Button>
      </div>

      <Tabs
        active={tab}
        onChange={setTab}
        tabs={[
          { id: 'all', label: 'All Steps' },
          { id: 'core', label: 'Core Modules' },
          { id: 'electives', label: 'Electives' },
          { id: 'assessments', label: 'Assessments' },
        ]}
      />

      <div className="space-y-4">
        {filteredPath.length === 0 ? (
          <Card className="p-8 text-center text-text-secondary">
            Take a quiz or complete onboarding to generate your adaptive path.
          </Card>
        ) : (
          filteredPath.map((step, i) => {
            const title = String(step.title ?? step.topic ?? `Step ${i + 1}`);
            const pct = masteryMap[title] ?? masteryMap[String(step.topic)] ?? 0;
            const prevPct = i > 0 ? (masteryMap[String(filteredPath[i - 1]?.title ?? '')] ?? 0) : 100;
            const status = pct >= 85 ? 'COMPLETED' : prevPct < 40 && i > 0 ? 'LOCKED' : pct >= 40 ? 'IN PROGRESS' : i === 0 ? 'IN PROGRESS' : 'LOCKED';
            return (
              <div key={String(step.item_id ?? i)} className="flex gap-4">
                <div className="flex flex-col items-center">
                  {status === 'COMPLETED' && <CheckCircle2 className="h-6 w-6 text-teal" />}
                  {status === 'IN PROGRESS' && <Play className="h-6 w-6 text-primary" />}
                  {status === 'LOCKED' && <Lock className="h-6 w-6 text-text-muted" />}
                  {i < filteredPath.length - 1 && <div className="mt-2 w-px flex-1 bg-border" />}
                </div>
                <Card className={cn('relative flex-1 p-6', status === 'LOCKED' && 'opacity-60')}>
                  {status === 'LOCKED' && <Lock className="absolute right-4 top-4 h-4 w-4 text-text-muted" />}
                  <div className="flex items-start justify-between">
                    <Badge variant={status === 'COMPLETED' ? 'teal' : status === 'IN PROGRESS' ? 'primary' : 'muted'}>
                      {status}
                    </Badge>
                    <span className="label-caps text-text-muted">MODULE {i + 1}</span>
                  </div>
                  <h3 className="mt-2 text-[18px] font-bold">{title}</h3>
                  <p className="mt-1 text-[14px] text-text-secondary">{String(step.objective ?? 'Study and practice')}</p>

                  {status === 'COMPLETED' && (
                    <p className="mt-3 flex items-center gap-2 text-[14px] text-teal">
                      <CheckCircle2 className="h-4 w-4" /> Mastery: {pct}%
                    </p>
                  )}

                  {status === 'IN PROGRESS' && (
                    <div className="mt-4">
                      <div className="mb-1 flex justify-between text-[13px]">
                        <span>Progress</span>
                        <span>{pct}%</span>
                      </div>
                      <ProgressBar value={pct} autoColor={false} />
                      <Button
                        className="mt-4"
                        onClick={() =>
                          navigate(`/student/ai-assistant?topic=${encodeURIComponent(title)}`)
                        }
                      >
                        Continue →
                      </Button>
                    </div>
                  )}

                  {status === 'LOCKED' && (
                    <p className="mt-4 text-[13px] text-text-muted">Complete the previous module to unlock.</p>
                  )}

                  {status !== 'LOCKED' && (
                    <div className="mt-4 flex gap-2">
                      <Link to={`/student/quiz/${encodeURIComponent(title)}`}>
                        <Button variant="secondary">Take Quiz</Button>
                      </Link>
                    </div>
                  )}
                </Card>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { BookOpen, Clock, ExternalLink } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Skeleton, ResourceCardSkeleton } from '@/components/ui/Skeleton';
import { getRecommendations } from '@/api/recommendations';
import { useAuth } from '@/hooks/useAuth';
import { useKnowledge } from '@/hooks/useStudent';
import { EmptyState } from '@/components/ui/EmptyState';
import { formatResourceType, matchesResourceFilter, resourceTypePillClass } from '@/lib/resourceTypes';
import { cn } from '@/lib/utils';

const filters = ['All Resources', 'Video Lectures', 'E-Books', 'Interactive Quizzes'];

export default function Library() {
  const navigate = useNavigate();
  const { learnerId } = useAuth();
  const knowledge = useKnowledge(learnerId);
  const [active, setActive] = useState('All Resources');
  const { data, isLoading } = useQuery({
    queryKey: ['library', learnerId],
    queryFn: () => getRecommendations({ learner_id: learnerId, message: 'resource library', limit: 12 }),
    enabled: !!learnerId,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });

  const items = (data?.recommendations ?? []).filter((item) =>
    matchesResourceFilter(item.modality, item.source_type, active),
  );

  const overallMastery = useMemo(() => {
    const subjects = knowledge.data?.subjects ?? [];
    if (subjects.length === 0) return null;
    const avg = subjects.reduce((sum, subject) => sum + subject.mastery, 0) / subjects.length;
    return Math.round(avg);
  }, [knowledge.data?.subjects]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-extrabold tracking-tight">Recommendations</h1>
          <p className="text-text-secondary">
            Personalized resources ranked by mastery match and learning gaps.
          </p>
        </div>
        <Card className="p-4">
          <div className="label-caps text-text-muted">Global Mastery Match</div>
          {knowledge.isLoading ? (
            <Skeleton className="mt-2 h-8 w-16" />
          ) : overallMastery === null ? (
            <div className="mt-2 text-[18px] font-semibold text-text-muted">Not yet calculated</div>
          ) : (
            <div className="stat-number text-teal">{overallMastery}%</div>
          )}
        </Card>
      </div>

      <div className="flex flex-wrap gap-2">
        {filters.map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setActive(f)}
            className={cn(
              'rounded-full border px-4 py-1.5 text-[13px] font-semibold',
              active === f ? 'border-primary bg-primary text-white' : 'border-border bg-card text-text-secondary',
            )}
          >
            {f}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <ResourceCardSkeleton key={i} />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title="No recommendations yet"
          description="Complete your profile and take a quiz so the AI can recommend resources for you."
          action={{ label: 'Take a Quiz', onClick: () => navigate('/student/curriculum') }}
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {items.map((item, i) => {
            const typeLabel = formatResourceType(item.modality ?? item.source_type ?? 'resource');
            const matchPct = item.score != null ? Math.round(item.score * 100) : null;
            return (
              <Card key={item.item_id} className={cn('relative p-6', i === 0 && 'md:col-span-2')}>
                {matchPct != null && (
                  <span className="absolute right-4 top-4 rounded-full px-2 py-0.5 text-[11px] font-bold text-primary">
                    {matchPct}% MATCH
                  </span>
                )}
                <span className={cn('label-caps rounded-full px-2 py-0.5 text-[11px] font-bold uppercase', resourceTypePillClass(item.modality ?? item.source_type ?? ''))}>
                  {typeLabel}
                </span>
                <h3 className="mt-2 text-[18px] font-bold">{item.title}</h3>
                <p className="mt-2 line-clamp-2 text-[14px] text-text-secondary">{item.description}</p>
                {(item.reason || item.reasons?.length) && (
                  <p className="mt-2 text-[12px] italic text-text-muted">
                    {item.reason ?? item.reasons?.join(' · ')}
                  </p>
                )}
                <div className="mt-4 flex items-center justify-between text-[12px] text-text-muted">
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" /> {item.duration_minutes ?? 15} min
                  </span>
                  {item.source_url && (
                    <a href={item.source_url} target="_blank" rel="noreferrer" className="text-primary">
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { BookOpen, Clock, ExternalLink } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Skeleton, ResourceCardSkeleton } from '@/components/ui/Skeleton';
import { getRecommendations } from '@/api/recommendations';
import { useAuth } from '@/hooks/useAuth';
import { useLearnerProfile } from '@/hooks/useStudent';
import { EmptyState } from '@/components/ui/EmptyState';
import { formatResourceType, matchesResourceFilter, resourceTypePillClass } from '@/lib/resourceTypes';
import { cn } from '@/lib/utils';
import type { Recommendation } from '@/types';

const filters = ['All Resources', 'Video Lectures', 'E-Books', 'Interactive Quizzes'];

function getMasteryPercent(profileData: ReturnType<typeof useLearnerProfile>['data']): number | null {
  const profile = profileData?.profile;
  if (!profile) return null;

  if (typeof profile.overall_mastery_percentage === 'number' && profile.overall_mastery_percentage > 0) {
    return Math.round(profile.overall_mastery_percentage);
  }

  const topicMastery = profile.topic_mastery ?? {};
  const entries = Object.values(topicMastery);
  if (entries.length > 0) {
    const avg = entries.reduce((sum, topic) => sum + (topic.p_l ?? 0), 0) / entries.length;
    const pct = Math.round(avg * 100);
    return pct > 0 ? pct : null;
  }

  return null;
}

function getMatchPercent(item: Recommendation): number | null {
  if (typeof item.score !== 'number' || !Number.isFinite(item.score)) return null;
  const pct = item.score <= 1 ? item.score * 100 : item.score;
  if (pct <= 0) return null;
  return Math.round(pct);
}

export default function Library() {
  const navigate = useNavigate();
  const { learnerId } = useAuth();
  const profile = useLearnerProfile(learnerId);
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

  const masteryPercent = useMemo(() => getMasteryPercent(profile.data), [profile.data]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-extrabold tracking-tight">Recommendations</h1>
          <p className="text-text-secondary">
            Personalized resources ranked by mastery match and learning gaps.
          </p>
        </div>
        <Card className="p-4 text-right">
          <div className="label-caps text-text-muted">Global Mastery</div>
          {profile.isLoading ? (
            <Skeleton className="ml-auto mt-2 h-8 w-24" />
          ) : masteryPercent === null ? (
            <div className="mt-2 text-[14px] text-text-muted">Complete a quiz to see your mastery</div>
          ) : (
            <div
              className={cn(
                'mt-2 text-[32px] font-extrabold tracking-tight',
                masteryPercent >= 70 ? 'text-teal' : masteryPercent >= 40 ? 'text-warning' : 'text-primary',
              )}
            >
              {masteryPercent}%
            </div>
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
            const matchPct = getMatchPercent(item);
            return (
              <Card key={item.item_id} className={cn('relative p-6', i === 0 && 'md:col-span-2')}>
                {matchPct != null && matchPct >= 40 && (
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

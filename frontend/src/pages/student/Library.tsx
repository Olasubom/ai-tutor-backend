import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { BookOpen } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Skeleton, ResourceCardSkeleton } from '@/components/ui/Skeleton';
import { RecommendationCard } from '@/components/recommendations/RecommendationCard';
import { getRecommendations } from '@/api/recommendations';
import { useAuth } from '@/hooks/useAuth';
import { useLearnerProfile } from '@/hooks/useStudent';
import { EmptyState } from '@/components/ui/EmptyState';
import { matchesResourceFilter } from '@/lib/resourceTypes';
import { getGlobalMasteryDescriptor } from '@/lib/masteryLabels';
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

function dedupeRecommendations(items: Recommendation[]): Recommendation[] {
  const seen = new Map<string, Recommendation>();
  for (const item of items) {
    const id = item.item_id;
    if (!id) continue;
    const existing = seen.get(id);
    if (!existing) {
      seen.set(id, item);
      continue;
    }
    const score = item.score ?? 0;
    const existingScore = existing.score ?? 0;
    if (score > existingScore) seen.set(id, item);
  }
  return Array.from(seen.values());
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

  const items = useMemo(() => {
    const deduped = dedupeRecommendations(data?.recommendations ?? []);
    return deduped.filter((item) => matchesResourceFilter(item.modality, item.source_type, active));
  }, [data?.recommendations, active]);

  const masteryPercent = useMemo(() => getMasteryPercent(profile.data), [profile.data]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-extrabold tracking-tight">Recommendations</h1>
          <p className="text-text-secondary">Personalized resources ranked by mastery match and learning gaps.</p>
        </div>
        <Card className="p-4 text-right">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Your Knowledge Level</p>
          {profile.isLoading ? (
            <Skeleton className="ml-auto mt-2 h-8 w-24" />
          ) : masteryPercent === null ? (
            <div className="mt-2 text-[14px] text-text-muted">Complete a quiz to see your mastery</div>
          ) : (
            <>
              <p
                className={cn(
                  'mt-2 text-3xl font-extrabold tracking-tight',
                  masteryPercent >= 70 ? 'text-teal' : masteryPercent >= 40 ? 'text-amber-500' : 'text-primary',
                )}
              >
                {masteryPercent}%
              </p>
              <p className="mt-1 text-xs text-gray-400">{getGlobalMasteryDescriptor(masteryPercent)}</p>
              <p className="mt-1 text-xs text-gray-400">
                Resources below are matched to fill your current knowledge gaps.
              </p>
            </>
          )}
        </Card>
      </div>

      <div className="rounded-xl border border-blue-100 bg-blue-50 p-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-semibold text-blue-900">Test your knowledge</h3>
            <p className="mt-0.5 text-xs text-blue-600">
              Take a quiz on any topic to update your mastery score and get better recommendations.
            </p>
          </div>
          <button
            type="button"
            onClick={() => navigate('/student/curriculum')}
            className="flex-shrink-0 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-700"
          >
            Go to Curriculum →
          </button>
        </div>
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
      ) : data?.status === 'no_content_for_courses' ? (
        <div className="py-16 text-center">
          <BookOpen className="mx-auto mb-3 h-12 w-12 text-gray-300" />
          <h3 className="font-semibold text-gray-700">No resources yet for your courses</h3>
          <p className="mx-auto mt-1 max-w-md text-sm text-gray-400">
            Your administrator needs to generate learning content for your department. Check back soon, or contact your
            department admin.
          </p>
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
          {items.map((item, i) => (
            <RecommendationCard
              key={item.item_id}
              item={item}
              matchPct={getMatchPercent(item)}
              className={cn('relative', i === 0 && 'md:col-span-2')}
            />
          ))}
        </div>
      )}
    </div>
  );
}

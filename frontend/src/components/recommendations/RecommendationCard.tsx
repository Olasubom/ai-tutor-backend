import { useNavigate } from 'react-router-dom';
import { Clock } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { formatResourceType, resourceTypePillClass } from '@/lib/resourceTypes';
import { coerceReasons } from '@/utils/formatAssistantMessage';
import { cn } from '@/lib/utils';
import type { Recommendation } from '@/types';

function getExternalUrl(item: Recommendation): string | null {
  return item.source_url || (item as { url?: string }).url || (item as { external_url?: string }).external_url || null;
}

function getCardAction(item: Recommendation, navigate: ReturnType<typeof useNavigate>) {
  const externalUrl = getExternalUrl(item);
  const sourceType = (item.source_type || item.modality || '').toLowerCase();

  if (sourceType === 'interactive' || sourceType === 'quiz') {
    return {
      primaryLabel: 'Start Practice',
      primaryIcon: '▶',
      primaryAction: () => {
        if (externalUrl) {
          window.open(externalUrl, '_blank', 'noopener,noreferrer');
        } else {
          const topic = item.title.replace(/[-–—]/g, ' ').replace(/\s+/g, ' ').trim();
          navigate(`/student/quiz/${encodeURIComponent(topic)}`);
        }
      },
    };
  }

  if (sourceType === 'youtube' || sourceType === 'video') {
    return {
      primaryLabel: 'Watch Video',
      primaryIcon: '▶',
      primaryAction: () => {
        if (externalUrl) window.open(externalUrl, '_blank', 'noopener,noreferrer');
      },
    };
  }

  if (sourceType === 'ebook' || sourceType === 'pdf' || sourceType === 'book') {
    return {
      primaryLabel: 'Read',
      primaryIcon: '📖',
      primaryAction: () => {
        if (externalUrl) window.open(externalUrl, '_blank', 'noopener,noreferrer');
      },
    };
  }

  if (sourceType === 'article' || sourceType === 'text') {
    return {
      primaryLabel: 'Read Article',
      primaryIcon: '→',
      primaryAction: () => {
        if (externalUrl) window.open(externalUrl, '_blank', 'noopener,noreferrer');
      },
    };
  }

  return {
    primaryLabel: 'Open Resource',
    primaryIcon: '→',
    primaryAction: () => {
      if (externalUrl) window.open(externalUrl, '_blank', 'noopener,noreferrer');
    },
  };
}

interface RecommendationCardProps {
  item: Recommendation;
  matchPct?: number | null;
  className?: string;
}

export function RecommendationCard({ item, matchPct, className }: RecommendationCardProps) {
  const navigate = useNavigate();
  const action = getCardAction(item, navigate);
  const externalUrl = getExternalUrl(item);
  const hasUrl = !!externalUrl;
  const sourceType = (item.source_type || item.modality || '').toLowerCase();
  const typeLabel = formatResourceType(item.modality ?? item.source_type ?? 'resource');
  const isLaunchable = sourceType === 'interactive' || sourceType === 'quiz';
  const reasons = coerceReasons(item);

  return (
    <Card
      className={cn(
        'cursor-pointer p-6 transition-all duration-200 hover:border-gray-300 hover:shadow-md',
        !hasUrl && !isLaunchable && 'opacity-75',
        className,
      )}
      onClick={action.primaryAction}
    >
      {matchPct != null && matchPct >= 40 && (
        <span className="absolute right-4 top-4 rounded-full px-2 py-0.5 text-[11px] font-bold text-primary">
          {matchPct}% MATCH
        </span>
      )}
      <span
        className={cn(
          'label-caps rounded-full px-2 py-0.5 text-[11px] font-bold uppercase',
          resourceTypePillClass(item.modality ?? item.source_type ?? ''),
        )}
      >
        {typeLabel}
      </span>
      <h3 className="mt-2 text-[18px] font-bold">{item.title}</h3>
      <p className="mt-2 line-clamp-2 text-[14px] text-text-secondary">{item.description}</p>
      {reasons.length > 0 && (
        <p className="mt-2 text-[12px] italic text-text-muted">{reasons.join(' · ')}</p>
      )}
      <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-3">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            action.primaryAction();
          }}
          className="flex items-center gap-2 text-sm font-semibold text-blue-600 transition-colors hover:text-blue-800"
        >
          <span>{action.primaryIcon}</span>
          <span>{action.primaryLabel}</span>
        </button>
        <div className="flex items-center gap-3 text-[12px] text-text-muted">
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" /> {item.duration_minutes ?? 15} min
          </span>
          {!hasUrl && !isLaunchable && <span className="text-xs text-gray-400">Link not available</span>}
          {hasUrl && (
            <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
              />
            </svg>
          )}
        </div>
      </div>
    </Card>
  );
}

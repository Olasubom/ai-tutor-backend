import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  Clock,
  RefreshCw,
  TrendingDown,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/hooks/useAuth';
import { getNotifications, markAllNotificationsRead, markNotificationRead } from '@/api/notifications';
import type { AppNotification } from '@/api/notifications';
import { cn, formatDate } from '@/lib/utils';

function groupLabel(dateStr: string): string {
  const d = new Date(dateStr);
  const now = new Date();
  const today = now.toDateString();
  const yesterday = new Date(now.getTime() - 86400000).toDateString();
  if (d.toDateString() === today) return 'Today';
  if (d.toDateString() === yesterday) return 'Yesterday';
  return 'Earlier this week';
}

function iconFor(type: AppNotification['type']) {
  switch (type) {
    case 'mastery_drop':
      return <TrendingDown className="h-4 w-4 text-error" />;
    case 'task_due':
      return <Clock className="h-4 w-4 text-warning" />;
    case 'new_resource':
      return <BookOpen className="h-4 w-4 text-primary" />;
    case 'review_due':
      return <RefreshCw className="h-4 w-4 text-purple-500" />;
    default:
      return <AlertTriangle className="h-4 w-4 text-error" />;
  }
}

export default function Notifications() {
  const { learnerId } = useAuth();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['notifications', learnerId],
    queryFn: () => getNotifications(learnerId),
    enabled: !!learnerId,
    refetchInterval: 60_000,
  });

  const markRead = useMutation({
    mutationFn: (id: string) => markNotificationRead(learnerId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications', learnerId] }),
  });

  const markAll = useMutation({
    mutationFn: () => markAllNotificationsRead(learnerId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications', learnerId] }),
  });

  const grouped = useMemo(() => {
    const map = new Map<string, AppNotification[]>();
    for (const n of data ?? []) {
      const label = groupLabel(n.created_at);
      if (!map.has(label)) map.set(label, []);
      map.get(label)!.push(n);
    }
    return map;
  }, [data]);

  if (isLoading) return <Skeleton className="h-64 w-full" />;

  const list = data ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-[28px] font-extrabold">Notifications</h1>
        {list.some((n) => !n.is_read) && (
          <Button variant="ghost" onClick={() => markAll.mutate()}>
            Mark all as read
          </Button>
        )}
      </div>

      {list.length === 0 ? (
        <EmptyState icon={CheckCircle2} title="You are all caught up." />
      ) : (
        Array.from(grouped.entries()).map(([label, items]) => (
          <section key={label} className="space-y-3">
            <h2 className="text-[13px] font-semibold uppercase text-text-muted">{label}</h2>
            {items.map((n) => (
              <Card
                key={n.notification_id}
                className={cn(
                  'flex cursor-pointer items-start gap-4 border p-4 transition hover:bg-card-hover',
                  !n.is_read && 'bg-primary/5 dark:bg-primary/10',
                )}
                onClick={() => {
                  if (!n.is_read) markRead.mutate(n.notification_id);
                  navigate(n.action_url.startsWith('/') ? n.action_url : `/${n.action_url}`);
                }}
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-card-hover">
                  {iconFor(n.type)}
                </div>
                <div className="flex-1">
                  <div className="font-bold">{n.title}</div>
                  <div className="text-[14px] text-text-secondary">{n.body}</div>
                  <div className="mt-1 text-[12px] text-text-muted">{formatDate(n.created_at)}</div>
                </div>
                {!n.is_read && <span className="mt-2 h-2 w-2 rounded-full bg-primary" />}
              </Card>
            ))}
          </section>
        ))
      )}
    </div>
  );
}

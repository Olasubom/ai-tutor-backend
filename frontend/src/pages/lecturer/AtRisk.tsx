import { useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Avatar } from '@/components/ui/Avatar';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { Skeleton } from '@/components/ui/Skeleton';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/hooks/useAuth';
import { dismissAtRiskAlert, getAtRiskStudents, sendResourceToStudent } from '@/api/atRisk';
import { useToastStore } from '@/components/ui/Toast';
import { formatDate } from '@/lib/utils';

type Filter = 'all' | 'high' | 'medium' | 'low';

export default function AtRisk() {
  const { user } = useAuth();
  const lecturerId = user?.user_id ?? '';
  const toast = useToastStore((s) => s.add);
  const qc = useQueryClient();
  const [filter, setFilter] = useState<Filter>('all');
  const [detailId, setDetailId] = useState<string | null>(null);
  const [sendId, setSendId] = useState<string | null>(null);
  const [resourceUrl, setResourceUrl] = useState('');
  const [note, setNote] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['at-risk', lecturerId],
    queryFn: () => getAtRiskStudents(lecturerId),
    enabled: !!lecturerId,
  });

  const dismiss = useMutation({
    mutationFn: (learnerId: string) => dismissAtRiskAlert(lecturerId, learnerId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['at-risk', lecturerId] });
      setDetailId(null);
      toast('Alert dismissed', 'success');
    },
  });

  const send = useMutation({
    mutationFn: () =>
      sendResourceToStudent({
        lecturer_id: lecturerId,
        learner_id: sendId!,
        resource_url: resourceUrl,
        note,
      }),
    onSuccess: () => {
      setSendId(null);
      setResourceUrl('');
      setNote('');
      toast('Resource sent to student', 'success');
    },
  });

  const filtered = useMemo(() => {
    const list = data ?? [];
    if (filter === 'all') return list;
    return list.filter((s) => s.severity === filter);
  }, [data, filter]);

  const selected = filtered.find((s) => s.learner_id === detailId);

  if (isLoading) {
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
      <div>
        <h1 className="text-[28px] font-extrabold">AI At-Risk Alerts</h1>
        <p className="text-text-secondary">
          Students flagged by the AI based on performance and engagement patterns.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {(['all', 'high', 'medium', 'low'] as Filter[]).map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={`rounded-full border px-4 py-1.5 text-[13px] font-semibold capitalize ${
              filter === f ? 'border-primary bg-primary text-white' : 'border-border bg-card'
            }`}
          >
            {f === 'all' ? 'All' : `${f} Severity`}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={CheckCircle2}
          title="No at-risk students detected this week."
          description="The AI will flag students when mastery drops or engagement falls off."
        />
      ) : (
        <div className="space-y-4">
          {filtered.map((s) => (
            <Card key={s.learner_id} className="flex flex-wrap items-center justify-between gap-4 p-6">
              <div className="flex items-center gap-4">
                <Avatar name={s.name} />
                <div>
                  <div className="font-bold">{s.name}</div>
                  <div className="text-[13px] text-text-muted">
                    {s.email || s.department} · Level {s.level}
                  </div>
                  {s.mastery != null && (
                    <div className="mt-2 w-48">
                      <div className="mb-1 flex justify-between text-[12px]">
                        <span>Mastery</span>
                        <span className={s.mastery < 30 ? 'text-error' : s.mastery < 40 ? 'text-warning' : ''}>
                          {s.mastery}%
                        </span>
                      </div>
                      <ProgressBar value={s.mastery} />
                    </div>
                  )}
                  {(s.weak_topics?.length ?? 0) > 0 && (
                    <p className="mt-2 text-[12px] text-text-secondary">
                      Weak: {s.weak_topics!.slice(0, 3).join(', ')}
                    </p>
                  )}
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {s.risk_factors.map((f) => (
                  <Badge key={f} variant={f.toLowerCase().includes('mastery') || f.toLowerCase().includes('quiz') ? 'error' : 'warning'}>
                    {f}
                  </Badge>
                ))}
              </div>
              <div className="flex items-center gap-3">
                <Badge variant={s.severity === 'high' ? 'error' : s.severity === 'medium' ? 'warning' : 'muted'}>
                  {s.severity.toUpperCase()}
                </Badge>
                <span className="text-[12px] text-text-muted">{formatDate(s.last_active)}</span>
                <Button variant="secondary" onClick={() => setDetailId(s.learner_id)}>
                  View Profile
                </Button>
                <Link to="/lecturer/students">
                  <Button variant="ghost">View Student</Button>
                </Link>
                <Button onClick={() => setSendId(s.learner_id)}>Send Resource</Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal open={!!detailId} onClose={() => setDetailId(null)} title={selected?.name ?? 'Student'}>
        {selected && (
          <div className="space-y-4">
            <p className="text-[14px] text-text-secondary">
              {selected.department} · Level {selected.level}
            </p>
            <div className="rounded-lg border border-border bg-card-hover p-4">
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-4 w-4 text-warning" />
                <p className="text-[14px]">{selected.suggested_action}</p>
              </div>
            </div>
            <Button variant="secondary" onClick={() => dismiss.mutate(selected.learner_id)}>
              Dismiss Alert
            </Button>
          </div>
        )}
      </Modal>

      <Modal open={!!sendId} onClose={() => setSendId(null)} title="Send Resource">
        <div className="space-y-4">
          <Input label="Resource URL or title" value={resourceUrl} onChange={(e) => setResourceUrl(e.target.value)} />
          <textarea
            className="w-full rounded-lg border border-border bg-input p-3 text-[14px]"
            placeholder="Personal note (optional)"
            rows={3}
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <Button disabled={!resourceUrl || send.isPending} onClick={() => send.mutate()}>
            Send to Student
          </Button>
        </div>
      </Modal>
    </div>
  );
}

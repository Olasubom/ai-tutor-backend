import { useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckCircle2, Download, FileAudio, FileText, FileVideo, Presentation } from 'lucide-react';
import axios from 'axios';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { useToastStore } from '@/components/ui/Toast';
import {
  approveMaterial,
  listMaterials,
  materialDownloadUrl,
  rejectMaterial,
  type UploadedMaterial,
} from '@/api/upload';
import { useAuthStore } from '@/stores/authStore';
import { cn } from '@/lib/utils';

type Tab = 'pending_review' | 'approved' | 'rejected' | 'all';

const TABS: { id: Tab; label: string }[] = [
  { id: 'pending_review', label: 'Pending Review' },
  { id: 'approved', label: 'Approved' },
  { id: 'rejected', label: 'Rejected' },
  { id: 'all', label: 'All' },
];

function fileTypeIcon(type: string) {
  if (type === 'pdf') return FileText;
  if (type === 'video') return FileVideo;
  if (type === 'audio') return FileAudio;
  if (type === 'slides') return Presentation;
  return FileText;
}

function statusBadge(status: UploadedMaterial['status']) {
  if (status === 'approved') return <Badge variant="teal">Approved</Badge>;
  if (status === 'rejected') return <Badge variant="error">Rejected</Badge>;
  return <Badge variant="warning">Pending Review</Badge>;
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return iso;
  }
}

export default function AdminMaterials() {
  const toast = useToastStore((s) => s.add);
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>('pending_review');
  const [acting, setActing] = useState<string | null>(null);
  const [rejectTarget, setRejectTarget] = useState<UploadedMaterial | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  const allMaterials = useQuery({
    queryKey: ['admin-materials'],
    queryFn: () => listMaterials(),
  });

  const materials = useMemo(() => {
    const rows = allMaterials.data?.materials ?? [];
    if (tab === 'all') return rows;
    return rows.filter((m) => m.status === tab);
  }, [allMaterials.data, tab]);

  const pendingCount = useMemo(
    () => (allMaterials.data?.materials ?? []).filter((m) => m.status === 'pending_review').length,
    [allMaterials.data],
  );

  const openPreview = async (material: UploadedMaterial) => {
    const { token } = useAuthStore.getState();
    try {
      const response = await axios.get(materialDownloadUrl(material.id), {
        responseType: 'blob',
        headers: {
          Authorization: token ? `Bearer ${token}` : '',
          'X-API-Key': localStorage.getItem('aitutor_api_key') || import.meta.env.VITE_API_KEY || 'change_me',
        },
      });
      const url = window.URL.createObjectURL(response.data);
      window.open(url, '_blank', 'noopener,noreferrer');
      setTimeout(() => window.URL.revokeObjectURL(url), 60_000);
    } catch {
      toast('Could not open file preview', 'error');
    }
  };

  const handleApprove = async (id: string) => {
    setActing(id);
    try {
      await approveMaterial(id);
      await qc.invalidateQueries({ queryKey: ['admin-materials'] });
      toast('Material approved and published to recommendations.', 'success');
    } catch {
      toast('Approval failed', 'error');
    } finally {
      setActing(null);
    }
  };

  const handleReject = async () => {
    if (!rejectTarget) return;
    setActing(rejectTarget.id);
    try {
      await rejectMaterial(rejectTarget.id, rejectReason.trim() || undefined);
      await qc.invalidateQueries({ queryKey: ['admin-materials'] });
      toast('Material rejected.', 'success');
      setRejectTarget(null);
      setRejectReason('');
    } catch {
      toast('Rejection failed', 'error');
    } finally {
      setActing(null);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <Badge variant="muted">ADMIN</Badge>
        <h1 className="mt-2 text-[28px] font-extrabold">Material Review Queue</h1>
        <p className="text-text-secondary">Review lecturer uploads before they appear in student recommendations.</p>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-border pb-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={cn(
              'rounded-lg px-4 py-2 text-[14px] font-semibold',
              tab === t.id ? 'bg-primary/10 text-primary' : 'text-text-muted hover:bg-card-hover',
            )}
          >
            {t.label}
            {t.id === 'pending_review' && pendingCount > 0 && (
              <span className="ml-2 rounded-full bg-warning-container px-2 py-0.5 text-[11px] text-warning">
                {pendingCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {allMaterials.isLoading ? (
        <Card className="p-6 text-text-muted">Loading materials…</Card>
      ) : materials.length === 0 ? (
        <Card className="flex flex-col items-center p-12 text-center">
          {tab === 'pending_review' ? (
            <>
              <CheckCircle2 className="h-10 w-10 text-teal" />
              <p className="mt-4 font-semibold">No materials pending review.</p>
            </>
          ) : (
            <p className="text-text-muted">No materials in this category.</p>
          )}
        </Card>
      ) : (
        <div className="space-y-4">
          {materials.map((m) => {
            const Icon = fileTypeIcon(m.file_type);
            return (
              <Card key={m.id} className="p-5">
                <div className="flex flex-wrap items-center gap-2 text-[12px] text-text-muted">
                  {statusBadge(m.status)}
                  <span>{formatDate(m.created_at)}</span>
                  <span>·</span>
                  <span>{m.uploaded_by_name}</span>
                  {(m.college || m.department) && (
                    <>
                      <span>·</span>
                      <span>
                        {[m.college, m.department].filter(Boolean).join(' / ')}
                      </span>
                    </>
                  )}
                </div>
                <h3 className="mt-2 text-[18px] font-bold">{m.title}</h3>
                {m.description && <p className="mt-1 text-[14px] text-text-secondary">{m.description}</p>}
                <div className="mt-3 flex flex-wrap gap-2">
                  {m.course_code && <Badge variant="muted">{m.course_code}</Badge>}
                  {m.subject && <Badge variant="muted">{m.subject}</Badge>}
                </div>
                <div className="mt-3 flex items-center gap-2 text-[13px] text-text-muted">
                  <Icon className="h-4 w-4" />
                  <span className="capitalize">{m.file_type}</span>
                  <span>·</span>
                  <span>{m.file_size_mb} MB</span>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Button type="button" variant="secondary" onClick={() => openPreview(m)}>
                    <Download className="mr-2 h-4 w-4" /> Preview / Download
                  </Button>
                  {m.status === 'pending_review' && (
                    <>
                      <Button type="button" disabled={acting === m.id} onClick={() => handleApprove(m.id)}>
                        Approve
                      </Button>
                      <Button
                        type="button"
                        variant="secondary"
                        disabled={acting === m.id}
                        onClick={() => {
                          setRejectTarget(m);
                          setRejectReason('');
                        }}
                      >
                        Reject
                      </Button>
                    </>
                  )}
                </div>
                {m.status === 'rejected' && m.rejection_reason && (
                  <p className="mt-3 text-[13px] italic text-error">Rejected: {m.rejection_reason}</p>
                )}
              </Card>
            );
          })}
        </div>
      )}

      <Modal open={!!rejectTarget} onClose={() => setRejectTarget(null)} title="Reject material">
        <p className="mb-4 text-[14px] text-text-secondary">
          Optionally provide a reason for <strong>{rejectTarget?.title}</strong>.
        </p>
        <label className="text-[13px] text-text-muted">Reason (optional)</label>
        <textarea
          rows={3}
          className="mt-1 w-full rounded-lg border border-border bg-input px-3 py-2 text-[14px]"
          value={rejectReason}
          onChange={(e) => setRejectReason(e.target.value)}
        />
        <div className="mt-4 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={() => setRejectTarget(null)}>
            Cancel
          </Button>
          <Button type="button" variant="secondary" className="border-error text-error" disabled={!!acting} onClick={handleReject}>
            Confirm Reject
          </Button>
        </div>
      </Modal>
    </div>
  );
}

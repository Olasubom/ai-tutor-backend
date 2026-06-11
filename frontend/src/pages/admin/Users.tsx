import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Trash2, Users } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { useToastStore } from '@/components/ui/Toast';
import {
  deleteLecturer,
  deleteStudent,
  listLecturers,
  listStudents,
  type AdminLecturer,
  type AdminStudent,
} from '@/api/admin';
import { cn } from '@/lib/utils';

type Tab = 'students' | 'lecturers';

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return iso;
  }
}

function lecturerStatusBadge(status?: string | null) {
  if (status === 'approved') return <Badge variant="teal">Approved</Badge>;
  if (status === 'pending_verification') return <Badge variant="warning">Pending</Badge>;
  if (status === 'rejected') return <Badge variant="error">Rejected</Badge>;
  return <Badge variant="muted">{status ?? 'Unknown'}</Badge>;
}

export default function AdminUsers() {
  const toast = useToastStore((s) => s.add);
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>('students');
  const [acting, setActing] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<
    { type: Tab; user: AdminStudent | AdminLecturer } | null
  >(null);

  const students = useQuery({
    queryKey: ['admin-users-students'],
    queryFn: () => listStudents(),
  });

  const lecturers = useQuery({
    queryKey: ['admin-users-lecturers'],
    queryFn: () => listLecturers(),
  });

  const rows = tab === 'students' ? students.data ?? [] : lecturers.data ?? [];
  const isLoading = tab === 'students' ? students.isLoading : lecturers.isLoading;

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setActing(deleteTarget.user.user_id);
    try {
      if (deleteTarget.type === 'students') {
        await deleteStudent(deleteTarget.user.user_id);
        await qc.invalidateQueries({ queryKey: ['admin-users-students'] });
      } else {
        await deleteLecturer(deleteTarget.user.user_id);
        await qc.invalidateQueries({ queryKey: ['admin-users-lecturers'] });
      }
      toast(`${deleteTarget.type === 'students' ? 'Student' : 'Lecturer'} deleted`, 'success');
      setDeleteTarget(null);
    } catch {
      toast('Could not delete user', 'error');
    } finally {
      setActing(null);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <Badge variant="muted">ADMIN</Badge>
        <h1 className="mt-2 text-[28px] font-extrabold">Registered users</h1>
        <p className="text-text-secondary">View and remove student and lecturer accounts.</p>
      </div>

      <div className="flex gap-2 border-b border-border pb-2">
        {(['students', 'lecturers'] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={cn(
              'rounded-lg px-4 py-2 text-[14px] font-semibold capitalize',
              tab === t ? 'bg-primary/10 text-primary' : 'text-text-muted hover:bg-card-hover',
            )}
          >
            {t}
            <span className="ml-2 text-[12px] text-text-muted">
              ({t === 'students' ? students.data?.length ?? 0 : lecturers.data?.length ?? 0})
            </span>
          </button>
        ))}
      </div>

      {isLoading ? (
        <Card className="p-6 text-text-muted">Loading users…</Card>
      ) : rows.length === 0 ? (
        <Card className="flex flex-col items-center p-12 text-center">
          <Users className="h-10 w-10 text-text-muted" />
          <p className="mt-4 font-semibold">No {tab} registered yet.</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {tab === 'students'
            ? (rows as AdminStudent[]).map((u) => (
                <Card key={u.user_id} className="flex flex-wrap items-center justify-between gap-4 p-4">
                  <div>
                    <div className="font-semibold">{u.name}</div>
                    <div className="text-[13px] text-text-muted">{u.email}</div>
                    <div className="mt-1 text-[12px] text-text-muted">
                      {[u.college, u.department, u.academic_level && `Level ${u.academic_level}`]
                        .filter(Boolean)
                        .join(' · ')}
                      {' · '}
                      Joined {formatDate(u.created_at)}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant={u.is_active ? 'teal' : 'error'}>
                      {u.is_active ? 'Active' : 'Suspended'}
                    </Badge>
                    <button
                      type="button"
                      className="rounded p-2 text-error hover:bg-card-hover"
                      onClick={() => setDeleteTarget({ type: 'students', user: u })}
                      aria-label={`Delete ${u.name}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </Card>
              ))
            : (rows as AdminLecturer[]).map((u) => (
                <Card key={u.user_id} className="flex flex-wrap items-center justify-between gap-4 p-4">
                  <div>
                    <div className="font-semibold">{u.name}</div>
                    <div className="text-[13px] text-text-muted">{u.email}</div>
                    <div className="mt-1 text-[12px] text-text-muted">
                      {[u.nuc_staff_id, u.college, u.department].filter(Boolean).join(' · ')}
                      {' · '}
                      Joined {formatDate(u.created_at)}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {lecturerStatusBadge(u.lecturer_status)}
                    <Badge variant={u.is_active ? 'teal' : 'error'}>
                      {u.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                    <button
                      type="button"
                      className="rounded p-2 text-error hover:bg-card-hover"
                      onClick={() => setDeleteTarget({ type: 'lecturers', user: u })}
                      aria-label={`Delete ${u.name}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </Card>
              ))}
        </div>
      )}

      <Modal open={!!deleteTarget} onClose={() => setDeleteTarget(null)} title="Delete user">
        <p className="text-[14px] text-text-secondary">
          Delete <strong>{deleteTarget?.user.name}</strong> ({deleteTarget?.user.email})? This cannot be undone.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={() => setDeleteTarget(null)}>
            Cancel
          </Button>
          <Button
            type="button"
            variant="secondary"
            className="border-error text-error"
            disabled={!!acting}
            onClick={handleDelete}
          >
            Delete user
          </Button>
        </div>
      </Modal>
    </div>
  );
}

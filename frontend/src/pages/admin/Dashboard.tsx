import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, LogOut, Pencil, Plus, Trash2, X } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import {
  addFaculty,
  approveLecturer,
  getFaculties,
  getPendingLecturers,
  getLecturers,
  getSystemHealth,
  getTestimonials,
  rejectLecturer,
  removeFaculty,
  saveTestimonial,
  updateFaculty,
} from '@/api/admin';
import { fetchDepartments } from '@/api/courses';
import { useAuth } from '@/hooks/useAuth';
import { useToastStore } from '@/components/ui/Toast';
import type { Testimonial, TestimonialPanel } from '@/types';

const PANEL_LABELS: Record<TestimonialPanel, string> = {
  login: 'Login page',
  student_register: 'Student sign-up',
  lecturer_register: 'Lecturer sign-up',
};

export default function AdminDashboard() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const toast = useToastStore((s) => s.add);
  const qc = useQueryClient();
  const [acting, setActing] = useState<string | null>(null);
  const [newFaculty, setNewFaculty] = useState('');
  const [editingFaculty, setEditingFaculty] = useState<string | null>(null);
  const [editFacultyName, setEditFacultyName] = useState('');

  const pending = useQuery({ queryKey: ['admin-pending'], queryFn: getPendingLecturers });
  const lecturers = useQuery({ queryKey: ['admin-lecturers'], queryFn: getLecturers });
  const health = useQuery({ queryKey: ['admin-health'], queryFn: getSystemHealth, staleTime: 30_000 });
  const faculties = useQuery({ queryKey: ['admin-faculties'], queryFn: getFaculties });
  const testimonials = useQuery({ queryKey: ['admin-testimonials'], queryFn: getTestimonials });

  const departments = fetchDepartments();
  const [drafts, setDrafts] = useState<Record<string, Testimonial>>({});

  const getDraft = (t: Testimonial) => drafts[t.id] ?? t;

  const handleApprove = async (userId: string) => {
    setActing(userId);
    try {
      approveLecturer(userId);
      await qc.invalidateQueries({ queryKey: ['admin-pending'] });
      await qc.invalidateQueries({ queryKey: ['admin-lecturers'] });
      toast('Lecturer approved', 'success');
    } finally {
      setActing(null);
    }
  };

  const handleReject = async (userId: string) => {
    setActing(userId);
    try {
      rejectLecturer(userId);
      await qc.invalidateQueries({ queryKey: ['admin-pending'] });
      toast('Lecturer rejected', 'success');
    } finally {
      setActing(null);
    }
  };

  const handleAddFaculty = () => {
    const name = newFaculty.trim();
    if (!name) return;
    addFaculty(name);
    setNewFaculty('');
    qc.invalidateQueries({ queryKey: ['admin-faculties'] });
    qc.invalidateQueries({ queryKey: ['faculties'] });
    toast('Faculty added', 'success');
  };

  const handleSaveFaculty = (id: string) => {
    const name = editFacultyName.trim();
    if (!name) return;
    updateFaculty(id, name);
    setEditingFaculty(null);
    qc.invalidateQueries({ queryKey: ['admin-faculties'] });
    qc.invalidateQueries({ queryKey: ['faculties'] });
    toast('Faculty updated', 'success');
  };

  const handleDeleteFaculty = (id: string) => {
    const hasDepts = departments.some((d) => d.faculty_id === id);
    if (hasDepts) {
      toast('Remove or reassign departments in this faculty first', 'error');
      return;
    }
    removeFaculty(id);
    qc.invalidateQueries({ queryKey: ['admin-faculties'] });
    qc.invalidateQueries({ queryKey: ['faculties'] });
    toast('Faculty removed', 'success');
  };

  const updateDraft = (id: string, patch: Partial<Testimonial>) => {
    const current = testimonials.data?.find((t) => t.id === id);
    if (!current) return;
    setDrafts((d) => ({ ...d, [id]: { ...getDraft(current), ...patch } }));
  };

  const handleSaveTestimonial = (t: Testimonial) => {
    const draft = getDraft(t);
    saveTestimonial(draft);
    qc.invalidateQueries({ queryKey: ['admin-testimonials'] });
    setDrafts((d) => {
      const next = { ...d };
      delete next[t.id];
      return next;
    });
    toast('Review updated', 'success');
  };

  return (
    <div className="mx-auto max-w-4xl space-y-8 p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Badge variant="muted">ADMIN</Badge>
          <h1 className="mt-2 text-[28px] font-extrabold">Platform administration</h1>
          <p className="text-text-secondary">
            Approve lecturers, manage faculties, and edit auth-page reviews. Access this at{' '}
            <code className="text-[13px]">/admin/login</code>
          </p>
        </div>
        <Button
          variant="secondary"
          onClick={() => {
            logout();
            navigate('/login');
          }}
        >
          <LogOut className="mr-2 h-4 w-4" /> Log out
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card className="p-4">
          <div className="text-[13px] text-text-muted">API readiness</div>
          <div className="mt-1 font-bold text-teal">
            {health.data?.readyz?.status === 'ready' ? 'Ready' : health.isLoading ? 'Checking…' : 'Unavailable'}
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-[13px] text-text-muted">Active lecturers</div>
          <div className="mt-1 text-[24px] font-extrabold">
            {lecturers.data?.filter((l) => l.status === 'active').length ?? 0}
          </div>
        </Card>
      </div>

      <Card className="p-6">
        <h2 className="text-[18px] font-bold">Faculties</h2>
        <p className="mt-1 text-[14px] text-text-muted">
          Shown on lecturer registration. Duplicates are removed automatically.
        </p>
        <div className="mt-4 flex gap-2">
          <Input
            placeholder="New faculty name, e.g. Faculty of Arts"
            value={newFaculty}
            onChange={(e) => setNewFaculty(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAddFaculty()}
          />
          <Button type="button" onClick={handleAddFaculty}>
            <Plus className="h-4 w-4" />
          </Button>
        </div>
        <div className="mt-4 space-y-2">
          {faculties.data?.map((f) => (
            <div key={f.id} className="flex items-center justify-between gap-3 rounded-lg border border-border px-4 py-3">
              {editingFaculty === f.id ? (
                <>
                  <Input value={editFacultyName} onChange={(e) => setEditFacultyName(e.target.value)} />
                  <Button type="button" onClick={() => handleSaveFaculty(f.id)}>
                    <Check className="h-4 w-4" />
                  </Button>
                  <Button type="button" variant="ghost" onClick={() => setEditingFaculty(null)}>
                    <X className="h-4 w-4" />
                  </Button>
                </>
              ) : (
                <>
                  <span className="font-medium">{f.name}</span>
                  <div className="flex gap-1">
                    <button
                      type="button"
                      className="rounded p-2 text-text-muted hover:bg-card-hover"
                      onClick={() => {
                        setEditingFaculty(f.id);
                        setEditFacultyName(f.name);
                      }}
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      className="rounded p-2 text-error hover:bg-card-hover"
                      onClick={() => handleDeleteFaculty(f.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-6">
        <h2 className="text-[18px] font-bold">Auth page reviews</h2>
        <p className="mt-1 text-[14px] text-text-muted">Testimonial cards on login and sign-up screens.</p>
        <div className="mt-4 space-y-6">
          {testimonials.data?.map((t) => {
            const draft = getDraft(t);
            return (
              <div key={t.id} className="rounded-xl border border-border p-4">
                <div className="mb-3 font-semibold text-primary">{PANEL_LABELS[t.panel]}</div>
                <div className="space-y-3">
                  <div>
                    <label className="text-[13px] text-text-muted">Quote</label>
                    <textarea
                      className="mt-1 w-full rounded-lg border border-border bg-input px-3 py-2 text-[14px]"
                      rows={3}
                      value={draft.quote}
                      onChange={(e) => updateDraft(t.id, { quote: e.target.value })}
                    />
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Input
                      label="Author"
                      value={draft.author}
                      onChange={(e) => updateDraft(t.id, { author: e.target.value })}
                    />
                    <Input
                      label="Role / title"
                      value={draft.role}
                      onChange={(e) => updateDraft(t.id, { role: e.target.value })}
                    />
                  </div>
                  <Button type="button" onClick={() => handleSaveTestimonial(t)}>
                    Save review
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      <Card className="p-6">
        <h2 className="text-[18px] font-bold">Pending lecturer approvals</h2>
        {!pending.data?.length ? (
          <p className="mt-4 text-[14px] text-text-muted">No pending lecturer registrations.</p>
        ) : (
          <div className="mt-4 space-y-3">
            {pending.data.map((l) => {
              const dept = departments.find((d) => d.id === l.department_id);
              return (
                <div
                  key={l.user_id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border p-4"
                >
                  <div>
                    <div className="font-semibold">{l.name}</div>
                    <div className="text-[13px] text-text-muted">
                      {l.email} · {l.staff_id} · {dept?.name ?? 'Department'}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button disabled={acting === l.user_id} onClick={() => handleApprove(l.user_id)}>
                      <Check className="mr-1 h-4 w-4" /> Approve
                    </Button>
                    <Button
                      variant="secondary"
                      disabled={acting === l.user_id}
                      onClick={() => handleReject(l.user_id)}
                    >
                      <X className="mr-1 h-4 w-4" /> Reject
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      <p className="text-center text-[13px] text-text-muted">
        <Link to="/" className="text-primary">
          Back to site
        </Link>
      </p>
    </div>
  );
}

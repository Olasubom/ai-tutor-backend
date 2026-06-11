import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Check, LogOut, Pencil, Plus, Trash2, X } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import {
  addCollege,
  addNucId,
  approveLecturer,
  deleteNucId,
  getColleges,
  getNucIds,
  getPendingLecturers,
  getLecturers,
  getSystemHealth,
  getTestimonials,
  rejectLecturer,
  removeCollege,
  revokeNucId,
  saveTestimonial,
  updateCollege,
} from '@/api/admin';
import {
  createCourse,
  createDepartment,
  fetchCourses,
  fetchDepartments,
  removeCourse,
  removeDepartment,
} from '@/api/courses';
import { Select } from '@/components/ui/Select';
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
  const [newCollege, setNewCollege] = useState('');
  const [editingCollege, setEditingCollege] = useState<string | null>(null);
  const [editCollegeName, setEditCollegeName] = useState('');
  const [newDeptName, setNewDeptName] = useState('');
  const [newDeptCollege, setNewDeptCollege] = useState('');
  const [courseDept, setCourseDept] = useState('');
  const [courseLevel, setCourseLevel] = useState('100');
  const [newCourseCode, setNewCourseCode] = useState('');
  const [newCourseTitle, setNewCourseTitle] = useState('');
  const [isSubmittingCourse, setIsSubmittingCourse] = useState(false);
  const [newStaffId, setNewStaffId] = useState('');
  const [newStaffLabel, setNewStaffLabel] = useState('');
  const [newStaffDept, setNewStaffDept] = useState('');
  const [newStaffCollege, setNewStaffCollege] = useState('');

  const pending = useQuery({ queryKey: ['admin-pending'], queryFn: getPendingLecturers });
  const lecturers = useQuery({ queryKey: ['admin-lecturers'], queryFn: getLecturers });
  const health = useQuery({ queryKey: ['admin-health'], queryFn: getSystemHealth, staleTime: 30_000 });
  const colleges = useQuery({ queryKey: ['admin-colleges'], queryFn: getColleges });
  const testimonials = useQuery({ queryKey: ['admin-testimonials'], queryFn: getTestimonials });
  const nucIds = useQuery({ queryKey: ['admin-nuc-ids'], queryFn: getNucIds });

  const departments = useQuery({ queryKey: ['admin-departments'], queryFn: () => fetchDepartments() });
  const courses = useQuery({
    queryKey: ['admin-courses', courseDept, courseLevel],
    queryFn: () => fetchCourses(courseDept, courseLevel || undefined),
    enabled: !!courseDept,
  });
  const departmentRows = departments.data ?? [];
  const courseRows = courses.data ?? [];

  useEffect(() => {
    if (!courseDept && departmentRows.length > 0) {
      setCourseDept(departmentRows[0].id);
    }
  }, [courseDept, departmentRows.length, departmentRows[0]?.id]);

  const selectedDeptName = departmentRows.find((d) => d.id === courseDept)?.name;
  const [drafts, setDrafts] = useState<Record<string, Testimonial>>({});

  const getDraft = (t: Testimonial) => drafts[t.id] ?? t;

  const refreshCatalog = async () => {
    await Promise.all([
      qc.refetchQueries({ queryKey: ['admin-colleges'] }),
      qc.refetchQueries({ queryKey: ['admin-departments'] }),
      qc.refetchQueries({ queryKey: ['admin-courses'] }),
      qc.refetchQueries({ queryKey: ['admin-nuc-ids'] }),
      qc.refetchQueries({ queryKey: ['colleges'] }),
    ]);
  };

  const handleApprove = async (userId: string) => {
    setActing(userId);
    try {
      await approveLecturer(userId);
      await qc.invalidateQueries({ queryKey: ['admin-pending'] });
      await qc.invalidateQueries({ queryKey: ['admin-lecturers'] });
      toast('Lecturer approved', 'success');
    } catch {
      toast('Could not approve lecturer', 'error');
    } finally {
      setActing(null);
    }
  };

  const handleReject = async (userId: string) => {
    setActing(userId);
    try {
      await rejectLecturer(userId);
      await qc.invalidateQueries({ queryKey: ['admin-pending'] });
      toast('Lecturer rejected', 'success');
    } catch {
      toast('Could not reject lecturer', 'error');
    } finally {
      setActing(null);
    }
  };

  const handleAddCollege = async () => {
    const name = newCollege.trim();
    if (!name) return;
    try {
      await addCollege(name);
      setNewCollege('');
      await refreshCatalog();
      toast('College added', 'success');
    } catch {
      toast('Could not add college', 'error');
    }
  };

  const handleSaveCollege = async (id: string) => {
    const name = editCollegeName.trim();
    if (!name) return;
    try {
      await updateCollege(id, name);
      setEditingCollege(null);
      await refreshCatalog();
      toast('College updated', 'success');
    } catch {
      toast('Could not update college', 'error');
    }
  };

  const handleDeleteCollege = async (id: string) => {
    const hasDepts = departmentRows.some((d) => d.college_id === id);
    if (hasDepts) {
      toast('Remove or reassign departments in this college first', 'error');
      return;
    }
    setActing(id);
    try {
      await removeCollege(id);
      await refreshCatalog();
      toast('College removed', 'success');
    } catch {
      toast('Could not remove college', 'error');
    } finally {
      setActing(null);
    }
  };

  const updateDraft = (id: string, patch: Partial<Testimonial>) => {
    const current = testimonials.data?.find((t) => t.id === id);
    if (!current) return;
    setDrafts((d) => ({ ...d, [id]: { ...getDraft(current), ...patch } }));
  };

  const handleAddDepartment = async () => {
    const name = newDeptName.trim();
    if (!name || !newDeptCollege) return;
    try {
      await createDepartment({ name, college_id: newDeptCollege });
      setNewDeptName('');
      await refreshCatalog();
      toast('Department added', 'success');
    } catch {
      toast('Could not add department', 'error');
    }
  };

  const handleDeleteDepartment = async (id: string) => {
    setActing(id);
    try {
      await removeDepartment(id);
      if (courseDept === id) setCourseDept('');
      await refreshCatalog();
      toast('Department removed', 'success');
    } catch {
      toast('Could not remove department', 'error');
    } finally {
      setActing(null);
    }
  };

  const handleAddCourse = async () => {
    if (!courseDept || !newCourseCode.trim() || !newCourseTitle.trim()) return;
    const level = courseLevel || '100';
    const code = newCourseCode.trim().toUpperCase();

    const isDuplicate = courseRows.some(
      (c) =>
        c.course_code.toLowerCase().trim() === code.toLowerCase().trim() &&
        c.department_id === courseDept &&
        c.level === level,
    );
    if (isDuplicate) {
      toast(`${code} already exists in this department at this level.`, 'error');
      return;
    }

    setIsSubmittingCourse(true);
    try {
      await createCourse({
        department_id: courseDept,
        course_code: code,
        course_title: newCourseTitle.trim(),
        level,
        units: 3,
        semester: 'First',
        type: 'Compulsory',
      });
      setCourseLevel(level);
      setNewCourseCode('');
      setNewCourseTitle('');
      await qc.refetchQueries({ queryKey: ['admin-courses', courseDept, level] });
      toast('Course added successfully', 'success');
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        const detail = err.response.data?.detail;
        toast(typeof detail === 'string' ? detail : 'Course already exists.', 'error');
      } else {
        toast('Failed to add course', 'error');
      }
    } finally {
      setIsSubmittingCourse(false);
    }
  };

  const handleAddStaffId = async () => {
    if (!newStaffId.trim() || !newStaffCollege || !newStaffDept) return;
    try {
      await addNucId({
        staff_id: newStaffId.trim().toUpperCase(),
        label: newStaffLabel.trim() || undefined,
        college_id: newStaffCollege,
        department_id: newStaffDept,
      });
      setNewStaffId('');
      setNewStaffLabel('');
      await qc.invalidateQueries({ queryKey: ['admin-nuc-ids'] });
      toast('Staff ID added', 'success');
    } catch {
      toast('Could not add staff ID', 'error');
    }
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
    <div className="mx-auto max-w-4xl space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Badge variant="muted">ADMIN</Badge>
          <h1 className="mt-2 text-[28px] font-extrabold">Platform Administration</h1>

        </div>
        <Button
          variant="secondary"
          onClick={() => {
            logout();
            navigate('/admin/login');
          }}
        >
          <LogOut className="mr-2 h-4 w-4" /> Log out
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card className="p-4">
          <div className="text-[13px] text-text-muted">API readiness</div>
          <div className="mt-1 font-bold text-teal">
            {health.data?.status === 'ready' ? 'Ready' : health.isLoading ? 'Checking…' : 'Unavailable'}
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
        <h2 className="text-[18px] font-bold">Colleges</h2>
        <p className="mt-1 text-[14px] text-text-muted">
          Shown on lecturer registration. Duplicates are removed automatically.
        </p>
        <div className="mt-4 flex gap-2">
          <Input
            placeholder="New college name, e.g. College of Arts"
            value={newCollege}
            onChange={(e) => setNewCollege(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAddCollege()}
          />
          <Button type="button" onClick={handleAddCollege}>
            <Plus className="h-4 w-4" />
          </Button>
        </div>
        <div className="mt-4 space-y-2">
          {colleges.data?.map((college) => (
            <div key={college.id} className="flex items-center justify-between gap-3 rounded-lg border border-border px-4 py-3">
              {editingCollege === college.id ? (
                <>
                  <Input value={editCollegeName} onChange={(e) => setEditCollegeName(e.target.value)} />
                  <Button type="button" onClick={() => handleSaveCollege(college.id)}>
                    <Check className="h-4 w-4" />
                  </Button>
                  <Button type="button" variant="ghost" onClick={() => setEditingCollege(null)}>
                    <X className="h-4 w-4" />
                  </Button>
                </>
              ) : (
                <>
                  <span className="font-medium">{college.name}</span>
                  <div className="flex gap-1">
                    <button
                      type="button"
                      className="rounded p-2 text-text-muted hover:bg-card-hover"
                      onClick={() => {
                        setEditingCollege(college.id);
                        setEditCollegeName(college.name);
                      }}
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      className="rounded p-2 text-error hover:bg-card-hover disabled:opacity-50"
                      disabled={acting === college.id}
                      onClick={() => handleDeleteCollege(college.id)}
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
        <h2 className="text-[18px] font-bold">Departments</h2>
        <p className="mt-1 text-[14px] text-text-muted">Used in lecturer registration and student course selection.</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <Input
            placeholder="Department name"
            value={newDeptName}
            onChange={(e) => setNewDeptName(e.target.value)}
          />
          <Select
            value={newDeptCollege}
            onChange={(e) => setNewDeptCollege(e.target.value)}
            options={[
              { value: '', label: 'Select college…' },
              ...(colleges.data ?? []).map((college) => ({ value: college.id, label: college.name })),
            ]}
          />
          <Button type="button" onClick={handleAddDepartment}>
            <Plus className="h-4 w-4" /> Add department
          </Button>
        </div>
        <div className="mt-4 space-y-2">
          {departmentRows.map((d) => {
            const college = colleges.data?.find((c) => c.id === d.college_id);
            return (
              <div key={d.id} className="flex items-center justify-between gap-3 rounded-lg border border-border px-4 py-3">
                <div>
                  <span className="font-medium">{d.name}</span>
                  <span className="ml-2 text-[13px] text-text-muted">
                    {college?.name} · {d.course_count ?? 0} courses
                  </span>
                </div>
                <button
                  type="button"
                  className="rounded p-2 text-error hover:bg-card-hover disabled:opacity-50"
                  disabled={acting === d.id}
                  onClick={() => handleDeleteDepartment(d.id)}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            );
          })}
        </div>
      </Card>

      <Card className="p-6">
        <h2 className="text-[18px] font-bold">Courses</h2>
        <p className="mt-1 text-[14px] text-text-muted">
          Courses appear in student onboarding when they pick a department and level.
        </p>
        {selectedDeptName && (
          <p className="mt-2 text-[13px] text-text-muted">
            Viewing: <span className="font-medium text-text-primary">{selectedDeptName}</span>
            {courseLevel ? ` · Level ${courseLevel}` : ' · All levels'}
          </p>
        )}
        {courseDept && courseLevel && !courses.isLoading && (
          <p className="mt-1 text-[13px] text-text-muted">
            {courseRows.length} course{courseRows.length !== 1 ? 's' : ''} at {courseLevel} Level
          </p>
        )}
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Select
            label="Department"
            value={courseDept}
            onChange={(e) => setCourseDept(e.target.value)}
            options={
              departmentRows.length === 0
                ? [{ value: '', label: 'Add a department first' }]
                : departmentRows.map((d) => ({ value: d.id, label: d.name }))
            }
          />
          <Select
            label="Level"
            value={courseLevel}
            onChange={(e) => setCourseLevel(e.target.value)}
            options={[
              { value: '', label: 'All levels' },
              ...['100', '200', '300', '400', '500'].map((l) => ({ value: l, label: `${l} Level` })),
            ]}
          />
          <Input
            label="Course code"
            placeholder="CSC 301"
            value={newCourseCode}
            onChange={(e) => setNewCourseCode(e.target.value)}
          />
          <Input
            label="Course title"
            placeholder="Operating Systems"
            value={newCourseTitle}
            onChange={(e) => setNewCourseTitle(e.target.value)}
          />
        </div>
        <Button
          type="button"
          className="mt-4"
          onClick={handleAddCourse}
          disabled={isSubmittingCourse || !courseDept || !newCourseCode.trim() || !newCourseTitle.trim()}
        >
          <Plus className="h-4 w-4" /> {isSubmittingCourse ? 'Adding…' : 'Add course'}
        </Button>
        <div className="mt-4 space-y-2">
          {courses.isLoading ? (
            <p className="text-[14px] text-text-muted">Loading courses…</p>
          ) : !courseDept ? (
            <p className="text-[14px] text-text-muted">Select a department to view courses.</p>
          ) : courseRows.length === 0 ? (
            <p className="text-[14px] text-text-muted">
              No courses for this filter. Add one above or try &quot;All levels&quot;.
            </p>
          ) : (
            courseRows.map((c) => (
              <div key={c.id} className="flex items-center justify-between gap-3 rounded-lg border border-border px-4 py-3">
                <div>
                  <span className="font-medium">{c.course_code}</span>
                  <span className="ml-2 text-[13px] text-text-muted">
                    {c.course_title} · Level {c.level}
                  </span>
                </div>
                <button
                  type="button"
                  className="rounded p-2 text-error hover:bg-card-hover disabled:opacity-50"
                  disabled={acting === c.id}
                  onClick={async () => {
                    setActing(c.id);
                    try {
                      await removeCourse(c.id);
                      await qc.refetchQueries({ queryKey: ['admin-courses', courseDept, courseLevel] });
                      toast('Course removed', 'success');
                    } catch {
                      toast('Could not remove course', 'error');
                    } finally {
                      setActing(null);
                    }
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))
          )}
        </div>
      </Card>

      <Card className="p-6">
        <h2 className="text-[18px] font-bold">Approved staff IDs</h2>
        <p className="mt-1 text-[14px] text-text-muted">
          Lecturers must register with one of these IDs. Demo IDs: NUC-2024-001, NUC-2024-002
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Input
            label="Staff ID"
            placeholder="NUC-2024-003"
            value={newStaffId}
            onChange={(e) => setNewStaffId(e.target.value)}
          />
          <Input
            label="Label (optional)"
            placeholder="Dr. Smith"
            value={newStaffLabel}
            onChange={(e) => setNewStaffLabel(e.target.value)}
          />
          <Select
            label="College"
            value={newStaffCollege}
            onChange={(e) => {
              setNewStaffCollege(e.target.value);
              setNewStaffDept('');
            }}
            options={[
              { value: '', label: 'Select college…' },
              ...(colleges.data ?? []).map((college) => ({ value: college.id, label: college.name })),
            ]}
          />
          <Select
            label="Department"
            value={newStaffDept}
            onChange={(e) => setNewStaffDept(e.target.value)}
            options={[
              { value: '', label: 'Select department…' },
              ...departmentRows
                .filter((d) => !newStaffCollege || d.college_id === newStaffCollege)
                .map((d) => ({ value: d.id, label: d.name })),
            ]}
          />
        </div>
        <Button type="button" className="mt-4" onClick={handleAddStaffId}>
          <Plus className="h-4 w-4" /> Add staff ID
        </Button>
        <div className="mt-4 space-y-2">
          {(nucIds.data ?? []).map((n) => {
            return (
              <div key={n.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border px-4 py-3">
                <div>
                  <span className="font-mono font-medium">{n.nuc_staff_id ?? n.staff_id}</span>
                  <span className="ml-2 text-[13px] text-text-muted">
                    {n.label ?? '—'} · {n.college} / {n.department} ·{' '}
                    <Badge variant={n.status === 'active' ? 'teal' : 'muted'}>{n.status}</Badge>
                  </span>
                </div>
                <div className="flex gap-1">
                  {n.status === 'active' && (
                    <Button
                      type="button"
                      variant="secondary"
                      disabled={acting === n.id}
                      onClick={async () => {
                        setActing(n.id);
                        try {
                          await revokeNucId(n.id);
                          await qc.invalidateQueries({ queryKey: ['admin-nuc-ids'] });
                          toast('Staff ID revoked', 'success');
                        } catch {
                          toast('Could not revoke staff ID', 'error');
                        } finally {
                          setActing(null);
                        }
                      }}
                    >
                      Revoke
                    </Button>
                  )}
                  <button
                    type="button"
                    className="rounded p-2 text-error hover:bg-card-hover disabled:opacity-50"
                    disabled={acting === n.id}
                    onClick={async () => {
                      setActing(n.id);
                      try {
                        await deleteNucId(n.id);
                        await qc.invalidateQueries({ queryKey: ['admin-nuc-ids'] });
                        toast('Staff ID deleted', 'success');
                      } catch {
                        toast('Could not delete staff ID', 'error');
                      } finally {
                        setActing(null);
                      }
                    }}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            );
          })}
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
              return (
                <div
                  key={l.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border p-4"
                >
                  <div>
                    <div className="font-semibold">{l.name}</div>
                    <div className="text-[13px] text-text-muted">
                      {l.email} · {l.nuc_staff_id} · {l.college} / {l.department}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button disabled={acting === l.id} onClick={() => handleApprove(l.id)}>
                      <Check className="mr-1 h-4 w-4" /> Approve
                    </Button>
                    <Button
                      variant="secondary"
                      disabled={acting === l.id}
                      onClick={() => handleReject(l.id)}
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

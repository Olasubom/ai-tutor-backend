import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BookOpen, Megaphone, Plus } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Skeleton } from '@/components/ui/Skeleton';
import { Tabs } from '@/components/ui/Tabs';
import {
  createCourseAnnouncement,
  createLecturerCourse,
  deleteCourseAnnouncement,
  getCourseMaterials,
  listCourseAnnouncements,
  listLecturerManagedCourses,
  updateCourseAnnouncement,
} from '@/api/lecturerDashboard';
import { useAuth } from '@/hooks/useAuth';
import { useToastStore } from '@/components/ui/Toast';

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return iso;
  }
}

export default function LecturerCourses() {
  const toast = useToastStore((s) => s.add);
  const qc = useQueryClient();
  const { user } = useAuth();
  const [selectedId, setSelectedId] = useState('');
  const [courseTab, setCourseTab] = useState('modules');
  const [showCreate, setShowCreate] = useState(false);
  const [code, setCode] = useState('');
  const [title, setTitle] = useState('');
  const [level, setLevel] = useState('100');
  const [annTitle, setAnnTitle] = useState('');
  const [annBody, setAnnBody] = useState('');
  const [editingAnnId, setEditingAnnId] = useState<string | null>(null);
  const [editAnnTitle, setEditAnnTitle] = useState('');
  const [editAnnBody, setEditAnnBody] = useState('');

  const coursesQ = useQuery({
    queryKey: ['lecturer-managed-courses'],
    queryFn: listLecturerManagedCourses,
  });

  const activeId = selectedId || coursesQ.data?.[0]?.id || '';
  const activeCourse = coursesQ.data?.find((c) => c.id === activeId);

  const courseMaterialsQ = useQuery({
    queryKey: ['lecturer-course-materials', activeId],
    queryFn: () => getCourseMaterials(activeId),
    enabled: !!activeId,
  });

  const announcementsQ = useQuery({
    queryKey: ['lecturer-course-announcements', activeId],
    queryFn: () => listCourseAnnouncements(activeId),
    enabled: !!activeId,
  });

  const createMut = useMutation({
    mutationFn: () => createLecturerCourse({ code, title, level }),
    onSuccess: async () => {
      toast('Course created', 'success');
      setShowCreate(false);
      setCode('');
      setTitle('');
      await qc.invalidateQueries({ queryKey: ['lecturer-managed-courses'] });
    },
    onError: () => toast('Could not create course', 'error'),
  });

  const postAnnMut = useMutation({
    mutationFn: () => createCourseAnnouncement(activeId, { title: annTitle.trim(), body: annBody.trim() }),
    onSuccess: (row) => {
      qc.setQueryData(['lecturer-course-announcements', activeId], (prev: typeof announcementsQ.data) => [
        row,
        ...(prev ?? []),
      ]);
      toast('Announcement posted', 'success');
      setAnnTitle('');
      setAnnBody('');
    },
    onError: () => toast('Could not post announcement', 'error'),
  });

  const updateAnnMut = useMutation({
    mutationFn: (id: string) =>
      updateCourseAnnouncement(id, { title: editAnnTitle.trim(), body: editAnnBody.trim() }),
    onSuccess: (row) => {
      qc.setQueryData(['lecturer-course-announcements', activeId], (prev: typeof announcementsQ.data) =>
        (prev ?? []).map((a) => (a.id === row.id ? { ...a, title: row.title, body: row.body } : a)),
      );
      toast('Announcement updated', 'success');
      setEditingAnnId(null);
    },
    onError: () => toast('Could not update announcement', 'error'),
  });

  const deleteAnnMut = useMutation({
    mutationFn: (id: string) => deleteCourseAnnouncement(id),
    onSuccess: (_, id) => {
      qc.setQueryData(['lecturer-course-announcements', activeId], (prev: typeof announcementsQ.data) =>
        (prev ?? []).filter((a) => a.id !== id),
      );
      toast('Announcement deleted', 'success');
    },
    onError: () => toast('Could not delete announcement', 'error'),
  });

  const startEditAnn = (id: string, t: string, b: string) => {
    setEditingAnnId(id);
    setEditAnnTitle(t);
    setEditAnnBody(b);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <Badge variant="muted">COURSES</Badge>
          <h1 className="mt-2 text-[28px] font-extrabold">Course &amp; Module Management</h1>
          <p className="text-text-secondary">Organize modules, link materials, and post announcements.</p>
        </div>
        <Button onClick={() => setShowCreate((v) => !v)}>
          <Plus className="mr-1 h-4 w-4" /> New Course
        </Button>
      </div>

      {showCreate && (
        <Card className="grid gap-3 p-6 md:grid-cols-4">
          <Input placeholder="Course code (e.g. CIL201)" value={code} onChange={(e) => setCode(e.target.value)} />
          <Input placeholder="Course title" value={title} onChange={(e) => setTitle(e.target.value)} />
          <Input placeholder="Level" value={level} onChange={(e) => setLevel(e.target.value)} />
          <Button disabled={!code || !title || createMut.isPending} onClick={() => createMut.mutate()}>
            {createMut.isPending ? 'Creating…' : 'Create'}
          </Button>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <Card className="p-4">
          <h2 className="mb-3 text-[14px] font-bold uppercase text-text-muted">Your courses</h2>
          {coursesQ.isLoading ? (
            <Skeleton className="h-20" />
          ) : !coursesQ.data?.length ? (
            <p className="text-[14px] text-text-secondary">No courses yet. Create one above.</p>
          ) : (
            <div className="space-y-2">
              {coursesQ.data.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => {
                    setSelectedId(c.id);
                    localStorage.setItem('lecturerActiveCourseId', c.id);
                  }}
                  className={`w-full rounded-lg border px-3 py-2 text-left text-[14px] ${
                    activeId === c.id ? 'border-primary bg-primary/5' : 'border-border hover:bg-card-hover'
                  }`}
                >
                  <div className="font-semibold">{c.code}</div>
                  <div className="text-text-muted">{c.title}</div>
                </button>
              ))}
            </div>
          )}
        </Card>

        <Card className="p-6">
          {!activeId ? (
            <p className="text-text-secondary">Select a course to manage modules.</p>
          ) : !activeCourse ? (
            <Skeleton className="h-32" />
          ) : (
            <>
              <div className="mb-4 flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-primary" />
                <div>
                  <h2 className="text-[18px] font-bold">
                    {activeCourse.code} — {activeCourse.title}
                  </h2>
                  <p className="text-[13px] text-text-muted">Level {activeCourse.level}</p>
                </div>
              </div>

              <Tabs
                active={courseTab}
                onChange={setCourseTab}
                tabs={[
                  { id: 'modules', label: 'Modules' },
                  { id: 'announcements', label: 'Announcements' },
                ]}
                className="mb-6"
              />

              {courseTab === 'modules' && (
                <div className="space-y-3">
                  <p className="text-[13px] text-text-secondary">
                    Curriculum modules from approved uploads — the same items students see on their Curriculum page.
                  </p>
                  {courseMaterialsQ.isLoading ? (
                    <Skeleton className="h-24" />
                  ) : !courseMaterialsQ.data?.length ? (
                    <div className="py-8 text-center text-[14px] text-text-secondary">
                      <p>No materials uploaded yet for this course.</p>
                      <Link
                        to="/lecturer/upload"
                        className="mt-2 inline-block text-primary underline hover:opacity-80"
                      >
                        Upload materials →
                      </Link>
                    </div>
                  ) : (
                    <>
                      {courseMaterialsQ.data.map((item, idx) => (
                        <div
                          key={item.id}
                          className="flex items-center gap-3 rounded-lg border border-border p-3"
                        >
                          <span className="w-6 font-mono text-xs text-text-muted">
                            {item.module_order ?? idx + 1}
                          </span>
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-medium">{item.title}</p>
                            {item.description && (
                              <p className="truncate text-xs text-text-muted">{item.description}</p>
                            )}
                          </div>
                          <div className="flex shrink-0 items-center gap-2">
                            {(item.source_type === 'pdf' || item.source_type === 'document') && (
                              <Badge
                                variant={
                                  item.embedding_status === 'embedded'
                                    ? 'teal'
                                    : item.embedding_status === 'failed'
                                      ? 'error'
                                      : 'warning'
                                }
                              >
                                {item.embedding_status === 'embedded'
                                  ? 'AI Ready'
                                  : item.embedding_status === 'failed'
                                    ? 'Failed'
                                    : 'Processing'}
                              </Badge>
                            )}
                            <Badge variant="teal">{item.status}</Badge>
                          </div>
                        </div>
                      ))}
                      <Link
                        to="/lecturer/upload"
                        className="inline-block text-xs text-primary underline hover:opacity-80"
                      >
                        + Upload more materials
                      </Link>
                    </>
                  )}
                </div>
              )}

              {courseTab === 'announcements' && (
                <div className="space-y-6">
                  <div className="rounded-xl border border-border p-4">
                    <h3 className="flex items-center gap-2 text-[15px] font-bold">
                      <Megaphone className="h-4 w-4 text-primary" /> Post announcement
                    </h3>
                    <div className="mt-3 space-y-3">
                      <Input
                        placeholder="Title"
                        value={annTitle}
                        onChange={(e) => setAnnTitle(e.target.value)}
                      />
                      <textarea
                        rows={4}
                        placeholder="Message for enrolled students…"
                        className="w-full rounded-lg border border-border bg-input px-3 py-2 text-[14px]"
                        value={annBody}
                        onChange={(e) => setAnnBody(e.target.value)}
                      />
                      <Button
                        disabled={!annTitle.trim() || !annBody.trim() || postAnnMut.isPending}
                        onClick={() => postAnnMut.mutate()}
                      >
                        {postAnnMut.isPending ? 'Posting…' : 'Post Announcement'}
                      </Button>
                    </div>
                  </div>

                  {announcementsQ.isLoading ? (
                    <Skeleton className="h-24" />
                  ) : !announcementsQ.data?.length ? (
                    <p className="text-[14px] text-text-secondary">No announcements yet.</p>
                  ) : (
                    <div className="space-y-3">
                      {announcementsQ.data.map((a) => (
                        <div key={a.id} className="rounded-xl border border-border p-4">
                          {editingAnnId === a.id ? (
                            <div className="space-y-3">
                              <Input value={editAnnTitle} onChange={(e) => setEditAnnTitle(e.target.value)} />
                              <textarea
                                rows={3}
                                className="w-full rounded-lg border border-border bg-input px-3 py-2 text-[14px]"
                                value={editAnnBody}
                                onChange={(e) => setEditAnnBody(e.target.value)}
                              />
                              <div className="flex gap-2">
                                <Button
                                  className="px-3 py-1.5 text-[13px]"
                                  disabled={updateAnnMut.isPending}
                                  onClick={() => updateAnnMut.mutate(a.id)}
                                >
                                  Save
                                </Button>
                                <Button className="px-3 py-1.5 text-[13px]" variant="ghost" onClick={() => setEditingAnnId(null)}>
                                  Cancel
                                </Button>
                              </div>
                            </div>
                          ) : (
                            <>
                              <div className="flex items-start justify-between gap-3">
                                <div>
                                  <div className="font-semibold">{a.title}</div>
                                  <div className="mt-1 text-[13px] text-text-muted">{formatDate(a.created_at)}</div>
                                </div>
                                {a.is_pinned && <Badge variant="primary">Pinned</Badge>}
                              </div>
                              <p className="mt-2 whitespace-pre-wrap text-[14px] text-text-secondary">{a.body}</p>
                              {a.lecturer_id === user?.user_id && (
                                <div className="mt-3 flex gap-2">
                                  <Button
                                    className="px-3 py-1.5 text-[13px]"
                                    variant="secondary"
                                    onClick={() => startEditAnn(a.id, a.title, a.body)}
                                  >
                                    Edit
                                  </Button>
                                  <Button
                                    className="px-3 py-1.5 text-[13px]"
                                    variant="ghost"
                                    onClick={() => {
                                      if (window.confirm('Delete this announcement?')) deleteAnnMut.mutate(a.id);
                                    }}
                                  >
                                    Delete
                                  </Button>
                                </div>
                              )}
                            </>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </Card>
      </div>
    </div>
  );
}

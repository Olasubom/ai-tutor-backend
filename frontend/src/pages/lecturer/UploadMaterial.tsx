import { useCallback, useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  CheckCircle2,
  Download,
  FileAudio,
  FileText,
  FileVideo,
  Presentation,
  Trash2,
  UploadCloud,
  X,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { useToastStore } from '@/components/ui/Toast';
import {
  deleteMaterial,
  downloadMaterial,
  getLecturerCourses,
  listMaterials,
  uploadMaterial,
  type UploadedMaterial,
} from '@/api/upload';
import { cn } from '@/lib/utils';
import axios from 'axios';

const ACCEPTED_EXTENSIONS = ['.pdf', '.mp4', '.webm', '.mp3', '.docx', '.pptx', '.txt'];
const ACCEPTED_MIME = [
  'application/pdf',
  'video/mp4',
  'video/webm',
  'audio/mpeg',
  'text/plain',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation',
];

function isAcceptedFile(file: File): boolean {
  const ext = file.name.includes('.') ? `.${file.name.split('.').pop()?.toLowerCase()}` : '';
  if (ACCEPTED_EXTENSIONS.includes(ext)) return true;
  return ACCEPTED_MIME.some((m) => file.type === m);
}

function fileTypeIcon(type: string) {
  if (type === 'pdf') return { icon: FileText, color: 'text-red-500' };
  if (type === 'video') return { icon: FileVideo, color: 'text-blue-500' };
  if (type === 'audio') return { icon: FileAudio, color: 'text-purple-500' };
  if (type === 'slides') return { icon: Presentation, color: 'text-amber-500' };
  return { icon: FileText, color: 'text-amber-500' };
}

function statusBadge(status: UploadedMaterial['status']) {
  if (status === 'approved') return <Badge variant="teal">Approved</Badge>;
  if (status === 'rejected') return <Badge variant="error">Rejected</Badge>;
  return <Badge variant="warning">Pending Review</Badge>;
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return iso;
  }
}

function semesterLabel(semester: string) {
  return semester === 'Both' ? 'Full Year' : `${semester} Semester`;
}

export default function UploadMaterial() {
  const toast = useToastStore((s) => s.add);
  const qc = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [title, setTitle] = useState('');
  const [courseId, setCourseId] = useState('');
  const [moduleOrder, setModuleOrder] = useState('');
  const [description, setDescription] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [success, setSuccess] = useState<{ status: string; message: string } | null>(null);
  const [error, setError] = useState('');

  const coursesQ = useQuery({
    queryKey: ['lecturer-courses'],
    queryFn: getLecturerCourses,
  });

  const myUploads = useQuery({
    queryKey: ['my-uploads'],
    queryFn: () => listMaterials({ mine: true }),
  });

  const groupedByCourse = useMemo(() => {
    const map: Record<string, UploadedMaterial[]> = {};
    for (const m of myUploads.data?.materials ?? []) {
      const label =
        m.course_code && m.course_title
          ? `${m.course_code} — ${m.course_title}`
          : m.course_code || 'Uncategorized';
      if (!map[label]) map[label] = [];
      map[label].push(m);
    }
    return map;
  }, [myUploads.data]);

  const pickFile = useCallback((picked: File | null) => {
    if (!picked) return;
    if (!isAcceptedFile(picked)) {
      setFile(null);
      setFileError('This file type is not supported. Please upload PDF, video, audio, or document.');
      return;
    }
    setFileError('');
    setFile(picked);
    if (!title.trim()) {
      const base = picked.name.replace(/\.[^.]+$/, '');
      setTitle(base.replace(/[-_]/g, ' '));
    }
  }, [title]);

  const resetForm = () => {
    setFile(null);
    setTitle('');
    setCourseId('');
    setModuleOrder('');
    setDescription('');
    setUploadProgress(0);
    setSuccess(null);
    setError('');
    setFileError('');
  };

  const handleUpload = async () => {
    if (!file || !title.trim() || !courseId) return;
    setUploading(true);
    setUploadProgress(0);
    setError('');
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title.trim());
    formData.append('course_id', courseId);
    if (description) formData.append('description', description);
    if (moduleOrder.trim()) formData.append('module_order', moduleOrder.trim());

    try {
      const res = await uploadMaterial(formData, setUploadProgress);
      setSuccess({
        status: res.status,
        message:
          res.status === 'pending_review'
            ? 'Your material is pending admin review and will appear in the course curriculum once approved.'
            : 'Your material is now live in the course curriculum.',
      });
      qc.invalidateQueries({ queryKey: ['my-uploads'] });
    } catch (e) {
      if (axios.isAxiosError(e)) {
        const detail = e.response?.data?.detail;
        setError(typeof detail === 'string' ? detail : 'Upload failed. Please try again.');
      } else {
        setError('Upload failed. Please try again.');
      }
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (material: UploadedMaterial) => {
    if (!window.confirm('Delete this material? This cannot be undone.')) return;
    try {
      await deleteMaterial(material.id);
      qc.invalidateQueries({ queryKey: ['my-uploads'] });
      toast('Material deleted', 'success');
    } catch {
      toast('Could not delete material', 'error');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-extrabold tracking-tight">Upload Learning Material</h1>
        <p className="mt-1 text-text-secondary">
          Upload materials linked to a specific course. They become curriculum modules once approved.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <h2 className="text-[18px] font-bold">Upload New Material</h2>

          {success ? (
            <div className="mt-6 flex flex-col items-center py-8 text-center">
              <CheckCircle2 className="h-12 w-12 text-teal" />
              <p className="mt-4 text-[18px] font-bold">Material uploaded successfully!</p>
              <p className="mt-2 max-w-sm text-[14px] text-text-secondary">{success.message}</p>
              <Button type="button" className="mt-6" onClick={resetForm}>
                Upload Another
              </Button>
            </div>
          ) : (
            <>
              <div
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragOver(false);
                  pickFile(e.dataTransfer.files[0] ?? null);
                }}
                onClick={() => inputRef.current?.click()}
                className={cn(
                  'mt-4 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-12 transition-colors',
                  dragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50',
                )}
              >
                <UploadCloud className="h-12 w-12 text-primary/60" />
                <p className="mt-4 font-semibold">Drag and drop your file here</p>
                <p className="text-[14px] text-text-muted">or click to browse</p>
                <p className="mt-2 text-[12px] text-text-muted">PDF, MP4, DOCX, PPTX, MP3, TXT up to 50MB</p>
                <input
                  ref={inputRef}
                  type="file"
                  className="hidden"
                  accept={ACCEPTED_EXTENSIONS.join(',')}
                  onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
                />
              </div>

              {fileError && <p className="mt-2 text-[13px] text-error">{fileError}</p>}

              {file && (
                <div className="mt-4 space-y-4">
                  <Input label="Title *" placeholder="e.g. Introduction to Contract Law" value={title} onChange={(e) => setTitle(e.target.value)} />

                  <div>
                    <label className="text-[13px] text-text-muted">Course *</label>
                    <select
                      className="mt-1 w-full rounded-lg border border-border bg-input px-3 py-2 text-[14px]"
                      value={courseId}
                      onChange={(e) => setCourseId(e.target.value)}
                      required
                    >
                      <option value="">Select a course</option>
                      {(coursesQ.data ?? []).map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.code} — {c.title} ({semesterLabel(c.semester)})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="text-[13px] text-text-muted">Module Order (optional)</label>
                    <input
                      type="number"
                      min={1}
                      className="mt-1 w-full rounded-lg border border-border bg-input px-3 py-2 text-[14px]"
                      value={moduleOrder}
                      onChange={(e) => setModuleOrder(e.target.value)}
                      placeholder="e.g. 1 (leave blank to add at the end)"
                    />
                    <p className="mt-1 text-xs text-text-muted">
                      Sets the position of this material in the course curriculum. Students unlock the next module after completing the previous one.
                    </p>
                  </div>

                  <div>
                    <label className="text-[13px] text-text-muted">Description</label>
                    <textarea
                      rows={3}
                      placeholder="Brief description of this material..."
                      className="mt-1 w-full rounded-lg border border-border bg-input px-3 py-2 text-[14px]"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                    />
                  </div>
                </div>
              )}

              {file && (
                <div className="mt-6">
                  <Button
                    type="button"
                    fullWidth
                    disabled={!file || !title.trim() || !courseId || uploading}
                    onClick={handleUpload}
                  >
                    {uploading ? `Uploading... ${uploadProgress}%` : 'Upload Material'}
                  </Button>
                  {uploading && (
                    <div className="mt-2">
                      <ProgressBar value={uploadProgress} />
                    </div>
                  )}
                  {error && (
                    <div className="mt-3 rounded-lg border border-error/30 bg-error-container px-4 py-3 text-[14px] text-error">
                      {error}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </Card>

        <Card className="p-6">
          <h2 className="text-[18px] font-bold">My Uploaded Materials</h2>
          <div className="mt-4 space-y-4">
            {myUploads.isLoading ? (
              <p className="text-[14px] text-text-muted">Loading…</p>
            ) : Object.keys(groupedByCourse).length === 0 ? (
              <p className="text-[14px] text-text-muted">You haven&apos;t uploaded any materials yet.</p>
            ) : (
              Object.entries(groupedByCourse).map(([courseLabel, items]) => (
                <div key={courseLabel}>
                  <h4 className="mb-2 text-sm font-semibold">{courseLabel}</h4>
                  {[...items]
                    .sort((a, b) => (a.module_order ?? 999) - (b.module_order ?? 999))
                    .map((m, i) => {
                      const { icon: Icon, color } = fileTypeIcon(m.file_type);
                      return (
                        <div key={m.id} className="mb-2 flex items-center gap-2 rounded-lg border border-border px-3 py-2">
                          <span className="w-6 text-xs text-text-muted">{m.module_order ?? i + 1}</span>
                          <Icon className={cn('h-4 w-4 shrink-0', color)} />
                          <div className="min-w-0 flex-1">
                            <div className="truncate text-sm font-medium">{m.title}</div>
                            <div className="text-[11px] text-text-muted">{formatDate(m.created_at)}</div>
                          </div>
                          {statusBadge(m.status)}
                          <button
                            type="button"
                            className="rounded p-1 text-text-muted hover:bg-card-hover"
                            onClick={() => downloadMaterial(m.id, m.original_name).catch(() => toast('Download failed', 'error'))}
                          >
                            <Download className="h-4 w-4" />
                          </button>
                          <button
                            type="button"
                            className="rounded p-1 text-error hover:bg-card-hover"
                            onClick={() => handleDelete(m)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      );
                    })}
                </div>
              ))
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

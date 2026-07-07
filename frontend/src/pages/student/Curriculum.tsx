import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckCircle2, Lock, Megaphone, Play, Sparkles } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { Tabs } from '@/components/ui/Tabs';
import { fetchCoursesByIds } from '@/api/courses';
import {
  fetchCurriculum,
  requestCurriculumUpdate,
  resolveModuleUrl,
  type CurriculumModule,
} from '@/api/curriculum';
import { startModuleSession } from '@/api/moduleSession';
import { openMaterialPreview, uploadIdFromContentItemId } from '@/api/upload';
import { getMe } from '@/api/auth';
import { listCourseAnnouncements } from '@/api/lecturerDashboard';
import { useAuth } from '@/hooks/useAuth';
import { useToastStore } from '@/components/ui/Toast';
import { cn } from '@/lib/utils';
import type { UniversityCourse } from '@/types';

function uiStatus(step: CurriculumModule): 'COMPLETED' | 'IN PROGRESS' | 'LOCKED' | 'NOT STARTED' {
  if (step.status === 'locked') return 'LOCKED';
  const pct = step.percent_complete ?? 0;
  if (pct >= 90) return 'COMPLETED';
  if (pct > 0 || step.status === 'in_progress') return 'IN PROGRESS';
  return 'NOT STARTED';
}

export default function Curriculum() {
  const { learnerId } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToastStore((s) => s.add);
  const qc = useQueryClient();
  const [tab, setTab] = useState('all');
  const [activeCourse, setActiveCourse] = useState<UniversityCourse | null>(null);
  const [continueLoading, setContinueLoading] = useState<string | null>(null);

  const meQ = useQuery({ queryKey: ['auth-me'], queryFn: getMe, enabled: !!learnerId });
  const enrolledIds = (meQ.data?.courses as string[] | undefined) ?? [];

  const enrolledDetailsQ = useQuery({
    queryKey: ['enrolled-details', enrolledIds],
    queryFn: () => fetchCoursesByIds(enrolledIds),
    enabled: enrolledIds.length > 0,
  });

  useEffect(() => {
    if (enrolledDetailsQ.data?.length && !activeCourse) {
      setActiveCourse(enrolledDetailsQ.data[0]);
    }
  }, [enrolledDetailsQ.data, activeCourse]);

  useEffect(() => {
    if (activeCourse?.id) {
      qc.invalidateQueries({ queryKey: ['curriculum', activeCourse.id] });
    }
  }, [activeCourse?.id, qc]);

  useEffect(() => {
    if ((location.state as { scrollToNext?: boolean } | null)?.scrollToNext) {
      qc.invalidateQueries({ queryKey: ['curriculum', activeCourse?.id] });
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [location.state, activeCourse?.id, qc, navigate, location.pathname]);

  const curriculumQ = useQuery({
    queryKey: ['curriculum', activeCourse?.id],
    queryFn: () => fetchCurriculum(learnerId!, activeCourse!.id),
    enabled: !!learnerId && !!activeCourse?.id,
    staleTime: 30_000,
  });

  const announcementsQ = useQuery({
    queryKey: ['course-announcements', activeCourse?.id],
    queryFn: () => listCourseAnnouncements(activeCourse!.id),
    enabled: !!activeCourse?.id,
  });

  const refresh = useMutation({
    mutationFn: () => requestCurriculumUpdate(learnerId!, activeCourse!.id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['curriculum', activeCourse?.id] });
      toast('Update requested. Refreshing curriculum...', 'info');
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ['curriculum', activeCourse?.id] });
      }, 5000);
    },
    onError: () => toast('Could not generate update right now.', 'error'),
  });

  const handleContinue = async (module: CurriculumModule) => {
    const contentItemId = module.content_item_id || module.item_id;
    if (!contentItemId) return;
    setContinueLoading(contentItemId);
    try {
      const res = await startModuleSession(contentItemId);
      navigate('/student/ai-assistant', {
        state: {
          moduleSession: {
            sessionId: res.session_id,
            stage: res.stage,
            courseCode: activeCourse?.course_code ?? '',
            moduleTitle: module.title ?? 'Module',
            pdfUrl: res.pdf_url,
            contentItemId,
            courseId: activeCourse?.id,
            initialMessage: res.message,
            initialOnboarding: res.options?.length
              ? {
                  options: res.options,
                  question: res.question,
                  onboardingStep: res.onboarding_step,
                }
              : undefined,
            awaitingCustomText: res.awaiting_custom_text,
            tasks: res.tasks,
            redirectToQuiz: res.redirect_to_quiz,
            quizTopic: res.topic,
            explanationProgress: res.explanation_progress,
            totalTopics: res.total_topics,
          },
        },
      });
    } catch {
      toast('Could not start module session', 'error');
    } finally {
      setContinueLoading(null);
    }
  };

  const handleViewPdf = async (module: CurriculumModule) => {
    const contentItemId = module.content_item_id || module.item_id;
    const sourceType = (module.source_type || '').toLowerCase();
    const sourceUrl = module.source_url;

    if (sourceType === 'pdf' || sourceType === 'document' || sourceType === 'slides') {
      const uploadId = uploadIdFromContentItemId(contentItemId);
      if (uploadId) {
        try {
          await openMaterialPreview(uploadId);
        } catch {
          toast('Could not open file', 'error');
        }
        return;
      }
    }

    if (sourceUrl) {
      window.open(resolveModuleUrl(sourceUrl), '_blank', 'noopener,noreferrer');
    }
  };

  const path = curriculumQ.data?.modules ?? [];
  const noCourseContent = curriculumQ.data?.status === 'not_generated';
  const subject = activeCourse?.course_title ?? 'Your Curriculum';

  const filteredPath = path.filter((step) => {
    if (tab === 'all') return true;
    const type = String(step.module_type ?? '').toLowerCase();
    if (tab === 'core') return type === 'core' || type === 'compulsory';
    if (tab === 'electives') return type === 'elective';
    if (tab === 'assessments') return type === 'assessment' || type === 'quiz';
    return false;
  });

  const isLoading = curriculumQ.isLoading || meQ.isLoading || enrolledDetailsQ.isLoading;

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
      {enrolledDetailsQ.data && enrolledDetailsQ.data.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {enrolledDetailsQ.data.map((course) => (
            <button
              key={course.id}
              type="button"
              onClick={() => setActiveCourse(course)}
              className={cn(
                'rounded-full border px-4 py-2 text-sm font-semibold transition-all',
                activeCourse?.id === course.id
                  ? 'border-blue-600 bg-blue-600 text-white'
                  : 'border-gray-200 bg-white text-gray-700 hover:border-gray-400',
              )}
            >
              {course.course_code}
              <span className="ml-2 text-xs opacity-70">{course.course_title}</span>
            </button>
          ))}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <Badge variant="muted">CURRICULUM</Badge>
          <h1 className="mt-2 text-[28px] font-extrabold">{subject}</h1>
          <p className="text-text-secondary">Course modules with per-module progress tracking.</p>
        </div>
        <Button variant="secondary" disabled={refresh.isPending || !activeCourse} onClick={() => refresh.mutate()}>
          {refresh.isPending ? 'Updating...' : 'Request AI Update'}
        </Button>
      </div>

      {curriculumQ.data?.source === 'lecturer_materials' && (
        <div className="inline-flex items-center gap-2 rounded-lg bg-green-50 px-3 py-1.5 text-xs text-green-600">
          <CheckCircle2 className="h-3.5 w-3.5" />
          Materials provided by your lecturer
        </div>
      )}
      {curriculumQ.data?.source === 'external_supplemental' && (
        <div className="inline-flex items-center gap-2 rounded-lg bg-blue-50 px-3 py-1.5 text-xs text-blue-600">
          <Sparkles className="h-3.5 w-3.5" />
          AI-curated resources (your lecturer hasn&apos;t uploaded materials yet)
        </div>
      )}

      {(announcementsQ.data?.length ?? 0) > 0 && (
        <Card className="border-primary/20 bg-primary/5 p-4">
          <div className="mb-3 flex items-center gap-2">
            <Megaphone className="h-4 w-4 text-primary" />
            <h2 className="text-[15px] font-bold">Course announcements</h2>
          </div>
          <div className="space-y-3">
            {announcementsQ.data!.map((a) => (
              <div key={a.id} className="rounded-lg border border-border bg-card px-4 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold">{a.title}</span>
                  {a.is_pinned && <Badge variant="primary">Pinned</Badge>}
                </div>
                <p className="mt-1 whitespace-pre-wrap text-[14px] text-text-secondary">{a.body}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Tabs
        active={tab}
        onChange={setTab}
        tabs={[
          { id: 'all', label: 'All Steps' },
          { id: 'core', label: 'Core Modules' },
          { id: 'electives', label: 'Electives' },
          { id: 'assessments', label: 'Assessments' },
        ]}
      />

      <div className="space-y-4">
        {curriculumQ.isFetching && !curriculumQ.isLoading ? (
          <p className="text-sm text-text-muted">Loading curriculum for {activeCourse?.course_code}…</p>
        ) : null}

        {noCourseContent ? (
          <div className="py-16 text-center">
            <Lock className="mx-auto mb-3 h-12 w-12 text-gray-300" />
            <h3 className="font-semibold text-gray-700">
              Curriculum not yet generated for {activeCourse?.course_code ?? 'your course'}
            </h3>
            <p className="mt-1 text-sm text-gray-400">
              Content for this course is being prepared. Try the &quot;Request AI Update&quot; button or check back later.
            </p>
          </div>
        ) : filteredPath.length === 0 ? (
          <Card className="p-8 text-center text-text-secondary">
            Take a quiz or complete onboarding to generate your adaptive path.
          </Card>
        ) : (
          filteredPath.map((step, i) => {
            const title = String(step.title ?? `Step ${i + 1}`);
            const contentItemId = step.content_item_id || step.item_id;
            const pct = step.percent_complete ?? 0;
            const status = uiStatus(step);
            return (
              <div key={String(contentItemId ?? i)} className="flex gap-4">
                <div className="flex flex-col items-center">
                  {status === 'COMPLETED' && <CheckCircle2 className="h-6 w-6 text-teal" />}
                  {status === 'IN PROGRESS' && <Play className="h-6 w-6 text-primary" />}
                  {status === 'LOCKED' && <Lock className="h-6 w-6 text-text-muted" />}
                  {i < filteredPath.length - 1 && <div className="mt-2 w-px flex-1 bg-border" />}
                </div>
                <Card className={cn('relative flex-1 p-6', status === 'LOCKED' && 'opacity-60')}>
                  {status === 'LOCKED' && <Lock className="absolute right-4 top-4 h-4 w-4 text-text-muted" />}
                  <div className="flex items-start justify-between">
                    <Badge variant={status === 'COMPLETED' ? 'teal' : status === 'IN PROGRESS' ? 'primary' : 'muted'}>
                      {status.replace(' ', ' ')}
                    </Badge>
                    <span className="label-caps text-text-muted">MODULE {step.module_number ?? i + 1}</span>
                  </div>
                  <h3 className="mt-2 text-[18px] font-bold">{title}</h3>
                  <p className="mt-1 text-[14px] text-text-secondary">
                    {String(step.description || step.objective || 'Study and practice')}
                  </p>

                  {status === 'COMPLETED' && (
                    <p className="mt-3 flex items-center gap-2 text-[14px] text-teal">
                      <CheckCircle2 className="h-4 w-4" /> Progress: {pct}%
                    </p>
                  )}

                  {status === 'IN PROGRESS' && (
                    <div className="mt-4">
                      <div className="mb-1 flex justify-between text-[13px]">
                        <span>Progress</span>
                        <span>{pct}%</span>
                      </div>
                      <div className="h-[5px] w-full overflow-hidden rounded-full bg-border">
                        <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
                      </div>
                      <div className="mt-4 flex flex-wrap items-center gap-3">
                        <Button
                          disabled={continueLoading === contentItemId}
                          onClick={() => handleContinue(step)}
                        >
                          {continueLoading === contentItemId ? 'Starting…' : 'Continue →'}
                        </Button>
                        {(step.source_url ||
                          uploadIdFromContentItemId(contentItemId) ||
                          ['pdf', 'document', 'slides'].includes(
                            String(step.source_type ?? '').toLowerCase(),
                          )) && (
                          <button
                            type="button"
                            onClick={() => handleViewPdf(step)}
                            className="text-xs text-text-muted underline hover:text-text-secondary"
                          >
                            View PDF
                          </button>
                        )}
                      </div>
                    </div>
                  )}

                  {status === 'NOT STARTED' && (
                    <div className="mt-4">
                      <Button
                        disabled={continueLoading === contentItemId}
                        onClick={() => handleContinue(step)}
                      >
                        {continueLoading === contentItemId ? 'Starting…' : 'Start Module →'}
                      </Button>
                    </div>
                  )}

                  {status === 'NOT STARTED' && (
                    <div className="mt-4">
                      <Button
                        disabled={continueLoading === contentItemId}
                        onClick={() => handleContinue(step)}
                      >
                        {continueLoading === contentItemId ? 'Starting…' : 'Start Module →'}
                      </Button>
                    </div>
                  )}

                  {status === 'LOCKED' && (
                    <p className="mt-4 text-[13px] text-text-muted">Complete the previous module to unlock.</p>
                  )}

                  {status !== 'LOCKED' && contentItemId && (
                    <div className="mt-4 flex gap-2">
                      <Link
                        to={`/student/quiz/${encodeURIComponent(activeCourse?.course_title ?? title)}?content_item_id=${encodeURIComponent(contentItemId)}`}
                      >
                        <Button variant="secondary">Take Quiz</Button>
                      </Link>
                    </div>
                  )}
                </Card>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

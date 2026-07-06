import { useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Check, ChevronDown, X } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { useAuth } from '@/hooks/useAuth';
import {
  generateQuiz,
  submitQuiz,
  gradeShortAnswer,
  type QuizGenerateResponse,
  type QuizSubmitResponse,
} from '@/api/quiz';
import { completeModuleSession } from '@/api/moduleSession';
import type { MixedQuizData } from '@/api/moduleSession';
import { useToastStore } from '@/components/ui/Toast';
import { cn } from '@/lib/utils';

type Step = 'start' | 'question' | 'short_answer' | 'review' | 'results';

interface ShortAnswerResult {
  question_id: string;
  score: number;
  feedback: string;
  points_missed?: string[];
}

interface LocationQuizState {
  moduleSessionId?: string;
  contentItemId?: string;
  quizData?: MixedQuizData;
  quizId?: string;
}

function extractErrorMessage(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (detail && typeof detail === 'object' && 'detail' in detail) {
      const nested = (detail as { detail?: string }).detail;
      if (typeof nested === 'string') return nested;
    }
    return err.message || fallback;
  }
  if (err instanceof Error) return err.message;
  return fallback;
}

export default function Quiz() {
  const { topic = 'General' } = useParams();
  const [searchParams] = useSearchParams();
  const contentItemId = searchParams.get('content_item_id') ?? undefined;
  const location = useLocation();
  const locState = (location.state as LocationQuizState | null) ?? {};
  const moduleSessionId = locState.moduleSessionId;
  const moduleContentItemId = locState.contentItemId ?? contentItemId;
  const mixedQuiz = locState.quizData;
  const moduleQuizId = locState.quizId;
  const isMixedModuleQuiz = Boolean(mixedQuiz?.mcq?.length);

  const decodedTopic = decodeURIComponent(topic);
  const { learnerId } = useAuth();
  const navigate = useNavigate();
  const toast = useToastStore((s) => s.add);

  const [step, setStep] = useState<Step>('start');
  const [generating, setGenerating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [quiz, setQuiz] = useState<QuizGenerateResponse | null>(null);
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [shortAnswers, setShortAnswers] = useState<Record<string, string>>({});
  const [shortAnswerResults, setShortAnswerResults] = useState<ShortAnswerResult[]>([]);
  const [mixedMcqCorrect, setMixedMcqCorrect] = useState(0);
  const [times, setTimes] = useState<Record<string, number>>({});
  const [results, setResults] = useState<QuizSubmitResponse | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [moduleCompleted, setModuleCompleted] = useState(false);
  const [nextModule, setNextModule] = useState<{
    content_item_id: string;
    title: string;
    module_number: number;
  } | null>(null);
  const qStart = useRef(Date.now());

  const mcqCount = isMixedModuleQuiz ? mixedQuiz!.mcq.length : quiz?.questions.length ?? 0;
  const shortCount = mixedQuiz?.short_answer?.length ?? 0;

  const start = async () => {
    if (!learnerId) {
      toast('Sign in as a student to take a quiz.', 'error');
      return;
    }
    setGenerating(true);
    setLoadError(null);
    try {
      if (isMixedModuleQuiz && mixedQuiz) {
        setQuiz({
          quiz_id: moduleQuizId ?? `mixed-${Date.now()}`,
          topic: decodedTopic,
          questions: mixedQuiz.mcq.map((q) => ({
            question_id: q.id,
            question_text: q.question,
            options: q.options,
            difficulty: 'medium' as const,
          })),
        });
        setIndex(0);
        setAnswers({});
        setShortAnswers({});
        setShortAnswerResults([]);
        setStep('question');
        qStart.current = Date.now();
        return;
      }

      const data = await generateQuiz(learnerId, decodedTopic);
      if (!data.questions?.length) {
        throw new Error('No questions were generated for this topic.');
      }
      setQuiz(data);
      setIndex(0);
      setAnswers({});
      setTimes({});
      setStep('question');
      qStart.current = Date.now();
    } catch (err) {
      setLoadError(extractErrorMessage(err, 'Failed to load quiz'));
    } finally {
      setGenerating(false);
    }
  };

  const selectOption = (opt: number) => {
    if (!quiz) return;
    const q = quiz.questions[index];
    if (!q) return;
    setAnswers((a) => ({ ...a, [q.question_id]: opt }));
  };

  const next = () => {
    if (!quiz) return;
    const q = quiz.questions[index];
    if (!q || answers[q.question_id] === undefined) return;
    const elapsed = Math.max(1, Math.round((Date.now() - qStart.current) / 1000));
    setTimes((t) => ({ ...t, [q.question_id]: elapsed }));
    if (index < quiz.questions.length - 1) {
      setIndex((i) => i + 1);
      qStart.current = Date.now();
    } else if (isMixedModuleQuiz && shortCount > 0) {
      setStep('short_answer');
    } else {
      setStep('review');
    }
  };

  const finish = async () => {
    if (!quiz || !learnerId) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      if (isMixedModuleQuiz && mixedQuiz) {
        let correct = 0;
        mixedQuiz.mcq.forEach((q) => {
          if (answers[q.id] === q.correct_index) correct += 1;
        });
        setMixedMcqCorrect(correct);

        const gradingResults: ShortAnswerResult[] = [];
        if (mixedQuiz.short_answer?.length && moduleContentItemId) {
          const graded = await Promise.all(
            mixedQuiz.short_answer.map(async (q) => {
              const r = await gradeShortAnswer({
                question: q.question,
                model_answer: q.model_answer,
                key_points: q.key_points,
                student_answer: shortAnswers[q.id] || '',
                content_item_id: moduleContentItemId,
              });
              return { ...r, question_id: q.id };
            }),
          );
          gradingResults.push(...graded);
        }
        setShortAnswerResults(gradingResults);
        setStep('results');

        if (moduleSessionId) {
          try {
            const completion = await completeModuleSession(moduleSessionId);
            setModuleCompleted(completion.stage === 'completed');
            setNextModule(completion.next_module ?? null);
          } catch {
            toast('Quiz submitted but module completion failed to sync', 'error');
          }
        }
        toast('Results ready.', 'success');
        return;
      }

      const responses = quiz.questions.map((q) => ({
        question_id: q.question_id,
        selected_option: answers[q.question_id] ?? 0,
        time_taken_seconds: times[q.question_id] ?? 1,
      }));
      const data = await submitQuiz(learnerId, quiz.quiz_id, responses, moduleContentItemId);
      setResults(data);
      setStep('results');
      if (moduleSessionId) {
        try {
          const completion = await completeModuleSession(moduleSessionId);
          setModuleCompleted(true);
          setNextModule(completion.next_module ?? null);
        } catch {
          toast('Quiz submitted but module completion failed to sync', 'error');
        }
      }
      toast('Results ready. Mastery updated.', 'success');
    } catch (err) {
      setSubmitError(extractErrorMessage(err, 'Failed to submit quiz'));
    } finally {
      setSubmitting(false);
    }
  };

  if (step === 'start') {
    return (
      <Card className="mx-auto max-w-xl p-8 text-center">
        <Badge variant="primary">{decodedTopic}</Badge>
        <h1 className="mt-4 text-[28px] font-extrabold">Topic Quiz</h1>
        <p className="mt-2 text-text-secondary">
          {isMixedModuleQuiz
            ? `${mcqCount} multiple choice · ${shortCount} short answer · ~10 minutes`
            : '5 questions · ~10 minutes estimated'}
        </p>
        {loadError && (
          <div className="mt-6 rounded-xl border border-error/30 bg-error/5 p-4 text-left">
            <p className="font-medium text-error">Failed to load quiz</p>
            <p className="mt-1 text-[14px] text-text-secondary">{loadError}</p>
            <Button type="button" className="mt-4" variant="secondary" onClick={start} disabled={generating}>
              Try Again
            </Button>
          </div>
        )}
        <Button className="mt-8" onClick={start} disabled={generating || !learnerId}>
          {generating ? 'Generating…' : 'Start Quiz'}
        </Button>
      </Card>
    );
  }

  if (step === 'question' && quiz) {
    const q = quiz.questions[index];
    if (!q) {
      return (
        <Card className="mx-auto max-w-xl p-8 text-center">
          <p className="text-error">This quiz has no questions.</p>
          <Button className="mt-4" onClick={() => setStep('start')}>
            Back
          </Button>
        </Card>
      );
    }
    const selected = answers[q.question_id];
    return (
      <div className="mx-auto max-w-2xl space-y-6">
        <div className="flex justify-between text-[13px] text-text-muted">
          <span>
            Question {index + 1} of {quiz.questions.length}
          </span>
          <Badge variant="muted">{q.difficulty}</Badge>
        </div>
        <Card className="p-8">
          <h2 className="text-[20px] font-bold">{q.question_text}</h2>
          <div className="mt-6 space-y-3">
            {q.options.map((opt, i) => (
              <button
                key={i}
                type="button"
                onClick={() => selectOption(i)}
                className={cn(
                  'w-full cursor-pointer rounded-xl border bg-card p-4 text-left text-[15px] transition',
                  selected === i ? 'border-primary bg-primary/5 font-medium' : 'border-border hover:border-primary/40 hover:bg-card-hover',
                )}
              >
                <span className="mr-3 font-medium text-text-muted">{String.fromCharCode(65 + i)}.</span>
                {opt}
              </button>
            ))}
          </div>
          <Button className="mt-6" disabled={selected === undefined} onClick={next}>
            {index < quiz.questions.length - 1 ? 'Next' : shortCount > 0 ? 'Short Answer Questions' : 'Review Answers'}
          </Button>
        </Card>
      </div>
    );
  }

  if (step === 'short_answer' && mixedQuiz?.short_answer?.length) {
    return (
      <div className="mx-auto max-w-2xl space-y-6">
        <h2 className="text-[22px] font-bold">Short Answer Questions</h2>
        <p className="text-text-secondary">Type your understanding — answers are AI-graded.</p>
        {mixedQuiz.short_answer.map((q) => (
          <Card key={q.id} className="space-y-3 p-5">
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                Short Answer
              </span>
              <span className="text-xs text-text-secondary">Type your understanding</span>
            </div>
            <p className="text-sm font-medium">{q.question}</p>
            <textarea
              value={shortAnswers[q.id] || ''}
              onChange={(e) => setShortAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))}
              rows={4}
              placeholder="Write your answer here..."
              className="w-full resize-none rounded-lg border border-border bg-input p-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </Card>
        ))}
        {submitError && (
          <div className="rounded-xl border border-error/30 bg-error/5 p-4">
            <p className="font-medium text-error">Failed to submit quiz</p>
            <p className="mt-1 text-[14px] text-text-secondary">{submitError}</p>
          </div>
        )}
        <Button onClick={finish} disabled={submitting}>
          {submitting ? 'Grading…' : 'Submit Quiz'}
        </Button>
      </div>
    );
  }

  if (step === 'review' && quiz) {
    return (
      <div className="mx-auto max-w-2xl space-y-6">
        <h2 className="text-[22px] font-bold">Submit for results?</h2>
        <p className="text-text-secondary">You answered all {quiz.questions.length} questions.</p>
        {submitError && (
          <div className="rounded-xl border border-error/30 bg-error/5 p-4">
            <p className="font-medium text-error">Failed to submit quiz</p>
            <p className="mt-1 text-[14px] text-text-secondary">{submitError}</p>
          </div>
        )}
        {quiz.questions.map((q, i) => (
          <Card key={q.question_id} className="p-4">
            <div className="text-[13px] text-text-muted">Q{i + 1}</div>
            <div className="font-medium">{q.question_text}</div>
            <div className="mt-2 text-[14px] text-text-secondary">
              Your answer: {q.options[answers[q.question_id] ?? 0]}
            </div>
          </Card>
        ))}
        <Button onClick={finish} disabled={submitting}>
          {submitting ? 'Submitting…' : 'Submit'}
        </Button>
      </div>
    );
  }

  if (step === 'results' && isMixedModuleQuiz && mixedQuiz) {
    const totalMcq = mixedQuiz.mcq.length;
    const avgShort =
      shortAnswerResults.length > 0
        ? Math.round(shortAnswerResults.reduce((s, r) => s + r.score, 0) / shortAnswerResults.length)
        : 0;

    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <Card className="p-8 text-center">
          {moduleCompleted && (
            <p className="mb-4 font-semibold text-teal">Module complete! Your curriculum has been updated.</p>
          )}
          <div className="text-[48px] font-extrabold">
            {mixedMcqCorrect}/{totalMcq}
          </div>
          <div className="text-text-secondary">
            MCQ score · Short answer avg: {avgShort}/100
          </div>
        </Card>

        <div className="space-y-3">
          {mixedQuiz.mcq.map((q) => {
            const selected = answers[q.id];
            const correct = selected === q.correct_index;
            return (
              <Card key={q.id} className={cn('border-l-4 p-4', correct ? 'border-l-teal' : 'border-l-error')}>
                <div className="flex items-start gap-2">
                  {correct ? <Check className="h-5 w-5 text-teal" /> : <X className="h-5 w-5 text-error" />}
                  <div>
                    <div className="font-medium">{q.question}</div>
                    {q.explanation && (
                      <p className="mt-2 text-[14px] text-text-secondary">{q.explanation}</p>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
          {shortAnswerResults.map((result) => (
            <Card key={result.question_id} className="space-y-2 p-4">
              <div
                className={cn(
                  'text-sm font-semibold',
                  result.score >= 70 ? 'text-teal' : 'text-amber-600',
                )}
              >
                Short Answer: {result.score}/100
              </div>
              <p className="text-sm text-text-secondary">{result.feedback}</p>
              {result.points_missed && result.points_missed.length > 0 && (
                <div className="text-xs text-error">Missed: {result.points_missed.join(', ')}</div>
              )}
            </Card>
          ))}
        </div>

        <div className="flex flex-wrap gap-3">
          {moduleCompleted && (
            <div className="w-full rounded-xl border border-teal-200 bg-teal-50 p-4 text-center">
              <p className="font-semibold text-teal-800">Module complete!</p>
              {nextModule ? (
                <Button
                  className="mt-3"
                  onClick={() => navigate('/student/curriculum', { state: { scrollToNext: true } })}
                >
                  Continue to Module {nextModule.module_number}: {nextModule.title} →
                </Button>
              ) : (
                <Button className="mt-3" onClick={() => navigate('/student/curriculum')}>
                  Back to Curriculum →
                </Button>
              )}
            </div>
          )}
          <Link to="/student/curriculum">
            <Button variant="ghost">Back to Curriculum</Button>
          </Link>
        </div>
      </div>
    );
  }

  if (step === 'results' && results) {
    const mu = results.mastery_update;
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <Card className="p-8 text-center">
          {moduleCompleted && (
            <p className="mb-4 font-semibold text-teal">Module complete! Your curriculum has been updated.</p>
          )}
          <div className="text-[48px] font-extrabold">
            {results.score}/{results.total}
          </div>
          <div className="text-text-secondary">{Math.round(results.percentage)}% · {results.time_taken_seconds}s total</div>
        </Card>

        {results.mastery_update && (
          <Card className="p-4">
            <h3 className="mb-3 text-sm font-bold uppercase tracking-wide text-gray-500">Knowledge Model Updated</h3>
            <div className="flex items-center justify-between">
              <div className="text-center">
                <p className="text-2xl font-extrabold text-gray-400">
                  {Math.round(results.mastery_update.previous_mastery * 100)}%
                </p>
                <p className="text-xs text-gray-400">Before quiz</p>
              </div>
              <div className="flex items-center gap-1">
                <div className="h-px w-8 bg-gray-200" />
                {results.mastery_update.new_mastery > results.mastery_update.previous_mastery ? (
                  <span className="text-lg font-bold text-green-500">↑</span>
                ) : (
                  <span className="text-lg font-bold text-red-400">↓</span>
                )}
                <div className="h-px w-8 bg-gray-200" />
              </div>
              <div className="text-center">
                <p
                  className={cn(
                    'text-2xl font-extrabold',
                    results.mastery_update.new_mastery > results.mastery_update.previous_mastery
                      ? 'text-green-600'
                      : 'text-red-500',
                  )}
                >
                  {Math.round(results.mastery_update.new_mastery * 100)}%
                </p>
                <p className="text-xs text-gray-400">After quiz</p>
              </div>
            </div>
            <p className="mt-3 text-center text-xs text-gray-400">
              Your knowledge model updated based on your quiz performance using Bayesian Knowledge Tracing.
            </p>
          </Card>
        )}

        <Card className="p-6">
          <h3 className="font-bold">BKT Parameters</h3>
          <div className="mt-4 space-y-2 text-[14px]">
            <div>Initial Mastery (p_L0): {Math.round(mu.bkt_params.p_l0 * 100)}%</div>
            <div>Learning Rate (p_T): {Math.round(mu.bkt_params.p_t * 100)}% per attempt</div>
            <div>Slip Probability (p_S): {Math.round(mu.bkt_params.p_s * 100)}%</div>
            <div>Guess Probability (p_G): {Math.round(mu.bkt_params.p_g * 100)}%</div>
          </div>
          <div className="mt-4 text-[32px] font-extrabold text-teal">{Math.round(mu.new_mastery * 100)}%</div>
        </Card>

        <div className="space-y-3">
          {results.results.map((r) => (
            <Card
              key={r.question_id}
              className={cn('border-l-4 p-4', r.is_correct ? 'border-l-teal' : 'border-l-error')}
            >
              <div className="flex items-start gap-2">
                {r.is_correct ? <Check className="h-5 w-5 text-teal" /> : <X className="h-5 w-5 text-error" />}
                <div className="flex-1">
                  <div className="line-clamp-2 font-medium">{r.question_text}</div>
                  <button
                    type="button"
                    className="mt-2 flex items-center gap-1 text-[13px] text-primary"
                    onClick={() => setExpanded(expanded === r.question_id ? null : r.question_id)}
                  >
                    Explanation <ChevronDown className="h-4 w-4" />
                  </button>
                  {expanded === r.question_id && (
                    <p className="mt-2 text-[14px] text-text-secondary">{r.explanation}</p>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>

        <div className="flex flex-wrap gap-3">
          {moduleCompleted && (
            <div className="w-full rounded-xl border border-teal-200 bg-teal-50 p-4 text-center">
              <p className="font-semibold text-teal-800">Module complete!</p>
              {nextModule ? (
                <Button
                  className="mt-3"
                  onClick={() => navigate('/student/curriculum', { state: { scrollToNext: true } })}
                >
                  Continue to Module {nextModule.module_number}: {nextModule.title} →
                </Button>
              ) : (
                <Button className="mt-3" onClick={() => navigate('/student/curriculum')}>
                  Back to Curriculum →
                </Button>
              )}
            </div>
          )}
          <Button
            onClick={() => {
              setStep('start');
              setQuiz(null);
              setResults(null);
              setIndex(0);
              setAnswers({});
              setLoadError(null);
              setModuleCompleted(false);
              setNextModule(null);
            }}
          >
            Practice Again
          </Button>
          <Button variant="secondary" onClick={() => navigate('/student/library')}>
            View Recommendations
          </Button>
          <Link to="/student/curriculum">
            <Button variant="ghost">Back to Curriculum</Button>
          </Link>
        </div>
      </div>
    );
  }

  return null;
}

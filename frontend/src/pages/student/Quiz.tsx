import { useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Check, ChevronDown, X } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { useAuth } from '@/hooks/useAuth';
import { generateQuiz, submitQuiz, type QuizGenerateResponse, type QuizSubmitResponse } from '@/api/quiz';
import { useToastStore } from '@/components/ui/Toast';
import { cn } from '@/lib/utils';

type Step = 'start' | 'question' | 'review' | 'results';

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
  const [times, setTimes] = useState<Record<string, number>>({});
  const [results, setResults] = useState<QuizSubmitResponse | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const qStart = useRef(Date.now());

  const start = async () => {
    if (!learnerId) {
      toast('Sign in as a student to take a quiz.', 'error');
      return;
    }
    setGenerating(true);
    setLoadError(null);
    try {
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
    } else {
      setStep('review');
    }
  };

  const finish = async () => {
    if (!quiz || !learnerId) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const responses = quiz.questions.map((q) => ({
        question_id: q.question_id,
        selected_option: answers[q.question_id] ?? 0,
        time_taken_seconds: times[q.question_id] ?? 1,
      }));
      const data = await submitQuiz(learnerId, quiz.quiz_id, responses, contentItemId);
      setResults(data);
      setStep('results');
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
        <p className="mt-2 text-text-secondary">5 questions · ~10 minutes estimated</p>
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
            {index < quiz.questions.length - 1 ? 'Next' : 'Review Answers'}
          </Button>
        </Card>
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

  if (step === 'results' && results) {
    const mu = results.mastery_update;
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <Card className="p-8 text-center">
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
          <Button onClick={() => { setStep('start'); setQuiz(null); setResults(null); setIndex(0); setAnswers({}); setLoadError(null); }}>
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

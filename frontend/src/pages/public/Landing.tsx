import { Link } from 'react-router-dom';
import { AlertTriangle, ArrowRight, Brain, Check, GraduationCap, Sparkles, Target, TrendingUp, Zap } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { TiltCard } from '@/components/ui/TiltCard';

const features = [
  { icon: Sparkles, title: 'Conversational AI Tutor', desc: 'Adaptive dialogue grounded in your mastery model.' },
  { icon: Target, title: 'Mastery Tracking', desc: 'Bayesian Knowledge Tracing across every topic.' },
  { icon: Brain, title: 'Personalized Resources', desc: 'Ranked content matched to gaps and modality.' },
  { icon: GraduationCap, title: 'Curriculum Mapping', desc: 'Align study paths with your university courses.' },
  { icon: Zap, title: 'Spaced Repetition', desc: 'Intelligent review scheduling for retention.' },
  { icon: Brain, title: 'Cognitive Analytics', desc: 'Radar and trajectory views of learning balance.' },
];

const masteryRows = [
  { name: 'Calculus II', value: 92 },
  { name: 'Organic Chemistry', value: 54 },
  { name: 'World History', value: 20, review: true },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-page">
      <nav className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-header px-4 py-3 sm:px-6 sm:py-4">
        <div className="flex min-w-0 items-center gap-2 sm:gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-white">
            <GraduationCap className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <div className="truncate font-bold text-text-primary">AITutor</div>
            <div className="truncate text-[12px] text-text-muted">Learning Intelligence</div>
          </div>
        </div>
        <div className="hidden gap-8 text-[14px] text-text-secondary md:flex">
          <a href="#features">Features</a>
          <a href="#how">How it Works</a>
        </div>
        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          <Link to="/login" className="whitespace-nowrap text-[13px] font-medium text-text-secondary sm:text-[14px]">
            Log In
          </Link>
          <Link to="/register">
            <Button className="whitespace-nowrap px-3 text-[13px] sm:px-4 sm:text-[14px]">Start Learning Free</Button>
          </Link>
        </div>
      </nav>

      <section className="page-grid px-6 py-20">
        <div className="mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-2">
          <div>
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-teal/30 bg-teal-container/20 px-3 py-1 text-[12px] font-semibold text-teal">
              <span className="h-2 w-2 rounded-full bg-teal" />
              New: AI-Powered Knowledge Tracking
            </div>
            <h1 className="text-[48px] font-extrabold leading-tight tracking-tight text-text-primary">
              Your personal AI tutor.
              <br />
              <span className="text-primary">Learns how you learn.</span>
            </h1>
            <p className="mt-4 max-w-xl text-[16px] leading-7 text-text-secondary">
              Experience adaptive learning powered by advanced cognitive models. AITutor continuously analyzes your
              mastery, identifying knowledge gaps and serving personalized resources exactly when you need them.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/register">
                <Button>
                  Start Learning Free <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Button variant="secondary">See How It Works</Button>
            </div>
            <div className="mt-6 flex flex-wrap gap-4 text-[13px] text-text-muted">
              <span className="flex items-center gap-1">
                <Check className="h-4 w-4 text-teal" /> No credit card required
              </span>
              <span className="flex items-center gap-1">
                <Check className="h-4 w-4 text-teal" /> Cancel anytime
              </span>
            </div>
          </div>

          <div className="relative flex items-center justify-center py-8">
            <div className="pointer-events-none absolute right-0 top-1/2 h-56 w-56 -translate-y-1/2 rounded-full border border-primary/10" />
            <div className="pointer-events-none absolute bottom-0 right-8 h-32 w-32 rounded-full border border-border/60" />

            <TiltCard className="w-full max-w-md">
              <Card className="relative p-8 shadow-card">
                <h3 className="text-[18px] font-bold text-text-primary">Knowledge Mastery</h3>
                {masteryRows.map((row) => (
                  <div key={row.name} className="mt-5">
                    <div className="mb-1.5 flex justify-between text-[13px]">
                      <span className="font-medium text-text-primary">{row.name}</span>
                      <span className="font-bold text-text-primary">{row.value}%</span>
                    </div>
                    <ProgressBar value={row.value} className="h-2" />
                    {row.review && (
                      <div className="mt-1.5 flex items-center gap-1 text-[11px] font-semibold text-error">
                        <AlertTriangle className="h-3 w-3" />
                        Review Needed
                      </div>
                    )}
                  </div>
                ))}

                <div
                  className="absolute -bottom-6 -left-4 rounded-xl border border-border bg-card px-4 py-3 shadow-card"
                  style={{ transform: 'translateZ(40px)' }}
                >
                  <div className="flex items-center gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal/10 text-teal">
                      <TrendingUp className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="text-[12px] font-semibold text-text-primary">Learning Velocity</div>
                      <div className="text-[13px] font-bold text-teal">+12% this week</div>
                    </div>
                  </div>
                </div>
              </Card>
            </TiltCard>
          </div>
        </div>
      </section>

      <section id="features" className="bg-page px-6 py-20">
        <div className="mx-auto max-w-6xl text-center">
          <h2 className="text-[28px] font-extrabold tracking-tight">Intelligence built for focus.</h2>
          <p className="mx-auto mt-2 max-w-2xl text-text-secondary">
            Everything you need to master complex subjects, structured in a distraction-free academic environment.
          </p>
          <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {features.map((f) => (
              <Card key={f.title} className="p-6 text-left">
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <f.icon className="h-5 w-5" />
                </div>
                <h3 className="text-[18px] font-bold">{f.title}</h3>
                <p className="mt-2 text-[14px] text-text-secondary">{f.desc}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section id="how" className="page-grid px-6 py-20">
        <div className="mx-auto max-w-4xl text-center">
          <h2 className="text-[28px] font-extrabold">The Learning Loop</h2>
          <p className="mt-2 text-text-secondary">A systematic approach to academic excellence.</p>
          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {['Diagnostic', 'Intervention', 'Update & Adapt'].map((step, i) => (
              <Card key={step} className="p-6">
                <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-lg border-2 border-primary text-[18px] font-extrabold text-primary">
                  {i + 1}
                </div>
                <h3 className="font-bold">{step}</h3>
              </Card>
            ))}
          </div>
        </div>
      </section>

    </div>
  );
}

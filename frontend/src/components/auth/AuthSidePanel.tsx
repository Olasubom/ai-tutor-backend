import { GraduationCap } from 'lucide-react';
import { localPlatform } from '@/api/localPlatform';
import type { TestimonialPanel } from '@/types';

interface AuthSidePanelProps {
  panel: TestimonialPanel;
}

export function AuthSidePanel({ panel }: AuthSidePanelProps) {
  const { quote, author, role } = localPlatform.getTestimonialForPanel(panel);

  return (
    <div className="page-grid relative hidden items-center justify-center overflow-hidden bg-[#f3f3fc] p-12 dark:bg-card lg:flex">
      <div className="pointer-events-none absolute -left-20 top-1/3 h-64 w-64 rounded-full bg-teal/10 blur-3xl" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-48 w-48 rounded-full border border-primary/10" />
      <div className="relative max-w-md text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-primary text-white shadow-card">
          <GraduationCap className="h-7 w-7" />
        </div>
        <div className="text-2xl font-bold text-text-primary">AITutor</div>

        <div className="mt-6 inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-2 shadow-card">
          <div className="flex -space-x-2">
            {['bg-primary', 'bg-teal', 'bg-warning'].map((c) => (
              <div key={c} className={`h-7 w-7 rounded-full border-2 border-card ${c}`} />
            ))}
          </div>
          <span className="text-[13px] font-medium text-text-secondary">Join 2,400+ learners</span>
        </div>

        <div className="mt-8 rounded-2xl border border-border bg-card p-6 text-left shadow-card">
          <div className="text-4xl font-bold leading-none text-primary">&ldquo;</div>
          <p className="mt-2 text-[16px] font-bold leading-relaxed text-text-primary">{quote}</p>
          <div className="mt-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-gradient-to-br from-primary to-teal" />
            <div>
              <div className="text-[14px] font-bold text-text-primary">{author}</div>
              <div className="text-[12px] text-text-muted">{role}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

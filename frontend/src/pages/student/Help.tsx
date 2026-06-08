import { useState } from 'react';
import { BarChart2, BookOpen, ChevronDown, MessageSquare } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { cn } from '@/lib/utils';

const FAQ = [
  {
    q: 'How does the AI personalize my learning?',
    a: 'AITutor uses Bayesian Knowledge Tracing to model your understanding of each subject. After every quiz and conversation, it updates your mastery probability and adjusts what it recommends to target your specific gaps.',
  },
  {
    q: 'What is the Curriculum page?',
    a: 'The Curriculum page shows your AI-generated learning path for each subject. Modules unlock sequentially as your mastery improves. Click Continue on an in-progress module to pick up where you left off.',
  },
  {
    q: 'What is the Recommendations page?',
    a: 'The Recommendations page shows videos, articles, ebooks and quizzes selected by the AI specifically for you, based on your weakest topics and your preferred learning style.',
  },
  {
    q: 'How do I start a quiz?',
    a: 'Go to the Curriculum page, open any module, and click the Take Quiz button. Quiz results automatically update your knowledge model.',
  },
  {
    q: 'Why is my mastery percentage low?',
    a: 'The AI starts conservatively and increases your mastery as you demonstrate understanding through quizzes and sessions. Low scores are expected when you are new.',
  },
  {
    q: 'How do I change my enrolled courses?',
    a: 'Go to Settings → My Courses. You can remove existing courses or add new ones from your department.',
  },
  {
    q: 'What happens if I click Log Out?',
    a: 'Your session ends and you return to the login page. All your progress is saved and will be there when you log back in.',
  },
];

export default function Help() {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-[28px] font-extrabold">Help & Guide</h1>
        <p className="text-text-secondary">Everything you need to know about using AITutor</p>
      </div>

      <section>
        <h2 className="mb-4 text-[18px] font-bold">Getting Started</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <Card className="p-6">
            <BookOpen className="mb-3 h-8 w-8 text-primary" />
            <h3 className="font-bold">Setting Up Your Profile</h3>
            <p className="mt-1 text-[14px] text-text-secondary">Complete onboarding to personalize your AI curriculum.</p>
          </Card>
          <Card className="p-6">
            <MessageSquare className="mb-3 h-8 w-8 text-primary" />
            <h3 className="font-bold">Using the AI Tutor</h3>
            <p className="mt-1 text-[14px] text-text-secondary">Ask questions, get explanations, and request study plans.</p>
          </Card>
          <Card className="p-6">
            <BarChart2 className="mb-3 h-8 w-8 text-primary" />
            <h3 className="font-bold">Tracking Your Progress</h3>
            <p className="mt-1 text-[14px] text-text-secondary">Your mastery updates automatically after every session.</p>
          </Card>
        </div>
      </section>

      <section>
        <h2 className="mb-4 text-[18px] font-bold">Frequently Asked Questions</h2>
        <div className="space-y-2">
          {FAQ.map((item, i) => (
            <Card key={item.q} className="overflow-hidden">
              <button
                type="button"
                className="flex w-full items-center justify-between p-4 text-left font-semibold"
                onClick={() => setOpen(open === i ? null : i)}
              >
                {item.q}
                <ChevronDown className={cn('h-4 w-4 transition', open === i && 'rotate-180')} />
              </button>
              {open === i && <p className="border-t border-border px-4 pb-4 text-[14px] text-text-secondary">{item.a}</p>}
            </Card>
          ))}
        </div>
      </section>

      <Card className="p-6">
        <h2 className="text-[18px] font-bold">Contact Support</h2>
        <p className="mt-2 text-[14px] text-text-secondary">
          Need more help? Reach out to your department administrator or email support.
        </p>
        <a
          href="mailto:adebayo@fountain.edu.ng"
          className="mt-4 inline-flex rounded-lg border border-border px-4 py-2 text-[14px] font-semibold hover:bg-card-hover"
        >
          adebayo@fountain.edu.ng
        </a>
      </Card>
    </div>
  );
}

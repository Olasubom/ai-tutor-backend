import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { GraduationCap, Presentation } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

export default function Register() {
  const [role, setRole] = useState<'student' | 'lecturer' | null>(null);
  const navigate = useNavigate();

  return (
    <div className="page-grid flex min-h-screen items-center justify-center px-4 py-12">
      <Card className="w-full max-w-lg">
        <h1 className="text-[28px] font-extrabold tracking-tight">Create your account</h1>
        <p className="mt-2 text-text-secondary">Select your role to get started.</p>
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          {[
            {
              id: 'student' as const,
              icon: GraduationCap,
              title: 'Student',
              desc: 'Access personalized curriculum, AI tutor, and track your academic mastery.',
            },
            {
              id: 'lecturer' as const,
              icon: Presentation,
              title: 'Lecturer',
              desc: 'Manage your classes, monitor student progress, and access AI teaching tools.',
            },
          ].map((r) => (
            <button
              key={r.id}
              type="button"
              onClick={() => setRole(r.id)}
              className={cn(
                'rounded-xl border p-5 text-left transition-colors',
                role === r.id ? 'border-2 border-primary bg-primary/5' : 'border-border bg-card hover:bg-card-hover',
              )}
            >
              <r.icon className="mb-3 h-6 w-6 text-primary" />
              <div className="font-bold">{r.title}</div>
              <p className="mt-1 text-[13px] text-text-secondary">{r.desc}</p>
            </button>
          ))}
        </div>
        <Button
          fullWidth
          className="mt-6"
          disabled={!role}
          onClick={() => navigate(role === 'student' ? '/register/student' : '/register/lecturer')}
        >
          Continue
        </Button>
        <p className="mt-4 text-center text-[14px] text-text-muted">
          Already have an account?{' '}
          <Link to="/login" className="text-primary">
            Sign in
          </Link>
        </p>
      </Card>
    </div>
  );
}

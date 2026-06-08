import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Bell, Search } from 'lucide-react';
import { ThemeToggle } from '@/components/ui/Toggle';
import { Button } from '@/components/ui/Button';
import { Avatar } from '@/components/ui/Avatar';
import { useAuth } from '@/hooks/useAuth';
import { getNotifications } from '@/api/notifications';

interface HeaderProps {
  showSession?: boolean;
  onNewSession?: () => void;
}

export function Header({ showSession = true, onNewSession }: HeaderProps) {
  const { user, learnerId } = useAuth();
  const navigate = useNavigate();

  const { data: notifications } = useQuery({
    queryKey: ['notifications', learnerId],
    queryFn: () => getNotifications(learnerId),
    enabled: !!learnerId && user?.role === 'student',
    refetchInterval: 60_000,
  });

  const unread = (notifications ?? []).filter((n) => !n.is_read).length;

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-header px-6 backdrop-blur">
      <div className="relative w-full max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
        <input
          placeholder="Search curriculum..."
          className="w-full rounded-full border border-border bg-input py-2 pl-10 pr-4 text-[14px] focus:outline-none focus:ring-2 focus:ring-primary"
        />
      </div>
      <div className="hidden items-center gap-6 px-6 text-[14px] text-text-secondary md:flex">
        <button type="button" className="hover:text-primary" onClick={() => navigate('/student/curriculum')}>
          My Courses
        </button>
      </div>
      <div className="flex items-center gap-3">
        <ThemeToggle />
        {user?.role === 'student' && (
          <button
            type="button"
            className="relative rounded-lg p-2 hover:bg-card-hover"
            onClick={() => navigate('/student/notifications')}
          >
            <Bell className="h-5 w-5 text-text-secondary" />
            {unread > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-error px-1 text-[10px] font-bold text-white">
                {unread > 9 ? '9+' : unread}
              </span>
            )}
          </button>
        )}
        {showSession && (
          <Button
            onClick={() => {
              onNewSession?.();
              navigate('/student/ai-assistant');
            }}
          >
            New Session
          </Button>
        )}
        <button type="button" onClick={() => navigate('/student/settings')} className="rounded-full">
          <Avatar name={user?.name} size="sm" />
        </button>
      </div>
    </header>
  );
}

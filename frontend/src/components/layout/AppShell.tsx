import { useEffect } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { recordEngagement } from '@/api/engagement';
import { BookOpen, Bot, HelpCircle, LayoutDashboard, Library, LogOut, Settings } from 'lucide-react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { useAuth } from '@/hooks/useAuth';

const nav = [
  { to: '/student/dashboard', label: 'Dashboard', icon: <LayoutDashboard className="h-4 w-4" /> },
  { to: '/student/curriculum', label: 'Curriculum', icon: <BookOpen className="h-4 w-4" /> },
  { to: '/student/library', label: 'Recommendations', icon: <Library className="h-4 w-4" /> },
  { to: '/student/ai-assistant', label: 'AI Assistant', icon: <Bot className="h-4 w-4" /> },
  { to: '/student/settings', label: 'Settings', icon: <Settings className="h-4 w-4" /> },
  { to: '/student/help', label: 'Help', icon: <HelpCircle className="h-4 w-4" /> },
];

export function AppShell() {
  const { logout, learnerId } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!learnerId) return;
    recordEngagement(learnerId, 'page_view', { page: location.pathname }).catch(() => {});
  }, [learnerId, location.pathname]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleNewSession = () => {
    sessionStorage.setItem('aitutor_new_session', '1');
  };

  return (
    <div className="min-h-screen bg-page">
      <Sidebar
        items={nav}
        bottomItems={[
          { to: '#logout', label: 'Log out', icon: <LogOut className="h-4 w-4" />, onClick: handleLogout },
        ]}
      />
      <div className="ml-[260px]">
        <Header onNewSession={handleNewSession} />
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

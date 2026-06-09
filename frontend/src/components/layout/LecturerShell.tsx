import { Outlet, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, LayoutDashboard, LogOut, Settings, User, Users } from 'lucide-react';
import { Sidebar, type NavItem } from './Sidebar';
import { Header } from './Header';
import { useAuth } from '@/hooks/useAuth';
import { getAtRiskStudents } from '@/api/atRisk';
import { ensureLecturerProfile } from '@/api/lecturer';
import { useEffect } from 'react';

export function LecturerShell() {
  const { logout, user } = useAuth();
  const navigate = useNavigate();
  const lecturerId = user?.user_id ?? '';

  useEffect(() => {
    if (!user || user.role !== 'lecturer') return;
    ensureLecturerProfile(lecturerId, {
      name: user.name,
      department_id: '',
      faculty_id: '',
    }).catch(() => {
      /* backend may be offline */
    });
  }, [lecturerId, user]);

  const atRisk = useQuery({
    queryKey: ['at-risk', lecturerId],
    queryFn: () => getAtRiskStudents(lecturerId),
    enabled: !!lecturerId,
  });

  const alertCount = atRisk.data?.length ?? 0;

  const nav: NavItem[] = [
    { to: '/lecturer/dashboard', label: 'Dashboard', icon: <LayoutDashboard className="h-4 w-4" /> },
    { to: '/lecturer/students', label: 'Students', icon: <Users className="h-4 w-4" /> },
    {
      to: '/lecturer/at-risk',
      label: alertCount > 0 ? `AI Alerts (${alertCount})` : 'AI Alerts',
      icon: <AlertTriangle className="h-4 w-4 text-error" />,
    },
    { to: '/lecturer/settings', label: 'Settings', icon: <Settings className="h-4 w-4" /> },
  ];

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-page">
      <Sidebar
        subtitle="LECTURER PORTAL"
        items={nav}
        bottomItems={[
          { to: '/lecturer/settings', label: 'Profile', icon: <User className="h-4 w-4" /> },
          { to: '#logout', label: 'Log out', icon: <LogOut className="h-4 w-4" />, onClick: handleLogout },
        ]}
      />
      <div className="ml-[260px]">
        <Header showSession={false} />
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

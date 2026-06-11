import { Outlet, useNavigate } from 'react-router-dom';
import { FileText, LayoutDashboard, LogOut, Settings, Users } from 'lucide-react';
import { Sidebar, type NavItem } from './Sidebar';
import { useAuth } from '@/hooks/useAuth';

export function AdminShell() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const nav: NavItem[] = [
    { to: '/admin', label: 'Dashboard', icon: <LayoutDashboard className="h-4 w-4" /> },
    { to: '/admin/users', label: 'Users', icon: <Users className="h-4 w-4" /> },
    { to: '/admin/materials', label: 'Materials', icon: <FileText className="h-4 w-4" /> },
  ];

  const handleLogout = () => {
    logout();
    navigate('/admin/login');
  };

  return (
    <div className="min-h-screen bg-page">
      <Sidebar
        subtitle="ADMIN PORTAL"
        items={nav}
        bottomItems={[
          { to: '/admin', label: 'Settings', icon: <Settings className="h-4 w-4" /> },
          { to: '#logout', label: 'Log out', icon: <LogOut className="h-4 w-4" />, onClick: handleLogout },
        ]}
      />
      <div className="ml-[260px]">
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

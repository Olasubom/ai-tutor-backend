import { Outlet, useNavigate } from 'react-router-dom';
import { FileText, LayoutDashboard, LogOut, Settings, Users } from 'lucide-react';
import { Sidebar, type NavItem } from './Sidebar';
import { MenuButton } from './MenuButton';
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
      <div className="lg:ml-[260px]">
        <div className="sticky top-0 z-30 flex h-16 items-center border-b border-border bg-header px-3 lg:hidden sm:px-4">
          <MenuButton />
          <span className="ml-2 text-[14px] font-semibold text-text-primary">Admin Portal</span>
        </div>
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

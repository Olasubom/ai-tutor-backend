import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import type { UserRole } from '@/types';
import { getRedirectForRole } from '@/stores/authStore';

export function PublicRoute() {
  const { isAuthenticated, user } = useAuth();
  if (isAuthenticated && user) return <Navigate to={getRedirectForRole(user.role)} replace />;
  return <Outlet />;
}

function RoleRoute({ role }: { role: UserRole }) {
  const { isAuthenticated, user } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (user?.role !== role) return <Navigate to={getRedirectForRole(user!.role)} replace />;
  if (role === 'student' && user && !user.onboarding_complete) {
    return <Navigate to="/onboarding/step1" replace />;
  }
  return <Outlet />;
}

export const StudentRoute = () => <RoleRoute role="student" />;
export const LecturerRoute = () => <RoleRoute role="lecturer" />;
export const AdminRoute = () => <RoleRoute role="admin" />;

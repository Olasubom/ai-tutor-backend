import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ToastContainer } from '@/components/ui/Toast';
import { PublicRoute, StudentRoute, LecturerRoute, AdminRoute } from '@/components/routes/Guards';
import { useAuthStore, getRedirectForRole } from '@/stores/authStore';
import { AppShell } from '@/components/layout/AppShell';
import { LecturerShell } from '@/components/layout/LecturerShell';
import Landing from '@/pages/public/Landing';
import Login from '@/pages/auth/Login';
import Register from '@/pages/auth/Register';
import StudentRegister from '@/pages/auth/StudentRegister';
import LecturerRegister from '@/pages/auth/LecturerRegister';
import LecturerPending from '@/pages/auth/LecturerPending';
import AdminLogin from '@/pages/auth/AdminLogin';
import ForgotPassword from '@/pages/auth/ForgotPassword';
import OnboardingShell from '@/pages/onboarding/OnboardingShell';
import Step1Profile from '@/pages/onboarding/Step1Profile';
import Step2CurriculumFocus from '@/pages/onboarding/Step2CurriculumFocus';
import Step3KnowledgeAssessment from '@/pages/onboarding/Step3KnowledgeAssessment';
import Step4StudyPreferences from '@/pages/onboarding/Step4StudyPreferences';
import GeneratingModel from '@/pages/onboarding/GeneratingModel';
import Dashboard from '@/pages/student/Dashboard';
import AIAssistant from '@/pages/student/AIAssistant';
import Library from '@/pages/student/Library';
import Curriculum from '@/pages/student/Curriculum';
import Settings from '@/pages/student/Settings';
import Quiz from '@/pages/student/Quiz';
import Goals from '@/pages/student/Goals';
import Tasks from '@/pages/student/Tasks';
import Notifications from '@/pages/student/Notifications';
import Analytics from '@/pages/student/Analytics';
import LecturerDashboard from '@/pages/lecturer/Dashboard';
import LecturerStudents from '@/pages/lecturer/Students';
import LecturerSettings from '@/pages/lecturer/Settings';
import AtRisk from '@/pages/lecturer/AtRisk';
import UploadMaterial from '@/pages/lecturer/UploadMaterial';
import AdminDashboard from '@/pages/admin/Dashboard';
import AdminMaterials from '@/pages/admin/Materials';
import { AdminShell } from '@/components/layout/AdminShell';
import Help from '@/pages/student/Help';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
});

function NotFound() {
  const { isAuthenticated, role } = useAuthStore();
  if (isAuthenticated && role) {
    return <Navigate to={getRedirectForRole(role)} replace />;
  }
  return <Navigate to="/" replace />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<PublicRoute />}>
            <Route path="/" element={<Landing />} />
          </Route>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/register/student" element={<StudentRegister />} />
          <Route path="/register/lecturer" element={<LecturerRegister />} />
          <Route path="/register/lecturer/pending" element={<LecturerPending />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />

          <Route path="/admin/login" element={<AdminLogin />} />

          <Route path="/onboarding" element={<OnboardingShell />}>
            <Route index element={<Navigate to="step1" replace />} />
            <Route path="step1" element={<Step1Profile />} />
            <Route path="step2" element={<Step2CurriculumFocus />} />
            <Route path="step3" element={<Step3KnowledgeAssessment />} />
            <Route path="step4" element={<Step4StudyPreferences />} />
          </Route>
          <Route path="/onboarding/generating" element={<GeneratingModel />} />

          <Route element={<StudentRoute />}>
            <Route element={<AppShell />}>
              <Route path="/student/dashboard" element={<Dashboard />} />
              <Route path="/student/curriculum" element={<Curriculum />} />
              <Route path="/student/library" element={<Library />} />
              <Route path="/student/ai-assistant" element={<AIAssistant />} />
              <Route path="/student/quiz/:topic" element={<Quiz />} />
              <Route path="/student/goals" element={<Goals />} />
              <Route path="/student/tasks" element={<Tasks />} />
              <Route path="/student/notifications" element={<Notifications />} />
              <Route path="/student/analytics" element={<Analytics />} />
              <Route path="/student/settings" element={<Settings />} />
              <Route path="/student/help" element={<Help />} />
            </Route>
          </Route>

          <Route element={<LecturerRoute />}>
            <Route element={<LecturerShell />}>
              <Route path="/lecturer/dashboard" element={<LecturerDashboard />} />
              <Route path="/lecturer/upload" element={<UploadMaterial />} />
              <Route path="/lecturer/students" element={<LecturerStudents />} />
              <Route path="/lecturer/at-risk" element={<AtRisk />} />
              <Route path="/lecturer/settings" element={<LecturerSettings />} />
            </Route>
          </Route>

          <Route element={<AdminRoute />}>
            <Route element={<AdminShell />}>
              <Route path="/admin" element={<AdminDashboard />} />
              <Route path="/admin/materials" element={<AdminMaterials />} />
            </Route>
          </Route>

          <Route path="*" element={<NotFound />} />
        </Routes>
        <ToastContainer />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

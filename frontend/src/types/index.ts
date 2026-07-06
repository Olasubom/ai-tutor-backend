export type UserRole = 'student' | 'lecturer' | 'admin';

export type AccountStatus = 'active' | 'pending_verification' | 'suspended' | 'rejected';

export interface AuthUser {
  user_id: string;
  role: UserRole;
  name: string;
  email: string;
  status?: AccountStatus;
  learner_id?: string;
  staff_id?: string;
  college_id?: string;
  department_id?: string;
  onboarding_complete?: boolean;
}

export interface AuthTokenPayload {
  user_id: string;
  role: UserRole;
  name: string;
  email: string;
  exp: number;
}

export interface PerformanceEvent {
  topic: string;
  correct: boolean;
  metadata?: Record<string, unknown>;
}

export interface TutorChatRequest {
  learner_id: string;
  message: string;
  session_id?: string;
  course_context?: Record<string, unknown>;
  events?: PerformanceEvent[];
  time_budget_minutes?: number;
}

export interface TutorChatResponse {
  request_id: string;
  learner_id: string;
  assistant_message: string;
  session_id?: string;
  artifacts: Record<string, unknown>;
  timestamp: string;
}

export interface TutorRecommendRequest {
  learner_id: string;
  message?: string;
  course_context?: Record<string, unknown>;
  events?: PerformanceEvent[];
  limit?: number;
  use_agent?: boolean;
}

export interface Recommendation {
  item_id: string;
  topic?: string;
  title: string;
  description?: string;
  difficulty?: string;
  duration_minutes?: number;
  modality?: string;
  bloom_level?: string;
  source_type?: string;
  provider?: string;
  source_url?: string;
  score?: number;
  reasons?: string[];
  reason?: string;
  tags?: string[];
}

export interface TutorRecommendResponse {
  request_id: string;
  learner_id: string;
  source: string;
  recommendations: Recommendation[];
  adaptive_path: Array<Record<string, unknown>>;
  memory_used?: MemoryBundle;
  timestamp: string;
  status?: string;
  message?: string;
}

export interface LearnerProfileResponse {
  learner_id: string;
  profile: LearnerProfile;
  memory: MemoryBundle;
  timestamp: string;
}

export interface LearnerProfile {
  topic_mastery?: Record<string, { p_l?: number; attempts?: number }>;
  knowledge_state_summary?: KnowledgeStateSummary;
  preferences?: Record<string, unknown>;
  preferred_modalities?: string[];
  last_recommendations?: { recommendations?: Recommendation[]; adaptive_path?: unknown[] };
  study_plan?: Record<string, unknown>;
  tasks?: LearnerTask[];
  onboarding?: OnboardingData;
  total_study_hours?: number;
  modules_completed?: number;
  current_streak?: number;
  overall_mastery_percentage?: number;
}

export interface KnowledgeStateSummary {
  weak_topics?: string[];
  developing_topics?: string[];
  mastered_topics?: string[];
  trend?: string;
  preferences?: Record<string, unknown>;
  modality?: string | null;
  preferred_modalities?: string[];
}

export interface MemoryBundle {
  learner_id?: string;
  query?: string;
  vector_memories?: Array<{
    content: string;
    memory_type?: string;
    topic_tags?: string[];
    score?: number;
    source?: string;
  }>;
  recent_turns?: Array<{ role: string; content: string; created_at?: string }>;
  profile_highlights?: KnowledgeStateSummary;
}

export interface LearnerTask {
  task_id?: string;
  id?: string;
  title?: string;
  text?: string;
  due_date?: string;
  priority?: 'urgent' | 'medium' | 'low' | string;
  status?: 'pending' | 'completed' | string;
  estimated_minutes?: number;
  course?: string;
  topic?: string;
}

export interface ContentItem {
  id: string;
  title: string;
  topic?: string;
  modality?: string;
  difficulty?: string;
  bloom_level?: string;
  source_type?: string;
  provider?: string;
  source_url?: string;
  quality_score?: number;
  source_origin?: string;
  tags?: string[];
  description?: string;
  duration_minutes?: number;
}

export interface OnboardingData {
  fullName?: string;
  fieldOfStudy?: string;
  institution?: string;
  proficiencyLevel?: string;
  departmentId?: string;
  level?: string;
  courses?: string[];
  subjects?: string[];
  knowledgeRatings?: Record<string, string>;
  weeklyHours?: number;
  contentFormats?: string[];
  primaryObjective?: string;
}

export interface College {
  id: string;
  name: string;
}

export interface Department {
  id: string;
  name: string;
  college_id: string;
  course_count?: number;
}

export interface UniversityCourse {
  id: string;
  department_id: string;
  course_code: string;
  course_title: string;
  level: string;
  units: number;
  semester: 'First' | 'Second' | 'Both';
  type: 'Compulsory' | 'Elective';
  description?: string;
}

export type TestimonialPanel = 'login' | 'student_register' | 'lecturer_register';

export interface Testimonial {
  id: string;
  panel: TestimonialPanel;
  quote: string;
  author: string;
  role: string;
}

export interface NucIdRecord {
  id: string;
  nuc_staff_id: string;
  /** @deprecated */
  staff_id?: string;
  label?: string;
  college: string;
  department: string;
  status: 'active' | 'revoked';
  added_at?: string;
  created_at?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  tasks?: Recommendation[];
  action?: {
    label: string;
    onClick: () => void;
  };
  isComprehensionCheck?: boolean;
  score?: number;
  onboardingOptions?: {
    options: import('@/api/moduleSession').OnboardingOption[];
    question: string;
    onboardingStep: string;
  };
}

export interface ApiConfig {
  baseUrl: string;
  apiKey: string;
  devToken: string;
  model: string;
}

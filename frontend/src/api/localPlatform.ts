/**
 * Client-side platform layer for endpoints not yet implemented on FastAPI backend.
 * Data persists in localStorage until backend auth/admin/course APIs exist.
 */
import type {
  AuthUser,
  College,
  Department,
  NucIdRecord,
  OnboardingData,
  Testimonial,
  TestimonialPanel,
  UniversityCourse,
  AccountStatus,
} from '@/types';
import { generateId, learnerIdFromUser } from '@/lib/utils';

const KEYS = {
  users: 'aitutor_users',
  passwords: 'aitutor_passwords',
  resetCodes: 'aitutor_reset_codes',
  colleges: 'aitutor_colleges',
  departments: 'aitutor_departments',
  courses: 'aitutor_courses',
  nucIds: 'aitutor_nuc_ids',
  onboarding: 'aitutor_onboarding',
  testimonials: 'aitutor_testimonials',
};

const RESET_CODE_TTL_MS = 10 * 60 * 1000;

interface StoredResetCode {
  email: string;
  code: string;
  expiresAt: number;
}

function normalizeEmail(email: string) {
  return email.trim().toLowerCase();
}

function generateResetCode() {
  return String(Math.floor(100000 + Math.random() * 900000));
}

function getPasswords(): Record<string, string> {
  return read<Record<string, string>>(KEYS.passwords, {});
}

function setPasswordForEmail(email: string, password: string) {
  const passwords = getPasswords();
  passwords[normalizeEmail(email)] = password;
  write(KEYS.passwords, passwords);
}

function verifyPasswordForEmail(email: string, password: string): boolean {
  const stored = getPasswords()[normalizeEmail(email)];
  if (!stored) return true;
  return stored === password;
}

const DEFAULT_TESTIMONIALS: Testimonial[] = [
  {
    id: 't_login',
    panel: 'login',
    quote: 'AITutor helped me identify exactly where I was struggling before exams.',
    author: 'Ada Okafor',
    role: 'Computer Science, 300 Level',
  },
  {
    id: 't_student',
    panel: 'student_register',
    quote:
      'AITutor has completely transformed how I approach complex topics. The structural breakdown of information and the logical flow of the curriculum is exactly what I needed.',
    author: 'Sarah Chen',
    role: 'Data Science Fellow',
  },
  {
    id: 't_lecturer',
    panel: 'lecturer_register',
    quote:
      'AITutor gives me a clear view of where each student is struggling, so I can intervene before exams instead of after.',
    author: 'Dr. Emeka Nwosu',
    role: 'Senior Lecturer, Computer Science',
  },
];

function dedupeColleges() {
  const colleges = read<College[]>(KEYS.colleges, []);
  const seen = new Map<string, College>();
  for (const college of colleges) {
    if (!seen.has(college.id)) seen.set(college.id, college);
  }
  write(KEYS.colleges, Array.from(seen.values()));
}

function read<T>(key: string, fallback: T): T {
  const raw = localStorage.getItem(key);
  if (!raw) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function write<T>(key: string, value: T) {
  localStorage.setItem(key, JSON.stringify(value));
}

function seedIfEmpty() {
  const colleges = read<College[]>(KEYS.colleges, []);
  if (colleges.length === 0) {
    const c1 = { id: 'col_eng', name: 'College of Engineering' };
    const c2 = { id: 'col_sci', name: 'College of Science' };
    write(KEYS.colleges, [c1, c2]);

    const d1 = { id: 'dept_csc', name: 'Computer Science', college_id: c1.id, course_count: 4 };
    const d2 = { id: 'dept_mat', name: 'Mathematics', college_id: c2.id, course_count: 2 };
    write(KEYS.departments, [d1, d2]);

    write(KEYS.courses, [] as UniversityCourse[]);
  }

  const nucIds = read<NucIdRecord[]>(KEYS.nucIds, []);
  if (nucIds.length === 0) {
    write(KEYS.nucIds, [
      {
        id: 'nuc_demo_1',
        nuc_staff_id: 'NUC-2024-001',
        staff_id: 'NUC-2024-001',
        label: 'Demo Lecturer ID',
        college: 'College of Engineering',
        department: 'Computer Science',
        status: 'active',
        created_at: new Date().toISOString(),
      },
      {
        id: 'nuc_demo_2',
        nuc_staff_id: 'NUC-2024-002',
        staff_id: 'NUC-2024-002',
        label: 'Demo Lecturer ID (Science)',
        college: 'College of Science',
        department: 'Mathematics',
        status: 'active',
        created_at: new Date().toISOString(),
      },
    ]);
  }

  const testimonials = read<Testimonial[]>(KEYS.testimonials, []);
  if (testimonials.length === 0) {
    write(KEYS.testimonials, DEFAULT_TESTIMONIALS);
  }
}

function platformInit() {
  seedIfEmpty();
  dedupeColleges();
}

platformInit();

function fakeJwt(user: AuthUser): string {
  const payload = {
    user_id: user.user_id,
    role: user.role,
    name: user.name,
    email: user.email,
    exp: Date.now() + 7 * 24 * 60 * 60 * 1000,
  };
  return `aitutor.${btoa(JSON.stringify(payload))}`;
}

export const localPlatform = {
  init: platformInit,

  login(email: string, password: string): { user: AuthUser; token: string } | null {
    const users = read<AuthUser[]>(KEYS.users, []);
    const user = users.find((u) => u.email.toLowerCase() === email.toLowerCase());
    if (!user) return null;
    if (!verifyPasswordForEmail(email, password)) return null;
    if (user.status === 'pending_verification') {
      throw new Error('Your account is pending administrator approval.');
    }
    if (user.status === 'suspended' || user.status === 'rejected') {
      throw new Error('Your account is not active. Contact your administrator.');
    }
    return { user, token: fakeJwt(user) };
  },

  loginWithGoogle(credential: string): { user: AuthUser; token: string } {
    const payload = JSON.parse(atob(credential.split('.')[1])) as {
      email?: string;
      name?: string;
      sub?: string;
    };
    if (!payload.email) {
      throw new Error('Google account did not return an email address.');
    }

    const users = read<AuthUser[]>(KEYS.users, []);
    let user = users.find((u) => u.email.toLowerCase() === payload.email!.toLowerCase());

    if (!user) {
      user = {
        user_id: generateId('user'),
        role: 'student',
        name: payload.name || payload.email.split('@')[0],
        email: payload.email,
        status: 'active',
        onboarding_complete: false,
      };
      user.learner_id = learnerIdFromUser(user.user_id);
      users.push(user);
      write(KEYS.users, users);
    } else if (user.status === 'pending_verification') {
      throw new Error('Your account is pending administrator approval.');
    } else if (user.status === 'suspended' || user.status === 'rejected') {
      throw new Error('Your account is not active. Contact your administrator.');
    }

    return { user, token: fakeJwt(user) };
  },

  registerStudent(data: {
    name: string;
    email: string;
    password: string;
  }): { user: AuthUser; token: string } {
    const users = read<AuthUser[]>(KEYS.users, []);
    if (users.some((u) => u.email.toLowerCase() === data.email.toLowerCase())) {
      throw new Error('An account with this email already exists.');
    }
    const user: AuthUser = {
      user_id: generateId('user'),
      role: 'student',
      name: data.name,
      email: data.email,
      status: 'active',
      learner_id: learnerIdFromUser(generateId('user')),
      onboarding_complete: false,
    };
    user.learner_id = learnerIdFromUser(user.user_id);
    users.push(user);
    write(KEYS.users, users);
    setPasswordForEmail(data.email, data.password);
    return { user, token: fakeJwt(user) };
  },

  registerLecturer(data: {
    name: string;
    email: string;
    staff_id: string;
    college_id: string;
    department_id: string;
    password: string;
  }): { user: AuthUser } {
    const nucIds = read<NucIdRecord[]>(KEYS.nucIds, []);
    const approved = nucIds.find(
      (n) =>
        (n.nuc_staff_id ?? n.staff_id ?? '').toLowerCase() === data.staff_id.toLowerCase() &&
        n.status === 'active',
    );
    if (!approved) {
      throw new Error('This Staff ID is not recognized. Please contact your department administrator.');
    }
    const users = read<AuthUser[]>(KEYS.users, []);
    if (users.some((u) => u.email.toLowerCase() === data.email.toLowerCase())) {
      throw new Error('An account with this email already exists.');
    }
    const user: AuthUser = {
      user_id: generateId('user'),
      role: 'lecturer',
      name: data.name,
      email: data.email,
      staff_id: data.staff_id,
      college_id: data.college_id,
      department_id: data.department_id,
      status: 'pending_verification' as AccountStatus,
    };
    users.push(user);
    write(KEYS.users, users);
    setPasswordForEmail(data.email, data.password);
    return { user };
  },

  requestPasswordResetCode(email: string): { message: string; devCode?: string } {
    const normalized = normalizeEmail(email);
    const users = read<AuthUser[]>(KEYS.users, []);
    const user = users.find((u) => u.email.toLowerCase() === normalized);
    if (!user) {
      throw new Error('No account found with that email address.');
    }
    if (user.role === 'admin') {
      throw new Error('Admin accounts cannot reset password here. Use the admin secret at /admin/login.');
    }
    const code = generateResetCode();
    const record: StoredResetCode = {
      email: normalized,
      code,
      expiresAt: Date.now() + RESET_CODE_TTL_MS,
    };
    write(KEYS.resetCodes, record);
    // TODO: send `code` via email (SMTP / SendGrid) in production
    return {
      message: 'A 6-digit verification code was sent to your email.',
      devCode: code,
    };
  },

  resetPasswordWithCode(email: string, code: string, newPassword: string): void {
    const normalized = normalizeEmail(email);
    const record = read<StoredResetCode | null>(KEYS.resetCodes, null);
    if (!record || record.email !== normalized) {
      throw new Error('Request a new verification code first.');
    }
    if (Date.now() > record.expiresAt) {
      localStorage.removeItem(KEYS.resetCodes);
      throw new Error('Verification code expired. Request a new one.');
    }
    if (record.code !== code.trim()) {
      throw new Error('Invalid verification code.');
    }
    if (newPassword.length < 8) {
      throw new Error('Password must be at least 8 characters.');
    }
    setPasswordForEmail(normalized, newPassword);
    localStorage.removeItem(KEYS.resetCodes);
  },

  adminLogin(email: string, secret: string): { user: AuthUser; token: string } | null {
    const adminSecret = import.meta.env.VITE_ADMIN_SECRET || 'admin-secret';
    if (secret !== adminSecret && email !== 'admin@aitutor.edu') return null;
    const user: AuthUser = {
      user_id: 'admin_1',
      role: 'admin',
      name: 'Platform Admin',
      email: email || 'admin@aitutor.edu',
      status: 'active',
    };
    return { user, token: fakeJwt(user) };
  },

  saveOnboarding(userId: string, data: OnboardingData) {
    const all = read<Record<string, OnboardingData>>(KEYS.onboarding, {});
    all[userId] = data;
    write(KEYS.onboarding, all);
    const users = read<AuthUser[]>(KEYS.users, []);
    const idx = users.findIndex((u) => u.user_id === userId);
    if (idx >= 0) {
      users[idx] = { ...users[idx], onboarding_complete: true };
      write(KEYS.users, users);
    }
  },

  getOnboarding(userId: string): OnboardingData | null {
    const all = read<Record<string, OnboardingData>>(KEYS.onboarding, {});
    return all[userId] ?? null;
  },

  getColleges(): College[] {
    const colleges = read<College[]>(KEYS.colleges, []);
    const seen = new Set<string>();
    return colleges.filter((college) => {
      if (seen.has(college.id)) return false;
      seen.add(college.id);
      return true;
    });
  },

  getDepartments(): Department[] {
    const departments = read<Department[]>(KEYS.departments, []);
    const courses = read<UniversityCourse[]>(KEYS.courses, []);
    return departments.map((d) => ({
      ...d,
      course_count: courses.filter((c) => c.department_id === d.id).length,
    }));
  },

  getCourses(departmentId?: string, level?: string): UniversityCourse[] {
    let courses = read<UniversityCourse[]>(KEYS.courses, []);
    if (departmentId) courses = courses.filter((c) => c.department_id === departmentId);
    if (level) courses = courses.filter((c) => c.level === level);
    return courses;
  },

  saveDepartment(data: Omit<Department, 'id' | 'course_count'> & { id?: string }) {
    const departments = read<Department[]>(KEYS.departments, []);
    if (data.id) {
      const idx = departments.findIndex((d) => d.id === data.id);
      if (idx >= 0) departments[idx] = { ...departments[idx], ...data };
    } else {
      departments.push({ ...data, id: generateId('dept') });
    }
    write(KEYS.departments, departments);
  },

  deleteDepartment(id: string) {
    write(
      KEYS.departments,
      read<Department[]>(KEYS.departments, []).filter((d) => d.id !== id),
    );
    write(
      KEYS.courses,
      read<UniversityCourse[]>(KEYS.courses, []).filter((c) => c.department_id !== id),
    );
  },

  saveCourse(data: Omit<UniversityCourse, 'id'> & { id?: string }): UniversityCourse {
    const courses = read<UniversityCourse[]>(KEYS.courses, []);
    let saved: UniversityCourse;
    if (data.id) {
      const idx = courses.findIndex((c) => c.id === data.id);
      saved = { ...courses[idx], ...data } as UniversityCourse;
      if (idx >= 0) courses[idx] = saved;
    } else {
      saved = { ...data, id: generateId('course') } as UniversityCourse;
      courses.push(saved);
    }
    write(KEYS.courses, courses);
    return saved;
  },

  deleteCourse(id: string) {
    write(KEYS.courses, read<UniversityCourse[]>(KEYS.courses, []).filter((c) => c.id !== id));
  },

  saveCollege(name: string, id?: string) {
    const colleges = read<College[]>(KEYS.colleges, []);
    if (id) {
      const idx = colleges.findIndex((c) => c.id === id);
      if (idx >= 0) colleges[idx].name = name;
    } else {
      colleges.push({ id: generateId('col'), name });
    }
    write(KEYS.colleges, colleges);
  },

  deleteCollege(id: string) {
    write(KEYS.colleges, read<College[]>(KEYS.colleges, []).filter((c) => c.id !== id));
  },

  getNucIds(): NucIdRecord[] {
    return read<NucIdRecord[]>(KEYS.nucIds, []);
  },

  saveNucId(data: Omit<NucIdRecord, 'id' | 'created_at' | 'status'> & { id?: string }) {
    const records = read<NucIdRecord[]>(KEYS.nucIds, []);
    records.push({
      ...data,
      id: data.id || generateId('nuc'),
      status: 'active',
      created_at: new Date().toISOString(),
    });
    write(KEYS.nucIds, records);
  },

  revokeNucId(id: string) {
    const records = read<NucIdRecord[]>(KEYS.nucIds, []);
    const idx = records.findIndex((r) => r.id === id);
    if (idx >= 0) records[idx].status = 'revoked';
    write(KEYS.nucIds, records);
  },

  deleteNucId(id: string) {
    write(KEYS.nucIds, read<NucIdRecord[]>(KEYS.nucIds, []).filter((r) => r.id !== id));
  },

  getStudents(): AuthUser[] {
    return read<AuthUser[]>(KEYS.users, []).filter((u) => u.role === 'student');
  },

  getLecturers(): AuthUser[] {
    return read<AuthUser[]>(KEYS.users, []).filter((u) => u.role === 'lecturer');
  },

  approveLecturer(userId: string) {
    const users = read<AuthUser[]>(KEYS.users, []);
    const idx = users.findIndex((u) => u.user_id === userId);
    if (idx >= 0) users[idx].status = 'active';
    write(KEYS.users, users);
  },

  rejectLecturer(userId: string) {
    const users = read<AuthUser[]>(KEYS.users, []);
    const idx = users.findIndex((u) => u.user_id === userId);
    if (idx >= 0) users[idx].status = 'rejected';
    write(KEYS.users, users);
  },

  getTestimonials(): Testimonial[] {
    return read<Testimonial[]>(KEYS.testimonials, DEFAULT_TESTIMONIALS);
  },

  getTestimonialForPanel(panel: TestimonialPanel): Testimonial {
    const all = read<Testimonial[]>(KEYS.testimonials, DEFAULT_TESTIMONIALS);
    return all.find((t) => t.panel === panel) ?? DEFAULT_TESTIMONIALS.find((t) => t.panel === panel)!;
  },

  saveTestimonial(data: Omit<Testimonial, 'id'> & { id?: string }) {
    const all = read<Testimonial[]>(KEYS.testimonials, DEFAULT_TESTIMONIALS);
    if (data.id) {
      const idx = all.findIndex((t) => t.id === data.id);
      if (idx >= 0) {
        all[idx] = { ...all[idx], ...data, id: data.id };
      }
    } else {
      all.push({ ...data, id: generateId('t') });
    }
    write(KEYS.testimonials, all);
  },

  deleteTestimonial(id: string) {
    write(KEYS.testimonials, read<Testimonial[]>(KEYS.testimonials, []).filter((t) => t.id !== id));
  },
};

import type { UniversityCourse } from '@/types';

export type SemesterFilter = 'All' | 'First' | 'Second' | 'Both';

export const SEMESTER_FILTER_OPTIONS: { value: SemesterFilter; label: string }[] = [
  { value: 'All', label: 'All Semesters' },
  { value: 'First', label: '1st Semester' },
  { value: 'Second', label: '2nd Semester' },
  { value: 'Both', label: 'Full Year' },
];

export const SEMESTER_FORM_OPTIONS = [
  { value: 'First', label: '1st Semester' },
  { value: 'Second', label: '2nd Semester' },
  { value: 'Both', label: 'Full Year (Both)' },
] as const;

export function filterCoursesBySemester<T extends Pick<UniversityCourse, 'semester'>>(
  courses: T[],
  semesterFilter: SemesterFilter,
): T[] {
  if (semesterFilter === 'All') return courses;
  return courses.filter((c) => c.semester === semesterFilter || c.semester === 'Both');
}

export function normalizeSemester(semester?: string | null): UniversityCourse['semester'] {
  if (semester === 'First' || semester === 'Second' || semester === 'Both') return semester;
  return 'Both';
}

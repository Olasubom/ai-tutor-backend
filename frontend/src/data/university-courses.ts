/** Seed structure — populated via admin dashboard / localPlatform */
export interface UniversityCourseSeed {
  course_code: string;
  course_title: string;
  level: string;
  units: number;
  semester: string;
  type: string;
}

export const EMPTY_COURSE_CATALOG: UniversityCourseSeed[] = [];

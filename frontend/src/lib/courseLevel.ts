/** Normalize level labels like "100 Level" to the DB value "100". */
export function normalizeCourseLevel(level?: string | number | null): string | undefined {
  if (level === undefined || level === null || level === '') return undefined;
  const cleaned = String(level)
    .replace(/\s*level\s*/gi, '')
    .trim();
  const parsed = parseInt(cleaned, 10);
  if (!Number.isNaN(parsed)) return String(parsed);
  return cleaned || undefined;
}

export const COURSE_LEVEL_OPTIONS = [
  { label: '100 Level', value: '100' },
  { label: '200 Level', value: '200' },
  { label: '300 Level', value: '300' },
  { label: '400 Level', value: '400' },
  { label: '500 Level', value: '500' },
] as const;

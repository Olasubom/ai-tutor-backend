const TYPE_MAP: Record<string, string> = {
  video: 'Video',
  VIDEO: 'Video',
  youtube: 'Video',
  ebook: 'E-Book',
  book: 'E-Book',
  pdf: 'E-Book',
  EBOOK: 'E-Book',
  BOOK: 'E-Book',
  PDF: 'E-Book',
  quiz: 'Quiz',
  QUIZ: 'Quiz',
  interactive: 'Interactive',
  INTERACTIVE: 'Interactive',
  article: 'Article',
  ARTICLE: 'Article',
  text: 'Article',
  TEXT: 'Article',
  game: 'Practice',
  GAME: 'Practice',
  practice: 'Practice',
  read_aloud: 'Audio',
  READ_ALOUD: 'Audio',
  audio: 'Audio',
  AUDIO: 'Audio',
  simulation: 'Simulation',
  internal: 'Interactive',
};

export function formatResourceType(type: string): string {
  if (!type) return 'Resource';
  if (TYPE_MAP[type]) return TYPE_MAP[type];
  const lower = type.toLowerCase();
  if (TYPE_MAP[lower]) return TYPE_MAP[lower];
  return type
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (l) => l.toUpperCase());
}

export function resourceTypePillClass(type: string): string {
  const label = formatResourceType(type).toLowerCase();
  if (label === 'video') return 'bg-red-50 text-red-600';
  if (label === 'e-book') return 'bg-amber-50 text-amber-600';
  if (label === 'pdf') return 'bg-amber-50 text-amber-600';
  if (label === 'quiz' || label === 'interactive') return 'bg-green-50 text-green-600';
  if (label === 'article') return 'bg-purple-50 text-purple-600';
  if (label === 'practice') return 'bg-orange-50 text-orange-600';
  if (label === 'audio') return 'bg-teal-50 text-teal-600';
  if (label === 'simulation') return 'bg-blue-50 text-blue-600';
  return 'bg-gray-50 text-gray-600';
}

export function matchesResourceFilter(
  modality: string | undefined,
  sourceType: string | undefined,
  filter: string,
): boolean {
  if (filter === 'All Resources') return true;
  const type = formatResourceType(modality ?? sourceType ?? '').toLowerCase();
  if (filter === 'Video Lectures') return type === 'video';
  if (filter === 'E-Books') return type === 'e-book' || type === 'pdf';
  if (filter === 'Interactive Quizzes') return type === 'quiz' || type === 'interactive';
  return true;
}

const TYPE_MAP: Record<string, string> = {
  video: 'Video',
  VIDEO: 'Video',
  youtube: 'Video',
  ebook: 'E-Book',
  EBOOK: 'E-Book',
  pdf: 'PDF',
  quiz: 'Quiz',
  QUIZ: 'Quiz',
  interactive: 'Interactive',
  INTERACTIVE: 'Interactive',
  article: 'Article',
  ARTICLE: 'Article',
  game: 'Practice',
  GAME: 'Practice',
  read_aloud: 'Audio',
  READ_ALOUD: 'Audio',
  simulation: 'Simulation',
  text: 'Article',
};

export function formatResourceType(type: string): string {
  if (TYPE_MAP[type]) return TYPE_MAP[type];
  return type
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ');
}

export function resourceTypePillClass(type: string): string {
  const label = formatResourceType(type).toLowerCase();
  if (label === 'video') return 'bg-red-500/10 text-red-600';
  if (label === 'e-book') return 'bg-amber-500/10 text-amber-600';
  if (label === 'pdf') return 'bg-gray-500/10 text-gray-600';
  if (label === 'quiz' || label === 'interactive') return 'bg-green-500/10 text-green-600';
  if (label === 'article') return 'bg-blue-500/10 text-blue-600';
  if (label === 'practice') return 'bg-purple-500/10 text-purple-600';
  if (label === 'audio') return 'bg-teal-500/10 text-teal-600';
  return 'bg-gray-500/10 text-gray-600';
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

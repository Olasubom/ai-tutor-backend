export function getMasteryLabel(pct: number): { label: string; color: string } {
  if (pct >= 80) return { label: 'Mastered', color: 'text-green-600' };
  if (pct >= 60) return { label: 'Developing', color: 'text-blue-600' };
  if (pct >= 40) return { label: 'Familiar', color: 'text-amber-600' };
  return { label: 'Needs Work', color: 'text-red-500' };
}

export function getMasteryBarColor(pct: number): string {
  if (pct >= 80) return 'bg-green-500';
  if (pct >= 60) return 'bg-blue-500';
  if (pct >= 40) return 'bg-amber-500';
  return 'bg-red-500';
}

export function getGlobalMasteryDescriptor(pct: number): string {
  if (pct >= 70) return 'Strong knowledge base';
  if (pct >= 45) return 'Building your foundation';
  return 'Just getting started';
}

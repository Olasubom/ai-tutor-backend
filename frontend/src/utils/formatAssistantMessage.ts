const JSON_FENCE_RE = /```(?:json)?\s*([\s\S]*?)```/gi;

function normalizeTitle(title: unknown): string {
  return String(title ?? '')
    .toLowerCase()
    .trim()
    .replace(/\s+/g, ' ');
}

function unifiedResourceList(data: Record<string, unknown>): Record<string, unknown>[] {
  const seen = new Set<string>();
  const unified: Record<string, unknown>[] = [];

  const recs = data.recommendations;
  if (Array.isArray(recs)) {
    for (const rec of recs) {
      if (!rec || typeof rec !== 'object') continue;
      const item = rec as Record<string, unknown>;
      const key = normalizeTitle(item.title ?? item.topic);
      if (!key || seen.has(key)) continue;
      seen.add(key);
      unified.push(item);
    }
  }

  const adaptive = data.adaptive_path;
  if (Array.isArray(adaptive)) {
    for (const step of adaptive) {
      if (!step || typeof step !== 'object') continue;
      const item = step as Record<string, unknown>;
      const key = normalizeTitle(item.title ?? item.topic);
      if (!key || seen.has(key)) continue;
      seen.add(key);
      unified.push(item);
    }
  }

  return unified;
}

function looksLikeResourceList(text: string): boolean {
  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean);
  return lines.filter((l) => /^\d+\./.test(l)).length >= 2;
}

function formatStructuredPayload(data: unknown): string {
  if (!data || typeof data !== 'object' || Array.isArray(data)) return '';

  const obj = data as Record<string, unknown>;
  const parts: string[] = [];

  const summary = obj.knowledge_state_summary as Record<string, unknown> | undefined;
  if (summary && typeof summary === 'object') {
    const weak = (summary.weak_topics as string[]) ?? [];
    const developing = (summary.developing_topics as string[]) ?? [];
    const mastered = (summary.mastered_topics as string[]) ?? [];
    if (weak.length || developing.length || mastered.length) {
      parts.push('**Your knowledge snapshot**');
      if (weak.length) parts.push(`- **Focus areas:** ${weak.join(', ')}`);
      if (developing.length) parts.push(`- **Developing:** ${developing.join(', ')}`);
      if (mastered.length) parts.push(`- **Strong topics:** ${mastered.join(', ')}`);
    }
    const trend = summary.trend;
    if (trend && String(trend).toLowerCase() !== 'stable') {
      parts.push(`- **Trend:** ${String(trend)}`);
    }
  }

  const notes = obj.diagnostic_notes ?? obj.notes;
  if (typeof notes === 'string' && notes.trim()) {
    parts.push(notes.trim());
  }

  const resources = unifiedResourceList(obj);
  if (resources.length) {
    parts.push('**Study recommendations**');
    resources.slice(0, 6).forEach((item, i) => {
      const title = String(item.title ?? item.topic ?? 'Resource');
      const duration = item.duration_minutes ?? item.estimated_minutes;
      const modality = item.modality ?? item.source_type;
      const reasons = (item.reasons as string[]) ?? (item.reason ? [String(item.reason)] : []);
      const meta: string[] = [];
      if (modality) meta.push(String(modality).replace(/_/g, ' '));
      if (duration) meta.push(`${duration} min`);
      let line = `${i + 1}. **${title}**`;
      if (meta.length) line += ` (${meta.join(', ')})`;
      parts.push(line);
      const reason = reasons.find(Boolean);
      if (reason) parts.push(`   - ${reason}`);
    });
  }

  if (obj.error) {
    parts.push(`_${String(obj.error)}_`);
  }

  return parts.join('\n');
}

/** Convert raw specialist JSON in chat output to readable markdown. */
export function formatAssistantMessage(text: string): string {
  if (!text?.trim()) return text;

  const stripped = text.trim();
  const blocks = [...stripped.matchAll(JSON_FENCE_RE)].map((m) => m[1]?.trim()).filter(Boolean);

  if (!blocks.length) {
    try {
      const payload = JSON.parse(stripped);
      const formatted = formatStructuredPayload(payload);
      return formatted || text;
    } catch {
      return text;
    }
  }

  const remainder = stripped.replace(JSON_FENCE_RE, '').trim();
  const formattedBlocks: string[] = [];

  for (const block of blocks) {
    try {
      const payload = JSON.parse(block);
      const formatted = formatStructuredPayload(payload);
      if (formatted) formattedBlocks.push(formatted);
    } catch {
      /* skip invalid json blocks */
    }
  }

  if (formattedBlocks.length) {
    const combined = formattedBlocks.join('\n\n');
    if (remainder && !looksLikeResourceList(remainder)) {
      return `${remainder}\n\n${combined}`.trim();
    }
    return combined;
  }

  return remainder || text;
}

export function looksLikeRawJsonStream(text: string): boolean {
  const t = text.trim();
  return t.startsWith('```json') || t.startsWith('{') || t.startsWith('["');
}

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

export function coerceReasons(item: { reason?: string; reasons?: unknown }): string[] {
  const raw = item.reasons;
  if (Array.isArray(raw)) {
    return raw.map((r) => String(r).trim()).filter(Boolean);
  }
  if (typeof raw === 'string' && raw.trim()) {
    return [raw.trim()];
  }
  const single = item.reason;
  if (typeof single === 'string' && single.trim()) {
    return [single.trim()];
  }
  return [];
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
      const reasons = coerceReasons(item);
      const meta: string[] = [];
      if (modality) meta.push(String(modality).replace(/_/g, ' '));
      if (duration) meta.push(`${duration} min`);
      let line = `${i + 1}. **${title}**`;
      if (meta.length) line += ` (${meta.join(', ')})`;
      parts.push(line);
      if (reasons.length) parts.push(`   - ${reasons.join(' · ')}`);
    });
  }

  if (obj.error) {
    parts.push(`_${String(obj.error)}_`);
  }

  const studyPlan = obj.study_plan as Record<string, unknown> | undefined;
  if (studyPlan && typeof studyPlan === 'object') {
    const sessions = (studyPlan.sessions as Record<string, unknown>[]) ?? [];
    if (sessions.length) {
      parts.push('### Study Plan');
      if (studyPlan.total_minutes) parts.push(`- **Total time:** ${studyPlan.total_minutes} minutes`);
      for (const sess of sessions) {
        const title = String(sess.title ?? `Session ${sess.session ?? ''}`);
        const dur = sess.duration_minutes;
        const objective = sess.objective;
        let line = `- **${title}**`;
        if (dur) line += ` (${dur} min)`;
        parts.push(line);
        if (objective) parts.push(`  - ${String(objective)}`);
      }
    }
  }

  const tasks = obj.tasks;
  if (Array.isArray(tasks) && tasks.length) {
    parts.push('### Tasks');
    for (const task of tasks) {
      if (!task || typeof task !== 'object') continue;
      const t = task as Record<string, unknown>;
      const title = String(t.title ?? 'Task');
      const meta = [
        t.priority ? String(t.priority) : null,
        t.due_date ? `due ${t.due_date}` : null,
        t.estimated_minutes ? `${t.estimated_minutes} min` : null,
      ].filter(Boolean);
      let line = `- **${title}**`;
      if (meta.length) line += ` (${meta.join(', ')})`;
      parts.push(line);
    }
  }

  return parts.join('\n');
}

function salvageProseSections(text: string): string {
  const markers = [
    '### Study Plan',
    '### Study Session',
    '### Tasks',
    '**Study recommendations**',
    '**Your knowledge snapshot**',
  ];
  const sections: string[] = [];
  for (const marker of markers) {
    const idx = text.indexOf(marker);
    if (idx === -1) continue;
    let chunk = text.slice(idx);
    const fence = chunk.indexOf('```');
    if (fence !== -1) chunk = chunk.slice(0, fence);
    chunk = chunk.trim();
    if (chunk && !sections.includes(chunk)) sections.push(chunk);
  }
  return sections.join('\n\n');
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

  const salvaged = salvageProseSections(stripped);
  if (salvaged) return salvaged;

  return remainder || text;
}

export function looksLikeRawJsonStream(text: string): boolean {
  const t = text.trim();
  return t.startsWith('```json') || t.startsWith('{') || t.startsWith('["');
}

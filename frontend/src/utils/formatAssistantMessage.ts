const JSON_FENCE_RE = /```(?:json)?\s*([\s\S]*?)```/gi;

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

  const recs = obj.recommendations;
  if (Array.isArray(recs) && recs.length) {
    parts.push('**Recommended for you**');
    recs.slice(0, 6).forEach((rec, i) => {
      if (!rec || typeof rec !== 'object') return;
      const item = rec as Record<string, unknown>;
      const title = String(item.title ?? item.topic ?? 'Resource');
      const duration = item.duration_minutes;
      const modality = item.modality ?? item.source_type;
      const reasons = (item.reasons as string[]) ?? (item.reason ? [String(item.reason)] : []);
      const meta: string[] = [];
      if (modality) meta.push(String(modality).replace(/_/g, ' '));
      if (duration) meta.push(`${duration} min`);
      let line = `${i + 1}. **${title}**`;
      if (meta.length) line += ` (${meta.join(', ')})`;
      parts.push(line);
      reasons.slice(0, 2).forEach((reason) => {
        if (reason) parts.push(`   - ${reason}`);
      });
    });
  }

  const adaptive = obj.adaptive_path;
  if (Array.isArray(adaptive) && adaptive.length) {
    parts.push('**Suggested learning path**');
    adaptive.slice(0, 5).forEach((step, i) => {
      if (step && typeof step === 'object') {
        const s = step as Record<string, unknown>;
        parts.push(`${i + 1}. ${String(s.title ?? s.topic ?? s.step ?? `Step ${i + 1}`)}`);
      } else if (step) {
        parts.push(`${i + 1}. ${String(step)}`);
      }
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

  const proseParts: string[] = [];
  const remainder = stripped.replace(JSON_FENCE_RE, '').trim();
  if (remainder) proseParts.push(remainder);

  for (const block of blocks) {
    try {
      const payload = JSON.parse(block);
      const formatted = formatStructuredPayload(payload);
      if (formatted) proseParts.push(formatted);
    } catch {
      /* skip invalid json blocks */
    }
  }

  return proseParts.join('\n\n').trim() || text;
}

export function looksLikeRawJsonStream(text: string): boolean {
  const t = text.trim();
  return t.startsWith('```json') || t.startsWith('{') || t.startsWith('["');
}

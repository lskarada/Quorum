import type { Citation, FinalVerdict } from "@/lib/types";

interface CitationPanelProps {
  verdict: FinalVerdict | null;
}

function dedupe(citations: Citation[]): Citation[] {
  const seen = new Set<string>();
  const out: Citation[] = [];
  for (const c of citations) {
    const key = `${c.source}::${c.title ?? ""}::${c.url ?? ""}`;
    if (!seen.has(key)) {
      seen.add(key);
      out.push(c);
    }
  }
  return out;
}

/**
 * Citation panel — deduplicated across all transcript messages and the final
 * differential candidates. Renders nothing when there are no citations.
 */
export function CitationPanel({ verdict }: CitationPanelProps) {
  if (!verdict) return null;
  const all: Citation[] = [];
  for (const m of verdict.transcript) all.push(...(m.citations ?? []));
  for (const cand of verdict.final_differential.candidates) all.push(...(cand.citations ?? []));
  const unique = dedupe(all);

  if (unique.length === 0) return null;

  return (
    <div>
      <div className="mb-1.5 text-[10.5px] font-extrabold uppercase tracking-wide text-faint">Citations</div>
      <ul className="space-y-1.5 text-[12.5px]">
        {unique.map((c, idx) => (
          <li key={idx} className="leading-snug">
            {c.url ? (
              <a
                href={c.url}
                target="_blank"
                rel="noreferrer"
                className="font-mono font-medium text-primary underline-offset-2 hover:underline"
              >
                {c.source}
              </a>
            ) : (
              <span className="font-mono font-medium text-ink-2">{c.source}</span>
            )}
            {c.title && <span className="text-muted-foreground"> — {c.title}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}

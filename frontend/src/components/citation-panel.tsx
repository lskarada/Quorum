import { Card } from "@/components/ui/card";
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
 * Right-rail citation panel — deduplicated across all transcript messages.
 *
 * TODO (visual pass):
 *   - Scroll into view when a citation chip in DebateView is clicked
 *   - Group by source (e.g. NEJM, UpToDate, PubMed)
 */
export function CitationPanel({ verdict }: CitationPanelProps) {
  if (!verdict) return null;
  const all: Citation[] = [];
  for (const m of verdict.transcript) all.push(...(m.citations ?? []));
  for (const cand of verdict.final_differential.candidates) all.push(...(cand.citations ?? []));
  const unique = dedupe(all);

  if (unique.length === 0) return null;

  return (
    <Card className="p-4 space-y-2">
      <h3 className="font-semibold">Citations</h3>
      <ul className="space-y-1 text-sm">
        {unique.map((c, idx) => (
          <li key={idx}>
            {c.url ? (
              <a href={c.url} target="_blank" rel="noreferrer" className="underline">
                {c.source}
              </a>
            ) : (
              <span>{c.source}</span>
            )}
            {c.title && <span className="text-muted-foreground"> — {c.title}</span>}
          </li>
        ))}
      </ul>
    </Card>
  );
}

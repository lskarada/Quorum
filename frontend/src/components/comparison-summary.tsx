import { cn } from "@/lib/utils";
import type { FinalVerdict } from "@/lib/types";

interface ComparisonSummaryProps {
  /**
   * Map keyed by panel_id. Expects exactly two keys once both panels have
   * emitted their verdicts. The render is best-effort if only one is set,
   * but the headline-color logic assumes both are present.
   */
  verdicts: Record<string, FinalVerdict>;
}

function topCandidate(v: FinalVerdict | undefined): string | null {
  if (!v || v.is_error) return null;
  return v.final_differential.candidates[0]?.name ?? null;
}

function topPosterior(v: FinalVerdict | undefined): number | null {
  if (!v || v.is_error) return null;
  return v.final_differential.candidates[0]?.posterior ?? null;
}

/**
 * Renders a side-by-side comparison header for two panel verdicts.
 *
 * Border-color semantics (clinical-trust palette):
 *   - red:    any panel errored (is_error=true)
 *   - ok:     both panels agree on top candidate
 *   - warn:   both panels finished but disagree
 *
 * When `verdict.is_error` is true, the cell renders an explicit "Panel failed"
 * state (data-testid `panel-failed-<id>`) instead of an empty "—" placeholder,
 * so the two states are distinguishable for QA.
 */
export function ComparisonSummary({ verdicts }: ComparisonSummaryProps) {
  const ids = Object.keys(verdicts);
  if (ids.length === 0) return null;

  const [aId, bId] = ids;
  const a = verdicts[aId];
  const b = verdicts[bId];

  const anyError = (a && a.is_error) || (b && b.is_error);
  const bothPresent = !!a && !!b;
  const agree =
    bothPresent &&
    !anyError &&
    topCandidate(a) !== null &&
    topCandidate(a) === topCandidate(b);

  const borderClass = anyError
    ? "border-red-400"
    : agree
      ? "border-ok"
      : bothPresent
        ? "border-warn"
        : "border-line";

  const headline = anyError
    ? "One or both panels failed"
    : !bothPresent
      ? "Awaiting second panel…"
      : agree
        ? `Both panels agree: ${topCandidate(a)}`
        : "Panels disagree on top candidate";

  const badge = anyError
    ? "error"
    : agree
      ? "agreement"
      : bothPresent
        ? "disagreement"
        : "pending";

  return (
    <div
      className={cn(
        "space-y-3 rounded-2xl border-2 bg-card p-[18px] shadow-card-2",
        borderClass,
      )}
      data-testid="comparison-summary"
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold tracking-tight">Comparison summary</h3>
        <span className="text-[10.5px] font-extrabold uppercase tracking-wide text-faint">
          {badge}
        </span>
      </div>
      <p className="text-[13.5px] font-semibold text-ink-2">{headline}</p>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {ids.map((id) => (
          <PanelColumn key={id} panelId={id} verdict={verdicts[id]} />
        ))}
      </div>
    </div>
  );
}

function PanelColumn({
  panelId,
  verdict,
}: {
  panelId: string;
  verdict: FinalVerdict | undefined;
}) {
  if (!verdict) {
    return (
      <div className="space-y-1 rounded-xl border border-dashed border-line p-3">
        <p className="text-[13px] font-semibold">{panelId}</p>
        <p className="text-xs italic text-muted-foreground">Awaiting verdict…</p>
      </div>
    );
  }
  if (verdict.is_error) {
    return (
      <div
        className="space-y-1 rounded-xl border border-red-400 bg-red-50 p-3"
        data-testid={`panel-failed-${panelId}`}
      >
        <p className="text-[13px] font-semibold">{panelId}</p>
        <p className="text-[13px] font-bold text-red-600">Panel failed</p>
        <p className="text-xs text-muted-foreground">
          Termination: {verdict.termination_reason}
        </p>
      </div>
    );
  }

  const top = topCandidate(verdict);
  const post = topPosterior(verdict);

  return (
    <div className="space-y-1.5 rounded-xl border border-line p-3">
      <p className="text-[13px] font-semibold">{panelId}</p>
      <dl className="space-y-1">
        <Row label="Top candidate" value={top ?? "—"} />
        <Row
          label="Top posterior"
          value={post !== null ? `${(post * 100).toFixed(0)}%` : "—"}
        />
        <Row
          label="Total cost"
          value={`$${verdict.total_cost_usd.toFixed(4)}`}
        />
        <Row label="Iterations" value={String(verdict.iterations_used)} />
        <Row label="Termination" value={verdict.termination_reason} />
      </dl>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-right font-mono text-xs font-semibold text-ink-2">
        {value}
      </dd>
    </div>
  );
}

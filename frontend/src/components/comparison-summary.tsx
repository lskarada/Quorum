import { Card } from "@/components/ui/card";
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
 * Border-color semantics (Phase 7):
 *   - red: any panel errored (is_error=true)
 *   - green: both panels agree on top candidate
 *   - yellow: both panels finished but disagree
 *
 * Architect MAJOR (CRITICAL per Phase 7 spec): when `verdict.is_error` is
 * true, the cell renders an explicit "Panel failed" state instead of an
 * empty "—" placeholder. The two states are distinguishable for QA.
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
    ? "border-red-500"
    : agree
      ? "border-green-500"
      : bothPresent
        ? "border-yellow-500"
        : "border-muted";

  const headline = anyError
    ? "One or both panels failed"
    : !bothPresent
      ? "Awaiting second panel..."
      : agree
        ? `Both panels agree: ${topCandidate(a)}`
        : "Panels disagree on top candidate";

  return (
    <Card
      className={cn(
        "p-4 mt-4 border-2 space-y-3",
        borderClass,
      )}
      data-testid="comparison-summary"
    >
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">Comparison summary</h3>
        <span className="text-xs uppercase tracking-wide text-muted-foreground">
          {anyError ? "error" : agree ? "agreement" : bothPresent ? "disagreement" : "pending"}
        </span>
      </div>
      <p className="text-sm">{headline}</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
        {ids.map((id) => (
          <PanelColumn key={id} panelId={id} verdict={verdicts[id]} />
        ))}
      </div>
    </Card>
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
      <div className="rounded-md border border-dashed p-3 space-y-1">
        <p className="font-medium">{panelId}</p>
        <p className="text-muted-foreground italic">Awaiting verdict...</p>
      </div>
    );
  }
  if (verdict.is_error) {
    return (
      <div
        className="rounded-md border border-red-500 bg-red-500/10 p-3 space-y-1"
        data-testid={`panel-failed-${panelId}`}
      >
        <p className="font-medium">{panelId}</p>
        <p className="text-red-700 dark:text-red-300 font-semibold">
          Panel failed
        </p>
        <p className="text-xs text-muted-foreground">
          Termination: {verdict.termination_reason}
        </p>
      </div>
    );
  }

  const top = topCandidate(verdict);
  const post = topPosterior(verdict);

  return (
    <div className="rounded-md border p-3 space-y-1">
      <p className="font-medium">{panelId}</p>
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
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-mono text-xs text-right">{value}</dd>
    </div>
  );
}

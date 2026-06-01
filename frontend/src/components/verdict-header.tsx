import { ConfidenceRing } from "@/components/ui/confidence-ring";
import type { Differential, FinalVerdict } from "@/lib/types";

const TERM_LABEL: Record<FinalVerdict["termination_reason"], string> = {
  consensus: "Consensus reached",
  max_iterations: "Max iterations",
  budget: "Budget reached",
  checklist_stop: "Checklist stop",
  error: "Panel error",
};

interface VerdictHeaderProps {
  verdict: FinalVerdict | null;
  liveDifferential?: Differential | null;
}

/**
 * Confidence ring + leading diagnosis + termination badge. While running it
 * reflects the live leading candidate's posterior; on verdict it shows the
 * final confidence and termination reason. `data-verify-leading` exposes the
 * rank-1 name for the invariant probe.
 */
export function VerdictHeader({ verdict, liveDifferential }: VerdictHeaderProps) {
  const diff = verdict?.final_differential ?? liveDifferential ?? null;
  const top = diff?.candidates[0] ?? null;
  if (!top) return null;
  const value = verdict ? verdict.confidence : top.posterior;
  const term = verdict ? (TERM_LABEL[verdict.termination_reason] ?? verdict.termination_reason) : null;
  const isError = verdict?.is_error || verdict?.termination_reason === "error";
  return (
    <div className="flex items-center gap-3.5" data-verify-leading={top.name}>
      <ConfidenceRing value={value} />
      <div>
        <div className="text-[10.5px] font-extrabold uppercase tracking-wide text-faint">Leading diagnosis</div>
        <div className="text-lg font-extrabold tracking-tight">{top.name}</div>
        <div className="text-[12.5px] text-muted-foreground">{diff?.candidates.length ?? 0} candidates</div>
      </div>
      {term && (
        <span
          className={`ml-auto rounded-full border px-3 py-1.5 text-[11.5px] font-bold ${
            isError ? "border-red-200 bg-red-50 text-red-700" : "border-green-200 bg-green-50 text-ok"
          }`}
        >
          ● {term}
        </span>
      )}
    </div>
  );
}

import { ConfidenceRing } from "@/components/ui/confidence-ring";
import type { FinalVerdict } from "@/lib/types";

interface ConfidenceMeterProps {
  verdict: FinalVerdict | null;
}

function bandFor(value: number): string {
  if (value < 0.4) return "Recommend further workup";
  if (value < 0.8) return "Consider next test";
  return "Differential is well-supported";
}

export function ConfidenceMeter({ verdict }: ConfidenceMeterProps) {
  if (!verdict) return null;
  return (
    <div className="flex items-center gap-3">
      <ConfidenceRing value={verdict.confidence} size={52} />
      <p className="text-xs text-muted-foreground">{bandFor(verdict.confidence)}</p>
    </div>
  );
}

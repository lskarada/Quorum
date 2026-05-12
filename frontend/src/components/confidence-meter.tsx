import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { FinalVerdict } from "@/lib/types";

interface ConfidenceMeterProps {
  verdict: FinalVerdict | null;
}

function bandFor(value: number): { label: string; copy: string } {
  if (value < 0.4) return { label: "low", copy: "Recommend further workup" };
  if (value < 0.8) return { label: "moderate", copy: "Consider next test" };
  return { label: "high", copy: "Differential is well-supported" };
}

export function ConfidenceMeter({ verdict }: ConfidenceMeterProps) {
  if (!verdict) return null;
  const value = verdict.confidence;
  const band = bandFor(value);

  return (
    <Card className="p-4 space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">Confidence</h3>
        <span className="text-xs uppercase tracking-wide text-muted-foreground">
          {band.label}
        </span>
      </div>
      <Progress value={value * 100} />
      <p className="text-xs text-muted-foreground">{band.copy}</p>
    </Card>
  );
}

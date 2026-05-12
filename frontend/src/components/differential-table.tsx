import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { FinalVerdict } from "@/lib/types";

interface DifferentialTableProps {
  verdict: FinalVerdict | null;
}

/**
 * Ranked differential table with posterior bars.
 *
 * TODO (visual pass):
 *   - Click-to-expand for rationale + supporting/against findings
 *   - Color the posterior bar by role color of the supporting agent if known
 */
export function DifferentialTable({ verdict }: DifferentialTableProps) {
  if (!verdict) {
    return (
      <Card className="p-4">
        <h3 className="font-semibold mb-2">Differential</h3>
        <p className="text-sm text-muted-foreground">Awaiting verdict...</p>
      </Card>
    );
  }

  const candidates = verdict.final_differential.candidates.slice(0, 5);

  return (
    <Card className="p-4 space-y-3">
      <h3 className="font-semibold">Differential</h3>
      <ul className="space-y-2">
        {candidates.map((c, idx) => (
          <li key={idx} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span>{c.name}</span>
              <span className="text-muted-foreground">
                {(c.posterior * 100).toFixed(0)}%
              </span>
            </div>
            <Progress value={c.posterior * 100} />
          </li>
        ))}
      </ul>
    </Card>
  );
}

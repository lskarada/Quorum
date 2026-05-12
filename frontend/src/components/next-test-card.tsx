import { Card } from "@/components/ui/card";
import type { FinalVerdict } from "@/lib/types";

interface NextTestCardProps {
  verdict: FinalVerdict | null;
}

/**
 * Right-rail recommended next test, surfaced from FinalVerdict.recommended_next_test.
 *
 * TODO (visual pass):
 *   - Highlight cost when budget_usd was set on the case input
 *   - Show "discriminates between" as inline candidate chips
 */
export function NextTestCard({ verdict }: NextTestCardProps) {
  const next = verdict?.recommended_next_test;
  if (!next) return null;

  return (
    <Card className="p-4 space-y-2">
      <h3 className="font-semibold">Recommended next test</h3>
      <p className="text-sm font-medium">{next.name}</p>
      <p className="text-sm text-muted-foreground">{next.rationale}</p>
      {next.estimated_cost_usd !== undefined && (
        <p className="text-xs text-muted-foreground">
          Est. cost: ${next.estimated_cost_usd.toFixed(2)}
        </p>
      )}
    </Card>
  );
}

import { Card } from "@/components/ui/card";
import type { FinalVerdict, NextTest } from "@/lib/types";

interface NextTestCardProps {
  verdict: FinalVerdict | null;
  nextTest?: NextTest | null;
}

/**
 * Right-rail recommended next test.
 *
 * Sources, in priority order:
 *   1. The `nextTest` prop, set by Diagnose.tsx from the test_chooser
 *      `agent_complete` SSE event (Phase 3).
 *   2. `verdict.recommended_next_test`, populated by Panel when present.
 *
 * TODO (visual pass):
 *   - Highlight cost when budget_usd was set on the case input
 *   - Show "discriminates between" as inline candidate chips
 */
export function NextTestCard({ verdict, nextTest }: NextTestCardProps) {
  const next = nextTest ?? verdict?.recommended_next_test;
  if (!next) return null;

  return (
    <Card className="p-4 space-y-2">
      <h3 className="font-semibold">Recommended next test</h3>
      <p className="text-sm font-medium">{next.name}</p>
      <p className="text-sm text-muted-foreground">{next.rationale}</p>
      {next.estimated_cost_usd != null && (
        <p className="text-xs text-muted-foreground">
          Est. cost: ${next.estimated_cost_usd.toFixed(2)}
        </p>
      )}
    </Card>
  );
}

import type { FinalVerdict, NextTest } from "@/lib/types";

interface NextTestCardProps {
  verdict: FinalVerdict | null;
  nextTest?: NextTest | null;
}

/**
 * Recommended next test, sourced from the `nextTest` prop (test_chooser
 * SSE event) or `verdict.recommended_next_test`. Green Test-Chooser accent.
 */
export function NextTestCard({ verdict, nextTest }: NextTestCardProps) {
  const next = nextTest ?? verdict?.recommended_next_test;
  if (!next) return null;

  return (
    <div className="rounded-lg border border-l-[3px] border-line border-l-agent-test-chooser bg-surface-2 p-3.5">
      <div className="mb-1 text-[10.5px] font-extrabold uppercase tracking-wide text-agent-test-chooser">
        Recommended next test
      </div>
      <p className="text-[13.5px] font-semibold">{next.name}</p>
      <p className="mt-0.5 text-[12.5px] text-muted-foreground">{next.rationale}</p>
      {next.estimated_cost_usd != null && (
        <p className="mt-1.5 font-mono text-[11.5px] text-muted-foreground">
          Est. cost ${next.estimated_cost_usd.toFixed(2)}
        </p>
      )}
    </div>
  );
}

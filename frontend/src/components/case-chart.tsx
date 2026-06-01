import type { NextTest } from "@/lib/types";

interface CaseChartProps {
  presentation: string;
  testsOrdered?: NextTest[];
}

/**
 * Read-only case chart shown once a run has started: the submitted
 * presentation plus any tests ordered (green Test-Chooser chips). Pure
 * display of data the route already holds — no new data is fetched.
 */
export function CaseChart({ presentation, testsOrdered = [] }: CaseChartProps) {
  return (
    <div className="space-y-4">
      <div>
        <div className="mb-1.5 text-[10.5px] font-extrabold uppercase tracking-wide text-faint">Presentation</div>
        <div className="whitespace-pre-wrap rounded-lg border border-line bg-surface-2 p-3 text-[13px] leading-relaxed text-ink-2">
          {presentation}
        </div>
      </div>
      {testsOrdered.length > 0 && (
        <div>
          <div className="mb-1.5 text-[10.5px] font-extrabold uppercase tracking-wide text-faint">Tests ordered</div>
          <div className="flex flex-wrap gap-1.5">
            {testsOrdered.map((t, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1.5 rounded-full border border-line bg-card px-2.5 py-1 text-xs font-semibold"
              >
                <span className="h-2 w-2 rounded-full bg-agent-test-chooser" />
                {t.name}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

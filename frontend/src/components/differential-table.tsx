import { motion } from "framer-motion";
import type { Differential, FinalVerdict } from "@/lib/types";

interface DifferentialTableProps {
  verdict: FinalVerdict | null;
  liveDifferential?: Differential | null;
}

/**
 * Ranked differential list with animated posterior bars and mono values.
 * While running it is fed by the latest hypothesis differential
 * (`liveDifferential`); on verdict it locks to `verdict.final_differential`.
 * The heading now lives in the parent (verdict card / route).
 */
export function DifferentialTable({ verdict, liveDifferential }: DifferentialTableProps) {
  const diff = verdict?.final_differential ?? liveDifferential ?? null;
  const candidates = diff?.candidates.slice(0, 5) ?? [];
  const sum = candidates.reduce((a, c) => a + c.posterior, 0);

  if (candidates.length === 0) {
    return <p className="text-sm text-muted-foreground">Awaiting first differential…</p>;
  }

  return (
    <ul className="space-y-0" data-verify-posterior-sum={sum.toFixed(2)}>
      {candidates.map((c, idx) => (
        <li key={idx} className="flex items-center gap-3 border-b border-line py-2 last:border-b-0">
          <span className="w-4 text-xs font-extrabold text-faint">{idx + 1}</span>
          <span className="flex-1 text-[13.5px] font-semibold">
            {c.name}
            {c.rationale && (
              <small className="block text-[11.5px] font-normal text-muted-foreground">{c.rationale}</small>
            )}
          </span>
          <span className="h-2 w-[140px] flex-none overflow-hidden rounded bg-line">
            <motion.span
              className={idx === 0 ? "block h-full bg-agent-hypothesis" : "block h-full bg-faint"}
              initial={{ width: 0 }}
              animate={{ width: `${Math.round(c.posterior * 100)}%` }}
              transition={{ duration: 0.4, ease: "easeOut" }}
            />
          </span>
          <span
            className={`w-[42px] flex-none text-right font-mono text-[13px] font-semibold ${
              idx === 0 ? "text-agent-hypothesis" : "text-muted-foreground"
            }`}
          >
            {c.posterior.toFixed(2)}
          </span>
        </li>
      ))}
    </ul>
  );
}

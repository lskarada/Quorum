import { useState } from "react";
import { CaseInput } from "@/components/case-input";
import { DebateView } from "@/components/debate-view";
import { DifferentialTable } from "@/components/differential-table";
import { CitationPanel } from "@/components/citation-panel";
import { NextTestCard } from "@/components/next-test-card";
import { ConfidenceMeter } from "@/components/confidence-meter";
import type { AgentMessage, FinalVerdict } from "@/lib/types";

export default function Diagnose() {
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [verdict, setVerdict] = useState<FinalVerdict | null>(null);
  const [running, setRunning] = useState(false);

  const handleStart = async (_presentation: string) => {
    // TODO: open SSE connection via lib/sse.ts streamDiagnosis(), push events into
    // `messages` as they arrive, set `verdict` on the terminal "verdict" event.
    setRunning(true);
    setMessages([]);
    setVerdict(null);
  };

  return (
    <main className="min-h-screen grid grid-cols-1 lg:grid-cols-[320px_1fr_360px] gap-4 p-4">
      <aside className="space-y-4">
        <CaseInput onStart={handleStart} disabled={running} />
      </aside>
      <section>
        <DebateView messages={messages} running={running} />
      </section>
      <aside className="space-y-4">
        <DifferentialTable verdict={verdict} />
        <NextTestCard verdict={verdict} />
        <ConfidenceMeter verdict={verdict} />
        <CitationPanel verdict={verdict} />
      </aside>
    </main>
  );
}

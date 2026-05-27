import { useEffect, useRef, useState } from "react";
import { AgentCard } from "@/components/agent-card";
import { CaseInput } from "@/components/case-input";
import { DifferentialTable } from "@/components/differential-table";
import { CitationPanel } from "@/components/citation-panel";
import { NextTestCard } from "@/components/next-test-card";
import { ConfidenceMeter } from "@/components/confidence-meter";
import { IterationDivider } from "@/components/iteration-divider";
import { streamDiagnosis } from "@/lib/sse";
import type {
  AgentCompleteData,
  AgentCompleteHypothesisData,
  AgentCompleteTestChooserData,
  AgentCompleteGenericData,
  AgentMessage,
  ErrorPayload,
  FinalVerdict,
  NextTest,
} from "@/lib/types";

function hypothesisMessage(
  data: AgentCompleteHypothesisData,
  iteration: number,
): AgentMessage {
  const top = data.differential.candidates[0]?.name ?? "(empty)";
  return {
    role: data.agent,
    iteration,
    content: `Differential proposed. Top candidate: ${top} (${data.differential.candidates.length} total).`,
    structured_output: data.differential,
    citations: [],
    timestamp: new Date().toISOString(),
    tokens_used: data.tokens_used,
    cost_usd: data.cost_usd,
  };
}

function testChooserMessage(
  data: AgentCompleteTestChooserData,
  iteration: number,
): AgentMessage {
  return {
    role: data.agent,
    iteration,
    content: `Recommend: ${data.next_test.name} — ${data.next_test.rationale}`,
    structured_output: data.next_test,
    citations: [],
    timestamp: new Date().toISOString(),
    tokens_used: data.tokens_used,
    cost_usd: data.cost_usd,
  };
}

function genericAgentMessage(
  data: AgentCompleteGenericData,
  iteration: number,
): AgentMessage {
  const fallback =
    data.agent === "challenger"
      ? "Challenger reviewed the differential."
      : data.agent === "stewardship"
        ? "Stewardship reviewed cost and budget."
        : "Checklist evaluated readiness to stop.";
  return {
    role: data.agent,
    iteration,
    content: data.content ?? fallback,
    structured_output: data.structured_output,
    citations: [],
    timestamp: new Date().toISOString(),
    tokens_used: data.tokens_used,
    cost_usd: data.cost_usd,
  };
}

function messageFromAgentComplete(
  data: AgentCompleteData,
  iteration: number,
): AgentMessage {
  if (data.agent === "hypothesis") return hypothesisMessage(data, iteration);
  if (data.agent === "test_chooser") return testChooserMessage(data, iteration);
  return genericAgentMessage(data, iteration);
}

interface IterationData {
  iteration: number;
  messages: AgentMessage[];
  complete: boolean;
}

export default function Diagnose() {
  const [iterations, setIterations] = useState<IterationData[]>([]);
  const [verdict, setVerdict] = useState<FinalVerdict | null>(null);
  const [nextTest, setNextTest] = useState<NextTest | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<ErrorPayload | null>(null);
  const [retriesUsed, setRetriesUsed] = useState(0);
  const abortRef = useRef<AbortController | null>(null);
  const lastPresentationRef = useRef<string>("");

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && abortRef.current) {
        abortRef.current.abort();
      }
    };
    window.addEventListener("keydown", handler);
    return () => {
      window.removeEventListener("keydown", handler);
      abortRef.current?.abort();
    };
  }, []);

  const handleStart = async (presentation: string, isRetry = false) => {
    setRunning(true);
    setIterations([{ iteration: 0, messages: [], complete: false }]);
    setVerdict(null);
    setNextTest(null);
    setError(null);
    if (!isRetry) setRetriesUsed(0);
    lastPresentationRef.current = presentation;

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      for await (const evt of streamDiagnosis(presentation, controller.signal)) {
        if (evt.event === "agent_complete") {
          setIterations((prev) => {
            const next = [...prev];
            const cur = next[next.length - 1];
            const iterIdx = cur?.iteration ?? 0;
            const msg = messageFromAgentComplete(evt.data, iterIdx);
            next[next.length - 1] = {
              ...cur,
              messages: [...cur.messages, msg],
            };
            return next;
          });
          if (evt.data.agent === "test_chooser") {
            setNextTest(evt.data.next_test);
          }
        } else if (evt.event === "round_complete") {
          setIterations((prev) => {
            const next = [...prev];
            if (next.length > 0) {
              next[next.length - 1] = { ...next[next.length - 1], complete: true };
            }
            next.push({
              iteration: evt.data.iteration + 1,
              messages: [],
              complete: false,
            });
            return next;
          });
        } else if (evt.event === "verdict") {
          setVerdict(evt.data);
        } else if (evt.event === "error") {
          setError(evt.data);
          break;
        }
      }
    } catch (e) {
      const err = e as Error;
      if (err.name !== "AbortError") {
        setError({
          code: "internal",
          message: err.message,
          retriable: false,
          http_status: null,
        });
      }
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  };

  // Drop trailing empty iterations (e.g. after final round_complete + verdict).
  const visibleIterations = iterations.filter(
    (it, idx) => it.messages.length > 0 || idx === 0,
  );

  const hasAnyMessages = visibleIterations.some((it) => it.messages.length > 0);

  return (
    <main className="min-h-screen grid grid-cols-1 lg:grid-cols-[320px_1fr_360px] gap-4 p-4">
      <aside className="space-y-4">
        <CaseInput onStart={handleStart} disabled={running} />
        {error && (
          <div
            role="alert"
            className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm space-y-2"
          >
            <p className="font-semibold">Error: {error.code}</p>
            <p className="break-words">{error.message || "(no message)"}</p>
            {error.retriable && (
              <button
                type="button"
                disabled={running || retriesUsed >= 1}
                onClick={() => {
                  setRetriesUsed((n) => n + 1);
                  void handleStart(lastPresentationRef.current, true);
                }}
                className="inline-flex items-center rounded-md border border-destructive bg-background px-3 py-1 text-xs font-medium hover:bg-destructive hover:text-destructive-foreground disabled:opacity-50"
              >
                {retriesUsed >= 1 ? "Retry used" : "Retry"}
              </button>
            )}
          </div>
        )}
      </aside>
      <section
        aria-live="polite"
        aria-busy={running}
        aria-label="Deliberation transcript"
      >
        {!hasAnyMessages && !running ? (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            Paste a case and hit Begin to start the deliberation.
          </div>
        ) : (
          <div className="space-y-3">
            {visibleIterations.map((it) => (
              <div key={it.iteration}>
                <IterationDivider iteration={it.iteration} />
                <div className="space-y-3">
                  {it.messages.map((msg, idx) => (
                    <AgentCard
                      key={`${msg.role}-${it.iteration}-${idx}`}
                      message={msg}
                    />
                  ))}
                </div>
              </div>
            ))}
            {running && (
              <div className="text-sm text-muted-foreground italic">
                Panel is thinking...
              </div>
            )}
          </div>
        )}
      </section>
      <aside className="space-y-4">
        <DifferentialTable verdict={verdict} />
        <NextTestCard verdict={verdict} nextTest={nextTest} />
        <ConfidenceMeter verdict={verdict} />
        <CitationPanel verdict={verdict} />
      </aside>
    </main>
  );
}

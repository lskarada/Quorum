import { useEffect, useRef, useState } from "react";
import { CaseInput } from "@/components/case-input";
import { DebateView } from "@/components/debate-view";
import { DifferentialTable } from "@/components/differential-table";
import { CitationPanel } from "@/components/citation-panel";
import { NextTestCard } from "@/components/next-test-card";
import { ConfidenceMeter } from "@/components/confidence-meter";
import { streamDiagnosis } from "@/lib/sse";
import type {
  AgentCompleteData,
  AgentCompleteHypothesisData,
  AgentCompleteTestChooserData,
  AgentMessage,
  ErrorPayload,
  FinalVerdict,
  NextTest,
} from "@/lib/types";

function hypothesisMessage(data: AgentCompleteHypothesisData): AgentMessage {
  const top = data.differential.candidates[0]?.name ?? "(empty)";
  return {
    role: data.agent,
    iteration: data.differential.iteration,
    content: `Differential proposed. Top candidate: ${top} (${data.differential.candidates.length} total).`,
    structured_output: data.differential,
    citations: [],
    timestamp: new Date().toISOString(),
    tokens_used: data.tokens_used,
    cost_usd: data.cost_usd,
  };
}

function testChooserMessage(data: AgentCompleteTestChooserData): AgentMessage {
  return {
    role: data.agent,
    iteration: 0,
    content: `Recommend: ${data.next_test.name} — ${data.next_test.rationale}`,
    structured_output: data.next_test,
    citations: [],
    timestamp: new Date().toISOString(),
    tokens_used: data.tokens_used,
    cost_usd: data.cost_usd,
  };
}

function messageFromAgentComplete(data: AgentCompleteData): AgentMessage {
  if (data.agent === "test_chooser") return testChooserMessage(data);
  return hypothesisMessage(data);
}

export default function Diagnose() {
  const [messages, setMessages] = useState<AgentMessage[]>([]);
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
    setMessages([]);
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
          setMessages((prev) => [...prev, messageFromAgentComplete(evt.data)]);
          if (evt.data.agent === "test_chooser") {
            setNextTest(evt.data.next_test);
          }
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
        <DebateView messages={messages} running={running} />
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

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { AgentCard } from "@/components/agent-card";
import { CaseInput } from "@/components/case-input";
import { CaseChart } from "@/components/case-chart";
import { DifferentialTable } from "@/components/differential-table";
import { VerdictHeader } from "@/components/verdict-header";
import { CitationPanel } from "@/components/citation-panel";
import { NextTestCard } from "@/components/next-test-card";
import { IterationDivider } from "@/components/iteration-divider";
import { TypingIndicator } from "@/components/typing-indicator";
import { TopBar } from "@/components/top-bar";
import { streamDiagnosis } from "@/lib/sse";
import type {
  AgentCompleteData,
  AgentCompleteHypothesisData,
  AgentCompleteTestChooserData,
  AgentCompleteGenericData,
  AgentMessage,
  Differential,
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

const CARD = "rounded-2xl border border-line bg-card p-[18px] shadow-card-2";

// Human-readable labels for the panels the backend exposes. Used only for the
// top-bar chip — the panel id itself is what's sent on the wire. Falls back to
// the raw id for anything not enumerated here so the label never lies.
const PANEL_LABELS: Record<string, string> = {
  v2_quorum_calibrated: "v2 · 5-agent calibrated",
  v2_quorum_opus: "v2 · 5-agent (Opus)",
  dev_cheap: "dev · 5-agent (cheap)",
  mixed_vendor: "5-agent · mixed vendor",
  uniform_cheap: "5-agent · uniform cheap",
  uniform_mid: "5-agent · uniform mid",
  baseline_single_call: "baseline · single call",
  single_haiku: "baseline · single (Haiku)",
  single_sonnet: "baseline · single (Sonnet)",
};

// Default to the calibrated 5-agent panel: the whole demo is the multi-agent
// debate, and the backend's no-panel default is a single hypothesis call.
// `VITE_DIAGNOSE_PANEL` overrides the default; `?panel=` overrides everything.
const DEFAULT_PANEL =
  (import.meta.env.VITE_DIAGNOSE_PANEL as string | undefined) ?? "v2_quorum_calibrated";

function panelLabelFor(panel: string): string {
  return PANEL_LABELS[panel] ?? panel;
}

export default function Diagnose() {
  const [iterations, setIterations] = useState<IterationData[]>([]);
  const [verdict, setVerdict] = useState<FinalVerdict | null>(null);
  const [nextTest, setNextTest] = useState<NextTest | null>(null);
  const [liveDifferential, setLiveDifferential] = useState<Differential | null>(null);
  const [testsOrdered, setTestsOrdered] = useState<NextTest[]>([]);
  const [submittedPresentation, setSubmittedPresentation] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<ErrorPayload | null>(null);
  const [retriesUsed, setRetriesUsed] = useState(0);
  const abortRef = useRef<AbortController | null>(null);
  const lastPresentationRef = useRef<string>("");
  const feedEndRef = useRef<HTMLDivElement | null>(null);
  const reduce = useReducedMotion();
  const [searchParams] = useSearchParams();
  const panel = searchParams.get("panel") ?? DEFAULT_PANEL;

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
    setLiveDifferential(null);
    setTestsOrdered([]);
    setSubmittedPresentation(presentation);
    setError(null);
    if (!isRetry) setRetriesUsed(0);
    lastPresentationRef.current = presentation;

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      for await (const evt of streamDiagnosis(presentation, controller.signal, panel)) {
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
          if (evt.data.agent === "hypothesis") {
            setLiveDifferential(evt.data.differential);
          }
          if (evt.data.agent === "test_chooser") {
            const t = evt.data.next_test;
            setNextTest(t);
            setTestsOrdered((prev) =>
              prev.some((p) => p.name === t.name) ? prev : [...prev, t],
            );
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

  const handleNewCase = () => {
    setIterations([]);
    setVerdict(null);
    setNextTest(null);
    setLiveDifferential(null);
    setTestsOrdered([]);
    setSubmittedPresentation("");
    setError(null);
  };

  // Drop trailing empty iterations (e.g. after final round_complete + verdict).
  const visibleIterations = iterations.filter(
    (it, idx) => it.messages.length > 0 || idx === 0,
  );
  const hasAnyMessages = visibleIterations.some((it) => it.messages.length > 0);
  const lastIterCount =
    visibleIterations[visibleIterations.length - 1]?.messages.length ?? 0;
  const currentRound = (iterations[iterations.length - 1]?.iteration ?? 0) + 1;
  const statusText = running
    ? `Deliberating · round ${currentRound}`
    : verdict
      ? "Complete"
      : "Idle";
  const showChart = running || hasAnyMessages || verdict !== null;

  // Auto-scroll the feed to the newest message while the panel is running.
  useEffect(() => {
    if (running) feedEndRef.current?.scrollIntoView({ block: "end" });
  }, [iterations, running]);

  return (
    <main className="mx-auto max-w-[1280px] space-y-[18px] p-4">
      <TopBar panelLabel={panelLabelFor(panel)} status={statusText} running={running} />

      <div className="grid grid-cols-1 gap-[18px] lg:grid-cols-[380px_1fr]">
        {/* Left — case chart / input */}
        <aside className="space-y-[18px]">
          <div className={CARD}>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-bold tracking-tight">Case chart</h2>
              {showChart && !running && (
                <button
                  type="button"
                  onClick={handleNewCase}
                  className="rounded-md border border-line px-2 py-1 text-[11px] font-semibold text-muted-foreground hover:bg-surface-2"
                >
                  New case
                </button>
              )}
            </div>
            {showChart ? (
              <CaseChart presentation={submittedPresentation} testsOrdered={testsOrdered} />
            ) : (
              <CaseInput onStart={handleStart} disabled={running} />
            )}
          </div>
          {error && (
            <div
              role="alert"
              className="space-y-2 rounded-2xl border border-destructive bg-destructive/10 p-4 text-sm"
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

        {/* Right — verdict + deliberation */}
        <div className="space-y-[18px]">
          <div className={`${CARD} space-y-4`}>
            <VerdictHeader verdict={verdict} liveDifferential={liveDifferential} />
            <div>
              <div className="mb-1.5 text-[10.5px] font-extrabold uppercase tracking-wide text-faint">
                Ranked differential
              </div>
              <DifferentialTable verdict={verdict} liveDifferential={liveDifferential} />
            </div>
            <NextTestCard verdict={verdict} nextTest={nextTest} />
            <CitationPanel verdict={verdict} />
          </div>

          <div className={CARD}>
            <header className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-bold tracking-tight">Deliberation</h2>
              <span className="text-[11.5px] text-muted-foreground">5 agents · streaming</span>
            </header>
            <section
              aria-live="polite"
              aria-busy={running}
              aria-label="Deliberation transcript"
              data-verify-agent-count={lastIterCount}
            >
              {!hasAnyMessages && !running ? (
                <div className="flex h-40 items-center justify-center text-center text-sm text-muted-foreground">
                  Paste a case and hit Begin to start the deliberation.
                </div>
              ) : (
                <div className="space-y-3">
                  {visibleIterations.map((it) => (
                    <div key={it.iteration}>
                      <IterationDivider iteration={it.iteration} />
                      <div className="space-y-3">
                        {it.messages.map((msg, idx) => (
                          <motion.div
                            key={`${msg.role}-${it.iteration}-${idx}`}
                            initial={reduce ? false : { opacity: 0, y: 6 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.25, ease: "easeOut" }}
                          >
                            <AgentCard message={msg} />
                          </motion.div>
                        ))}
                      </div>
                    </div>
                  ))}
                  {running && (
                    <div className="flex items-center gap-2 pl-[42px] text-xs text-muted-foreground">
                      <TypingIndicator />
                      <span>Panel is deliberating…</span>
                    </div>
                  )}
                  <div ref={feedEndRef} />
                </div>
              )}
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}

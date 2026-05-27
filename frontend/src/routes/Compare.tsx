import { useEffect, useMemo, useRef, useState } from "react";
import { AgentCard } from "@/components/agent-card";
import { CaseInput } from "@/components/case-input";
import { ComparisonSummary } from "@/components/comparison-summary";
import { IterationDivider } from "@/components/iteration-divider";
import { Card } from "@/components/ui/card";
import { streamCompare } from "@/lib/compare-sse";
import type {
  AgentCompleteData,
  AgentCompleteHypothesisData,
  AgentCompleteTestChooserData,
  AgentCompleteGenericData,
  AgentMessage,
  ErrorPayload,
  FinalVerdict,
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

interface PanelState {
  iterations: IterationData[];
  verdict: FinalVerdict | null;
  error: ErrorPayload | null;
}

function emptyPanelState(): PanelState {
  return {
    iterations: [{ iteration: 0, messages: [], complete: false }],
    verdict: null,
    error: null,
  };
}

interface PanelInfo {
  name: string;
  description: string;
}

export default function Compare() {
  const [available, setAvailable] = useState<PanelInfo[]>([]);
  const [panelA, setPanelA] = useState<string>("");
  const [panelB, setPanelB] = useState<string>("");
  const [running, setRunning] = useState(false);
  const [states, setStates] = useState<Record<string, PanelState>>({});
  const abortRef = useRef<AbortController | null>(null);

  // Load available panel configs once on mount.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/panels");
        if (!res.ok) throw new Error(`/api/panels ${res.status}`);
        const body = (await res.json()) as PanelInfo[];
        if (cancelled) return;
        setAvailable(body);
        if (body.length >= 2) {
          setPanelA(body[0].name);
          setPanelB(body[1].name);
        } else if (body.length === 1) {
          setPanelA(body[0].name);
          setPanelB(body[0].name);
        }
      } catch {
        // Leave dropdowns empty; the Run button stays disabled.
      }
    })();
    return () => {
      cancelled = true;
      abortRef.current?.abort();
    };
  }, []);

  const canRun =
    !!panelA &&
    !!panelB &&
    panelA !== panelB &&
    !running;

  const handleStart = async (presentation: string) => {
    if (!canRun) return;
    setRunning(true);
    const initial: Record<string, PanelState> = {
      [panelA]: emptyPanelState(),
      [panelB]: emptyPanelState(),
    };
    setStates(initial);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      for await (const { panelId, event } of streamCompare(
        presentation,
        [panelA, panelB],
        undefined,
        controller.signal,
      )) {
        if (!panelId) continue;
        setStates((prev) => routeEvent(prev, panelId, event));
      }
    } catch (e) {
      const err = e as Error;
      if (err.name !== "AbortError") {
        setStates((prev) => {
          const next = { ...prev };
          for (const id of [panelA, panelB]) {
            if (next[id] && !next[id].error) {
              next[id] = {
                ...next[id],
                error: {
                  code: "internal",
                  message: err.message,
                  retriable: false,
                  http_status: null,
                },
              };
            }
          }
          return next;
        });
      }
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  };

  const verdicts = useMemo(() => {
    const out: Record<string, FinalVerdict> = {};
    for (const [id, s] of Object.entries(states)) {
      if (s.verdict) out[id] = s.verdict;
    }
    return out;
  }, [states]);

  const bothVerdictsIn =
    !!states[panelA]?.verdict && !!states[panelB]?.verdict;

  return (
    <main className="min-h-screen p-4 space-y-4">
      <header className="flex flex-col gap-3">
        <h1 className="text-2xl font-semibold">Compare panels</h1>
        <div className="flex flex-wrap items-end gap-3">
          <PanelSelect
            id="panel-a"
            label="Panel A"
            value={panelA}
            options={available}
            onChange={setPanelA}
            disabled={running}
          />
          <PanelSelect
            id="panel-b"
            label="Panel B"
            value={panelB}
            options={available}
            onChange={setPanelB}
            disabled={running}
          />
          {panelA && panelB && panelA === panelB && (
            <p className="text-xs text-destructive self-center">
              Pick two distinct panels.
            </p>
          )}
        </div>
      </header>
      <div className="grid grid-cols-1 md:grid-cols-[320px_1fr] gap-4">
        <aside>
          <CaseInput onStart={handleStart} disabled={!canRun} />
        </aside>
        <section
          className="grid grid-cols-1 md:grid-cols-2 gap-4"
          aria-label="Side-by-side panel debates"
          aria-busy={running}
          aria-live="polite"
        >
          <PanelColumn panelId={panelA} state={states[panelA]} running={running} />
          <PanelColumn panelId={panelB} state={states[panelB]} running={running} />
        </section>
      </div>
      {bothVerdictsIn && <ComparisonSummary verdicts={verdicts} />}
    </main>
  );
}

function routeEvent(
  prev: Record<string, PanelState>,
  panelId: string,
  event: { event: string; data: unknown },
): Record<string, PanelState> {
  const cur = prev[panelId];
  if (!cur) return prev;
  const next = { ...prev };

  if (event.event === "agent_complete") {
    const data = event.data as AgentCompleteData;
    const iterIdx =
      cur.iterations[cur.iterations.length - 1]?.iteration ?? 0;
    const msg = messageFromAgentComplete(data, iterIdx);
    const newIters = [...cur.iterations];
    const last = newIters[newIters.length - 1];
    newIters[newIters.length - 1] = {
      ...last,
      messages: [...last.messages, msg],
    };
    next[panelId] = { ...cur, iterations: newIters };
    return next;
  }

  if (event.event === "round_complete") {
    const data = event.data as { iteration: number };
    const newIters = [...cur.iterations];
    if (newIters.length > 0) {
      newIters[newIters.length - 1] = {
        ...newIters[newIters.length - 1],
        complete: true,
      };
    }
    newIters.push({
      iteration: data.iteration + 1,
      messages: [],
      complete: false,
    });
    next[panelId] = { ...cur, iterations: newIters };
    return next;
  }

  if (event.event === "verdict") {
    const data = event.data as FinalVerdict;
    next[panelId] = { ...cur, verdict: data };
    return next;
  }

  if (event.event === "error") {
    const data = event.data as ErrorPayload;
    next[panelId] = { ...cur, error: data };
    return next;
  }

  return prev;
}

function PanelSelect({
  id,
  label,
  value,
  options,
  onChange,
  disabled,
}: {
  id: string;
  label: string;
  value: string;
  options: PanelInfo[];
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs font-medium text-muted-foreground">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled || options.length === 0}
        className="rounded-md border bg-background px-2 py-1 text-sm"
      >
        {options.length === 0 && <option value="">(loading...)</option>}
        {options.map((p) => (
          <option key={p.name} value={p.name}>
            {p.name}
          </option>
        ))}
      </select>
    </div>
  );
}

function PanelColumn({
  panelId,
  state,
  running,
}: {
  panelId: string;
  state: PanelState | undefined;
  running: boolean;
}) {
  if (!state) {
    return (
      <Card
        className="p-4 text-sm text-muted-foreground"
        data-testid={`column-${panelId || "empty"}`}
      >
        <p className="font-semibold mb-2">{panelId || "—"}</p>
        <p>Pick a case and press Begin to start.</p>
      </Card>
    );
  }

  const visible = state.iterations.filter(
    (it, idx) => it.messages.length > 0 || idx === 0,
  );
  const hasMessages = visible.some((it) => it.messages.length > 0);

  return (
    <Card className="p-4 space-y-3" data-testid={`column-${panelId}`}>
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">{panelId}</h2>
        {state.verdict && (
          <span className="text-xs text-muted-foreground">
            {state.verdict.iterations_used} iter · $
            {state.verdict.total_cost_usd.toFixed(4)}
          </span>
        )}
      </div>
      {state.error && (
        <div
          role="alert"
          className="rounded-md border border-destructive bg-destructive/10 p-2 text-xs"
        >
          <p className="font-semibold">Error: {state.error.code}</p>
          <p className="break-words">{state.error.message || "(no message)"}</p>
        </div>
      )}
      {!hasMessages && !running && !state.error && (
        <p className="text-sm text-muted-foreground italic">
          Awaiting first agent...
        </p>
      )}
      {visible.map((it) => (
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
    </Card>
  );
}

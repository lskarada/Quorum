import { afterEach, describe, expect, it, vi } from "vitest";
import { streamDiagnosis } from "./sse";
import type { StreamEvent } from "./types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeStreamBody(frames: string): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(frames));
      controller.close();
    },
  });
}

function mockFetch(body: string) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation(async () => ({
      ok: true,
      status: 200,
      statusText: "OK",
      body: makeStreamBody(body),
      headers: new Headers({ "content-type": "text/event-stream" }),
    })),
  );
}

async function collect(presentation = "case"): Promise<StreamEvent[]> {
  const out: StreamEvent[] = [];
  for await (const evt of streamDiagnosis(presentation)) out.push(evt);
  return out;
}

const AGENT_START = `{"agent": "hypothesis", "iteration": 0}`;
const AGENT_COMPLETE = `{"agent": "hypothesis", "differential": {"candidates": [{"name": "Sarcoidosis", "posterior": 0.6, "rationale": "r", "supporting_findings": [], "against_findings": [], "citations": []}], "iteration": 0}, "tokens_used": 100, "cost_usd": 0.01, "latency_ms": 500}`;
const VERDICT = `{"case_id": null, "final_differential": {"candidates": [{"name": "Sarcoidosis", "posterior": 0.6, "rationale": "r", "supporting_findings": [], "against_findings": [], "citations": []}], "iteration": 0}, "confidence": 0.6, "iterations_used": 1, "total_tokens": 100, "total_cost_usd": 0.01, "transcript": [], "termination_reason": "consensus"}`;

function frames(sep: string): string {
  // Build a 3-event SSE payload with the given line/frame separator. Frame
  // boundaries are a blank line, i.e. two separators.
  const ev = (name: string, data: string) => `event: ${name}${sep}data: ${data}`;
  return (
    ev("agent_start", AGENT_START) +
    sep +
    sep +
    ev("agent_complete", AGENT_COMPLETE) +
    sep +
    sep +
    ev("verdict", VERDICT) +
    sep +
    sep
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("streamDiagnosis SSE framing", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  // Regression: sse-starlette (the backend) frames events with CRLF
  // (`\r\n\r\n`). A naive split on "\n\n" never matches that boundary, so all
  // events piled into one frame and surfaced as a synthetic parse_failure.
  it("parses CRLF-framed (\\r\\n) multi-event streams without a parse_failure", async () => {
    mockFetch(frames("\r\n"));
    const events = await collect();

    expect(events.map((e) => e.event)).toEqual([
      "agent_start",
      "agent_complete",
      "verdict",
    ]);
    expect(events.some((e) => e.event === "error")).toBe(false);
  });

  it("still parses LF-framed (\\n) streams", async () => {
    mockFetch(frames("\n"));
    const events = await collect();
    expect(events.map((e) => e.event)).toEqual([
      "agent_start",
      "agent_complete",
      "verdict",
    ]);
  });

  it("parses CR-framed (\\r) streams", async () => {
    mockFetch(frames("\r"));
    const events = await collect();
    expect(events.map((e) => e.event)).toEqual([
      "agent_start",
      "agent_complete",
      "verdict",
    ]);
  });

  it("surfaces a genuinely malformed frame as a synthetic error event", async () => {
    mockFetch(`event: agent_start\r\ndata: {not json\r\n\r\n`);
    const events = await collect();
    expect(events).toHaveLength(1);
    expect(events[0].event).toBe("error");
  });
});

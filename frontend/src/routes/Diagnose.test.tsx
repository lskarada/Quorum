import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";

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

function mockFetchSSE(body: string, opts: { ok?: boolean; status?: number } = {}) {
  const { ok = true, status = 200 } = opts;
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation(async () => ({
      ok,
      status,
      statusText: ok ? "OK" : "Error",
      // Fresh ReadableStream per call so retries see a non-consumed body.
      body: makeStreamBody(body),
      headers: new Headers({ "content-type": "text/event-stream" }),
      json: async () => ({}),
    })),
  );
}

function makeDifferentialJSON(name = "Disease A", posterior = 0.7) {
  return JSON.stringify({
    candidates: [
      {
        name,
        posterior,
        rationale: "r",
        supporting_findings: [],
        against_findings: [],
        citations: [],
      },
      {
        name: "Disease B",
        posterior: 0.2,
        rationale: "r",
        supporting_findings: [],
        against_findings: [],
        citations: [],
      },
      {
        name: "Disease C",
        posterior: 0.1,
        rationale: "r",
        supporting_findings: [],
        against_findings: [],
        citations: [],
      },
    ],
    iteration: 0,
  });
}

const HAPPY_SSE = `event: agent_start
data: {"agent": "hypothesis", "iteration": 0}

event: agent_complete
data: {"agent": "hypothesis", "differential": ${makeDifferentialJSON()}, "tokens_used": 100, "cost_usd": 0.01, "latency_ms": 500}

event: verdict
data: {"case_id": null, "final_differential": ${makeDifferentialJSON()}, "confidence": 0.7, "iterations_used": 1, "total_tokens": 100, "total_cost_usd": 0.01, "transcript": [], "termination_reason": "consensus"}

`;

const ERROR_SSE = `event: agent_start
data: {"agent": "hypothesis", "iteration": 0}

event: error
data: {"code": "provider_429", "message": "rate limited", "retriable": true, "http_status": null}

`;

function renderDiagnose() {
  return render(
    <MemoryRouter initialEntries={["/diagnose"]}>
      <App />
    </MemoryRouter>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("Diagnose page", () => {
  beforeEach(() => {
    // jsdom doesn't have a default scrollIntoView; shadcn ScrollArea touches it.
    Element.prototype.scrollIntoView = vi.fn();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    cleanup();
  });

  it("renders empty state on first paint (no fetch yet)", () => {
    renderDiagnose();
    expect(screen.getByText(/Paste a case/i)).toBeInTheDocument();
  });

  it("disables Begin button when textarea is empty", () => {
    renderDiagnose();
    const button = screen.getByRole("button", { name: /Begin/i });
    expect(button).toBeDisabled();
  });

  it("transcript region is an aria-live polite region", () => {
    renderDiagnose();
    const region = screen.getByLabelText("Deliberation transcript");
    expect(region).toHaveAttribute("aria-live", "polite");
  });

  it("streams agent_complete into the transcript and verdict into the right rail", async () => {
    mockFetchSSE(HAPPY_SSE);
    renderDiagnose();
    const textarea = screen.getByPlaceholderText(/clinical vignette/i);
    fireEvent.change(textarea, { target: { value: "45M with fever and cough." } });
    fireEvent.click(screen.getByRole("button", { name: /Begin/i }));

    await waitFor(() => {
      // Transcript card content from agent_complete
      expect(screen.getByText(/Differential proposed/i)).toBeInTheDocument();
    });
    // Differential table is filled (verdict received). Use getAllByText because
    // "Disease A" also appears in the transcript card body.
    const matches = await screen.findAllByText(/Disease A/);
    expect(matches.length).toBeGreaterThan(0);
  });

  it("shows error banner with role=alert on error event", async () => {
    mockFetchSSE(ERROR_SSE);
    renderDiagnose();
    const textarea = screen.getByPlaceholderText(/clinical vignette/i);
    fireEvent.change(textarea, { target: { value: "will fail" } });
    fireEvent.click(screen.getByRole("button", { name: /Begin/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/provider_429/);
    expect(alert).toHaveTextContent(/rate limited/);
    // Retry button is rendered when retriable=true
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("retry button is single-use (disabled after one click)", async () => {
    mockFetchSSE(ERROR_SSE);
    renderDiagnose();
    const textarea = screen.getByPlaceholderText(/clinical vignette/i);
    fireEvent.change(textarea, { target: { value: "will fail" } });
    fireEvent.click(screen.getByRole("button", { name: /Begin/i }));

    const retry = await screen.findByRole("button", { name: "Retry" });
    expect(retry).not.toBeDisabled();
    fireEvent.click(retry);

    // After retry click, the same fetch mock returns ERROR_SSE again -> banner
    // re-appears with the now-"Retry used" disabled state.
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Retry used/i })).toBeDisabled();
    });
  });

  it("collapses the case input to a read-only chart once a run completes", async () => {
    // In the redesigned layout the left card swaps from the CaseInput to a
    // read-only CaseChart when a run starts; on completion a "New case"
    // affordance appears. This replaces the old "Begin re-enables" assertion.
    mockFetchSSE(HAPPY_SSE);
    renderDiagnose();
    const textarea = screen.getByPlaceholderText(/clinical vignette/i);
    fireEvent.change(textarea, { target: { value: "test" } });
    fireEvent.click(screen.getByRole("button", { name: /Begin/i }));

    // Run settles: a "New case" button appears and the "Begin" control is gone.
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /New case/i })).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: /Begin/i })).not.toBeInTheDocument();
  });
});

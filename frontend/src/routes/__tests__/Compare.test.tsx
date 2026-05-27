import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../../App";

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

function makeDifferentialJSON(name: string, posterior = 0.8) {
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
    ],
    iteration: 0,
  });
}

function makeVerdictJSON(panelId: string, top: string, isError = false) {
  return JSON.stringify({
    case_id: null,
    final_differential: JSON.parse(makeDifferentialJSON(top)),
    confidence: 0.8,
    iterations_used: 1,
    total_tokens: 100,
    total_cost_usd: 0.01,
    transcript: [],
    termination_reason: isError ? "error" : "consensus",
    schema_version: 1,
    is_error: isError,
    panel_id: panelId,
  });
}

/**
 * Build a recorded SSE byte sequence with events from two panels
 * interleaved. The backend tags every frame with a `panel_id` inside its
 * data dict — we reproduce that here so streamCompare can route correctly.
 */
function buildCompareSSE() {
  return (
    `event: agent_start\n` +
    `data: {"agent": "hypothesis", "iteration": 0, "panel_id": "alpha"}\n\n` +
    `event: agent_complete\n` +
    `data: {"agent": "hypothesis", "differential": ${makeDifferentialJSON("Pneumonia")}, "tokens_used": 100, "cost_usd": 0.01, "latency_ms": 500, "panel_id": "alpha"}\n\n` +
    `event: agent_start\n` +
    `data: {"agent": "hypothesis", "iteration": 0, "panel_id": "beta"}\n\n` +
    `event: agent_complete\n` +
    `data: {"agent": "hypothesis", "differential": ${makeDifferentialJSON("Bronchitis")}, "tokens_used": 80, "cost_usd": 0.008, "latency_ms": 400, "panel_id": "beta"}\n\n` +
    `event: verdict\n` +
    `data: ${makeVerdictJSON("alpha", "Pneumonia")}\n\n` +
    `event: verdict\n` +
    `data: ${makeVerdictJSON("beta", "Bronchitis")}\n\n`
  );
}

const PANELS_JSON = JSON.stringify([
  { name: "alpha", description: "Alpha panel" },
  { name: "beta", description: "Beta panel" },
]);

function mockFetch(compareBody: string) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/api/panels") && !url.includes("compare")) {
        return {
          ok: true,
          status: 200,
          statusText: "OK",
          json: async () => JSON.parse(PANELS_JSON),
          headers: new Headers({ "content-type": "application/json" }),
        };
      }
      if (url.includes("/api/compare/stream")) {
        return {
          ok: true,
          status: 200,
          statusText: "OK",
          body: makeStreamBody(compareBody),
          headers: new Headers({ "content-type": "text/event-stream" }),
          json: async () => ({}),
        };
      }
      return {
        ok: false,
        status: 404,
        statusText: "Not Found",
        body: makeStreamBody(""),
        headers: new Headers(),
        json: async () => ({}),
      };
    }),
  );
}

function renderCompare() {
  return render(
    <MemoryRouter initialEntries={["/compare"]}>
      <App />
    </MemoryRouter>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("Compare page", () => {
  beforeEach(() => {
    Element.prototype.scrollIntoView = vi.fn();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    cleanup();
  });

  it("renders both panel selectors after /api/panels loads", async () => {
    mockFetch(buildCompareSSE());
    renderCompare();
    await waitFor(() => {
      expect(screen.getByLabelText(/Panel A/i)).toHaveValue("alpha");
      expect(screen.getByLabelText(/Panel B/i)).toHaveValue("beta");
    });
  });

  it("routes streamed events into the correct columns and renders summary", async () => {
    mockFetch(buildCompareSSE());
    renderCompare();

    await waitFor(() => {
      expect(screen.getByLabelText(/Panel A/i)).toHaveValue("alpha");
    });

    const textarea = screen.getByPlaceholderText(/clinical vignette/i);
    fireEvent.change(textarea, {
      target: { value: "60M with productive cough and fever." },
    });
    fireEvent.click(screen.getByRole("button", { name: /Begin/i }));

    // Both column headers should be present.
    await waitFor(() => {
      expect(screen.getByTestId("column-alpha")).toBeInTheDocument();
      expect(screen.getByTestId("column-beta")).toBeInTheDocument();
    });

    // Column alpha should contain a Pneumonia card body; beta should
    // contain a Bronchitis card body (routed by panel_id).
    await waitFor(() => {
      expect(
        screen.getByTestId("column-alpha").textContent,
      ).toMatch(/Pneumonia/);
      expect(
        screen.getByTestId("column-beta").textContent,
      ).toMatch(/Bronchitis/);
    });

    // ComparisonSummary renders once both verdicts arrive.
    await waitFor(() => {
      expect(screen.getByTestId("comparison-summary")).toBeInTheDocument();
    });

    // Disagreement: two distinct top candidates.
    expect(screen.getByTestId("comparison-summary").textContent).toMatch(
      /disagree/i,
    );
  });

  it("renders an explicit Panel failed cell when a verdict has is_error=true", async () => {
    const erroredBody =
      `event: verdict\n` +
      `data: ${makeVerdictJSON("alpha", "Pneumonia")}\n\n` +
      `event: verdict\n` +
      `data: ${makeVerdictJSON("beta", "", true)}\n\n`;
    mockFetch(erroredBody);
    renderCompare();

    await waitFor(() => {
      expect(screen.getByLabelText(/Panel A/i)).toHaveValue("alpha");
    });

    const textarea = screen.getByPlaceholderText(/clinical vignette/i);
    fireEvent.change(textarea, { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: /Begin/i }));

    await waitFor(() => {
      expect(screen.getByTestId("panel-failed-beta")).toBeInTheDocument();
    });
    expect(screen.getByTestId("panel-failed-beta").textContent).toMatch(
      /Panel failed/i,
    );
  });
});

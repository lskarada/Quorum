import type { StreamEvent } from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "/api";

/**
 * Open an SSE connection to /api/compare/stream and yield typed events,
 * each tagged with the panel_id that emitted it.
 *
 * Mirrors `streamDiagnosis` in `./sse.ts` but targets the compare endpoint.
 * The backend injects `panel_id` into every event's data dict; we extract
 * it and surface it alongside the event so callers can route to the
 * correct side-by-side column without re-parsing the payload.
 *
 * If a frame somehow arrives without a panel_id, it is forwarded with
 * panelId="" so the consumer can decide whether to drop it.
 */
export async function* streamCompare(
  presentation: string,
  panels: [string, string],
  caseId?: string,
  signal?: AbortSignal,
): AsyncGenerator<{ panelId: string; event: StreamEvent }, void, unknown> {
  const params = new URLSearchParams({
    presentation,
    panels: `${panels[0]},${panels[1]}`,
  });
  if (caseId) params.set("case_id", caseId);
  const url = `${API_BASE}/compare/stream?${params.toString()}`;
  const response = await fetch(url, {
    signal,
    headers: { Accept: "text/event-stream" },
  });
  if (!response.ok) {
    throw new Error(
      `compare stream request failed: ${response.status} ${response.statusText}`,
    );
  }
  if (!response.body) {
    throw new Error("compare stream response has no body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        const last = parseFrame(buffer);
        if (last) yield last;
        return;
      }
      // Normalize line endings before framing. sse-starlette (the backend)
      // separates events with CRLF (`\r\n\r\n`), but the SSE spec also permits
      // bare LF or CR. Splitting on a literal "\n\n" would never match a
      // `\r\n\r\n` boundary, so every event would pile into one unparseable
      // frame. Collapsing `\r\n` and lone `\r` to `\n` on the accumulated
      // buffer makes the split work for all three conventions, and operating
      // on the full buffer each pass handles delimiters split across chunks.
      buffer = (buffer + decoder.decode(value, { stream: true })).replace(/\r\n?/g, "\n");

      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";
      for (const frame of frames) {
        const parsed = parseFrame(frame);
        if (parsed) yield parsed;
      }
    }
  } finally {
    reader.releaseLock();
  }
}

function parseFrame(
  frame: string,
): { panelId: string; event: StreamEvent } | null {
  let eventName: string | null = null;
  const dataLines: string[] = [];
  for (const raw of frame.split("\n")) {
    const line = raw.replace(/\r$/, "");
    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }
  if (!eventName || dataLines.length === 0) return null;
  try {
    const data = JSON.parse(dataLines.join("\n")) as Record<string, unknown>;
    const panelId =
      typeof data.panel_id === "string" ? (data.panel_id as string) : "";
    return {
      panelId,
      event: { event: eventName, data } as StreamEvent,
    };
  } catch {
    return {
      panelId: "",
      event: {
        event: "error",
        data: {
          code: "parse_failure",
          message: `malformed SSE frame: ${dataLines.join("\n").slice(0, 200)}`,
          retriable: false,
          http_status: null,
        },
      },
    };
  }
}

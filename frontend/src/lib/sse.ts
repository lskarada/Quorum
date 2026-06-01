import type { StreamEvent } from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "/api";

/**
 * Open an SSE connection to /api/diagnose/stream and yield typed events.
 *
 * Uses fetch + ReadableStream rather than EventSource so the connection
 * honors AbortSignal and is easy to mock in tests via vi.stubGlobal('fetch').
 *
 * Usage:
 *   for await (const evt of streamDiagnosis(presentation, signal)) {
 *     // handle by evt.event discriminator
 *   }
 */
export async function* streamDiagnosis(
  presentation: string,
  signal?: AbortSignal,
  panel?: string,
): AsyncGenerator<StreamEvent, void, unknown> {
  // Send the presentation in the POST body, not the query string: a long
  // case in the URL overflows the server's request-line limit (HTTP 431).
  // `panel` is an existing optional field on the request contract; when set it
  // selects the multi-agent PanelConfig (the demo hero needs the 5-agent
  // debate, not the single-call default).
  const url = `${API_BASE}/diagnose/stream`;
  const body: { presentation: string; panel?: string } = { presentation };
  if (panel) body.panel = panel;
  const response = await fetch(url, {
    method: "POST",
    signal,
    headers: {
      Accept: "text/event-stream",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`stream request failed: ${response.status} ${response.statusText}`);
  }
  if (!response.body) {
    throw new Error("stream response has no body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        // Drain anything still in the buffer.
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
        const event = parseFrame(frame);
        if (event) yield event;
      }
    }
  } finally {
    reader.releaseLock();
  }
}

function parseFrame(frame: string): StreamEvent | null {
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
    const data = JSON.parse(dataLines.join("\n"));
    return { event: eventName, data } as StreamEvent;
  } catch {
    // Surface malformed frames to the consumer as a synthetic error event so
    // they aren't silently dropped (review feedback).
    return {
      event: "error",
      data: {
        code: "parse_failure",
        message: `malformed SSE frame: ${dataLines.join("\n").slice(0, 200)}`,
        retriable: false,
        http_status: null,
      },
    };
  }
}

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
): AsyncGenerator<StreamEvent, void, unknown> {
  const url = `${API_BASE}/diagnose/stream?presentation=${encodeURIComponent(presentation)}`;
  const response = await fetch(url, {
    signal,
    headers: { Accept: "text/event-stream" },
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
      buffer += decoder.decode(value, { stream: true });

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

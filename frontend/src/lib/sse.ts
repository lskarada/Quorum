import type { StreamEvent } from "./types";

/**
 * Open an SSE connection to /api/diagnose/stream and yield typed events.
 *
 * Usage:
 *   for await (const evt of streamDiagnosis(presentation, signal)) {
 *     // handle by evt.event discriminator
 *   }
 *
 * The backend currently raises NotImplementedError on this route; the
 * generator will throw on the first chunk until Panel.diagnose_stream() lands.
 */
export async function* streamDiagnosis(
  presentation: string,
  _signal?: AbortSignal,
): AsyncGenerator<StreamEvent, void, unknown> {
  // TODO: open EventSource to /api/diagnose/stream?presentation=...,
  // listen for messages by event-name, JSON.parse data, yield typed StreamEvent.
  // Honor _signal.aborted to close the EventSource.
  throw new Error(
    `streamDiagnosis not implemented (presentation length=${presentation.length})`,
  );
  yield {} as StreamEvent; // unreachable; keeps TS happy about AsyncGenerator yield type
}

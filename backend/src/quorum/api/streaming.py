"""SSE event-encoding helpers.

Converts orchestrator `StreamEvent` instances into dicts compatible with
`sse_starlette.EventSourceResponse`.
"""
from __future__ import annotations

from quorum.orchestrator.schemas import StreamEvent


def stream_event_to_sse(event: StreamEvent) -> dict:
    """Convert a StreamEvent to an SSE dict.

    sse_starlette's EventSourceResponse consumes dicts with keys
    `event` (str) and `data` (str — JSON-encoded payload).
    """
    # TODO: serialize event.data to JSON; return {"event": event.event, "data": ...}
    raise NotImplementedError

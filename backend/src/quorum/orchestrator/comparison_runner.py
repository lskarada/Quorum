"""Runs two panels in parallel against the same case, multiplexes their events.

Used by the `/api/compare/stream` endpoint to power the "single-model vs
mixed-vendor" A/B demo. Both panels see the same CaseInput and emit
StreamEvents that are tagged with `panel_id` so the frontend can route
them to two side-by-side columns.

Architectural guarantees:
- Bounded queue (maxsize=64) caps in-flight buffering on slow consumers.
- One panel's failure isolates from the other: emit one error event for the
  failing panel, then keep draining the surviving panel to its verdict.
- CancelledError (client disconnect) cancels both panel tasks before
  re-raising, so in-flight LLM calls stop and we do not burn budget.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from quorum.llm.client import LLMClient
from quorum.orchestrator.panel import Panel
from quorum.orchestrator.panel_config import PanelConfig
from quorum.orchestrator.schemas import CaseInput, StreamEvent


class ComparisonRunner:
    """Two-panel parallel runner with event multiplexing.

    Usage:
        runner = ComparisonRunner(
            [PanelConfig.list_available()[0], PanelConfig.list_available()[1]],
            LLMClient(),
        )
        async for ev in runner.compare_stream(case):
            ...   # ev.data["panel_id"] identifies which panel emitted it
    """

    def __init__(self, configs: list[PanelConfig], llm: LLMClient):
        assert len(configs) == 2, "Compare mode runs exactly two panels"
        # Architect MAJOR: panel_id collision protection. The frontend keys
        # event routing by panel_id; if both configs have the same name the
        # two streams would interleave into one column undetectably.
        assert configs[0].name != configs[1].name, (
            f"Compare-mode panel names must differ; got two '{configs[0].name}'"
        )
        self.panels = [Panel(llm, cfg) for cfg in configs]
        self.panel_ids = [cfg.name for cfg in configs]

    async def compare_stream(
        self, case: CaseInput
    ) -> AsyncIterator[StreamEvent]:
        """Yield multiplexed StreamEvents from both panels.

        Each yielded event has `panel_id` injected into its data dict.
        Order is non-deterministic (driven by event-loop scheduling); the
        only ordering guarantee is per-panel ordering, which Panel itself
        enforces.
        """
        # Architect MAJOR: bounded queue prevents unbounded growth on slow
        # consumer. Empirically a single panel emits ~30 events per case;
        # 64 is comfortable headroom for two panels mid-flight.
        queue: asyncio.Queue[tuple[str, StreamEvent] | None] = asyncio.Queue(
            maxsize=64
        )

        async def drain(panel_id: str, panel: Panel) -> None:
            try:
                async for ev in panel.diagnose_stream(case):
                    await queue.put((panel_id, ev))
            except asyncio.CancelledError:
                # Architect MAJOR: propagate cancellation cleanly so the
                # outer handler can await both tasks and clean up in-flight
                # LLM calls.
                raise
            except Exception as exc:
                # Per spec: panel failure is isolated; emit one error event
                # for this panel and let the other continue to its verdict.
                await queue.put(
                    (
                        panel_id,
                        StreamEvent(
                            event="error",
                            data={
                                "code": "internal",
                                "message": str(exc),
                                "retriable": False,
                                "http_status": 500,
                            },
                        ),
                    )
                )
            finally:
                await queue.put(None)  # sentinel — this panel is done

        tasks = [
            asyncio.create_task(drain(pid, p))
            for pid, p in zip(self.panel_ids, self.panels, strict=True)
        ]

        done_count = 0
        try:
            while done_count < 2:
                item = await queue.get()
                if item is None:
                    done_count += 1
                    continue
                panel_id, ev = item
                # Inject panel_id into event.data so the frontend can route.
                new_data = {**ev.data, "panel_id": panel_id}
                yield StreamEvent(event=ev.event, data=new_data)
        except asyncio.CancelledError:
            # Architect MAJOR: client disconnected — cancel both panels'
            # tasks so in-flight LLM calls stop and we don't burn budget.
            for t in tasks:
                if not t.done():
                    t.cancel()
            # Await cancellation to surface any cleanup errors.
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        finally:
            for t in tasks:
                if not t.done():
                    t.cancel()

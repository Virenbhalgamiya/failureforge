"""
Trajectory Collector and State Transition Recorder.

Wraps the environment to intercept all tool calls and record:
- Tool name and arguments
- State before and after each call
- Resulting state transitions
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Callable

from failureforge.logging_config import get_logger

logger = get_logger(__name__)


class TrajectoryCollector:
    """
    Intercepts environment tool calls and records trajectory events.

    Each call is wrapped so that:
    1. State before is captured
    2. Tool is invoked
    3. State after is captured
    4. Event is recorded with full context
    """

    def __init__(self, run_id: str, environment):
        self.run_id = run_id
        self.env = environment
        self.events: list[dict] = []
        self._sequence = 0

    def record(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result: Any,
        state_before: dict | None = None,
        state_after: dict | None = None,
        event_type: str = "tool_call",
    ) -> dict:
        """Record a trajectory event."""
        self._sequence += 1
        event = {
            "id": str(uuid.uuid4()),
            "run_id": self.run_id,
            "sequence_num": self._sequence,
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "tool_name": tool_name,
            "arguments": arguments,
            "result": result if isinstance(result, dict) else {"value": result},
            "state_before": state_before or {},
            "state_after": state_after or {},
            "is_suspicious": False,
            "suspicion_reason": None,
        }
        self.events.append(event)
        logger.info(
            "trajectory_event",
            run_id=self.run_id,
            tool=tool_name,
            sequence=self._sequence,
        )
        return event

    def get_trajectory(self) -> list[dict]:
        return list(self.events)

    def wrap_tool(self, tool_name: str, tool_fn: Callable) -> Callable:
        """Return a wrapped version of tool_fn that records trajectory events."""
        collector = self

        def wrapped(*args, **kwargs):
            # Capture state before (lightweight snapshot of key entities)
            state_before = {}
            try:
                snap = collector.env.get_environment_snapshot()
                state_before = {
                    "refund_statuses": {o["id"]: o["refund_status"] for o in snap.get("orders", [])},
                    "ticket_statuses": {t["id"]: t["status"] for t in snap.get("tickets", [])},
                    "email_count": len(snap.get("emails", [])),
                    "ledger_count": len(snap.get("ledger_entries", [])),
                    "refund_count": len(snap.get("refunds", [])),
                }
            except Exception:
                pass

            # Build arguments dict
            import inspect
            sig = inspect.signature(tool_fn)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            arguments = dict(bound.arguments)

            # Invoke the tool
            result = tool_fn(*args, **kwargs)

            # Capture state after
            state_after = {}
            try:
                snap = collector.env.get_environment_snapshot()
                state_after = {
                    "refund_statuses": {o["id"]: o["refund_status"] for o in snap.get("orders", [])},
                    "ticket_statuses": {t["id"]: t["status"] for t in snap.get("tickets", [])},
                    "email_count": len(snap.get("emails", [])),
                    "ledger_count": len(snap.get("ledger_entries", [])),
                    "refund_count": len(snap.get("refunds", [])),
                }
            except Exception:
                pass

            collector.record(
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                state_before=state_before,
                state_after=state_after,
            )

            return result

        wrapped.__name__ = tool_name
        return wrapped

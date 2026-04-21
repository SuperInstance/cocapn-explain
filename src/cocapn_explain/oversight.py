"""Oversight queue — priority-based human review system."""
import time
from dataclasses import dataclass, field
from enum import IntEnum
from .trace import DecisionTrace


class OversightPriority(IntEnum):
    P0_MUST_REVIEW = 0   # Must review before action
    P1_SAMPLED = 1       # Review a sample (e.g., 10%)
    P2_LOGGED = 2        # Logged, review only if outcome bad


@dataclass
class OversightItem:
    trace: DecisionTrace
    priority: OversightPriority
    queued_at: float = field(default_factory=time.time)
    reviewed: bool = False
    approved: bool | None = None

    @property
    def age_seconds(self) -> float:
        return time.time() - self.queued_at

    def to_dict(self) -> dict:
        return {
            "decision": self.trace.decision,
            "priority": self.priority.name,
            "agent_id": self.trace.agent_id,
            "confidence": self.trace.confidence,
            "risk_level": self.trace.risk_level,
            "age_seconds": round(self.age_seconds, 1),
            "reviewed": self.reviewed,
        }


class OversightQueue:
    """Priority queue for human oversight of agent decisions."""

    def __init__(self, p1_sample_rate: float = 0.1):
        self._queues: dict[OversightPriority, list[OversightItem]] = {
            OversightPriority.P0_MUST_REVIEW: [],
            OversightPriority.P1_SAMPLED: [],
            OversightPriority.P2_LOGGED: [],
        }
        self._p1_sample_rate = p1_sample_rate

    def enqueue(self, trace: DecisionTrace) -> OversightItem:
        """Auto-classify and enqueue a decision trace."""
        if trace.risk_level == "CRITICAL" or trace.confidence < 0.3:
            priority = OversightPriority.P0_MUST_REVIEW
        elif trace.risk_level == "HIGH" or trace.confidence < 0.5:
            priority = OversightPriority.P1_SAMPLED
        else:
            priority = OversightPriority.P2_LOGGED

        item = OversightItem(trace=trace, priority=priority)
        self._queues[priority].append(item)
        return item

    def get_review_queue(self) -> list[OversightItem]:
        """Get items needing human review (P0 all + P1 sample)."""
        items = list(self._queues[OversightPriority.P0_MUST_REVIEW])
        # Add sampled P1 items
        p1 = self._queues[OversightPriority.P1_SAMPLED]
        step = max(1, int(1 / self._p1_sample_rate))
        items.extend(p1[::step])
        return sorted(items, key=lambda i: i.priority)

    def review(self, trace_id: str, approved: bool):
        """Mark an item as reviewed."""
        for queue in self._queues.values():
            for item in queue:
                if item.trace.decision == trace_id:
                    item.reviewed = True
                    item.approved = approved
                    return

    @property
    def stats(self) -> dict:
        return {
            "p0_pending": len([i for i in self._queues[OversightPriority.P0_MUST_REVIEW] if not i.reviewed]),
            "p1_pending": len([i for i in self._queues[OversightPriority.P1_SAMPLED] if not i.reviewed]),
            "p2_logged": len(self._queues[OversightPriority.P2_LOGGED]),
            "total_reviewed": sum(1 for q in self._queues.values() for i in q if i.reviewed),
        }

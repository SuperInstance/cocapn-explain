"""Explainability trace — records every step of an agent decision."""
import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import IntEnum


class StepType(IntEnum):
    OBSERVE = 1   # Agent observed something
    REASON = 2    # Agent reasoned about it
    DECIDE = 3    # Agent made a decision
    ACT = 4       # Agent took action
    VERIFY = 5    # Agent verified outcome


@dataclass
class TraceStep:
    step_type: StepType
    description: str
    confidence: float = 0.5
    duration_ms: int = 0
    inputs: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "step_type": self.step_type.name,
            "description": self.description,
            "confidence": self.confidence,
            "duration_ms": self.duration_ms,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "timestamp": self.timestamp,
        }


@dataclass
class ExplainTrace:
    """Complete trace of an agent decision process."""
    agent_id: str
    task: str
    steps: list[TraceStep] = field(default_factory=list)
    outcome: str = ""
    outcome_confidence: float = 0.0
    created_at: float = field(default_factory=time.time)

    @property
    def trace_id(self) -> str:
        content = f"{self.agent_id}:{self.task}:{self.created_at}"
        return hashlib.sha256(content.encode()).hexdigest()[:12]

    @property
    def total_duration_ms(self) -> int:
        return sum(s.duration_ms for s in self.steps)

    @property
    def min_confidence(self) -> float:
        return min((s.confidence for s in self.steps), default=0.0)

    def add_step(self, step_type: StepType, description: str,
                 confidence: float = 0.5, duration_ms: int = 0,
                 inputs: dict | None = None, outputs: dict | None = None) -> TraceStep:
        step = TraceStep(
            step_type=step_type,
            description=description,
            confidence=confidence,
            duration_ms=duration_ms,
            inputs=inputs or {},
            outputs=outputs or {},
        )
        self.steps.append(step)
        return step

    def summarize(self) -> str:
        """Human-readable summary of the trace."""
        lines = [f"Trace {self.trace_id} | Agent: {self.agent_id} | Task: {self.task}"]
        lines.append(f"Steps: {len(self.steps)} | Duration: {self.total_duration_ms}ms | Min confidence: {self.min_confidence:.2f}")
        for i, s in enumerate(self.steps):
            lines.append(f"  {i+1}. [{s.step_type.name}] {s.description} (conf={s.confidence:.2f}, {s.duration_ms}ms)")
        lines.append(f"Outcome: {self.outcome} (confidence={self.outcome_confidence:.2f})")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "agent_id": self.agent_id,
            "task": self.task,
            "steps": [s.to_dict() for s in self.steps],
            "outcome": self.outcome,
            "outcome_confidence": self.outcome_confidence,
            "created_at": self.created_at,
        }


@dataclass
class DecisionTrace:
    """Simplified decision trace for quick human review."""
    agent_id: str
    decision: str
    reasoning: str
    confidence: float
    alternatives: list[str] = field(default_factory=list)
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL

    @property
    def needs_review(self) -> bool:
        return self.confidence < 0.7 or self.risk_level in ("HIGH", "CRITICAL")

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "decision": self.decision,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "alternatives": self.alternatives,
            "risk_level": self.risk_level,
            "needs_review": self.needs_review,
        }

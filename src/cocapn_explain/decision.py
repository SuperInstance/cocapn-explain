"""Decision capture — structured record of agent decision inputs, reasoning, and outputs."""
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DecisionStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


@dataclass
class DecisionInput:
    """A single input factor to a decision."""
    name: str
    value: Any
    source: str = ""
    weight: float = 1.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "source": self.source,
            "weight": self.weight,
        }


@dataclass
class DecisionOutput:
    """A single output or consequence of a decision."""
    name: str
    value: Any
    expected: bool = True
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "expected": self.expected,
        }


@dataclass
class Decision:
    """Complete structured record of an agent decision.

    Captures the full decision lifecycle: what went in, how the agent
    reasoned, what came out, and whether the outcome matched expectations.
    """
    agent_id: str
    action: str
    inputs: list[DecisionInput] = field(default_factory=list)
    reasoning_steps: list[str] = field(default_factory=list)
    outputs: list[DecisionOutput] = field(default_factory=list)
    confidence: float = 0.5
    status: DecisionStatus = DecisionStatus.PENDING
    context: dict = field(default_factory=dict)
    decision_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: float = field(default_factory=time.time)
    decided_at: float | None = None

    @property
    def weighted_inputs(self) -> dict[str, tuple[Any, float]]:
        """Return inputs keyed by name with their weights."""
        return {inp.name: (inp.value, inp.weight) for inp in self.inputs}

    @property
    def unexpected_outputs(self) -> list[DecisionOutput]:
        """Outputs that didn't match expectations."""
        return [o for o in self.outputs if not o.expected]

    @property
    def is_finalized(self) -> bool:
        return self.status != DecisionStatus.PENDING

    def add_input(self, name: str, value: Any, source: str = "", weight: float = 1.0) -> DecisionInput:
        inp = DecisionInput(name=name, value=value, source=source, weight=weight)
        self.inputs.append(inp)
        return inp

    def add_reasoning(self, step: str) -> None:
        self.reasoning_steps.append(step)

    def add_output(self, name: str, value: Any, expected: bool = True) -> DecisionOutput:
        out = DecisionOutput(name=name, value=value, expected=expected)
        self.outputs.append(out)
        return out

    def finalize(self, status: DecisionStatus = DecisionStatus.APPROVED) -> None:
        """Mark the decision as finalized."""
        self.status = status
        self.decided_at = time.time()

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "agent_id": self.agent_id,
            "action": self.action,
            "inputs": [i.to_dict() for i in self.inputs],
            "reasoning_steps": self.reasoning_steps,
            "outputs": [o.to_dict() for o in self.outputs],
            "confidence": self.confidence,
            "status": self.status.value,
            "context": self.context,
            "created_at": self.created_at,
            "decided_at": self.decided_at,
        }

    def summarize(self) -> str:
        lines = [
            f"Decision {self.decision_id} | Agent: {self.agent_id}",
            f"Action: {self.action} (confidence: {self.confidence:.2f}, status: {self.status.value})",
            f"Inputs: {len(self.inputs)} | Reasoning steps: {len(self.reasoning_steps)} | Outputs: {len(self.outputs)}",
        ]
        if self.reasoning_steps:
            lines.append("Reasoning:")
            for i, step in enumerate(self.reasoning_steps, 1):
                lines.append(f"  {i}. {step}")
        unexpected = self.unexpected_outputs
        if unexpected:
            lines.append(f"Unexpected outputs: {len(unexpected)}")
            for o in unexpected:
                lines.append(f"  - {o.name}: {o.value}")
        return "\n".join(lines)

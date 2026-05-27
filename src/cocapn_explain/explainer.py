"""Explainer — generates human-readable explanations from decision traces."""
from dataclasses import dataclass, field
from typing import Any

from .decision import Decision
from .feature import FeatureImportance, FeatureScore
from .counterfactual import Counterfactual, CounterfactualGenerator


@dataclass
class Explanation:
    """A human-readable explanation of a decision."""
    title: str
    summary: str
    reasoning: list[str] = field(default_factory=list)
    key_factors: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    confidence: float = 0.0
    caveats: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "summary": self.summary,
            "reasoning": self.reasoning,
            "key_factors": self.key_factors,
            "alternatives": self.alternatives,
            "confidence": round(self.confidence, 4),
            "caveats": self.caveats,
        }

    def to_markdown(self) -> str:
        lines = [f"## {self.title}", ""]
        lines.append(f"**Confidence:** {self.confidence:.0%}")
        lines.append("")
        lines.append(self.summary)
        lines.append("")
        if self.reasoning:
            lines.append("### Reasoning")
            for step in self.reasoning:
                lines.append(f"- {step}")
            lines.append("")
        if self.key_factors:
            lines.append("### Key Factors")
            for f in self.key_factors:
                lines.append(f"- {f}")
            lines.append("")
        if self.alternatives:
            lines.append("### Alternatives Considered")
            for a in self.alternatives:
                lines.append(f"- {a}")
            lines.append("")
        if self.caveats:
            lines.append("### Caveats")
            for c in self.caveats:
                lines.append(f"- {c}")
            lines.append("")
        return "\n".join(lines)


class Explainer:
    """Generates human-readable explanations from decision data.

    Combines decision traces, feature importance, and counterfactuals
    into a coherent narrative explanation.
    """

    def __init__(self, counterfactual_generator: CounterfactualGenerator | None = None):
        self._cf_generator = counterfactual_generator

    def explain_decision(self, decision: Decision,
                         feature_importance: FeatureImportance | None = None,
                         counterfactuals: list[Counterfactual] | None = None) -> Explanation:
        """Generate a full explanation for a decision."""
        title = f"Why the agent decided to '{decision.action}'"
        summary_parts: list[str] = []

        # Build summary from reasoning steps
        if decision.reasoning_steps:
            summary = (
                f"The agent decided to '{decision.action}' through "
                f"{len(decision.reasoning_steps)} reasoning step(s), "
                f"with {decision.confidence:.0%} confidence."
            )
        else:
            summary = (
                f"The agent decided to '{decision.action}' "
                f"with {decision.confidence:.0%} confidence."
            )

        # Key factors
        key_factors: list[str] = []
        if feature_importance:
            for fs in feature_importance.features[:5]:
                direction = "supported" if fs.direction >= 0 else "opposed"
                factor = f"'{fs.name}' ({direction}, importance={fs.score:.2f})"
                if fs.contribution:
                    factor += f" — {fs.contribution}"
                key_factors.append(factor)

        # Alternatives from counterfactuals
        alternatives: list[str] = []
        if counterfactuals:
            for cf in counterfactuals[:5]:
                if cf.would_change_decision:
                    alt = f"{cf.description} → would result in '{cf.predicted_outcome}'"
                    alternatives.append(alt)

        # Caveats
        caveats: list[str] = []
        if decision.confidence < 0.5:
            caveats.append(f"Low confidence ({decision.confidence:.0%}) — decision may be unreliable")
        unexpected = decision.unexpected_outputs
        if unexpected:
            caveats.append(f"{len(unexpected)} unexpected output(s) detected")
        if decision.context.get("data_quality") == "low":
            caveats.append("Input data quality is low")

        return Explanation(
            title=title,
            summary=summary,
            reasoning=list(decision.reasoning_steps),
            key_factors=key_factors,
            alternatives=alternatives,
            confidence=decision.confidence,
            caveats=caveats,
        )

    def explain_with_counterfactuals(self, decision: Decision,
                                     features: dict[str, Any],
                                     perturbations: dict[str, list[Any]],
                                     feature_importance: FeatureImportance | None = None) -> Explanation:
        """Generate explanation including counterfactual what-if analysis."""
        counterfactuals: list[Counterfactual] = []
        if self._cf_generator:
            counterfactuals = self._cf_generator.generate_grid(features, perturbations)
        return self.explain_decision(decision, feature_importance, counterfactuals)

    def quick_explain(self, action: str, confidence: float,
                      reasoning: list[str] | None = None,
                      key_factors: list[str] | None = None) -> Explanation:
        """Quick one-shot explanation without a full Decision object."""
        return Explanation(
            title=f"Why '{action}'",
            summary=f"The agent chose to '{action}' with {confidence:.0%} confidence.",
            reasoning=reasoning or [],
            key_factors=key_factors or [],
            confidence=confidence,
        )

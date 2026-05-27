"""Counterfactual generator — explore "what if" scenarios for decisions."""
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Counterfactual:
    """A single counterfactual scenario."""
    description: str
    changes: dict[str, tuple[Any, Any]]  # {feature: (original, changed)}
    predicted_outcome: str = ""
    predicted_confidence: float = 0.0
    feasibility: float = 0.5  # How realistic is this change? 0-1

    @property
    def would_change_decision(self) -> bool:
        return self.predicted_confidence > 0.0

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "changes": {k: {"from": v[0], "to": v[1]} for k, v in self.changes.items()},
            "predicted_outcome": self.predicted_outcome,
            "predicted_confidence": round(self.predicted_confidence, 4),
            "feasibility": round(self.feasibility, 4),
            "would_change_decision": self.would_change_decision,
        }


@dataclass
class CounterfactualGenerator:
    """Generates counterfactual "what if" scenarios for agent decisions.

    Explores how changing input features would alter the decision outcome.
    Useful for understanding decision boundaries and robustness.
    """
    decide_fn: Callable[[dict[str, Any]], tuple[str, float]] | None = None

    def generate_single(self, features: dict[str, Any],
                        feature_name: str, new_value: Any,
                        description: str = "",
                        feasibility: float = 0.5) -> Counterfactual:
        """Generate one counterfactual by changing a single feature."""
        original_value = features.get(feature_name)
        if original_value == new_value:
            return Counterfactual(
                description=description or f"No change for '{feature_name}'",
                changes={},
                feasibility=1.0,
            )

        changed = {**features, feature_name: new_value}
        changes = {feature_name: (original_value, new_value)}

        if self.decide_fn:
            try:
                outcome, confidence = self.decide_fn(changed)
            except Exception:
                outcome, confidence = "error", 0.0
        else:
            outcome, confidence = "", 0.0

        if not description:
            description = f"If '{feature_name}' were {new_value!r} instead of {original_value!r}"

        return Counterfactual(
            description=description,
            changes=changes,
            predicted_outcome=outcome,
            predicted_confidence=confidence,
            feasibility=feasibility,
        )

    def generate_grid(self, features: dict[str, Any],
                      perturbations: dict[str, list[Any]]) -> list[Counterfactual]:
        """Generate counterfactuals for multiple features with multiple values each.

        Args:
            features: Original feature values.
            perturbations: {feature_name: [alt_value1, alt_value2, ...]}
        """
        results: list[Counterfactual] = []
        for fname, alt_values in perturbations.items():
            for alt in alt_values:
                if alt == features.get(fname):
                    continue
                cf = self.generate_single(features, fname, alt)
                results.append(cf)
        return sorted(results, key=lambda c: c.predicted_confidence, reverse=True)

    def find_decision_boundary(self, features: dict[str, Any],
                               feature_name: str,
                               test_values: list[Any],
                               threshold: float = 0.5) -> Counterfactual | None:
        """Find the value that flips the decision across a confidence threshold.

        Returns the counterfactual closest to the threshold crossing.
        """
        results = self.generate_grid(features, {feature_name: test_values})
        # Find where confidence crosses the threshold
        closest: Counterfactual | None = None
        closest_dist = float("inf")
        for cf in results:
            dist = abs(cf.predicted_confidence - threshold)
            if dist < closest_dist:
                closest_dist = dist
                closest = cf
        return closest

    def summarize(self, counterfactuals: list[Counterfactual]) -> str:
        """Human-readable summary of counterfactual scenarios."""
        if not counterfactuals:
            return "No counterfactual scenarios generated."
        lines = [f"Counterfactual Scenarios ({len(counterfactuals)}):"]
        for i, cf in enumerate(counterfactuals, 1):
            change_str = ", ".join(
                f"{k}: {v[0]!r}→{v[1]!r}" for k, v in cf.changes.items()
            )
            lines.append(
                f"  {i}. {cf.description}"
            )
            lines.append(
                f"     Outcome: {cf.predicted_outcome} "
                f"(conf={cf.predicted_confidence:.2f}, "
                f"feasibility={cf.feasibility:.2f})"
            )
        return "\n".join(lines)

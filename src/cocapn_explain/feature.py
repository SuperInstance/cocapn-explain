"""Feature importance — score and rank influential factors in decisions."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ImportanceLevel(Enum):
    CRITICAL = "critical"      # Decision would change without this
    HIGH = "high"              # Major influence
    MODERATE = "moderate"      # Notable influence
    LOW = "low"                # Minor influence
    NEGLIGIBLE = "negligible"  # Barely affects outcome


@dataclass
class FeatureScore:
    """Importance score for a single feature/factor."""
    name: str
    score: float              # 0.0 to 1.0
    contribution: str = ""    # Human-readable description of what it contributed
    direction: float = 0.0    # Positive = for decision, negative = against
    rank: int = 0

    @property
    def level(self) -> ImportanceLevel:
        if self.score >= 0.8:
            return ImportanceLevel.CRITICAL
        elif self.score >= 0.6:
            return ImportanceLevel.HIGH
        elif self.score >= 0.4:
            return ImportanceLevel.MODERATE
        elif self.score >= 0.2:
            return ImportanceLevel.LOW
        return ImportanceLevel.NEGLIGIBLE

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "score": round(self.score, 4),
            "level": self.level.value,
            "contribution": self.contribution,
            "direction": round(self.direction, 4),
            "rank": self.rank,
        }


@dataclass
class FeatureImportance:
    """Scores and ranks features by their influence on a decision.

    Supports manual scoring, automatic weight-based scoring from DecisionInput
    weights, and perturbation-based analysis (what changes when you remove a feature).
    """
    features: list[FeatureScore] = field(default_factory=list)

    def add_feature(self, name: str, score: float, contribution: str = "",
                    direction: float = 0.0) -> FeatureScore:
        fs = FeatureScore(name=name, score=score, contribution=contribution, direction=direction)
        self.features.append(fs)
        self._rerank()
        return fs

    def score_from_weights(self, weighted_inputs: dict[str, tuple[Any, float]],
                           decision_confidence: float = 1.0) -> None:
        """Auto-score features from weighted inputs.

        Args:
            weighted_inputs: {name: (value, weight)} — normalized weights become scores.
            decision_confidence: Overall decision confidence to modulate scores.
        """
        if not weighted_inputs:
            return
        total_weight = sum(abs(w) for _, w in weighted_inputs.values())
        if total_weight == 0:
            return
        self.features.clear()
        for name, (_, weight) in weighted_inputs.items():
            normalized = (abs(weight) / total_weight) * decision_confidence
            direction = weight / abs(weight) if weight != 0 else 0.0
            self.features.append(FeatureScore(
                name=name,
                score=min(normalized, 1.0),
                direction=direction,
            ))
        self._rerank()

    def perturbation_analysis(self, features: dict[str, Any],
                              decide_fn, baseline_confidence: float) -> None:
        """Score features by removing each one and measuring confidence drop.

        Args:
            features: {name: value} — the full feature set.
            decide_fn: Callable(features_dict) -> confidence_float.
            baseline_confidence: Confidence with all features present.
        """
        self.features.clear()
        for name in features:
            reduced = {k: v for k, v in features.items() if k != name}
            try:
                reduced_conf = decide_fn(reduced)
            except Exception:
                reduced_conf = 0.0
            drop = max(0.0, baseline_confidence - reduced_conf)
            self.features.append(FeatureScore(
                name=name,
                score=drop,
                contribution=f"Removing '{name}' drops confidence by {drop:.2f}",
                direction=1.0 if drop > 0 else 0.0,
            ))
        self._rerank()

    def _rerank(self) -> None:
        """Re-rank features by score descending."""
        sorted_features = sorted(self.features, key=lambda f: f.score, reverse=True)
        for i, f in enumerate(sorted_features, 1):
            f.rank = i
        self.features = sorted_features

    @property
    def top_features(self, n: int = 3) -> list[FeatureScore]:
        return self.features[:n]

    @property
    def critical_features(self) -> list[FeatureScore]:
        return [f for f in self.features if f.level == ImportanceLevel.CRITICAL]

    def to_dict(self) -> dict:
        return {"features": [f.to_dict() for f in self.features]}

    def summarize(self) -> str:
        if not self.features:
            return "No features scored."
        lines = ["Feature Importance:"]
        for f in self.features:
            bar = "█" * int(f.score * 20)
            direction = "+" if f.direction >= 0 else "-"
            lines.append(f"  {f.rank}. {f.name}: {f.score:.2f} {direction} {bar} [{f.level.value}]")
            if f.contribution:
                lines.append(f"     {f.contribution}")
        return "\n".join(lines)

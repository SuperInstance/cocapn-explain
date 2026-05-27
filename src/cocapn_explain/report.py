"""Explanation report — comprehensive report with confidence, alternatives, and audit trail."""
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from .decision import Decision, DecisionStatus
from .feature import FeatureImportance
from .counterfactual import Counterfactual
from .explainer import Explanation


class ReportStatus(Enum):
    DRAFT = "draft"
    FINAL = "final"
    FLAGGED = "flagged"    # Needs human attention
    ARCHIVED = "archived"


@dataclass
class ExplanationReport:
    """Comprehensive explanation report combining all analysis.

    Brings together the decision trace, feature importance, counterfactuals,
    and narrative explanation into a single auditable report.
    """
    decision: Decision
    explanation: Explanation
    feature_importance: FeatureImportance | None = None
    counterfactuals: list[Counterfactual] = field(default_factory=list)
    status: ReportStatus = ReportStatus.DRAFT
    report_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    created_at: float = field(default_factory=time.time)
    reviewed_by: str = ""
    review_notes: str = ""
    tags: list[str] = field(default_factory=list)

    @property
    def needs_human_review(self) -> bool:
        """Whether this report needs human attention."""
        if self.status == ReportStatus.FLAGGED:
            return True
        if self.decision.confidence < 0.5:
            return True
        if self.decision.status == DecisionStatus.ROLLED_BACK:
            return True
        if self.decision.unexpected_outputs:
            return True
        return False

    @property
    def confidence_score(self) -> float:
        """Aggregate confidence considering all factors."""
        base = self.decision.confidence
        # Penalize for unexpected outputs
        unexpected_count = len(self.decision.unexpected_outputs)
        penalty = min(0.1 * unexpected_count, 0.3)
        return max(0.0, base - penalty)

    @property
    def risk_assessment(self) -> str:
        """Qualitative risk assessment."""
        conf = self.confidence_score
        if conf >= 0.9:
            return "LOW"
        elif conf >= 0.7:
            return "MODERATE"
        elif conf >= 0.5:
            return "HIGH"
        return "CRITICAL"

    def flag(self, reason: str = "") -> None:
        """Flag the report for human review."""
        self.status = ReportStatus.FLAGGED
        if reason:
            self.review_notes = reason

    def approve(self, reviewer: str = "", notes: str = "") -> None:
        """Approve the report."""
        self.status = ReportStatus.FINAL
        self.reviewed_by = reviewer
        if notes:
            self.review_notes = notes

    def archive(self) -> None:
        """Archive the report."""
        self.status = ReportStatus.ARCHIVED

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "status": self.status.value,
            "decision": self.decision.to_dict(),
            "explanation": self.explanation.to_dict(),
            "feature_importance": self.feature_importance.to_dict() if self.feature_importance else None,
            "counterfactuals": [cf.to_dict() for cf in self.counterfactuals],
            "confidence_score": round(self.confidence_score, 4),
            "risk_assessment": self.risk_assessment,
            "needs_human_review": self.needs_human_review,
            "reviewed_by": self.reviewed_by,
            "review_notes": self.review_notes,
            "tags": self.tags,
            "created_at": self.created_at,
        }

    def to_markdown(self) -> str:
        """Generate a full markdown report."""
        lines = [
            f"# Explanation Report {self.report_id}",
            "",
            f"**Status:** {self.status.value} | "
            f"**Confidence:** {self.confidence_score:.0%} | "
            f"**Risk:** {self.risk_assessment}",
            "",
        ]
        if self.needs_human_review:
            lines.insert(2, "> ⚠️ **This report needs human review**")
            lines.insert(3, "")

        lines.append(self.explanation.to_markdown())
        lines.append("")

        if self.feature_importance:
            lines.append("### Feature Importance")
            lines.append(self.feature_importance.summarize())
            lines.append("")

        if self.counterfactuals:
            lines.append(f"### Counterfactual Scenarios ({len(self.counterfactuals)})")
            for i, cf in enumerate(self.counterfactuals[:10], 1):
                change_str = ", ".join(
                    f"{k}: {v[0]!r}→{v[1]!r}" for k, v in cf.changes.items()
                )
                lines.append(
                    f"{i}. {cf.description} → "
                    f"outcome: '{cf.predicted_outcome}' "
                    f"(conf={cf.predicted_confidence:.2f})"
                )
            lines.append("")

        if self.reviewed_by:
            lines.append(f"**Reviewed by:** {self.reviewed_by}")
            if self.review_notes:
                lines.append(f"**Notes:** {self.review_notes}")
            lines.append("")

        lines.append(f"---\n*Generated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.created_at))}*")
        return "\n".join(lines)

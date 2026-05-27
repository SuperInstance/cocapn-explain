"""Cocapn Explain — agent explainability traces and explanations."""
from .trace import ExplainTrace, TraceStep, DecisionTrace, StepType
from .oversight import OversightQueue, OversightPriority
from .decision import Decision, DecisionInput, DecisionOutput, DecisionStatus
from .feature import FeatureImportance, FeatureScore, ImportanceLevel
from .counterfactual import Counterfactual, CounterfactualGenerator
from .explainer import Explainer, Explanation
from .report import ExplanationReport, ReportStatus

__version__ = "0.2.0"
__all__ = [
    # Trace
    "ExplainTrace", "TraceStep", "DecisionTrace", "StepType",
    # Oversight
    "OversightQueue", "OversightPriority",
    # Decision
    "Decision", "DecisionInput", "DecisionOutput", "DecisionStatus",
    # Feature importance
    "FeatureImportance", "FeatureScore", "ImportanceLevel",
    # Counterfactual
    "Counterfactual", "CounterfactualGenerator",
    # Explainer
    "Explainer", "Explanation",
    # Report
    "ExplanationReport", "ReportStatus",
]

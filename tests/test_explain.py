"""Comprehensive tests for cocapn-explain."""
import pytest
from cocapn_explain import (
    ExplainTrace, TraceStep, DecisionTrace, StepType,
    OversightQueue, OversightPriority,
    Decision, DecisionInput, DecisionOutput, DecisionStatus,
    FeatureImportance, FeatureScore, ImportanceLevel,
    Counterfactual, CounterfactualGenerator,
    Explainer, Explanation,
    ExplanationReport, ReportStatus,
)


# --- Decision ---

class TestDecisionInput:
    def test_create(self):
        inp = DecisionInput(name="temperature", value=72.5, source="sensor", weight=0.8)
        assert inp.name == "temperature"
        assert inp.value == 72.5
        d = inp.to_dict()
        assert d["name"] == "temperature"
        assert d["weight"] == 0.8


class TestDecisionOutput:
    def test_create(self):
        out = DecisionOutput(name="action", value="open_valve", expected=True)
        assert out.expected is True
        assert out.to_dict()["expected"] is True

    def test_unexpected(self):
        out = DecisionOutput(name="result", value="overflow", expected=False)
        assert out.expected is False


class TestDecision:
    def test_basic_decision(self):
        d = Decision(agent_id="agent-1", action="open_valve")
        d.add_input("temperature", 85.0, source="sensor", weight=0.9)
        d.add_input("pressure", 1.2, source="gauge", weight=0.6)
        d.add_reasoning("Temperature exceeds threshold of 80")
        d.add_reasoning("Pressure is within safe range")
        d.add_output("valve_opened", True)
        d.confidence = 0.85
        d.finalize()
        assert d.is_finalized
        assert d.status == DecisionStatus.APPROVED
        assert len(d.inputs) == 2
        assert len(d.reasoning_steps) == 2
        assert len(d.outputs) == 1
        assert d.decided_at is not None

    def test_weighted_inputs(self):
        d = Decision(agent_id="a", action="test")
        d.add_input("x", 1, weight=0.8)
        d.add_input("y", 2, weight=0.3)
        wi = d.weighted_inputs
        assert "x" in wi and wi["x"] == (1, 0.8)
        assert "y" in wi and wi["y"] == (2, 0.3)

    def test_unexpected_outputs(self):
        d = Decision(agent_id="a", action="test")
        d.add_output("expected", "ok", expected=True)
        d.add_output("unexpected", "fail", expected=False)
        assert len(d.unexpected_outputs) == 1
        assert d.unexpected_outputs[0].name == "unexpected"

    def test_summarize(self):
        d = Decision(agent_id="a", action="deploy")
        d.add_reasoning("Tests pass")
        d.add_output("result", "error", expected=False)
        summary = d.summarize()
        assert "deploy" in summary
        assert "Tests pass" in summary
        assert "Unexpected" in summary

    def test_to_dict(self):
        d = Decision(agent_id="a", action="test")
        d.add_input("x", 1)
        d.add_reasoning("step 1")
        d.add_output("y", 2)
        dd = d.to_dict()
        assert dd["agent_id"] == "a"
        assert len(dd["inputs"]) == 1
        assert len(dd["reasoning_steps"]) == 1
        assert len(dd["outputs"]) == 1

    def test_rollback(self):
        d = Decision(agent_id="a", action="delete")
        d.finalize(DecisionStatus.ROLLED_BACK)
        assert d.status == DecisionStatus.ROLLED_BACK

    def test_decision_id_unique(self):
        d1 = Decision(agent_id="a", action="x")
        d2 = Decision(agent_id="a", action="x")
        assert d1.decision_id != d2.decision_id


# --- Feature Importance ---

class TestFeatureScore:
    def test_critical(self):
        fs = FeatureScore(name="temp", score=0.9)
        assert fs.level == ImportanceLevel.CRITICAL

    def test_high(self):
        fs = FeatureScore(name="temp", score=0.65)
        assert fs.level == ImportanceLevel.HIGH

    def test_moderate(self):
        fs = FeatureScore(name="temp", score=0.45)
        assert fs.level == ImportanceLevel.MODERATE

    def test_low(self):
        fs = FeatureScore(name="temp", score=0.25)
        assert fs.level == ImportanceLevel.LOW

    def test_negligible(self):
        fs = FeatureScore(name="temp", score=0.05)
        assert fs.level == ImportanceLevel.NEGLIGIBLE


class TestFeatureImportance:
    def test_add_features(self):
        fi = FeatureImportance()
        fi.add_feature("temperature", 0.9, "Primary trigger")
        fi.add_feature("humidity", 0.3)
        assert len(fi.features) == 2
        assert fi.features[0].rank == 1
        assert fi.features[0].name == "temperature"

    def test_score_from_weights(self):
        fi = FeatureImportance()
        fi.score_from_weights({"a": (1, 0.8), "b": (2, 0.2)}, decision_confidence=1.0)
        assert len(fi.features) == 2
        assert fi.features[0].name == "a"
        assert fi.features[0].score > fi.features[1].score

    def test_perturbation_analysis(self):
        def decide_fn(features):
            if "temperature" not in features:
                return 0.1
            return 0.9
        fi = FeatureImportance()
        fi.perturbation_analysis(
            features={"temperature": 85, "humidity": 40},
            decide_fn=decide_fn,
            baseline_confidence=0.9,
        )
        assert len(fi.features) == 2
        # Temperature should have highest drop
        assert fi.features[0].name == "temperature"
        assert fi.features[0].score > 0.5

    def test_critical_features(self):
        fi = FeatureImportance()
        fi.add_feature("critical_one", 0.9)
        fi.add_feature("minor_one", 0.1)
        crit = fi.critical_features
        assert len(crit) == 1
        assert crit[0].name == "critical_one"

    def test_summarize(self):
        fi = FeatureImportance()
        fi.add_feature("a", 0.8, "Important")
        s = fi.summarize()
        assert "a" in s
        assert "Important" in s

    def test_empty_summarize(self):
        fi = FeatureImportance()
        assert "No features" in fi.summarize()

    def test_to_dict(self):
        fi = FeatureImportance()
        fi.add_feature("x", 0.5)
        d = fi.to_dict()
        assert "features" in d
        assert d["features"][0]["name"] == "x"


# --- Counterfactual ---

class TestCounterfactual:
    def test_would_change(self):
        cf = Counterfactual(
            description="test",
            changes={"x": (1, 2)},
            predicted_outcome="different",
            predicted_confidence=0.8,
        )
        assert cf.would_change_decision is True

    def test_would_not_change(self):
        cf = Counterfactual(
            description="test",
            changes={"x": (1, 2)},
            predicted_confidence=0.0,
        )
        assert cf.would_change_decision is False

    def test_to_dict(self):
        cf = Counterfactual(
            description="test",
            changes={"x": (1, 2)},
            predicted_outcome="y",
            predicted_confidence=0.6,
            feasibility=0.8,
        )
        d = cf.to_dict()
        assert d["changes"]["x"]["from"] == 1
        assert d["changes"]["x"]["to"] == 2


class TestCounterfactualGenerator:
    def test_generate_single(self):
        def decide(features):
            if features.get("temp", 0) > 100:
                return ("shutdown", 0.9)
            return ("continue", 0.7)

        gen = CounterfactualGenerator(decide_fn=decide)
        cf = gen.generate_single({"temp": 80}, "temp", 120)
        assert cf.predicted_outcome == "shutdown"
        assert "temp" in cf.changes

    def test_generate_single_no_change(self):
        gen = CounterfactualGenerator()
        cf = gen.generate_single({"x": 1}, "x", 1)
        assert cf.changes == {}

    def test_generate_grid(self):
        def decide(features):
            return ("ok", 0.5)

        gen = CounterfactualGenerator(decide_fn=decide)
        results = gen.generate_grid(
            {"a": 1, "b": 2},
            {"a": [3, 5], "b": [10]},
        )
        assert len(results) == 3
        assert results[0].predicted_confidence >= results[-1].predicted_confidence

    def test_find_decision_boundary(self):
        def decide(features):
            val = features.get("threshold", 50)
            if val >= 80:
                return ("alert", 0.9)
            return ("normal", 0.3)

        gen = CounterfactualGenerator(decide_fn=decide)
        result = gen.find_decision_boundary(
            {"threshold": 50},
            "threshold",
            [60, 70, 75, 80, 85, 90],
            threshold=0.5,
        )
        assert result is not None
        assert "threshold" in result.changes

    def test_summarize(self):
        gen = CounterfactualGenerator()
        cfs = [
            Counterfactual("test", {"x": (1, 2)}, "out", 0.5, 0.8),
        ]
        s = gen.summarize(cfs)
        assert "test" in s
        assert "Counterfactual" in s

    def test_empty_summarize(self):
        gen = CounterfactualGenerator()
        assert "No counterfactual" in gen.summarize([])


# --- Explainer ---

class TestExplainer:
    def _make_decision(self):
        d = Decision(agent_id="agent-1", action="open_valve")
        d.add_input("temperature", 85.0, source="sensor", weight=0.9)
        d.add_reasoning("Temperature exceeds threshold")
        d.add_reasoning("Pressure stable")
        d.add_output("valve", "opened")
        d.confidence = 0.85
        return d

    def test_explain_decision(self):
        explainer = Explainer()
        d = self._make_decision()
        exp = explainer.explain_decision(d)
        assert "open_valve" in exp.title
        assert len(exp.reasoning) == 2
        assert exp.confidence == 0.85

    def test_explain_with_features(self):
        explainer = Explainer()
        d = self._make_decision()
        fi = FeatureImportance()
        fi.add_feature("temperature", 0.9, "Main trigger")
        fi.add_feature("pressure", 0.2, "Minor factor")
        exp = explainer.explain_decision(d, feature_importance=fi)
        assert len(exp.key_factors) == 2
        assert "temperature" in exp.key_factors[0]

    def test_explain_with_counterfactuals(self):
        explainer = Explainer()
        d = self._make_decision()
        cfs = [
            Counterfactual("If temp was lower", {"temperature": (85, 70)},
                           predicted_outcome="no_action", predicted_confidence=0.7),
        ]
        exp = explainer.explain_decision(d, counterfactuals=cfs)
        assert len(exp.alternatives) == 1

    def test_low_confidence_caveat(self):
        explainer = Explainer()
        d = Decision(agent_id="a", action="guess", confidence=0.3)
        exp = explainer.explain_decision(d)
        assert any("Low confidence" in c for c in exp.caveats)

    def test_unexpected_output_caveat(self):
        explainer = Explainer()
        d = Decision(agent_id="a", action="deploy", confidence=0.8)
        d.add_output("status", "error", expected=False)
        exp = explainer.explain_decision(d)
        assert any("unexpected" in c.lower() for c in exp.caveats)

    def test_quick_explain(self):
        explainer = Explainer()
        exp = explainer.quick_explain("shutdown", 0.9, reasoning=["Too hot"], key_factors=["temperature"])
        assert "shutdown" in exp.title
        assert exp.confidence == 0.9

    def test_explanation_to_markdown(self):
        exp = Explanation(
            title="Test",
            summary="Testing.",
            reasoning=["Step 1"],
            key_factors=["Factor A"],
            alternatives=["Alt 1"],
            confidence=0.8,
        )
        md = exp.to_markdown()
        assert "## Test" in md
        assert "Step 1" in md
        assert "Factor A" in md
        assert "Alt 1" in md

    def test_explain_with_counterfactuals_method(self):
        def decide(features):
            return ("action", 0.7)
        gen = CounterfactualGenerator(decide_fn=decide)
        explainer = Explainer(counterfactual_generator=gen)
        d = Decision(agent_id="a", action="test", confidence=0.8)
        d.add_input("x", 1)
        exp = explainer.explain_with_counterfactuals(
            d, {"x": 1, "y": 2}, {"x": [5, 10], "y": [3]}
        )
        assert len(exp.alternatives) > 0


# --- Report ---

class TestExplanationReport:
    def _make_report(self, confidence=0.85):
        d = Decision(agent_id="a", action="deploy", confidence=confidence)
        d.add_reasoning("Tests pass")
        exp = Explanation(title="Deploy", summary="Safe to deploy", reasoning=["Tests pass"])
        return ExplanationReport(decision=d, explanation=exp)

    def test_basic_report(self):
        r = self._make_report()
        assert r.status == ReportStatus.DRAFT
        assert r.risk_assessment == "MODERATE"
        assert not r.needs_human_review

    def test_low_confidence_needs_review(self):
        r = self._make_report(confidence=0.3)
        assert r.needs_human_review

    def test_flagged_needs_review(self):
        r = self._make_report()
        r.flag("Suspicious pattern")
        assert r.needs_human_review
        assert r.status == ReportStatus.FLAGGED
        assert "Suspicious" in r.review_notes

    def test_approve(self):
        r = self._make_report()
        r.approve(reviewer="alice", notes="Looks good")
        assert r.status == ReportStatus.FINAL
        assert r.reviewed_by == "alice"

    def test_archive(self):
        r = self._make_report()
        r.archive()
        assert r.status == ReportStatus.ARCHIVED

    def test_confidence_penalty(self):
        r = self._make_report(confidence=0.8)
        r.decision.add_output("error", "fail", expected=False)
        assert r.confidence_score < 0.8

    def test_risk_levels(self):
        assert self._make_report(0.95).risk_assessment == "LOW"
        assert self._make_report(0.75).risk_assessment == "MODERATE"
        assert self._make_report(0.55).risk_assessment == "HIGH"
        assert self._make_report(0.3).risk_assessment == "CRITICAL"

    def test_to_dict(self):
        r = self._make_report()
        d = r.to_dict()
        assert "report_id" in d
        assert d["status"] == "draft"
        assert d["risk_assessment"] == "MODERATE"
        assert "decision" in d
        assert "explanation" in d

    def test_to_markdown(self):
        r = self._make_report()
        md = r.to_markdown()
        assert "# Explanation Report" in md
        assert "deploy" in md
        assert "Tests pass" in md

    def test_rollback_needs_review(self):
        d = Decision(agent_id="a", action="delete", confidence=0.9)
        d.finalize(DecisionStatus.ROLLED_BACK)
        exp = Explanation(title="Delete", summary="Rolled back")
        r = ExplanationReport(decision=d, explanation=exp)
        assert r.needs_human_review

    def test_report_with_features_and_counterfactuals(self):
        d = Decision(agent_id="a", action="open", confidence=0.9)
        d.add_reasoning("OK")
        exp = Explanation(title="Open", summary="OK")
        fi = FeatureImportance()
        fi.add_feature("temp", 0.8)
        cfs = [Counterfactual("test", {"x": (1, 2)}, "y", 0.6, 0.7)]
        r = ExplanationReport(decision=d, explanation=exp,
                              feature_importance=fi, counterfactuals=cfs)
        md = r.to_markdown()
        assert "Feature Importance" in md
        assert "Counterfactual" in md

    def test_tags(self):
        r = self._make_report()
        r.tags = ["safety", "production"]
        assert "safety" in r.tags
        d = r.to_dict()
        assert "safety" in d["tags"]

    def test_report_id_unique(self):
        r1 = self._make_report()
        r2 = self._make_report()
        assert r1.report_id != r2.report_id


# --- Existing tests still pass ---

class TestExplainTrace:
    def test_create_trace(self):
        trace = ExplainTrace(agent_id="agent-1", task="explore harbor")
        trace.add_step(StepType.OBSERVE, "Saw 3 ships in harbor", confidence=0.9, duration_ms=50)
        trace.add_step(StepType.REASON, "Ships are friendly based on flags", confidence=0.8, duration_ms=100)
        trace.add_step(StepType.DECIDE, "Approach and greet", confidence=0.85, duration_ms=30)
        trace.outcome = "Greeted 3 ships"
        trace.outcome_confidence = 0.85
        assert len(trace.steps) == 3
        assert trace.trace_id != ""
        assert trace.total_duration_ms == 180

    def test_summarize(self):
        trace = ExplainTrace(agent_id="agent-1", task="test")
        trace.add_step(StepType.OBSERVE, "saw something", confidence=0.9)
        summary = trace.summarize()
        assert "agent-1" in summary
        assert "OBSERVE" in summary


class TestDecisionTrace:
    def test_needs_review_low_confidence(self):
        dt = DecisionTrace(agent_id="a", decision="deploy", reasoning="looks good", confidence=0.3)
        assert dt.needs_review

    def test_no_review_needed(self):
        dt = DecisionTrace(agent_id="a", decision="log message", reasoning="routine", confidence=0.95, risk_level="LOW")
        assert not dt.needs_review


class TestOversightQueue:
    def test_p0_critical(self):
        q = OversightQueue()
        dt = DecisionTrace("a", "nuke", "press button", 0.1, risk_level="CRITICAL")
        item = q.enqueue(dt)
        assert item.priority == OversightPriority.P0_MUST_REVIEW

    def test_p2_normal(self):
        q = OversightQueue()
        dt = DecisionTrace("a", "log metric", "routine", 0.9, risk_level="LOW")
        item = q.enqueue(dt)
        assert item.priority == OversightPriority.P2_LOGGED

    def test_stats(self):
        q = OversightQueue()
        q.enqueue(DecisionTrace("a", "c1", "!", 0.1, risk_level="CRITICAL"))
        q.enqueue(DecisionTrace("b", "n1", "ok", 0.9, risk_level="LOW"))
        stats = q.stats
        assert stats["p0_pending"] == 1
        assert stats["p2_logged"] == 1

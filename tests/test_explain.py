"""Tests for cocapn-explain."""
import pytest
from cocapn_explain import (
    ExplainTrace, TraceStep, DecisionTrace,
    OversightQueue, OversightPriority,
)
from cocapn_explain.trace import StepType


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

    def test_min_confidence(self):
        trace = ExplainTrace(agent_id="a", task="t")
        trace.add_step(StepType.OBSERVE, "high", confidence=0.9)
        trace.add_step(StepType.REASON, "low", confidence=0.3)
        assert trace.min_confidence == 0.3


class TestDecisionTrace:
    def test_needs_review_low_confidence(self):
        dt = DecisionTrace(agent_id="a", decision="deploy", reasoning="looks good", confidence=0.3)
        assert dt.needs_review

    def test_needs_review_high_risk(self):
        dt = DecisionTrace(agent_id="a", decision="delete all", reasoning="cleanup", confidence=0.9, risk_level="HIGH")
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

    def test_p1_high_risk(self):
        q = OversightQueue()
        dt = DecisionTrace("a", "restart service", "service hanging", 0.6, risk_level="HIGH")
        item = q.enqueue(dt)
        assert item.priority == OversightPriority.P1_SAMPLED

    def test_p2_normal(self):
        q = OversightQueue()
        dt = DecisionTrace("a", "log metric", "routine", 0.9, risk_level="LOW")
        item = q.enqueue(dt)
        assert item.priority == OversightPriority.P2_LOGGED

    def test_review_queue(self):
        q = OversightQueue()
        q.enqueue(DecisionTrace("a", "critical", "!", 0.1, risk_level="CRITICAL"))
        q.enqueue(DecisionTrace("b", "normal", "ok", 0.9, risk_level="LOW"))
        review = q.get_review_queue()
        assert len(review) >= 1
        assert review[0].priority == OversightPriority.P0_MUST_REVIEW

    def test_stats(self):
        q = OversightQueue()
        q.enqueue(DecisionTrace("a", "c1", "!", 0.1, risk_level="CRITICAL"))
        q.enqueue(DecisionTrace("b", "n1", "ok", 0.9, risk_level="LOW"))
        stats = q.stats
        assert stats["p0_pending"] == 1
        assert stats["p2_logged"] == 1

# cocapn-explain — Agent Explainability

**Trace every agent decision, generate human-readable explanations, detect what needs oversight.**

## What This Gives You

- **Decision traces** — record every step an agent takes, with inputs, outputs, and timing
- **Feature importance** — score which inputs most influenced each decision
- **Counterfactuals** — "what if X had been different?" exploration for any decision
- **Oversight queue** — automatically flag high-stakes or low-confidence decisions for human review
- **Explanation reports** — markdown or JSON reports that explain *why* an agent did what it did

## Quick Start

```bash
pip install cocapn-explain
```

```python
from cocapn_explain import (
    Explainer, ExplainTrace, Decision, FeatureImportance,
    CounterfactualGenerator, OversightQueue
)

# Record a decision trace
trace = ExplainTrace(agent_id="agent-1")
trace.add_step(step_type="input", description="Received query", data={"query": "deploy v2?"})
trace.add_step(step_type="reasoning", description="Checked constraints", data={"pass": True})
trace.add_step(step_type="output", description="Approved deployment", data={"version": "v2"})

# Generate an explanation
explainer = Explainer()
explanation = explainer.explain_decision(
    decision=Decision(
        inputs=[{"query": "deploy v2?"}],
        outputs=[{"approved": True}],
        confidence=0.87
    ),
    trace=trace
)
print(explanation.to_markdown())

# Flag decisions that need human review
queue = OversightQueue()
queue.add_if_needed(explanation, threshold=0.7)
```

## API Reference

### Tracing
- **`ExplainTrace`** — Step-by-step record of agent reasoning
- **`TraceStep`** — Single step with type, description, data, timing
- **`DecisionTrace`** — Specialized trace focused on a single decision

### Decisions
- **`Decision`** — Input/output pair with status and confidence
- **`DecisionInput` / `DecisionOutput`** — Typed wrappers

### Analysis
- **`FeatureImportance`** — Score and rank decision inputs by influence
- **`CounterfactualGenerator`** — Generate "what if" alternatives
- **`Explainer`** — Produce `Explanation` objects from traces + decisions

### Reporting & Oversight
- **`ExplanationReport`** — Full report with status, explanations, metadata
- **`OversightQueue`** — Priority-sorted queue of decisions needing review

## How It Fits
- [OpenConstruct Documentation](https://github.com/SuperInstance/openconstruct-docs) — ecosystem-wide docs and guides

Explainability layer for the [SuperInstance fleet](https://github.com/SuperInstance). Every fleet agent can emit traces that `cocapn-explain` captures, analyzes, and reports.

- **[cocapn](https://github.com/SuperInstance/cocapn)** — Core agent infrastructure
- **[cocapn-health-rs](https://github.com/SuperInstance/cocapn-health-rs)** — Fleet health monitoring
- **[guard-constraints](https://github.com/SuperInstance/guard-constraints)** — Constraint enforcement
- **[agent-therapy](https://github.com/SuperInstance/agent-therapy)** — Behavioral health monitoring

## Testing

```bash
pip install pytest
pytest tests/
```

## Installation

```bash
pip install cocapn-explain
```

Requires Python 3.10+. MIT license.

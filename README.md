# cocapn-explain

**Trace every agent decision, score what mattered, explore what-if alternatives, flag what needs human review.** A structured explainability library for AI agent systems.

## What This Does

When an AI agent makes a decision — approve a deployment, route a ticket, trigger an alert — you need to know *why*. Cocapn-explain captures the full decision lifecycle: what went in, how the agent reasoned step by step, what came out, and whether the outcome matched expectations. It then analyses that trace to produce feature importance scores, counterfactual "what if" scenarios, and human-readable explanations.

The library gives you:

- **Decision traces** — record every step (observe → reason → decide → act → verify) with inputs, outputs, confidence, and timing
- **Decision objects** — structured records of agent decisions with inputs, reasoning steps, outputs, status, and confidence
- **Feature importance** — score and rank which inputs most influenced a decision (manual, weight-based, or perturbation analysis)
- **Counterfactuals** — "what if X had been different?" exploration: single-feature changes, grid search, boundary detection
- **Explainer** — combines traces + importance + counterfactuals into human-readable narrative explanations (markdown or JSON)
- **Oversight queue** — automatically triage decisions by priority (must-review, sampled, logged) based on confidence and risk
- **Explanation reports** — comprehensive auditable reports combining all analysis with confidence, risk assessment, and review workflow

## Key Idea

Explainability isn't one thing — it's a pipeline:

```
Decision Trace → Feature Importance → Counterfactuals → Narrative → Oversight → Report
```

Each layer adds a different kind of understanding:
- **Trace** answers "what happened?"
- **Importance** answers "what mattered?"
- **Counterfactuals** answer "what would change the outcome?"
- **Narrative** answers "why did the agent do this?" in human language
- **Oversight** answers "does a human need to look at this?"
- **Report** packages everything for audit

## Install

```bash
pip install cocapn-explain
```

Requires Python ≥ 3.10. No external dependencies.

## Quick Start

### Record a decision trace

```python
from cocapn_explain import ExplainTrace, StepType

trace = ExplainTrace(agent_id="deploy-bot", task="deploy v2.3.1")

trace.add_step(StepType.OBSERVE, "Received deployment request", confidence=0.9,
               inputs={"version": "v2.3.1", "environment": "staging"})
trace.add_step(StepType.REASON, "All CI checks pass", confidence=0.95,
               inputs={"tests_passed": 47, "lint_clean": True})
trace.add_step(StepType.DECIDE, "Approve deployment", confidence=0.88)
trace.add_step(StepType.ACT, "Deployed to staging", confidence=0.85,
               outputs={"deploy_id": "d-12345"})
trace.add_step(StepType.VERIFY, "Health check passed", confidence=0.92)

print(trace.summarize())
```

### Score feature importance

```python
from cocapn_explain import FeatureImportance, Decision, DecisionInput

# Build a decision
decision = Decision(agent_id="deploy-bot", action="deploy", confidence=0.88)
decision.add_input("ci_status", "passing", source="github", weight=0.9)
decision.add_input("test_coverage", 0.87, source="pytest", weight=0.6)
decision.add_input("time_since_last_deploy", "2h", source="scheduler", weight=0.3)
decision.add_input("rollback_count", 0, source="history", weight=0.8)

# Auto-score from weights
fi = FeatureImportance()
fi.score_from_weights(decision.weighted_inputs, decision.confidence)
print(fi.summarize())

# Feature Importance:
#   1. ci_status: 0.43 + █████████ ████ [critical]
#   2. rollback_count: 0.38 + ████████ [high]
#   3. test_coverage: 0.29 + ██████ [moderate]
#   4. time_since_last_deploy: 0.14 + ███ [low]
```

### Perturbation analysis

```python
from cocapn_explain import FeatureImportance

# Score by removing each feature and measuring confidence drop
def mock_decide(features):
    # Your actual decision function
    if features.get("ci_status") != "passing":
        return 0.2  # low confidence without CI
    return 0.88

fi = FeatureImportance()
fi.perturbation_analysis(
    features={"ci_status": "passing", "test_coverage": 0.87, "rollback_count": 0},
    decide_fn=mock_decide,
    baseline_confidence=0.88,
)
# Removing "ci_status" drops confidence by 0.68 → CRITICAL importance
```

### Generate counterfactuals

```python
from cocapn_explain import CounterfactualGenerator

def decide_fn(features):
    if features.get("ci_status") != "passing":
        return ("reject", 0.3)
    return ("approve", 0.88)

cf_gen = CounterfactualGenerator(decide_fn=decide_fn)
features = {"ci_status": "passing", "test_coverage": 0.87, "rollback_count": 0}

# Single counterfactual
cf = cf_gen.generate_single(features, "ci_status", "failing")
print(cf.description)          # "If 'ci_status' were 'failing' instead of 'passing'"
print(cf.predicted_outcome)    # "reject"
print(cf.predicted_confidence) # 0.3
print(cf.would_change_decision) # True

# Grid of counterfactuals
cfs = cf_gen.generate_grid(features, {
    "ci_status": ["failing", "error", "unknown"],
    "test_coverage": [0.5, 0.6, 0.7],
})
for cf in cfs:
    if cf.would_change_decision:
        print(f"  {cf.description} → {cf.predicted_outcome}")
```

### Generate explanations

```python
from cocapn_explain import Explainer, Decision, FeatureImportance, CounterfactualGenerator

decision = Decision(agent_id="deploy-bot", action="deploy", confidence=0.88)
decision.add_input("ci_status", "passing", weight=0.9)
decision.add_reasoning("CI checks all passing")
decision.add_reasoning("Test coverage above threshold (87%)")
decision.add_reasoning("No rollbacks in recent history")
decision.add_output("deploy_id", "d-12345")

explainer = Explainer(counterfactual_generator=cf_gen)
explanation = explainer.explain_decision(decision, feature_importance=fi, counterfactuals=cfs)

# Markdown output
print(explanation.to_markdown())

# ## Why the agent decided to 'deploy'
#
# **Confidence:** 88%
#
# The agent decided to 'deploy' through 3 reasoning step(s), with 88% confidence.
#
# ### Reasoning
# - CI checks all passing
# - Test coverage above threshold (87%)
# - No rollbacks in recent history
#
# ### Key Factors
# - 'ci_status' (supported, importance=0.43) — ...
#
# ### Alternatives Considered
# - If 'ci_status' were 'failing' instead of 'passing' → would result in 'reject'
```

### Quick one-shot explanation

```python
from cocapn_explain import Explainer

explainer = Explainer()
explanation = explainer.quick_explain(
    action="restart_service",
    confidence=0.72,
    reasoning=["Memory usage > 95%", "Last restart was 6h ago"],
    key_factors=["memory_usage", "uptime"],
)
print(explanation.summary)
```

### Oversight queue

```python
from cocapn_explain import OversightQueue, DecisionTrace

queue = OversightQueue(p1_sample_rate=0.1)

# Enqueue traces — auto-classified by risk/confidence
queue.enqueue(DecisionTrace(
    agent_id="deploy-bot",
    decision="deploy to production",
    reasoning="CI passed, low risk",
    confidence=0.45,  # Low → P0 (must review)
    risk_level="CRITICAL",
))

queue.enqueue(DecisionTrace(
    agent_id="monitor",
    decision="scale up pods",
    reasoning="CPU > 80%",
    confidence=0.92,  # High → P2 (logged)
    risk_level="LOW",
))

# Get review queue (all P0 + sampled P1)
for item in queue.get_review_queue():
    print(f"[{item.priority.name}] {item.trace.decision} "
          f"(conf={item.trace.confidence:.2f}, age={item.age_seconds:.0f}s)")

# Review a decision
queue.review("deploy to production", approved=True)
```

### Full explanation report

```python
from cocapn_explain import ExplanationReport, Explainer, Decision

decision = Decision(agent_id="deploy-bot", action="deploy", confidence=0.88)
# ... add inputs, reasoning, outputs ...

report = ExplanationReport(
    decision=decision,
    explanation=explanation,
    feature_importance=fi,
    counterfactuals=cfs,
    tags=["deployment", "staging"],
)

print(f"Needs review: {report.needs_human_review}")  # True if low confidence / unexpected outputs
print(f"Risk: {report.risk_assessment}")               # LOW / MODERATE / HIGH / CRITICAL
print(f"Confidence: {report.confidence_score:.0%}")     # Adjusted for unexpected outputs

# Full markdown report
print(report.to_markdown())

# Approve and archive
report.approve(reviewer="alice", notes="Looks good")
```

## API Reference

### Tracing

| Class | Description |
|---|---|
| `ExplainTrace(agent_id, task)` | Complete trace of an agent decision process |
| `ExplainTrace.add_step(step_type, description, ...)` | Record a step (OBSERVE, REASON, DECIDE, ACT, VERIFY) |
| `ExplainTrace.summarize()` | Human-readable trace summary |
| `TraceStep` | Single step with type, description, confidence, timing, I/O |
| `DecisionTrace(agent_id, decision, reasoning, confidence, ...)` | Simplified trace for quick human review |
| `StepType` | Enum: OBSERVE, REASON, DECIDE, ACT, VERIFY |

### Decisions

| Class | Description |
|---|---|
| `Decision(agent_id, action)` | Complete structured decision record |
| `.add_input(name, value, source, weight)` | Add a weighted input factor |
| `.add_reasoning(step)` | Add a reasoning step |
| `.add_output(name, value, expected)` | Add an output (with expected flag) |
| `.finalize(status)` | Mark as APPROVED / REJECTED / ROLLED_BACK |
| `.weighted_inputs` | Dict of {name: (value, weight)} |
| `.unexpected_outputs` | Outputs that didn't match expectations |
| `.summarize()` | Human-readable decision summary |
| `DecisionInput` | Single input factor with name, value, source, weight |
| `DecisionOutput` | Single output with name, value, expected flag |
| `DecisionStatus` | Enum: PENDING, APPROVED, REJECTED, ROLLED_BACK |

### Feature Importance

| Class / Method | Description |
|---|---|
| `FeatureImportance()` | Score and rank features by influence |
| `.add_feature(name, score, contribution, direction)` | Manual scoring |
| `.score_from_weights(weighted_inputs, confidence)` | Auto-score from DecisionInput weights |
| `.perturbation_analysis(features, decide_fn, baseline)` | Score by removing each feature |
| `.top_features` | Top 3 features by score |
| `.critical_features` | Features with score ≥ 0.8 |
| `.summarize()` | ASCII bar chart + importance levels |
| `FeatureScore` | Single feature score with rank, direction, level |
| `ImportanceLevel` | Enum: CRITICAL, HIGH, MODERATE, LOW, NEGLIGIBLE |

### Counterfactuals

| Class / Method | Description |
|---|---|
| `CounterfactualGenerator(decide_fn)` | Generate "what if" scenarios |
| `.generate_single(features, name, new_value)` | One counterfactual by changing one feature |
| `.generate_grid(features, perturbations)` | Multiple features × multiple values |
| `.find_decision_boundary(features, name, test_values, threshold)` | Find the value that flips the decision |
| `.summarize(counterfactuals)` | Human-readable summary |
| `Counterfactual` | Single scenario: description, changes, predicted outcome, feasibility |

### Explainer

| Class / Method | Description |
|---|---|
| `Explainer(counterfactual_generator)` | Generate explanations from decision data |
| `.explain_decision(decision, feature_importance, counterfactuals)` | Full explanation |
| `.explain_with_counterfactuals(decision, features, perturbations, ...)` | Explanation + auto counterfactuals |
| `.quick_explain(action, confidence, reasoning, key_factors)` | One-shot without Decision object |
| `Explanation` | Human-readable explanation: title, summary, reasoning, key_factors, alternatives, caveats |
| `Explanation.to_markdown()` | Render as markdown |
| `Explanation.to_dict()` | Render as dict |

### Oversight

| Class / Method | Description |
|---|---|
| `OversightQueue(p1_sample_rate=0.1)` | Priority queue for human review |
| `.enqueue(trace)` | Auto-classify and enqueue (P0/P1/P2) |
| `.get_review_queue()` | Items needing review (all P0 + sampled P1) |
| `.review(trace_id, approved)` | Mark as reviewed |
| `.stats` | Dict of pending/reviewed counts per priority |
| `OversightPriority` | Enum: P0_MUST_REVIEW, P1_SAMPLED, P2_LOGGED |

### Reports

| Class / Method | Description |
|---|---|
| `ExplanationReport(decision, explanation, ...)` | Comprehensive auditable report |
| `.needs_human_review` | True if low confidence, unexpected outputs, or rolled back |
| `.confidence_score` | Aggregate confidence (penalised for unexpected outputs) |
| `.risk_assessment` | LOW / MODERATE / HIGH / CRITICAL |
| `.flag(reason)` | Flag for human attention |
| `.approve(reviewer, notes)` | Approve and finalise |
| `.archive()` | Archive the report |
| `.to_markdown()` | Full markdown report |
| `.to_dict()` | Full dict serialisation |
| `ReportStatus` | Enum: DRAFT, FINAL, FLAGGED, ARCHIVED |

## How It Works

```
┌─────────────┐
│  Agent makes │
│  a decision  │
└──────┬──────┘
       │
       ▼
┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  trace.py    │────▶│  feature.py      │────▶│  counterfactual  │
│              │     │                  │     │     .py          │
│ ExplainTrace │     │ FeatureImportance│     │ Counterfactual   │
│ TraceStep    │     │ FeatureScore     │     │ Counterfactual   │
│ DecisionTrace│     │ perturbation     │     │   Generator      │
│ StepType     │     │ score_from_      │     │ decision_boundary│
│              │     │   weights        │     │ grid search      │
└──────────────┘     └────────┬─────────┘     └────────┬─────────┘
       │                      │                         │
       │                      └───────────┬─────────────┘
       │                                  │
       │                         ┌────────▼────────┐
       │                         │  explainer.py   │
       │                         │                 │
       │                         │ Explainer       │
       │                         │ Explanation     │
       │                         │ .to_markdown()  │
       │                         └────────┬────────┘
       │                                  │
       ▼                                  ▼
┌──────────────┐                ┌──────────────────┐
│ oversight.py │                │   report.py      │
│              │                │                  │
│ OversightQ   │                │ ExplanationReport│
│ Priority P0  │◀──────────────│ .needs_review    │
│   P1, P2     │                │ .risk_assessment │
│ Auto-triage  │                │ .flag() / .      │
│              │                │   approve()      │
└──────────────┘                └──────────────────┘
       │
       ▼
  Human reviewer
```

### Triage logic

When a `DecisionTrace` is enqueued, it's auto-classified:

| Condition | Priority |
|---|---|
| `risk_level == "CRITICAL"` or `confidence < 0.3` | **P0 — Must review** before action |
| `risk_level == "HIGH"` or `confidence < 0.5` | **P1 — Sampled** (default 10%) |
| Everything else | **P2 — Logged**, review only if outcome bad |

### Feature importance levels

| Score | Level | Meaning |
|---|---|---|
| ≥ 0.8 | CRITICAL | Decision would change without this feature |
| ≥ 0.6 | HIGH | Major influence |
| ≥ 0.4 | MODERATE | Notable influence |
| ≥ 0.2 | LOW | Minor influence |
| < 0.2 | NEGLIGIBLE | Barely affects outcome |

### Report risk assessment

| Adjusted confidence | Risk |
|---|---|
| ≥ 0.9 | LOW |
| ≥ 0.7 | MODERATE |
| ≥ 0.5 | HIGH |
| < 0.5 | CRITICAL |

Adjusted confidence penalises for unexpected outputs (up to −0.3).

## Testing

```bash
pip install pytest
pytest tests/ -v
```

71 tests across test files covering every module.

## License

MIT

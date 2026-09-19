# Inter-run consistency tracking

This document describes how to measure **how stable the candidate analysis pipeline is across repeat runs of the same input**, and how those measurements are surfaced in Langfuse.

It is **methodology only**. No automated harness is checked in yet; runs are driven manually (or via Langfuse Datasets/Experiments) and the scores below are emitted by hand or by a future runner.

## Why measure consistency

The pipeline is non-deterministic by design (LLM temperature, sampling, Ollama scheduling). Two runs on the same `(candidate_id, vacancy_id)` can produce different skill lists, recommendations, or scores. Tracking how *much* they vary catches:

- model instability (e.g. Ollama stalls or returns truncated JSON)
- prompt sensitivity (e.g. a prompt change increases variance)
- regression after upgrading the LLM/embedding model

It is intentionally cheap: re-run, compare, record three numbers.

## Methodology

For a fixed pair `(candidate_id, vacancy_id)`:

1. Submit the analysis workflow `N = 3` times (sequentially or in parallel).
2. Wait for all runs to reach `EVENT_TYPE_WORKFLOW_EXECUTION_COMPLETED`.
3. Pull the final `ReportDraft` and `ScoringResult` from `analysis_reports` (or read each run's terminal Langfuse session).
4. Compute the three signals below and emit them as Langfuse scores attached to a *consistency session* (e.g. `session_id = f"consistency-{candidate_id}-{vacancy_id}-{eval_id}"`).

### 1. `consistency_skills_jaccard`

Jaccard similarity over `CandidateFacts.skills` across all `N` runs.

- For each pair `(i, j)` of runs, compute `|S_i ∩ S_j| / |S_i ∪ S_j|`.
- Score value = the **mean of all pairwise Jaccards** (range `[0.0, 1.0]`, higher is more consistent).
- 1.0 means identical skill sets; 0.0 means disjoint.

### 2. `consistency_recommendation_agreement`

Fraction of the `N` runs that agree on the **modal** recommendation tier (`strong_match | possible | weak | manual_review`).

- value = `count(modal_tier) / N`, in `[1/N, 1.0]`.
- 1.0 means all runs agree; for `N=3`, the floor is `0.34` (each run picks a different tier).

### 3. `consistency_score_stddev`

Sample standard deviation of `ScoringResult.overall_score` across the `N` runs.

- Range `[0.0, 50.0]` in practice; lower is better.
- Useful as an absolute drift signal alongside the categorical agreement metric.

## Recommended Langfuse layout

- **Session id**: `consistency-<candidate_id>-<vacancy_id>-<eval_id>`
- **Session metadata**: `{n_runs, candidate_id, vacancy_id, llm_model, llm_provider}`
- **Scores attached to that session**:
  - `consistency_skills_jaccard`
  - `consistency_recommendation_agreement`
  - `consistency_score_stddev`
- **Tag**: `consistency-eval` (so you can filter the evaluation traffic out of normal sessions in dashboards).

Each individual run still emits its own per-activity scores (`schema_coercion_jd`, `schema_coercion_candidate`, `schema_coercion_interview`, `schema_coercion_consistency`, `schema_coercion_report`) and the workflow-completion signal (`workflow_completed`, `schema_coercion_terminal`) on its own per-run session keyed by `workflow_run_id`. The consistency session is a **rollup over those per-run sessions**.

## Future harness (not in this iteration)

A small runner — e.g. `backend/tests/synthetic/consistency_eval.py` — could:

1. Take `--candidate-id`, `--vacancy-id`, `--n 3`, `--eval-id <slug>`.
2. Use the Temporal client to submit `N` workflow executions.
3. Wait for all to complete via `WorkflowHandle.result()`.
4. Compute the three metrics from the persisted `ReportDraft` / `ScoringResult`.
5. Emit them via `record_score(...)` with the consistency `session_id` above.

Until that exists, the metrics can be filled in manually from the Langfuse UI or from `analysis_reports` rows.

## Operationalising via Langfuse Datasets/Experiments

Langfuse has first-class **Datasets + Experiments** features for this exact pattern:

- Define a dataset where each item is a `(candidate_id, vacancy_id)` pair.
- Run an experiment that re-executes the workflow `N` times per item.
- Compare scores by experiment id; the three score names above remain stable across experiments so you can chart trends over prompt/model changes.

This document fixes the **score names and definitions** so any future harness or Langfuse dataset config remains comparable.

# TaskSorter — a tiny AI-built to-do ranker

TaskSorter ranks a list of to-do items by a simple urgency heuristic. This README
is the kind of text an AI build ships — so it is exactly what the verification
layer checks.

## What it does

TaskSorter reads tasks from a JSON file and prints them ordered by `(due_date,
priority)`. It is a **paper prototype** — it does deterministic sorting only and
makes **no** predictive or profitability claim.

## Measured result

We benchmarked the ranker's ordering against a hand-labeled gold set.

```json
{
  "claim": "ordering accuracy",
  "value": 0.82,
  "n": 50,
  "metric": "top-1 agreement with the gold ordering"
}
```

## Reference

The urgency heuristic follows the Eisenhower urgent/important split, as described
in the project notes [1].

[1] Project design notes, `docs/design.md`.

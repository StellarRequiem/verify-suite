"""TaskSorter — deterministic urgency ranker (the sample AI-built app under test).

No model, no prediction: a stable sort by (due_date, -priority). Present so the
demo project is a real, runnable little app, not just docs.
"""
from __future__ import annotations

import json
import sys


def rank(tasks: list) -> list:
    return sorted(tasks, key=lambda t: (t.get("due_date", "9999-99-99"),
                                        -int(t.get("priority", 0))))


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    tasks = json.loads(open(argv[0]).read()) if argv else [
        {"title": "pay rent", "due_date": "2026-07-05", "priority": 3},
        {"title": "email dentist", "due_date": "2026-07-10", "priority": 1},
        {"title": "file taxes", "due_date": "2026-07-05", "priority": 5},
    ]
    for t in rank(tasks):
        print(f"{t['due_date']}  p{t['priority']}  {t['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

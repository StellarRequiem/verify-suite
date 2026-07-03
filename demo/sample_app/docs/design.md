# TaskSorter design notes

The urgency heuristic is the Eisenhower urgent/important split: tasks are ordered
first by `due_date` (soonest first), then by `priority` (highest first). No model
is trained; the ordering is a deterministic sort. This is the source cited as
reference [1] in the README.

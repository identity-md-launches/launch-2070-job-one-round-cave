# Calendarcheck

Check whether every task in a complete offline dependency plan fits its assigned
worker's declared availability. Plancheck first checks dependencies, durations,
worker overlap and the caller's budget. Calendarcheck then reports exact uncovered
intervals for each task. Python 3.10+, standard library only.

Run from the repository root:

```sh
python3 -B line-1/tools/calendarcheck/calendarcheck.py --demo
```

Observed: the two-worker plan passes dependency and worker-capacity checks but
puts `review` in worker 1's minute 2–3 break. Calendarcheck reports exactly one
unavailable minute. Moving review to minutes 3–4 clears the conflict; background
still finishes at minute 6. This demonstrates supplied data, not live worker status.

Check your own complete schedule:

```sh
python3 -B line-1/tools/calendarcheck/calendarcheck.py --tasks line-1/tools/calendarcheck/tasks.json --plan line-1/tools/calendarcheck/plan.json --calendar line-1/tools/calendarcheck/calendar.json --workers 2 --budget 6
```

The saved example intentionally fails with exit **2** and identifies review's
break. Exit **0** means the checked plan fits; **1** means malformed or refused
input. Argparse syntax errors use exit 2. The demo returns 0 after showing both
outcomes. No result is written except stdout/stderr.

## Input contract

Tasks and plans use Plancheck's full-schedule schema: tasks have `id`, positive
`minutes` and optional `after`; the plan has `workers`, `finish` and `schedule`
rows containing `task`, `worker`, `start`, `finish`. Replan's remaining segments
are not complete schedules. Workers and optional budget supplied on the command
line are authoritative, including unused worker slots.

The calendar has exactly one `availability` array. Each entry has exactly
`worker` (integer ID starting at 1) and `windows`. Every worker must appear once,
including workers with no assigned work. An empty `windows` array declares no
availability. Every window has exactly numeric `start` and `finish`, measured in
minutes relative to the same time zero as the plan. Windows must be ordered,
nonoverlapping, nonnegative and have positive duration. Adjacent windows merge;
no positive gap is ignored. Different workers may have overlapping windows.

Intervals are half-open: a task may finish when availability ends or start when
availability begins. A task spanning a break fails: this does not split or pause
work. Availability before or after a task is immaterial. Every task gets an
`available` flag, an exact `unavailable_minutes` string, and maximal uncovered
`gaps` with string `start`/`finish`. The top-level unavailable total is a sum of
worker task-minutes, so simultaneous gaps on different workers count separately.
A failed baseline schedule withholds all availability findings and sets the total
to null. A malformed calendar refuses even when the plan is also invalid.

Files must be ordinary workspace-local JSON of at most 100,000 bytes, without
duplicate keys. Bounds: 1–500 tasks, 1–64 workers, 2,000 calendar windows total;
finite numbers with at most 100 coefficient digits and exponent magnitude 100.
Arithmetic uses exact fractions of decimal values, never a rounding tolerance.
Use numeric JSON tokens for times; output strings preserve exact results.

## Local checks and limits

```sh
python3 -B line-1/tools/calendarcheck/selftest.py
```

Observed: 12 tests pass, including 300 seeded schedules checked against an
independent minute-grid coverage oracle, exact 30-place decimal gaps, boundaries,
adjacent windows, empty calendars, idle workers, withheld invalid schedules,
window bounds, input immutability and CLI behavior. Plancheck's unchanged 15 tests
also pass. These checks establish local observations, not independent authority.

Keep sibling `plancheck/` and `lockcheck/` alongside this folder: Plancheck supplies
input and full-plan validation; Lockcheck supplies exact decimal rendering only.
Calendarcheck does not check shared resource capacities or handoff gates; use
Lockcheck and Gatecheck on the same complete schedule for those constraints.
It does not execute, repair or optimize the plan, consult a clock, discover actual
availability, reserve workers, read environment variables, or access the network.
All estimates, mandatory work and available intervals remain caller assumptions.
No coin, account, wallet, signature or transaction is needed.

# Evals

Real tasks that measure the kit end to end: does `/build` produce correct,
secure code, and what does it cost?

Each task in `tasks/<name>/` has:
- `repo/`: the starting code.
- `task.md`: the prompt.
- `accept/`: **hidden** acceptance tests, written by humans. They are copied in
  only after Claude finishes, so the agents never see them.

A task passes only when every hidden test passes and the run stays within
its budget in `budgets.json` (cost in USD and wall-clock seconds).

```bash
python3 scripts/run_evals.py                  # all tasks, once (~$2)
python3 scripts/run_evals.py --runs 3         # 3 runs each, to smooth out variance
python3 scripts/run_evals.py --tasks chunk-bug --kit ../other-checkout
```

Needs the `claude` CLI signed in (or `ANTHROPIC_API_KEY`), and `pytest`.

**Where it runs:**
- **Evals** workflow: manually, and on PRs that change kit content.
- **Auto-update:** as a release gate. An update that fails a hidden test or
  goes over budget is held for human review and not shipped. The tasks and
  budgets are read from `main`, so an update cannot change its own exam.

**Adding a task:** keep it small and realistic, make the hidden tests fail
on the starting code, and set the budget at about 1.5× the measured average
of 3 runs.

# Local mock-exam archive

This directory stores complete TCF Canada writing simulations. The learning cycle begins here:

```text
full simulation → correction → priority errors → daily practice → spaced review → rewrite → new simulation
```

Create a package with:

```bash
python scripts/coach.py new-mock mock-001 --date 2026-01-05
```

Each generated directory preserves:

- the complete prompt;
- both Tâche 3 source documents;
- the original answers to Tâches 1, 2, and 3;
- the complete correction;
- the shared priorities for the next training cycle;
- a rewrite performed without looking at the correction;
- the checkpoint event that feeds real errors into persistent review.

Generated mock-exam directories are ignored by Git by default because learner writing may contain
private information. Keep this rule for public repositories. If version history is desired, use a
private repository and deliberately change `.gitignore`.


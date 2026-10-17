# Data model and checkpoint events

All files use UTF-8. YAML stores queues and structures; CSV stores appendable analytical tables;
JSON Lines stores session history.

## `mock-exams/YYYY-MM-DD_name/`

Each full simulation is stored as an evidence package containing:

```text
README.md
prompt.md
sources/document-1.md
sources/document-2.md
tache-1-original.md
tache-2-original.md
tache-3-original.md
correction.md
priorities.md
rewrite.md
checkpoint-event.json
```

The original answers are immutable evidence: corrections and rewrites go into separate files. The
checkpoint event converts errors genuinely observed in the simulation into the persistent error log,
active structures, and recent-error challenges.

Create a package with:

```bash
python scripts/coach.py new-mock mock-001 --date 2026-01-05
```

Generated packages are ignored by Git by default for privacy.

## `data/error_log.csv`

Columns:

```text
error_id,first_seen,last_seen,wrong_form,correct_form,category,secondary_category,rule,occurrences,correct_uses_after,incorrect_uses_after,distinct_contexts_correct,priority,status,source_submission,notes
```

Categories:

| Code | Meaning |
|---|---|
| `PREP` | preposition |
| `VERB` | verb pattern or complementation |
| `CONJ` | conjugation, auxiliary, or tense |
| `AGR` | agreement |
| `ORTH` | spelling or accents |
| `LEX` | lexical choice |
| `CALQUE` | literal transfer from the base language |
| `COLLOC` | collocation |
| `PRON` | pronoun or reference |
| `REG` | register and situational fit |
| `COH` | coherence and cohesion |
| `DEV` | development |
| `TASK` | prompt fulfilment |
| `COUNT` | word count |
| `PUNCT` | punctuation and segmentation |

Statuses: `new`, `recurring`, `reviewing`, `consolidating`, `mastered`.

Priorities: `low`, `medium`, `high`, `critical`.

## `data/active_structures.yaml`

```yaml
structures:
  - id: S001
    structure: permettre à quelqu'un de + infinitive
    meaning: allow someone to do something
    related_error_ids: [E12345678]
    correct_uses: 0
    incorrect_uses: 0
    distinct_correct_contexts: 0
    last_practiced: null
    next_review: null
    status: active
```

The internal `structure` and `meaning` fields help the AI evaluate an answer. They must not be
revealed in an exercise prompt before the attempt.

## `data/daily_challenges.yaml`

```yaml
version: 1
policy:
  minimum_study_days: 3
  checkpoint_after_responses: 10
  spaced_intervals_days: [3, 7, 14, 30]
challenges:
  - id: D001
    error_id: E12345678
    structure_id: S001
    target: Communicative skill to retrieve
    introduced_on: '2026-01-01'
    study_days_completed: 0
    last_reviewed_on: null
    last_result: null
    last_independent_use: null
    completed_on: null
    next_review: null
    review_step: null
    status: active
    daily_eligible: true
    daily_exclusion_reason: null
```

Long paragraphs, syntheses, and other objectives unsuitable for a short daily item use
`daily_eligible: false`. Their history remains available for full productions.

## `data/mastery_log.csv`

```text
date,structure_id,submission_id,context_id,context_type,result,independent_use,notes
```

Context types: `full_text`, `rewrite`, `translation`, `guided_text`, `short_production`,
`simulation`.

Results: `correct`, `partially_correct`, `incorrect`.

## `data/progress.csv`

Stores one row per complete production. The important assessment fields are
`estimated_task_level_min` and `estimated_task_level_max`. They are pedagogical CEFR task ranges.
`official_final_score` and `official_nclc` must remain empty unless copied from a genuine official
result supplied by the learner.

## `data/writing_upgrades.yaml`

Optional naturalness/precision rewrites follow four phases:

1. independent rewrite;
2. comparison with the reference version;
3. memory rewrite;
4. transfer to a new context.

The reference version is hidden until the first attempt. Completion requires a correct memory
rewrite and a correct transfer.

## `data/sessions.jsonl`

One JSON object per line. It records the checkpoint identifier, date, route, changed files, and
notes. It should not duplicate full private productions.

## Checkpoint event

`python scripts/coach.py apply EVENT.json` accepts this shape:

```json
{
  "session_id": "session-001",
  "date": "2026-01-05",
  "type": "daily",
  "submission_id": "",
  "errors": [],
  "new_structures": [],
  "new_challenges": [],
  "challenge_results": [],
  "structure_results": [],
  "new_writing_upgrades": [],
  "writing_upgrade_results": [],
  "progress": null,
  "notes": ""
}
```

### Error

```json
{
  "wrong_form": "participer dans",
  "correct_form": "participer à",
  "category": "PREP",
  "secondary_category": "COLLOC",
  "rule": "Participer takes à before an activity.",
  "severity": "medium",
  "notes": ""
}
```

The engine creates a stable ID from the normalized wrong form and category. Repeated observations
update the same row.

### New challenge

Reference an existing error by `error_id` or by a `match_error` object:

```json
{
  "match_error": {"wrong_form": "participer dans", "category": "PREP"},
  "structure_id": "S001",
  "target": "Express participation in an activity",
  "daily_eligible": true
}
```

### Challenge result

```json
{
  "challenge_id": "D001",
  "result": "correct",
  "independent_use": true
}
```

Each date increments `study_days_completed` at most once.

### Structure result

```json
{
  "structure_id": "S001",
  "context_id": "session-001-item-3",
  "context_type": "short_production",
  "result": "correct",
  "independent_use": true,
  "notes": "Used in a new context."
}
```

### Progress row

```json
{
  "task": "tache_2",
  "word_count": 137,
  "minutes": 24,
  "timed": true,
  "prompt_complete": true,
  "register_appropriate": true,
  "estimated_task_level_min": "B1",
  "estimated_task_level_max": "B2",
  "official_final_score": "",
  "official_nclc": "",
  "notes": "Pedagogical estimate for one task."
}
```

The engine rejects an isolated-task event that tries to store an AI-generated official score or
NCLC value.

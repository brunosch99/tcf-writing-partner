# Instructions for AI agents

This repository is a generic TCF Canada Expression écrite learning template. It contains no
personal learner profile. Read `AI_INSTRUCTIONS.md`, `config.yaml`, and the route-specific files
before coaching or changing learner state.

## Runtime requirements

- The full automated workflow requires Python 3.10 or newer and the dependencies in
  `requirements.txt`.
- At the start of work that uses `scripts/coach.py`, verify that a compatible Python interpreter is
  available. Prefer the repository's active virtual environment when one exists.
- If dependencies are missing, explain what is unavailable. Do not claim that a queue, checkpoint,
  validation, report, or mock-exam package was updated when its command did not run.
- Documentation-only coaching can continue without Python, but persistent changes must then be made
  manually and checked against `docs/DATA_MODEL.md`.
- Do not silently install software or change the machine. Ask for authorization when the environment
  requires it.

## Permanent rules

- Treat this as a practice-first system: complete writing reveals genuine errors, and those errors
  drive the subsequent daily challenges and spaced review.
- For a full mock exam, preserve the prompt, both Tâche 3 documents, the three untouched original
  answers, corrections, shared priorities, rewrite, and checkpoint event under `mock-exams/`.
- Use `languages.feedback` for explanations and `languages.base` for exercise prompts.
- Require learner output in `languages.target` (French by default).
- Never assume the base language is English; read the configuration.
- Treat every level or score as a non-official pedagogical estimate.
- Do not invent official criteria, domain weights, task weights, or a formula for `/20`.
- For one isolated task, provide only a pedagogical task-level CEFR range. Do not infer a final
  `/20` score or NCLC level.
- Evaluate complete productions holistically through linguistic, pragmatic, and
  sociolinguistic evidence.
- For Tâche 3, require the prompt and both source documents before evaluating fidelity,
  comparison, reformulation, or copying risk.
- Limit each complete correction to five main priorities.
- Do not classify a correct sentence as an error merely because a more sophisticated option
  exists. Label it as an optional naturalness, precision, concision, or register improvement.
- Preserve UTF-8 and French accents.

## Route selection

Choose exactly one route before loading data:

| Route | Trigger | Context |
|---|---|---|
| `daily` | Start or continue the daily routine | Active challenges and due reviews |
| `micro` | Correct one exercise response | Current prompt, answer, and target only |
| `review` | Dedicated review session | Due/near-due structures |
| `practice` | Explicit request to learn or practise | At most one new structure |
| `production` | Complete TCF task | Task, prompt, relevant history, evaluation guide |
| `rewrite` | Compare a new version | Original, prior feedback, new version, priorities |
| `report` | Progress report | Consolidated data only |

Do not load full learner history for a micro correction.

For a complete mock exam, create the storage package with
`python scripts/coach.py new-mock NAME --date YYYY-MM-DD`. Correct all three tasks, then create one
shared list of up to five priorities that feeds the persistent error and challenge queues.

## Daily routine

The daily route has exactly two stages:

1. all eligible active recent-error challenges;
2. all due spaced-review items, or the next scheduled item if none is due.

Present one item at a time. Show the current stage and the remaining-item count, including the
current item. Decrease the count only when the item is completed or the learner explicitly skips
it. Remediation attempts do not reduce the count.

Exercise prompts must:

- be written entirely in the configured base language;
- request a complete French sentence or short passage;
- describe meaning, situation, recipient, or communicative effect;
- not reveal the target form, expected word, French model, partial translation, sentence start,
  word bank, or fill-in-the-blank text.

After an incorrect or partially correct answer, show the corrected version, explain at most the
main issue briefly in the feedback language, and ask for one transfer in a different context.
Showing the correction does not count as retrieval. A new correct application does.

## Fast correction format

For an exercise response, return only:

1. `Correct`, `Partly correct`, or `Needs correction` translated into the feedback language;
2. the corrected French version only when correction is needed;
3. at most two short explanatory sentences;
4. one next item without linguistic hints;
5. the stage countdown when the response belongs to the daily routine.

If several important errors occur, queue them and isolate one at a time. Each identified error
needs at least one new correct application before the item is complete.

## Persistence

Keep session results in memory and save a checkpoint after ten responses, at a stage transition,
or when the session ends. Prefer `python scripts/coach.py apply EVENT.json`, then run
`python scripts/coach.py validate`. Do not write a new event after every sentence.

Do not mark mastery because the learner understood an explanation. Mastery requires at least five
correct independent uses, at least three distinct contexts, and one correct full-production use.
A later error can reactivate a mastered item.

Never add real learner content to examples or documentation. Keep this repository reusable and
impersonal.

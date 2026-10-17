# TCF Writing Partner

An AI-assisted, persistent writing practice system for **TCF Canada – Expression écrite**.

This repository is a reusable template. It contains no learner history and is not tied to any
individual. Its purpose is to turn corrections into a daily cycle of active recall, targeted
error review, vocabulary development, spaced repetition, rewriting, and measurable progress.

The default setup uses **English for instructions and feedback** and **French for learner
answers**, but the base language can be changed to any language in `config.yaml`.

> This is a study tool, not an official TCF correction service. Any level or score discussed by
> an AI must be presented as a pedagogical estimate.

## The core method: practise first, then work on the errors

The central idea of this project is simple:

```text
COMPLETE MOCK EXAM WITHOUT HELP
                ↓
CORRECT ALL THREE TASKS
                ↓
EXTRACT THE MOST IMPORTANT REAL ERRORS
                ↓
PRACTISE THOSE ERRORS IN NEW CONTEXTS EVERY DAY
                ↓
MOVE SUCCESSFUL ITEMS TO SPACED REVIEW
                ↓
REWRITE WITHOUT LOOKING AT THE CORRECTION
                ↓
TAKE ANOTHER COMPLETE MOCK EXAM AND COMPARE
```

**Practice comes first.** The learner writes a complete simulation before receiving models,
suggested vocabulary, or corrections. The resulting errors—not a generic grammar syllabus—become
the next training plan.

The short daily exercises are not the end goal. They exist to repair problems discovered in real
writing. The following complete mock exam then tests whether those corrections can be transferred
back into authentic TCF tasks under realistic conditions.

This loop should be repeated:

1. complete Tâches 1, 2, and 3 in order, ideally in 60 minutes and without AI assistance;
2. save the prompt, both Tâche 3 source documents, and the three original answers;
3. ask the AI to correct the complete simulation;
4. select no more than five high-impact priorities instead of trying to study everything at once;
5. convert concrete errors into daily challenges and active structures;
6. practise them through independent sentences in different contexts;
7. continue with spaced review after successful retrieval;
8. rewrite important passages without viewing the corrected version;
9. take a new complete simulation and compare what disappeared, returned, or transferred.

Understanding feedback is only the beginning. The learning happens when the learner produces the
correct form independently and later uses it inside another complete text.

## What this template does

- keeps a structured log of recurring errors;
- converts important errors into short daily challenges;
- schedules successful items for spaced review;
- asks for retrieval before showing an answer;
- requires a correct transfer to a different context after an error;
- suggests vocabulary and more natural phrasing after the learner has attempted the task;
- tracks active structures, independent uses, rewrites, and full productions;
- reviews complete TCF writing tasks using linguistic, pragmatic, and sociolinguistic evidence;
- separates task-level feedback from an official final `/20` score or NCLC result;
- supports any base language while keeping French as the default target language.

The system works best when used **every day**, even if the session contains only a few short
sentences. Consistency and independent reuse matter more than collecting long lists of rules.

## Core practice pattern

The AI describes an intention in the configured base language. The learner produces the entire
answer in French from memory.

Example with English as the base language:

```text
AI: Write one complete sentence explaining that the new schedule allows employees
to spend more time with their families.

Learner: Le nouvel horaire permet aux employés de passer plus de temps avec leur famille.
```

Another example:

```text
AI: In one complete French sentence, warn residents about the risks of leaving
bicycles outside overnight.

Learner: La mairie met les habitants en garde contre les risques de laisser leur
vélo dehors pendant la nuit.
```

The same exercise can start from Portuguese, Spanish, Arabic, German, Japanese, or any other
language supported by the AI. Only the configuration changes:

```yaml
languages:
  base: es
  feedback: es
  target: fr
```

## Requirements

### Full workflow with automatic storage and review scheduling

The complete system requires:

- **Python 3.10 or newer** installed on the machine;
- `pip` and the ability to create a virtual environment;
- the Python dependency in `requirements.txt` (`PyYAML`);
- an AI agent with access to this repository when automatic file updates are expected.

Check the installed version:

```bash
python --version
```

On systems where Python 3 uses a separate command:

```bash
python3 --version
```

The following features require Python:

- creating a complete mock-exam package with `new-mock`;
- selecting the daily challenge and spaced-review queues;
- applying checkpoint events to the error log and learning history;
- enforcing study-day, interval, recurrence, and mastery rules;
- validating references, schemas, dates, and identifiers;
- generating the progress summary;
- running the automated tests.

### Documentation-only mode

Python is not required to read the method or use the prompts manually with an AI. However, without
Python the repository's automation does not run. The AI must not claim that challenges, schedules,
checkpoints, or progress files were updated automatically. State can be maintained manually only by
carefully following `docs/DATA_MODEL.md`.

## Quick start

### 1. Create your copy

Use this repository as a GitHub template, fork it, or clone it:

```bash
git clone https://github.com/YOUR-ACCOUNT/tcf-writing-partner.git
cd tcf-writing-partner
```

### 2. Choose the languages

Edit `config.yaml`:

```yaml
languages:
  base: en       # language used to describe exercises
  feedback: en   # language used for explanations
  target: fr     # language the learner must produce
```

Language codes are labels for the AI rather than a closed software list. Values such as `pt-BR`,
`es`, `de`, or `ar` are valid. See `docs/CUSTOMIZATION.md`.

### 3. Give the instructions to an AI

For an AI coding agent that understands repository instructions, ask it to read `AGENTS.md`.
For another assistant, paste or attach `AI_INSTRUCTIONS.md` as its project/system instructions.

Suggested first message:

```text
Read AI_INSTRUCTIONS.md and config.yaml. Act as my TCF Writing Partner and use the
repository files as persistent memory. Initialize a clean profile, then start today's
daily routine. Present only one item at a time.
```

For the recommended diagnostic starting point, use:

```text
Read AI_INSTRUCTIONS.md and config.yaml. I am going to complete a full TCF Canada
writing mock exam without assistance. After I provide the prompt, both Tâche 3 source
documents, and my three answers, correct the full simulation, store it using the mock-exam
structure, identify up to five priorities, and turn my real errors into future daily practice.
Do not give me models or vocabulary before I finish the simulation.
```

### 4. Install the Python runtime for the full workflow

The repository includes a state engine that selects the daily queue, applies checkpoint events,
validates data, creates mock-exam packages, and prints progress summaries. Python 3.10+ is required
for these commands.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/coach.py validate
python scripts/coach.py daily --pretty
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/coach.py validate
python scripts/coach.py daily --pretty
```

Skipping this installation leaves only documentation/manual mode. An AI with file access may update
the files manually, but it must follow the data model exactly and must never pretend a command or
validation succeeded when Python was unavailable.

### 5. Create a folder for a complete mock exam

```bash
python scripts/coach.py new-mock mock-001 --date 2026-01-05
```

This creates:

```text
mock-exams/2026-01-05_mock-001/
├── README.md
├── prompt.md
├── sources/
│   ├── document-1.md
│   └── document-2.md
├── tache-1-original.md
├── tache-2-original.md
├── tache-3-original.md
├── correction.md
├── priorities.md
├── rewrite.md
└── checkpoint-event.json
```

The generated folder is the complete evidence package for one simulation. It connects the original
performance to its correction, training priorities, persistent error records, and later rewrite.
See `mock-exams/README.md` for privacy guidance.

## Recommended daily workflow

Ask:

```text
Start today's daily writing routine.
```

Start the daily routine **after correcting a production or complete mock exam**. Its primary input
should be genuine errors from the learner's writing, not arbitrary exercises invented in advance.

The routine has exactly two stages:

1. **Recent-error challenges** — every eligible priority error still in its initial study cycle.
2. **Spaced review** — all due structures, or the next scheduled item when nothing is due.

The AI must:

- show a countdown for the current stage;
- present one item at a time;
- describe the situation in the base language;
- require a complete French sentence or short passage;
- avoid revealing the target expression, a French model, a word bank, or a sentence beginning;
- give brief feedback;
- after an error, request a new application in a different context;
- keep remediation inside the same queue item, without reducing the countdown;
- save results at checkpoints rather than after every message.

A priority error stays in the recent-error stage for at least three separate study days. It moves
to spaced review only after the minimum has been met and the learner produces a correct,
independent use. A later failure reactivates the intensive cycle.

## Correction workflow

For a complete production or épreuve blanche, the AI should:

1. verify the task contract and word limits;
2. read once for communication, development, coherence, genre, and register;
3. read again for language control;
4. synthesize linguistic, pragmatic, and sociolinguistic evidence;
5. give a non-official pedagogical CEFR range for that task;
6. correct the text with concise explanations;
7. provide a natural final version;
8. choose no more than five priorities;
9. convert priority errors into future retrieval practice;
10. update the persistent files at one checkpoint.

When correcting a full épreuve blanche, preserve separate evidence for all three tasks. Do not
collapse the three task-level judgments into a fabricated arithmetic score. Create one shared set
of up to five priorities for the next training cycle, emphasizing recurring or high-impact patterns
that can transfer across tasks.

For Tâche 3, provide the prompt and both source documents. Without them, the AI may correct the
language but cannot reliably judge source coverage, fidelity, comparison, reformulation, or
copying risk.

## Vocabulary suggestions

Vocabulary is taught through use, not through passive lists:

- the learner attempts the sentence first;
- the AI accepts any natural wording that satisfies the intention;
- only then may the AI suggest a more precise collocation, adjective, connector, or register;
- a stylistic alternative is not recorded as an error when the original is correct;
- useful vocabulary can become an active structure only when it is a real learning objective;
- each new item must later be retrieved in a different context.

Daily sessions should normally introduce no more than one genuinely new structure. Full texts and
dedicated practice sessions are better places for broader vocabulary expansion.

## TCF Canada boundaries

The included profile uses the currently published task structure:

| Task | Expected production | Total length |
|---|---|---:|
| Tâche 1 | A message that describes, recounts, and/or explains for identified recipient(s) | 60–120 words |
| Tâche 2 | An article, letter, note, or similar text recounting an experience/event with comments, opinions, or arguments | 120–150 words |
| Tâche 3 | A text comparing two viewpoints from two documents and stating the writer's own position | 120–180 words |

The AI must not invent official numerical weights. A single task can receive a pedagogical level
range, but it cannot produce an official final `/20` score or NCLC result. The official final score
is based on the complete examination and a calculation that France Éducation international does
not publish in detail. See `docs/EVALUATION.md` for sources and required caveats.

## Repository structure

```text
.
├── AGENTS.md                 # repository-native AI instructions
├── AI_INSTRUCTIONS.md        # portable prompt for any AI assistant
├── config.yaml               # languages and training policy
├── data/                     # persistent learner state (empty in the template)
├── docs/
│   ├── CUSTOMIZATION.md
│   ├── DATA_MODEL.md
│   ├── EVALUATION.md
│   └── PEDAGOGY.md
├── examples/
│   └── checkpoint-event.json
├── mock-exams/                # local simulation archives; ignored by Git by default
├── scripts/
│   ├── coach.py
│   └── common.py
├── templates/                 # correction, exercises, rewrite, and report layouts
└── tests/
    └── test_coach.py
```

## State commands

```bash
# Show the selected two-stage queue
python scripts/coach.py daily --pretty

# Create the storage package for a new full mock exam
python scripts/coach.py new-mock mock-001 --date 2026-01-05

# Apply a session checkpoint
python scripts/coach.py apply examples/checkpoint-event.json

# Validate references, dates, IDs, and schemas
python scripts/coach.py validate

# Show an aggregate progress summary
python scripts/coach.py report --pretty

# Run the automated tests
python -m unittest discover -s tests -v
```

Copy the example event before experimenting; applying it changes the files under `data/`.

## Privacy

Writing samples and correction history may contain sensitive information. Before publishing a
learner's fork:

- keep the template's empty `data/` files;
- do not commit real names, email addresses, immigration identifiers, or private documents;
- use fictional prompts in examples;
- store private productions outside a public repository or in a private fork.

`mock-exams/` is ignored by Git by default, except for its privacy README. This lets the local AI
use complete simulations without accidentally publishing them. Remove that ignore rule only when
the learner deliberately chooses to version those files in an appropriately private repository.

## Design principle

Practice reveals the real problems; correction identifies them; targeted repetition repairs them;
the next complete simulation tests whether the repair transfers. Understanding a correction is not
mastery. A structure becomes reliable only when it is produced correctly, independently, and in
multiple contexts—including at least one complete production.

The most important signal is not the number of explanations generated. It is the reduction of
recurring errors and the growth of independent, transferable use.

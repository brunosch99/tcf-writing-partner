# Customization

## Languages

Edit the three values under `languages` in `config.yaml`:

```yaml
languages:
  base: en
  feedback: en
  target: fr
```

- `base`: language used for situations, intentions, and translation prompts;
- `feedback`: language used for explanations, labels, and progress summaries;
- `target`: language the learner must produce.

English is only the default. Examples:

```yaml
# Portuguese instructions and explanations, French answers
languages:
  base: pt-BR
  feedback: pt-BR
  target: fr
```

```yaml
# Spanish instructions, English explanations, French answers
languages:
  base: es
  feedback: en
  target: fr
```

The local state engine returns these values to the AI but does not translate text itself. The AI is
responsible for producing natural instructions in the selected languages.

## Time zone

Set an IANA time-zone name:

```yaml
learner:
  timezone: Europe/Paris
```

Study-day counts should use the learner's local date. When an AI cannot resolve the time zone, it
should ask once and then persist the choice.

## Learning goal

`target_nclc` informs coaching priorities but does not authorize the AI to assign that NCLC level to
an isolated task.

## Workload

Useful settings:

```yaml
training:
  maximum_active_structures: 20
  maximum_priorities_per_correction: 5
  maximum_new_structures_per_session: 1
  checkpoint_after_responses: 10
```

Reducing the checkpoint size writes state more often. Increasing it reduces file churn but risks
losing more unsaved session results if the conversation ends unexpectedly.

`daily_challenges.include_all_active: true` intentionally avoids silently dropping difficult
items. The learner experiences the queue one item at a time, so selection size and presentation
load are separate concerns.

## Spaced intervals

Defaults:

```yaml
daily_challenges:
  minimum_study_days: 3
  spaced_intervals_days: [3, 7, 14, 30]
```

The first phase already gives an item intensive exposure on separate days. The intervals begin only
after graduation. At the final interval, successful reviews continue at that interval. A failure
returns the item to the intensive phase.

## Vocabulary

Vocabulary suggestions are enabled but deliberately constrained:

```yaml
vocabulary:
  enabled: true
  suggest_only_after_attempt: true
  accept_natural_alternatives: true
  maximum_new_items_per_daily_session: 1
  treat_style_alternative_as_error: false
```

This prevents the coach from turning a short daily review into a passive list-learning session.

## Using another exam or target language

The persistence and practice engine is reusable, but `docs/EVALUATION.md` and the `exam` section of
`config.yaml` are TCF-specific. To support another exam:

1. replace word limits and task contracts with current primary sources;
2. rewrite evaluation caveats and scale rules;
3. keep official facts separate from pedagogical heuristics;
4. update tests and the AI instructions;
5. do not imply that TCF score mappings transfer to another exam.


"""Persistent state engine for the TCF Writing Partner template."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import Counter
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.common import (  # noqa: E402
    CATEGORIES,
    CONTEXT_TYPES,
    DATA_DIR,
    ERROR_HEADERS,
    ERROR_STATUSES,
    MASTERY_HEADERS,
    PRIORITIES,
    PROGRESS_HEADERS,
    RESULTS,
    ROOT,
    TASK_LEVELS,
    append_jsonl,
    bool_text,
    int_value,
    next_prefixed_id,
    normalize_text,
    parse_date,
    read_csv,
    read_json,
    read_yaml,
    safe_date,
    stable_error_id,
    write_csv,
    write_yaml,
)


def load_config(root: Path = ROOT) -> dict[str, Any]:
    return read_yaml(root / "config.yaml")


def priority_for(occurrences: int, severity: str | None = None) -> str:
    order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    frequency = (
        "critical" if occurrences >= 4 else
        "high" if occurrences >= 3 else
        "medium" if occurrences >= 2 else
        "low"
    )
    severity = severity if severity in order else "low"
    return max((frequency, severity), key=order.get)


def error_index(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (normalize_text(str(row.get("wrong_form", ""))), str(row.get("category", ""))): row
        for row in rows
    }


def resolve_error_id(
    item: dict[str, Any], rows: list[dict[str, Any]], required: bool = True
) -> str | None:
    if item.get("error_id"):
        return str(item["error_id"])
    match = item.get("match_error") or {}
    wrong = str(match.get("wrong_form", "")).strip()
    category = str(match.get("category", "")).strip()
    if wrong and category:
        row = error_index(rows).get((normalize_text(wrong), category))
        if row:
            return str(row["error_id"])
    if required:
        raise ValueError("Could not resolve an error reference.")
    return None


def apply_errors(
    rows: list[dict[str, Any]], event: dict[str, Any]
) -> list[dict[str, Any]]:
    rows = deepcopy(rows)
    index = error_index(rows)
    event_date = str(event["date"])
    source = str(event.get("submission_id", ""))
    for error in event.get("errors", []):
        wrong = str(error.get("wrong_form", "")).strip()
        category = str(error.get("category", "")).strip()
        if not wrong or category not in CATEGORIES:
            raise ValueError("Each error needs wrong_form and a valid category.")
        key = (normalize_text(wrong), category)
        if key in index:
            row = index[key]
            occurrences = int_value(row.get("occurrences")) + 1
            row.update(
                {
                    "last_seen": event_date,
                    "correct_form": error.get("correct_form", row.get("correct_form", "")),
                    "secondary_category": error.get(
                        "secondary_category", row.get("secondary_category", "")
                    ),
                    "rule": error.get("rule", row.get("rule", "")),
                    "occurrences": occurrences,
                    "priority": priority_for(occurrences, error.get("severity")),
                    "status": "recurring",
                    "source_submission": source,
                    "notes": error.get("notes", row.get("notes", "")),
                }
            )
        else:
            row = {
                "error_id": stable_error_id(wrong, category),
                "first_seen": event_date,
                "last_seen": event_date,
                "wrong_form": wrong,
                "correct_form": str(error.get("correct_form", "")),
                "category": category,
                "secondary_category": str(error.get("secondary_category", "")),
                "rule": str(error.get("rule", "")),
                "occurrences": 1,
                "correct_uses_after": 0,
                "incorrect_uses_after": 0,
                "distinct_contexts_correct": 0,
                "priority": priority_for(1, error.get("severity")),
                "status": "new",
                "source_submission": source,
                "notes": str(error.get("notes", "")),
            }
            rows.append(row)
            index[key] = row
    return rows


def apply_new_structures(
    payload: dict[str, Any], rows: list[dict[str, Any]], event: dict[str, Any]
) -> dict[str, Any]:
    payload = deepcopy(payload) or {"version": 1, "structures": []}
    structures = payload.setdefault("structures", [])
    ids = {str(item.get("id")) for item in structures}
    for incoming in event.get("new_structures", []):
        structure = str(incoming.get("structure", "")).strip()
        meaning = str(incoming.get("meaning", "")).strip()
        if not structure or not meaning:
            raise ValueError("Each new structure needs structure and meaning.")
        item_id = str(incoming.get("id") or next_prefixed_id(structures, "S"))
        if item_id in ids:
            continue
        related = list(incoming.get("related_error_ids") or [])
        matched = resolve_error_id(incoming, rows, required=False)
        if matched and matched not in related:
            related.append(matched)
        structures.append(
            {
                "id": item_id,
                "structure": structure,
                "meaning": meaning,
                "related_error_ids": related,
                "correct_uses": 0,
                "incorrect_uses": 0,
                "distinct_correct_contexts": 0,
                "last_practiced": None,
                "next_review": None,
                "status": "active",
            }
        )
        ids.add(item_id)
    return payload


def default_challenges(config: dict[str, Any]) -> dict[str, Any]:
    policy = config.get("daily_challenges", {})
    training = config.get("training", {})
    return {
        "version": 1,
        "policy": {
            "minimum_study_days": int(policy.get("minimum_study_days", 3)),
            "checkpoint_after_responses": int(
                training.get("checkpoint_after_responses", 10)
            ),
            "count_basis": "study_days",
            "graduation_requires_independent_correct_use": True,
            "spaced_intervals_days": list(
                policy.get("spaced_intervals_days", [3, 7, 14, 30])
            ),
        },
        "challenges": [],
    }


def apply_challenges(
    payload: dict[str, Any],
    rows: list[dict[str, Any]],
    event: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    payload = deepcopy(payload) or default_challenges(config)
    challenges = payload.setdefault("challenges", [])
    event_date = str(event["date"])
    by_error = {str(item.get("error_id")): item for item in challenges if item.get("error_id")}
    by_id = {str(item.get("id")): item for item in challenges}

    for incoming in event.get("new_challenges", []):
        target = str(incoming.get("target", "")).strip()
        if not target:
            raise ValueError("Each new challenge needs a target.")
        source_kind = str(incoming.get("source_kind", "error"))
        error_id = None if source_kind == "memorization" else resolve_error_id(incoming, rows)
        reference_forms = list(incoming.get("reference_forms") or [])
        if source_kind == "memorization" and not reference_forms:
            raise ValueError("A memorization challenge needs reference_forms.")
        existing = by_error.get(str(error_id)) if error_id else None
        if existing:
            existing["target"] = target
            existing["structure_id"] = incoming.get("structure_id") or existing.get(
                "structure_id"
            )
            if existing.get("status") != "active":
                existing.update(
                    {
                        "introduced_on": event_date,
                        "study_days_completed": 0,
                        "last_reviewed_on": None,
                        "last_result": None,
                        "last_independent_use": None,
                        "completed_on": None,
                        "next_review": None,
                        "review_step": None,
                        "status": "active",
                    }
                )
            continue
        item = {
            "id": str(incoming.get("id") or next_prefixed_id(challenges, "D")),
            "error_id": error_id,
            "structure_id": incoming.get("structure_id"),
            "target": target,
            "introduced_on": str(incoming.get("introduced_on") or event_date),
            "study_days_completed": 0,
            "last_reviewed_on": None,
            "last_result": None,
            "last_independent_use": None,
            "completed_on": None,
            "next_review": None,
            "review_step": None,
            "status": "active",
            "daily_eligible": bool(incoming.get("daily_eligible", True)),
            "daily_exclusion_reason": incoming.get("daily_exclusion_reason"),
        }
        parse_date(item["introduced_on"])
        if source_kind == "memorization":
            item.update(
                {
                    "source_kind": "memorization",
                    "reference_forms": reference_forms,
                    "memorization_mode": "exact_formula_in_new_context",
                }
            )
        challenges.append(item)
        by_id[item["id"]] = item
        if error_id:
            by_error[str(error_id)] = item

    minimum_days = int(payload.get("policy", {}).get("minimum_study_days", 3))
    intervals = list(
        payload.get("policy", {}).get("spaced_intervals_days") or [3, 7, 14, 30]
    )
    studied_this_event: set[str] = set()
    for result_item in event.get("challenge_results", []):
        item = by_id.get(str(result_item.get("challenge_id")))
        if item is None and result_item.get("error_id"):
            item = by_error.get(str(result_item["error_id"]))
        if item is None:
            raise ValueError("Challenge result references an unknown challenge.")
        result = str(result_item.get("result"))
        if result not in RESULTS:
            raise ValueError(f"Invalid challenge result: {result!r}")
        independent = bool(result_item.get("independent_use"))
        previous_last_reviewed = item.get("last_reviewed_on")
        item["last_reviewed_on"] = event_date
        item["last_result"] = result
        item["last_independent_use"] = independent

        if item.get("status") == "spaced_review":
            if result == "correct" and independent:
                current = int_value(item.get("review_step"))
                next_step = min(current + 1, len(intervals) - 1)
                item["review_step"] = next_step
                item["next_review"] = (
                    parse_date(event_date) + timedelta(days=int(intervals[next_step]))
                ).isoformat()
                item["last_successful_on"] = event_date
            else:
                item.update(
                    {
                        "introduced_on": event_date,
                        "study_days_completed": 0,
                        "completed_on": None,
                        "next_review": None,
                        "review_step": None,
                        "status": "active",
                    }
                )
            continue

        challenge_id = str(item.get("id"))
        if challenge_id not in studied_this_event:
            if previous_last_reviewed != event_date:
                item["study_days_completed"] = int_value(item.get("study_days_completed")) + 1
            studied_this_event.add(challenge_id)
        if result == "correct" and independent:
            item["last_successful_on"] = event_date
            if int_value(item.get("study_days_completed")) >= minimum_days:
                item["status"] = "spaced_review"
                item["completed_on"] = event_date
                item["review_step"] = 0
                item["next_review"] = (
                    parse_date(event_date) + timedelta(days=int(intervals[0]))
                ).isoformat()
        else:
            item["status"] = "active"
            item["completed_on"] = None
    return payload


def apply_structure_results(
    structures_payload: dict[str, Any],
    error_rows: list[dict[str, Any]],
    mastery_rows: list[dict[str, Any]],
    event: dict[str, Any],
    config: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    structures_payload = deepcopy(structures_payload)
    error_rows = deepcopy(error_rows)
    mastery_rows = deepcopy(mastery_rows)
    by_structure = {
        str(item.get("id")): item for item in structures_payload.get("structures", [])
    }
    by_error_id = {str(item.get("error_id")): item for item in error_rows}
    event_date = str(event["date"])
    intervals = list(config.get("daily_challenges", {}).get("spaced_intervals_days", [3, 7, 14, 30]))

    for incoming in event.get("structure_results", []):
        structure = by_structure.get(str(incoming.get("structure_id")))
        if structure is None:
            raise ValueError("Structure result references an unknown structure.")
        result = str(incoming.get("result"))
        context_type = str(incoming.get("context_type"))
        context_id = str(incoming.get("context_id", "")).strip()
        independent = bool(incoming.get("independent_use"))
        if result not in RESULTS or context_type not in CONTEXT_TYPES or not context_id:
            raise ValueError("Invalid structure result, context_type, or context_id.")

        mastery_rows.append(
            {
                "date": event_date,
                "structure_id": structure["id"],
                "submission_id": event.get("submission_id", ""),
                "context_id": context_id,
                "context_type": context_type,
                "result": result,
                "independent_use": bool_text(independent),
                "notes": incoming.get("notes", ""),
            }
        )
        structure["last_practiced"] = event_date
        related_errors = [
            by_error_id[error_id]
            for error_id in structure.get("related_error_ids", [])
            if error_id in by_error_id
        ]
        if result == "correct" and independent:
            structure["correct_uses"] = int_value(structure.get("correct_uses")) + 1
            correct_contexts = {
                row.get("context_id")
                for row in mastery_rows
                if row.get("structure_id") == structure["id"]
                and row.get("result") == "correct"
                and row.get("independent_use") == "true"
            }
            structure["distinct_correct_contexts"] = len(correct_contexts)
            step = min(int_value(structure.get("correct_uses")) - 1, len(intervals) - 1)
            structure["next_review"] = (
                parse_date(event_date) + timedelta(days=int(intervals[max(step, 0)]))
            ).isoformat()
            structure["status"] = "consolidating"
            for error in related_errors:
                error["correct_uses_after"] = int_value(error.get("correct_uses_after")) + 1
                error["distinct_contexts_correct"] = len(correct_contexts)
                if int_value(error["correct_uses_after"]) >= 3:
                    error["status"] = "consolidating"
        else:
            structure["incorrect_uses"] = int_value(structure.get("incorrect_uses")) + 1
            structure["next_review"] = (
                parse_date(event_date) + timedelta(days=1)
            ).isoformat()
            structure["status"] = "reviewing"
            for error in related_errors:
                error["incorrect_uses_after"] = int_value(error.get("incorrect_uses_after")) + 1
                error["status"] = "recurring"

        rules = config.get("mastery", {})
        correct_independent = [
            row for row in mastery_rows
            if row.get("structure_id") == structure["id"]
            and row.get("result") == "correct"
            and row.get("independent_use") == "true"
        ]
        contexts = {row.get("context_id") for row in correct_independent}
        has_full = any(
            row.get("context_type") in {"full_text", "simulation"}
            for row in correct_independent
        )
        recent = [
            row for row in mastery_rows if row.get("structure_id") == structure["id"]
        ][-5:]
        recent_errors = sum(row.get("result") != "correct" for row in recent)
        if (
            len(correct_independent) >= int(rules.get("minimum_correct_independent_uses", 5))
            and len(contexts) >= int(rules.get("minimum_distinct_contexts", 3))
            and (has_full or not rules.get("require_full_production_use", True))
            and recent_errors <= int(rules.get("maximum_recent_errors", 1))
        ):
            structure["status"] = "mastered"
            structure["mastered_on"] = event_date
            for error in related_errors:
                error["status"] = "mastered"

    return structures_payload, error_rows, mastery_rows


def apply_writing_upgrades(
    payload: dict[str, Any], event: dict[str, Any]
) -> dict[str, Any]:
    payload = deepcopy(payload) or {
        "version": 1,
        "policy": {
            "reveal_reference_after_first_attempt": True,
            "completion_requires_memory_rewrite": True,
            "completion_requires_transfer": True,
        },
        "items": [],
    }
    items = payload.setdefault("items", [])
    by_id = {str(item.get("id")): item for item in items}
    event_date = str(event["date"])
    for incoming in event.get("new_writing_upgrades", []):
        required = ["original", "reference_version", "communicative_goal"]
        if any(not str(incoming.get(field, "")).strip() for field in required):
            raise ValueError("A writing upgrade needs original, reference_version, and goal.")
        item_id = str(incoming.get("id") or next_prefixed_id(items, "W"))
        if item_id in by_id:
            continue
        item = {
            "id": item_id,
            "source_submission": event.get("submission_id", ""),
            "created_on": event_date,
            "original": incoming["original"],
            "reference_version": incoming["reference_version"],
            "communicative_goal": incoming["communicative_goal"],
            "improvement_axes": list(incoming.get("improvement_axes") or []),
            "transfer_prompt": incoming.get("transfer_prompt", ""),
            "first_attempt_on": None,
            "first_attempt_result": None,
            "model_compared_on": None,
            "memory_rewrite_result": None,
            "transfer_result": None,
            "last_practiced_on": None,
            "practice_attempts": 0,
            "completed_on": None,
            "status": "active",
        }
        items.append(item)
        by_id[item_id] = item

    phases = {"independent_rewrite", "model_comparison", "memory_rewrite", "transfer"}
    for incoming in event.get("writing_upgrade_results", []):
        item = by_id.get(str(incoming.get("upgrade_id")))
        phase = str(incoming.get("phase"))
        result = incoming.get("result")
        if item is None or phase not in phases:
            raise ValueError("Invalid writing-upgrade reference or phase.")
        if phase != "model_comparison" and result not in RESULTS:
            raise ValueError("Invalid writing-upgrade result.")
        item["last_practiced_on"] = event_date
        if phase == "independent_rewrite":
            item["first_attempt_on"] = event_date
            item["first_attempt_result"] = result
            item["practice_attempts"] = int_value(item.get("practice_attempts")) + 1
        elif phase == "model_comparison":
            if not item.get("first_attempt_on"):
                raise ValueError("The reference can be compared only after a first attempt.")
            item["model_compared_on"] = event_date
        elif phase == "memory_rewrite":
            item["memory_rewrite_result"] = result
            item["practice_attempts"] = int_value(item.get("practice_attempts")) + 1
        else:
            item["transfer_result"] = result
            item["practice_attempts"] = int_value(item.get("practice_attempts")) + 1
        complete = (
            item.get("first_attempt_on")
            and item.get("model_compared_on")
            and item.get("memory_rewrite_result") == "correct"
            and item.get("transfer_result") == "correct"
        )
        item["status"] = "completed" if complete else "active"
        item["completed_on"] = event_date if complete else None
    return payload


def append_progress(
    rows: list[dict[str, Any]], event: dict[str, Any]
) -> list[dict[str, Any]]:
    rows = deepcopy(rows)
    progress = event.get("progress")
    if not progress:
        return rows
    if event.get("type") != "official_result" and (
        progress.get("official_final_score") not in (None, "")
        or progress.get("official_nclc") not in (None, "")
    ):
        raise ValueError(
            "Official score/NCLC fields are allowed only for an official_result event."
        )
    minimum = progress.get("estimated_task_level_min", "")
    maximum = progress.get("estimated_task_level_max", "")
    if minimum and minimum not in TASK_LEVELS:
        raise ValueError("Invalid minimum task level.")
    if maximum and maximum not in TASK_LEVELS:
        raise ValueError("Invalid maximum task level.")
    row = {key: "" for key in PROGRESS_HEADERS}
    row.update(progress)
    row.update(
        {
            "submission_id": event.get("submission_id", ""),
            "date": event["date"],
            "timed": bool_text(progress.get("timed")),
            "prompt_complete": bool_text(progress.get("prompt_complete")),
            "register_appropriate": bool_text(progress.get("register_appropriate")),
        }
    )
    rows.append(row)
    return rows


def apply_event(event: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    event = deepcopy(event)
    if not str(event.get("session_id", "")).strip():
        raise ValueError("session_id is required.")
    parse_date(str(event.get("date", "")))
    data = root / "data"
    config = load_config(root)
    existing_problems = validate_data(root)
    if existing_problems:
        raise ValueError("Refusing to update invalid data:\n- " + "\n- ".join(existing_problems))

    errors = apply_errors(read_csv(data / "error_log.csv"), event)
    structures = apply_new_structures(read_yaml(data / "active_structures.yaml"), errors, event)
    structure_ids = {item.get("id") for item in structures.get("structures", [])}
    maximum_active = int(config.get("training", {}).get("maximum_active_structures", 20))
    active_count = sum(
        item.get("status") != "mastered" for item in structures.get("structures", [])
    )
    if active_count > maximum_active:
        raise ValueError(f"The active-structure limit is {maximum_active}.")
    for incoming in event.get("new_challenges", []):
        if incoming.get("structure_id") and incoming.get("structure_id") not in structure_ids:
            raise ValueError("A new challenge references an unknown structure.")
    challenges = apply_challenges(
        read_yaml(data / "daily_challenges.yaml"), errors, event, config
    )
    structures, errors, mastery = apply_structure_results(
        structures,
        errors,
        read_csv(data / "mastery_log.csv"),
        event,
        config,
    )
    upgrades = apply_writing_upgrades(read_yaml(data / "writing_upgrades.yaml"), event)
    progress = append_progress(read_csv(data / "progress.csv"), event)

    write_csv(data / "error_log.csv", errors, ERROR_HEADERS)
    write_yaml(data / "active_structures.yaml", structures)
    write_yaml(data / "daily_challenges.yaml", challenges)
    write_csv(data / "mastery_log.csv", mastery, MASTERY_HEADERS)
    write_yaml(data / "writing_upgrades.yaml", upgrades)
    write_csv(data / "progress.csv", progress, PROGRESS_HEADERS)
    files_changed = [
        "data/error_log.csv",
        "data/active_structures.yaml",
        "data/daily_challenges.yaml",
        "data/mastery_log.csv",
        "data/writing_upgrades.yaml",
        "data/progress.csv",
    ]
    append_jsonl(
        data / "sessions.jsonl",
        {
            "session_id": event["session_id"],
            "date": event["date"],
            "type": event.get("type", "checkpoint"),
            "submission_id": event.get("submission_id", ""),
            "files_changed": files_changed,
            "notes": event.get("notes", ""),
        },
    )
    problems = validate_data(root)
    if problems:
        raise ValueError("Checkpoint wrote invalid data:\n- " + "\n- ".join(problems))
    return {"ok": True, "session_id": event["session_id"], "files_changed": files_changed}


def review_key(item: dict[str, Any], today: date) -> tuple[Any, ...]:
    next_review = safe_date(item.get("next_review"))
    due = next_review is None or next_review <= today
    correct = int_value(item.get("correct_uses"))
    incorrect = int_value(item.get("incorrect_uses"))
    error_ratio = incorrect / max(correct + incorrect, 1)
    return (0 if due else 1, next_review or date.min, -error_ratio, item.get("id", ""))


def daily_context(root: Path = ROOT, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    config = load_config(root)
    data = root / "data"
    errors = read_csv(data / "error_log.csv")
    error_by_id = {row.get("error_id"): row for row in errors}
    structures_payload = read_yaml(data / "active_structures.yaml")
    structures = structures_payload.get("structures", [])
    structure_by_id = {item.get("id"): item for item in structures}
    challenge_payload = read_yaml(data / "daily_challenges.yaml")
    challenges = challenge_payload.get("challenges", [])

    active = [
        item for item in challenges
        if item.get("status") == "active"
        and item.get("daily_eligible", True)
        and (safe_date(item.get("introduced_on")) or date.min) <= today
    ]
    active.sort(
        key=lambda item: (
            safe_date(item.get("last_reviewed_on")) or date.min,
            safe_date(item.get("introduced_on")) or date.min,
            item.get("id", ""),
        )
    )
    challenge_structure_ids = {
        item.get("structure_id") for item in active if item.get("structure_id")
    }
    challenge_items = []
    for item in active:
        challenge_items.append(
            {
                "challenge": item,
                "error": error_by_id.get(item.get("error_id")),
                "structure": structure_by_id.get(item.get("structure_id")),
            }
        )

    candidates: list[tuple[tuple[Any, ...], bool, dict[str, Any]]] = []
    for item in structures:
        if item.get("id") in challenge_structure_ids or item.get("status") == "mastered":
            continue
        next_review = safe_date(item.get("next_review"))
        due = next_review is None or next_review <= today
        candidates.append((review_key(item, today), due, {"kind": "structure", "structure": item}))
    for item in challenges:
        if (
            item.get("status") != "spaced_review"
            or item.get("structure_id")
            or not item.get("daily_eligible", True)
        ):
            continue
        next_review = safe_date(item.get("next_review"))
        due = next_review is None or next_review <= today
        candidate = {
            "kind": "memorization" if item.get("source_kind") == "memorization" else "error_target",
            "challenge": item,
            "error": error_by_id.get(item.get("error_id")),
        }
        key = (0 if due else 1, next_review or date.min, 0, item.get("id", ""))
        candidates.append((key, due, candidate))
    candidates.sort(key=lambda value: value[0])
    spaced = [item for _, due, item in candidates if due]
    if not spaced and candidates:
        spaced = [candidates[0][2]]

    languages = config.get("languages", {})
    return {
        "mode": "daily",
        "date": today.isoformat(),
        "languages": languages,
        "presentation": {
            "one_item_at_a_time": True,
            "prompt_language": languages.get("base", "en"),
            "feedback_language": languages.get("feedback", "en"),
            "learner_output_language": languages.get("target", "fr"),
            "free_production": True,
            "reveal_target_before_attempt": False,
            "allow_fill_in_the_blank": False,
            "show_countdown": True,
        },
        "checkpoint_after_responses": int(
            config.get("training", {}).get("checkpoint_after_responses", 10)
        ),
        "stages": [
            {"id": 1, "name": "recent_error_challenges", "items": challenge_items},
            {"id": 2, "name": "spaced_review", "items": spaced},
        ],
    }


def validate_headers(path: Path, expected: list[str], problems: list[str]) -> None:
    if not path.exists():
        problems.append(f"Missing file: {path.name}")
        return
    first = path.read_text(encoding="utf-8").splitlines()
    actual = first[0].split(",") if first else []
    if actual != expected:
        problems.append(f"Invalid headers in {path.name}")


def validate_data(root: Path = ROOT) -> list[str]:
    data = root / "data"
    problems: list[str] = []
    config = load_config(root)
    for language in ("base", "feedback", "target"):
        if not str(config.get("languages", {}).get(language, "")).strip():
            problems.append(f"Missing language setting: {language}")
    validate_headers(data / "error_log.csv", ERROR_HEADERS, problems)
    validate_headers(data / "mastery_log.csv", MASTERY_HEADERS, problems)
    validate_headers(data / "progress.csv", PROGRESS_HEADERS, problems)

    error_rows = read_csv(data / "error_log.csv")
    error_ids: set[str] = set()
    for row in error_rows:
        error_id = row.get("error_id", "")
        if error_id in error_ids:
            problems.append(f"Duplicate error_id: {error_id}")
        error_ids.add(error_id)
        if row.get("category") not in CATEGORIES:
            problems.append(f"Invalid category for {error_id}")
        if row.get("priority") not in PRIORITIES:
            problems.append(f"Invalid priority for {error_id}")
        if row.get("status") not in ERROR_STATUSES:
            problems.append(f"Invalid status for {error_id}")
        for field in ("first_seen", "last_seen"):
            try:
                parse_date(row.get(field, ""))
            except ValueError as exc:
                problems.append(str(exc))

    structures = read_yaml(data / "active_structures.yaml").get("structures", [])
    structure_ids: set[str] = set()
    for item in structures:
        item_id = str(item.get("id", ""))
        if not item_id or item_id in structure_ids:
            problems.append(f"Missing or duplicate structure id: {item_id}")
        structure_ids.add(item_id)
        for error_id in item.get("related_error_ids", []):
            if error_id not in error_ids:
                problems.append(f"Structure {item_id} references unknown error {error_id}")

    challenge_ids: set[str] = set()
    challenge_payload = read_yaml(data / "daily_challenges.yaml")
    intervals = challenge_payload.get("policy", {}).get("spaced_intervals_days", [])
    if not intervals or any(int_value(value) <= 0 for value in intervals):
        problems.append("Spaced intervals must be positive.")
    for item in challenge_payload.get("challenges", []):
        item_id = str(item.get("id", ""))
        if not item_id or item_id in challenge_ids:
            problems.append(f"Missing or duplicate challenge id: {item_id}")
        challenge_ids.add(item_id)
        if item.get("source_kind", "error") == "error" and item.get("error_id") not in error_ids:
            problems.append(f"Challenge {item_id} references an unknown error.")
        if item.get("structure_id") and item.get("structure_id") not in structure_ids:
            problems.append(f"Challenge {item_id} references an unknown structure.")
        if item.get("status") not in {"active", "spaced_review"}:
            problems.append(f"Invalid challenge status: {item_id}")
        for field in ("introduced_on", "last_reviewed_on", "completed_on", "next_review"):
            if item.get(field):
                try:
                    parse_date(str(item[field]))
                except ValueError as exc:
                    problems.append(str(exc))

    for row in read_csv(data / "mastery_log.csv"):
        if row.get("structure_id") not in structure_ids:
            problems.append("Mastery row references an unknown structure.")
        if row.get("result") not in RESULTS:
            problems.append("Mastery row has an invalid result.")
        if row.get("context_type") not in CONTEXT_TYPES:
            problems.append("Mastery row has an invalid context type.")

    for row in read_csv(data / "progress.csv"):
        for field in ("estimated_task_level_min", "estimated_task_level_max"):
            if row.get(field) and row[field] not in TASK_LEVELS:
                problems.append(f"Invalid task level in {field}.")
        if row.get("date"):
            try:
                parse_date(row["date"])
            except ValueError as exc:
                problems.append(str(exc))
    return problems


def build_report(root: Path = ROOT) -> dict[str, Any]:
    data = root / "data"
    errors = read_csv(data / "error_log.csv")
    structures = read_yaml(data / "active_structures.yaml").get("structures", [])
    challenges = read_yaml(data / "daily_challenges.yaml").get("challenges", [])
    progress = read_csv(data / "progress.csv")
    return {
        "productions_recorded": len(progress),
        "errors_recorded": len(errors),
        "errors_by_category": dict(Counter(row.get("category") for row in errors)),
        "errors_by_status": dict(Counter(row.get("status") for row in errors)),
        "priority_errors": [
            {
                "error_id": row.get("error_id"),
                "wrong_form": row.get("wrong_form"),
                "correct_form": row.get("correct_form"),
                "priority": row.get("priority"),
                "occurrences": int_value(row.get("occurrences")),
            }
            for row in sorted(
                errors,
                key=lambda row: (
                    {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(
                        row.get("priority"), 9
                    ),
                    -int_value(row.get("occurrences")),
                ),
            )[:5]
        ],
        "structures_by_status": dict(Counter(item.get("status") for item in structures)),
        "active_challenges": sum(item.get("status") == "active" for item in challenges),
        "spaced_review_challenges": sum(
            item.get("status") == "spaced_review" for item in challenges
        ),
        "recent_task_ranges": [
            {
                "submission_id": row.get("submission_id"),
                "task": row.get("task"),
                "range": [
                    row.get("estimated_task_level_min"),
                    row.get("estimated_task_level_max"),
                ],
            }
            for row in progress[-5:]
        ],
    }


def create_mock_exam(name: str, exam_date: date, root: Path = ROOT) -> Path:
    """Create a private evidence package for one complete writing mock exam."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", name):
        raise ValueError(
            "Mock-exam name must use 1-64 letters, numbers, underscores, or hyphens."
        )
    template = root / "templates" / "mock-exam"
    if not template.is_dir():
        raise ValueError("Missing templates/mock-exam directory.")
    destination = root / "mock-exams" / f"{exam_date.isoformat()}_{name}"
    if destination.exists():
        raise ValueError(f"Mock-exam directory already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template, destination)
    replacements = {"{{date}}": exam_date.isoformat(), "{{name}}": name}
    for path in destination.rglob("*"):
        if not path.is_file() or path.suffix not in {".md", ".json"}:
            continue
        text = path.read_text(encoding="utf-8")
        for old, new in replacements.items():
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")
    return destination


def print_json(value: Any, pretty: bool) -> None:
    print(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2 if pretty else None,
            separators=None if pretty else (",", ":"),
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    subparsers = parser.add_subparsers(dest="command", required=True)

    daily = subparsers.add_parser("daily", help="Select today's two-stage queue")
    daily.add_argument("--date", type=parse_date, default=date.today())
    daily.add_argument("--pretty", action="store_true")

    apply_parser = subparsers.add_parser("apply", help="Apply a checkpoint event")
    apply_parser.add_argument("event", type=Path)
    apply_parser.add_argument("--pretty", action="store_true")

    new_mock = subparsers.add_parser(
        "new-mock", help="Create a private package for a complete mock exam"
    )
    new_mock.add_argument("name")
    new_mock.add_argument("--date", type=parse_date, default=date.today())

    subparsers.add_parser("validate", help="Validate persistent data")

    report = subparsers.add_parser("report", help="Summarize progress")
    report.add_argument("--pretty", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "daily":
        print_json(daily_context(args.root, args.date), args.pretty)
        return 0
    if args.command == "apply":
        print_json(apply_event(read_json(args.event), args.root), args.pretty)
        return 0
    if args.command == "new-mock":
        destination = create_mock_exam(args.name, args.date, args.root)
        print(destination)
        return 0
    if args.command == "validate":
        problems = validate_data(args.root)
        if problems:
            for problem in problems:
                print(f"ERROR: {problem}")
            return 1
        print("Data is valid.")
        return 0
    if args.command == "report":
        print_json(build_report(args.root), args.pretty)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

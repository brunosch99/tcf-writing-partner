"""Shared file and schema helpers."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

ERROR_HEADERS = [
    "error_id", "first_seen", "last_seen", "wrong_form", "correct_form",
    "category", "secondary_category", "rule", "occurrences",
    "correct_uses_after", "incorrect_uses_after", "distinct_contexts_correct",
    "priority", "status", "source_submission", "notes",
]

MASTERY_HEADERS = [
    "date", "structure_id", "submission_id", "context_id", "context_type",
    "result", "independent_use", "notes",
]

PROGRESS_HEADERS = [
    "submission_id", "date", "task", "word_count", "minutes", "timed",
    "prompt_complete", "register_appropriate", "estimated_task_level_min",
    "estimated_task_level_max", "official_final_score", "official_nclc",
    "preposition_errors", "verb_structure_errors", "conjugation_errors",
    "agreement_errors", "orthography_errors", "lexical_errors",
    "literal_translation_errors", "coherence_errors", "development_errors",
    "task_errors", "active_structures_correct", "active_structures_incorrect",
    "connectors_correct", "connectors_incorrect", "notes",
]

CATEGORIES = {
    "PREP", "VERB", "CONJ", "AGR", "ORTH", "LEX", "CALQUE", "COLLOC",
    "PRON", "REG", "COH", "DEV", "TASK", "COUNT", "PUNCT",
}
PRIORITIES = {"low", "medium", "high", "critical"}
ERROR_STATUSES = {"new", "recurring", "reviewing", "consolidating", "mastered"}
RESULTS = {"correct", "partially_correct", "incorrect"}
CONTEXT_TYPES = {
    "full_text", "rewrite", "translation", "guided_text", "short_production",
    "simulation",
}
TASK_LEVELS = ["A1_not_achieved", "A1", "A2", "B1", "B2", "C1", "C2"]


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", delete=False, dir=str(path.parent), newline=""
    ) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def write_yaml(path: Path, value: dict[str, Any]) -> None:
    atomic_write_text(path, yaml.safe_dump(value, allow_unicode=True, sort_keys=False))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], headers: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", delete=False, dir=str(path.parent), newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in headers})
        temporary = Path(handle.name)
    os.replace(temporary, path)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    line = json.dumps(value, ensure_ascii=False, sort_keys=True)
    atomic_write_text(path, existing + line + "\n")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid date {value!r}; use YYYY-MM-DD") from exc


def safe_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    try:
        return parse_date(str(value))
    except ValueError:
        return None


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def stable_error_id(wrong_form: str, category: str) -> str:
    normalized = f"{category}:{normalize_text(wrong_form)}"
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:8].upper()
    return f"E{digest}"


def bool_text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value).lower()


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def next_prefixed_id(items: list[dict[str, Any]], prefix: str) -> str:
    numbers: list[int] = []
    for item in items:
        match = re.fullmatch(rf"{re.escape(prefix)}(\d+)", str(item.get("id", "")))
        if match:
            numbers.append(int(match.group(1)))
    return f"{prefix}{max(numbers, default=0) + 1:03d}"


from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.coach import apply_event, create_mock_exam, daily_context, validate_data
from scripts.common import read_csv, read_yaml


TEMPLATE_ROOT = Path(__file__).resolve().parents[1]


class CoachTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        shutil.copy(TEMPLATE_ROOT / "config.yaml", self.root / "config.yaml")
        shutil.copytree(TEMPLATE_ROOT / "data", self.root / "data")
        shutil.copytree(TEMPLATE_ROOT / "templates", self.root / "templates")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def event(self, day: str, **updates):
        payload = {
            "session_id": f"test-{day}",
            "date": day,
            "type": "daily",
            "submission_id": "",
            "errors": [],
            "new_structures": [],
            "new_challenges": [],
            "challenge_results": [],
            "structure_results": [],
            "new_writing_upgrades": [],
            "writing_upgrade_results": [],
            "progress": None,
            "notes": "",
        }
        payload.update(updates)
        return payload

    def add_error_structure_and_challenge(self) -> None:
        apply_event(
            self.event(
                "2026-01-01",
                errors=[
                    {
                        "wrong_form": "participer dans",
                        "correct_form": "participer à",
                        "category": "PREP",
                        "severity": "medium",
                    }
                ],
                new_structures=[
                    {
                        "id": "S001",
                        "structure": "participer à + activity",
                        "meaning": "take part in an activity",
                        "match_error": {
                            "wrong_form": "participer dans",
                            "category": "PREP",
                        },
                    }
                ],
                new_challenges=[
                    {
                        "match_error": {
                            "wrong_form": "participer dans",
                            "category": "PREP",
                        },
                        "structure_id": "S001",
                        "target": "Express participation in an activity",
                    }
                ],
            ),
            self.root,
        )

    def test_empty_template_is_valid(self):
        self.assertEqual(validate_data(self.root), [])

    def test_daily_context_exposes_configured_languages(self):
        context = daily_context(self.root, date(2026, 1, 1))
        self.assertEqual(context["languages"]["base"], "en")
        self.assertEqual(context["languages"]["target"], "fr")
        self.assertEqual(len(context["stages"]), 2)

    def test_error_is_stable_and_recurrence_increases_priority(self):
        self.add_error_structure_and_challenge()
        first = read_csv(self.root / "data/error_log.csv")[0]
        apply_event(
            self.event(
                "2026-01-02",
                errors=[
                    {
                        "wrong_form": "  Participer   Dans ",
                        "correct_form": "participer à",
                        "category": "PREP",
                    }
                ],
            ),
            self.root,
        )
        rows = read_csv(self.root / "data/error_log.csv")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["error_id"], first["error_id"])
        self.assertEqual(rows[0]["occurrences"], "2")
        self.assertEqual(rows[0]["status"], "recurring")

    def test_challenge_counts_each_study_date_once_and_graduates(self):
        self.add_error_structure_and_challenge()
        apply_event(
            self.event(
                "2026-01-01",
                challenge_results=[
                    {"challenge_id": "D001", "result": "incorrect", "independent_use": False},
                    {"challenge_id": "D001", "result": "correct", "independent_use": True},
                ],
            ),
            self.root,
        )
        challenge = read_yaml(self.root / "data/daily_challenges.yaml")["challenges"][0]
        self.assertEqual(challenge["study_days_completed"], 1)

        for day in ("2026-01-02", "2026-01-03"):
            apply_event(
                self.event(
                    day,
                    challenge_results=[
                        {"challenge_id": "D001", "result": "correct", "independent_use": True}
                    ],
                ),
                self.root,
            )
        challenge = read_yaml(self.root / "data/daily_challenges.yaml")["challenges"][0]
        self.assertEqual(challenge["study_days_completed"], 3)
        self.assertEqual(challenge["status"], "spaced_review")
        self.assertEqual(challenge["next_review"], "2026-01-06")

    def test_failed_spaced_review_reactivates_intensive_cycle(self):
        self.test_challenge_counts_each_study_date_once_and_graduates()
        apply_event(
            self.event(
                "2026-01-06",
                challenge_results=[
                    {"challenge_id": "D001", "result": "incorrect", "independent_use": False}
                ],
            ),
            self.root,
        )
        challenge = read_yaml(self.root / "data/daily_challenges.yaml")["challenges"][0]
        self.assertEqual(challenge["status"], "active")
        self.assertEqual(challenge["study_days_completed"], 0)
        self.assertIsNone(challenge["next_review"])

    def test_mastery_requires_independent_contexts_and_full_text(self):
        self.add_error_structure_and_challenge()
        results = []
        for index, context in enumerate(("a", "b", "c", "a", "b"), 1):
            results.append(
                {
                    "structure_id": "S001",
                    "context_id": context,
                    "context_type": "full_text" if index == 3 else "short_production",
                    "result": "correct",
                    "independent_use": True,
                }
            )
        apply_event(self.event("2026-01-02", structure_results=results), self.root)
        structure = read_yaml(self.root / "data/active_structures.yaml")["structures"][0]
        self.assertEqual(structure["status"], "mastered")
        self.assertEqual(structure["distinct_correct_contexts"], 3)

    def test_isolated_task_cannot_store_an_official_ai_score(self):
        with self.assertRaisesRegex(ValueError, "official_result"):
            apply_event(
                self.event(
                    "2026-01-02",
                    type="production",
                    submission_id="fictional-t1",
                    progress={
                        "task": "tache_1",
                        "estimated_task_level_min": "B1",
                        "estimated_task_level_max": "B2",
                        "official_final_score": "12",
                    },
                ),
                self.root,
            )

    def test_new_mock_creates_complete_evidence_package(self):
        destination = create_mock_exam("mock-001", date(2026, 1, 5), self.root)
        self.assertEqual(destination.name, "2026-01-05_mock-001")
        expected = {
            "README.md",
            "prompt.md",
            "sources/document-1.md",
            "sources/document-2.md",
            "tache-1-original.md",
            "tache-2-original.md",
            "tache-3-original.md",
            "correction.md",
            "priorities.md",
            "rewrite.md",
            "checkpoint-event.json",
        }
        actual = {
            str(path.relative_to(destination))
            for path in destination.rglob("*")
            if path.is_file()
        }
        self.assertEqual(actual, expected)
        readme = (destination / "README.md").read_text(encoding="utf-8")
        self.assertIn("2026-01-05", readme)
        self.assertIn("mock-001", readme)


if __name__ == "__main__":
    unittest.main()

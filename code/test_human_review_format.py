#!/usr/bin/env python3
"""Check human-sheet format with synthetic records in temporary directories only."""

import csv
from pathlib import Path
import tempfile
import unittest

from prepare_human_classification_review import (
    ValidationError, label_columns, read_human_sheet,
)


class HumanReviewFormatTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="synthetic-human-review-")
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "synthetic_review.csv"
        self.axes = {
            "domains": [{"code": code} for code in (
                "d_exercise", "d_body", "d_food", "d_life", "d_tools", "d_other",
            )],
            "functions": [{"code": code} for code in (
                "f_activity_update", "f_experience_report", "f_future_intention",
                "f_explanation", "f_practical_guidance", "f_reflection",
                "f_exhortation", "f_greeting_wish", "f_relational_bid",
                "f_reader_response_request", "f_appraisal", "f_caption",
                "f_gratitude", "f_sale_offer", "f_other_expression",
            )],
        }
        self.columns = label_columns(self.axes)
        self.blind = {"SYN001": "合成格式测试：早安。"}
        self.codebook_hash = "synthetic-codebook-hash"

    def row(self, observation="", domain_state="", label=""):
        record = {column: label for _, _, column in self.columns}
        record.update(
            sample_id="SYN001", fulltext=self.blind["SYN001"],
            observation_state=observation, domain_state=domain_state,
            codebook_sha256=self.codebook_hash,
        )
        return record

    def read(self, record):
        fields = ["sample_id", "fulltext", "observation_state", "domain_state"]
        fields += [column for _, _, column in self.columns] + ["codebook_sha256"]
        with self.path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerow(record)
        return read_human_sheet(self.path, self.blind, self.axes, self.codebook_hash)

    def test_blank_sheet_stays_pending(self):
        annotations, status = self.read(self.row())
        self.assertIsNone(annotations)
        self.assertEqual(status["status"], "pending")
        self.assertEqual(status["reason"], "all_annotation_cells_blank")
        self.assertEqual(status["filled_cells"], 0)
        self.assertEqual(status["missing_cells"]["blank_label_cells"], 21)

    def test_missing_state_or_label_stays_pending(self):
        records = [self.row(label="U"), self.row("insufficient", label="U")]
        partial = self.row("readable", "unspecified", "U")
        partial["function_f_greeting_wish"] = ""
        records.append(partial)
        for record in records:
            with self.subTest(record=record):
                annotations, status = self.read(record)
                self.assertIsNone(annotations)
                self.assertEqual(status["status"], "pending")
                self.assertEqual(status["reason"], "partially_filled")

    def test_readable_unspecified_keeps_unknown_domains_and_loads_behavior(self):
        record = self.row("readable", "unspecified", "0")
        for axis, _, column in self.columns:
            if axis == "domains":
                record[column] = "U"
        record["function_f_greeting_wish"] = "1"
        annotations, status = self.read(record)
        self.assertEqual(status["status"], "filled")
        self.assertEqual(annotations["SYN001"]["domains"], [])
        self.assertEqual(len(annotations["SYN001"]["uncertain_domains"]), 6)
        self.assertEqual(annotations["SYN001"]["functions"], ["f_greeting_wish"])

    def test_unknown_domains_cannot_be_filled_with_zeros(self):
        for domain_state, observation in (("unspecified", "readable"), ("unavailable", "")):
            with self.subTest(domain_state=domain_state):
                with self.assertRaisesRegex(ValidationError, "domain label must be U"):
                    self.read(self.row(observation, domain_state, "0"))

    def test_empty_and_insufficient_load_all_unknown_labels(self):
        for observation, text in (("empty", ""), ("insufficient", "合成片段：……")):
            with self.subTest(observation=observation):
                self.blind["SYN001"] = text
                annotations, status = self.read(self.row(observation, "unavailable", "U"))
                self.assertEqual(status["status"], "filled")
                self.assertEqual(len(annotations["SYN001"]["uncertain_domains"]), 6)
                self.assertEqual(len(annotations["SYN001"]["uncertain_functions"]), 15)
                self.assertEqual(annotations["SYN001"]["domains"], [])
                self.assertEqual(annotations["SYN001"]["functions"], [])

    def test_empty_and_insufficient_reject_known_labels_on_either_axis(self):
        for observation, text in (("empty", ""), ("insufficient", "合成片段：……")):
            self.blind["SYN001"] = text
            for column in ("domain_d_exercise", "function_f_activity_update"):
                for value in ("0", "1"):
                    with self.subTest(observation=observation, column=column, value=value):
                        record = self.row(observation, "unavailable", "U")
                        record[column] = value
                        with self.assertRaisesRegex(ValidationError, "label must be U"):
                            self.read(record)

    def test_state_mismatches_are_rejected(self):
        for observation, text in (("empty", ""), ("insufficient", "合成片段：……")):
            self.blind["SYN001"] = text
            for domain_state in ("specified", "unspecified", "uncertain"):
                with self.subTest(observation=observation, domain_state=domain_state):
                    with self.assertRaisesRegex(ValidationError, "requires unavailable domain_state"):
                        self.read(self.row(observation, domain_state, "U"))
        self.blind["SYN001"] = "合成格式测试：早安。"
        with self.assertRaisesRegex(ValidationError, "readable observation cannot have unavailable"):
            self.read(self.row("readable", "unavailable", "U"))

    def test_unfilled_cells_under_unknown_states_stay_pending(self):
        self.blind["SYN001"] = "合成片段：……"
        for domain_state in ("", "unavailable"):
            with self.subTest(domain_state=domain_state):
                record = self.row("insufficient", domain_state, "U")
                record["function_f_activity_update"] = ""
                annotations, status = self.read(record)
                self.assertIsNone(annotations)
                self.assertEqual(status["status"], "pending")
                self.assertEqual(status["missing_cells"]["blank_label_cells"], 1)

    def test_fulltext_and_codebook_hash_must_be_preserved(self):
        for field, changed, error in (
            ("fulltext", "另一条合成测试正文。", "fulltext changed"),
            ("codebook_sha256", "changed-synthetic-hash", "codebook hash mismatch"),
        ):
            with self.subTest(field=field):
                record = self.row("readable", "unspecified", "U")
                record[field] = changed
                with self.assertRaisesRegex(ValidationError, error):
                    self.read(record)

    def test_empty_state_must_still_match_source_text(self):
        with self.assertRaisesRegex(ValidationError, "empty-state/text mismatch"):
            self.read(self.row("empty", "unavailable", "U"))


if __name__ == "__main__":
    unittest.main()

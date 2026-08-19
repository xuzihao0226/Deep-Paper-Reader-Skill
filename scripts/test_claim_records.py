import json
import tempfile
import unittest
from pathlib import Path

from claim_records import apply_review, prepare_records, validate_records


class ClaimRecordTests(unittest.TestCase):
    def make_workspace(self, root: Path) -> Path:
        evidence = root / "evidence"
        evidence.mkdir(parents=True)
        pages = {
            "pages": [
                {
                    "pdf_page": 1,
                    "blocks": [
                        {"block_id": "P001-B001", "text": "1 Introduction", "heading_candidate": True},
                        {
                            "block_id": "P001-B002",
                            "text": "We argue that traceable evidence improves review reliability.",
                            "heading_candidate": False,
                        },
                        {"block_id": "P001-B003", "text": "The comparison is limited in scale.", "heading_candidate": False},
                    ],
                }
            ]
        }
        candidates = {
            "candidates": [
                {
                    "candidate_id": "CC001",
                    "source_locator": "P001-B002",
                    "pdf_page": 1,
                    "section_id": "S001",
                    "section_type": "introduction",
                    "text": "We argue that traceable evidence improves review reliability.",
                }
            ]
        }
        (evidence / "pages.json").write_text(json.dumps(pages), encoding="utf-8")
        (evidence / "claim_candidates.json").write_text(json.dumps(candidates), encoding="utf-8")
        return root

    def complete_first_claim(self, workspace: Path) -> None:
        path = workspace / "evidence" / "claims.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        claim = payload["claims"][0]
        claim.update(
            {
                "decision": "keep",
                "decision_reason": "Central paper claim.",
                "review_status": "reviewed",
                "authors_claim": "Traceable evidence improves review reliability.",
                "claim_category": "explicit_author_claim",
                "support_strength": "direct_but_limited",
                "largest_gap": "Small comparison set.",
                "verdict": "partially_supported",
                "safe_version": "Traceable evidence improved reliability in the reported comparison.",
                "wording_to_avoid": "Traceable evidence always eliminates unsupported interpretation.",
                "result_claim_boundary": "demonstrated",
                "review_notes": "Checked target and adjacent source blocks.",
            }
        )
        claim["evidence_records"][0].update(
            {
                "evidence_summary": "The paper reports a comparison with fewer unsupported interpretations.",
                "relevance": "Directly tests the reliability claim.",
                "limitation": "The comparison set is small.",
            }
        )
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_prepare_includes_source_context(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self.make_workspace(Path(temp_dir))
            result = prepare_records(workspace)
            self.assertEqual(result["claim_record_count"], 1)
            payload = json.loads((workspace / "evidence" / "claims.json").read_text(encoding="utf-8"))
            context = payload["claims"][0]["source_context"]
            self.assertEqual(context["target"]["block_id"], "P001-B002")
            self.assertEqual(context["before"]["block_id"], "P001-B001")
            self.assertEqual(context["after"]["block_id"], "P001-B003")

    def test_prepare_refuses_to_overwrite_review_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self.make_workspace(Path(temp_dir))
            prepare_records(workspace)
            with self.assertRaises(FileExistsError):
                prepare_records(workspace)

    def test_pending_record_fails_validation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self.make_workspace(Path(temp_dir))
            prepare_records(workspace)
            result = validate_records(workspace)
            self.assertFalse(result["passed"])
            self.assertTrue(any("pending" in error for error in result["errors"]))

    def test_completed_record_passes_validation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self.make_workspace(Path(temp_dir))
            prepare_records(workspace)
            self.complete_first_claim(workspace)
            result = validate_records(workspace)
            self.assertTrue(result["passed"])
            self.assertEqual(result["kept_claim_count"], 1)

    def test_invalid_source_locator_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self.make_workspace(Path(temp_dir))
            prepare_records(workspace)
            self.complete_first_claim(workspace)
            path = workspace / "evidence" / "claims.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["claims"][0]["source_locator"] = "P999-B999"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = validate_records(workspace)
            self.assertFalse(result["passed"])
            self.assertTrue(any("does not exist" in error for error in result["errors"]))

    def test_compact_review_overlay_keeps_selected_and_discards_unlisted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self.make_workspace(Path(temp_dir))
            candidates_path = workspace / "evidence" / "claim_candidates.json"
            candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
            candidates["candidates"].append(
                {
                    "candidate_id": "CC002",
                    "source_locator": "P001-B003",
                    "pdf_page": 1,
                    "section_id": "S001",
                    "section_type": "introduction",
                    "text": "The comparison is limited in scale.",
                }
            )
            candidates_path.write_text(json.dumps(candidates), encoding="utf-8")
            prepare_records(workspace)
            review = workspace / "review.json"
            review.write_text(
                json.dumps(
                    {
                        "discard_unlisted": True,
                        "discard_reason": "Not central after contextual review.",
                        "claims": [
                            {
                                "claim_id": "C1",
                                "decision": "keep",
                                "authors_claim": "Traceable evidence improves review reliability.",
                                "claim_category": "explicit_author_claim",
                                "evidence_records": [
                                    {
                                        "evidence_id": "E1",
                                        "source_locator": "P001-B002",
                                        "source_type": "pdf_text_block",
                                        "evidence_summary": "The authors state the traceability result.",
                                        "relevance": "Directly states the selected claim.",
                                        "limitation": "Synthetic test evidence only.",
                                    }
                                ],
                                "support_strength": "direct_but_limited",
                                "largest_gap": "No external replication.",
                                "verdict": "partially_supported",
                                "safe_version": "The test supports traceable review in this example.",
                                "wording_to_avoid": "The method always guarantees correctness.",
                                "result_claim_boundary": "demonstrated",
                                "review_notes": "Reviewed against the source block.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            result = apply_review(workspace, review)
            self.assertEqual(result["reviewed_claim_count"], 1)
            records = json.loads((workspace / "evidence" / "claims.json").read_text(encoding="utf-8"))["claims"]
            self.assertEqual(records[0]["decision"], "keep")
            self.assertEqual(records[1]["decision"], "discard")
            self.assertTrue(validate_records(workspace)["passed"])

    def test_review_overlay_can_add_missed_central_claim(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self.make_workspace(Path(temp_dir))
            prepare_records(workspace)
            review = workspace / "review-new.json"
            review.write_text(
                json.dumps(
                    {
                        "discard_unlisted": True,
                        "discard_reason": "Not central.",
                        "claims": [],
                        "new_claims": [
                            {
                                "claim_id": "C-manual-1",
                                "source_locator": "P001-B003",
                                "decision": "keep",
                                "decision_reason": "Central limitation missed by cue retrieval.",
                                "authors_claim": "The comparison is limited in scale.",
                                "claim_category": "explicit_author_claim",
                                "evidence_records": [
                                    {
                                        "evidence_id": "E-manual-1",
                                        "source_locator": "P001-B003",
                                        "source_type": "pdf_text_block",
                                        "evidence_summary": "The source directly states the scale limitation.",
                                        "relevance": "Defines the scope of the result.",
                                        "limitation": "Synthetic test evidence only."
                                    }
                                ],
                                "support_strength": "direct_and_decisive",
                                "largest_gap": "No broader evaluation.",
                                "verdict": "supported",
                                "safe_version": "The reported comparison is limited in scale.",
                                "wording_to_avoid": "The result generalizes broadly.",
                                "result_claim_boundary": "demonstrated",
                                "review_notes": "Manually added after checking the source context."
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            result = apply_review(workspace, review)
            self.assertEqual(result["new_claim_count"], 1)
            self.assertTrue(validate_records(workspace)["passed"])


if __name__ == "__main__":
    unittest.main()

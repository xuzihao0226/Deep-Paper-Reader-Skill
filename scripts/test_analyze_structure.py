import json
import tempfile
import unittest
from pathlib import Path

from analyze_structure import analyze_workspace, build_claim_candidates, build_sections, classify_section


class AnalyzeStructureTests(unittest.TestCase):
    def block(self, block_id, text, page=1, heading=False):
        return {
            "block_id": block_id,
            "text": text,
            "pdf_page": page,
            "heading_candidate": heading,
            "removed_as_repeated_margin": False,
        }

    def test_classifies_technical_and_humanities_sections(self):
        self.assertEqual(classify_section("2 Experimental Setup"), "experiment")
        self.assertEqual(classify_section("三、异议与回应"), "objection_response")
        self.assertEqual(classify_section("结论"), "conclusion")
        self.assertEqual(classify_section("Notes"), "references")

    def test_builds_sections_and_traceable_candidates(self):
        blocks = [
            self.block("P001-B001", "1 Introduction", heading=True),
            self.block("P001-B002", "We argue that traceable evidence improves review reliability."),
            self.block("P002-B001", "2 Results", page=2, heading=True),
            self.block("P002-B002", "The results show that the method reduces unsupported claims.", page=2),
            self.block("P003-B001", "3 Conclusion", page=3, heading=True),
            self.block("P003-B002", "Therefore, future reports should preserve source locations.", page=3),
        ]
        sections = build_sections(blocks)
        candidates = build_claim_candidates(blocks, sections, 20)
        self.assertEqual([section["section_type"] for section in sections], ["introduction", "results", "conclusion"])
        self.assertEqual(len(candidates), 3)
        self.assertEqual(candidates[0]["source_locator"], "P001-B002")
        self.assertIn("author_claim", candidates[0]["cue_categories"])
        self.assertIn("result", candidates[1]["cue_categories"])

    def test_chinese_philosophy_claim_cues(self):
        blocks = [
            self.block("P001-B001", "异议与回应", heading=True),
            self.block("P001-B002", "本文认为，道德判断应当考虑共同观点，因此私人偏爱不能直接构成公共标准。"),
        ]
        sections = build_sections(blocks)
        candidates = build_claim_candidates(blocks, sections, 10)
        self.assertEqual(sections[0]["section_type"], "objection_response")
        self.assertEqual(len(candidates), 1)
        self.assertIn("author_claim", candidates[0]["cue_categories"])
        self.assertIn("normative", candidates[0]["cue_categories"])
        self.assertIn("inference", candidates[0]["cue_categories"])

    def test_prioritizes_author_claims_and_skips_front_matter(self):
        blocks = [
            self.block("P001-B001", "Cover page"),
            self.block("P001-B002", "Users must retain this copyright notice."),
            self.block("P002-B001", "1. Main Argument", page=2, heading=True),
            self.block("P002-B002", "Therefore, this is a supporting inference.", page=2),
            self.block("P002-B003", "I argue that sympathy is a form of understanding.", page=2),
        ]
        sections = build_sections(blocks)
        candidates = build_claim_candidates(blocks, sections, 1)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["source_locator"], "P002-B003")
        self.assertIn("author_claim", candidates[0]["cue_categories"])
        self.assertGreaterEqual(candidates[0]["retrieval_score"], 5)

    def test_review_strategy_prioritizes_scope_and_skips_figure_descriptions(self):
        blocks = [
            self.block("P001-B001", "1 Overview", heading=True),
            self.block("P001-B002", "In this section, we discuss value-based and policy-based methods."),
            self.block("P001-B003", "In Figure 2, we show the final learning curves."),
        ]
        sections = build_sections(blocks)
        candidates = build_claim_candidates(blocks, sections, 10, review_like=True)
        self.assertEqual(len(candidates), 1)
        self.assertIn("scope", candidates[0]["cue_categories"])
        self.assertEqual(candidates[0]["source_locator"], "P001-B002")

    def test_workspace_outputs_reading_map(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            evidence = workspace / "evidence"
            evidence.mkdir()
            (workspace / "metadata.json").write_text(
                json.dumps({"extraction": {}, "reading": {}}, ensure_ascii=False), encoding="utf-8"
            )
            pages = {
                "schema_version": 1,
                "pages": [
                    {
                        "pdf_page": 1,
                        "blocks": [
                            self.block("P001-B001", "摘要", heading=True),
                            self.block("P001-B002", "研究结果表明，该方法能够支持证据定位。"),
                        ],
                    }
                ],
            }
            (evidence / "pages.json").write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
            summary = analyze_workspace(workspace)
            self.assertEqual(summary["section_count"], 1)
            self.assertEqual(summary["claim_candidate_count"], 1)
            reading_map = (evidence / "reading-map.md").read_text(encoding="utf-8")
            self.assertIn("P001-B002", reading_map)
            self.assertTrue((evidence / "sections.json").is_file())
            self.assertTrue((evidence / "claim_candidates.json").is_file())

    def test_missing_pages_file_has_clear_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "metadata.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(FileNotFoundError):
                analyze_workspace(workspace)


if __name__ == "__main__":
    unittest.main()

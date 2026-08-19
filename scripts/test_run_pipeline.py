import argparse
import json
import tempfile
import unittest
from pathlib import Path

import fitz

from run_pipeline import run_pipeline


class RunPipelineTests(unittest.TestCase):
    def create_pdf(self, path: Path) -> None:
        document = fitz.open()
        data = [
            ("1 Introduction", "We argue that traceable evidence improves academic review reliability. This paragraph explains the central motivation in enough detail for extraction."),
            ("2 Results", "The results show that block locators reduce unsupported interpretations. The comparison remains limited to a small test setting."),
            ("3 Conclusion", "Therefore, reading reports should preserve PDF pages and source identifiers. Broader evaluation is still needed before generalization."),
        ]
        for heading, body in data:
            page = document.new_page(width=595, height=842)
            page.insert_text((72, 90), heading, fontsize=18)
            page.insert_textbox(fitz.Rect(72, 130, 520, 300), body, fontsize=11)
        document.save(path)
        document.close()

    def args(self, **overrides):
        values = {
            "paper": None,
            "resume_workspace": None,
            "output_root": ".",
            "workspace_name": "pipeline-test",
            "title": "Pipeline Test",
            "authors": None,
            "year": None,
            "source_url": None,
            "mode": "deep_read",
            "paper_type": "unclassified",
            "access_level": "unknown",
            "language": "follow_user",
            "template": None,
            "force": False,
            "timeout": 5,
            "user_agent": "test-agent",
            "max_candidates": 20,
            "keep_repeated_margins": False,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_local_pdf_runs_to_claim_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pdf = root / "paper.pdf"
            self.create_pdf(pdf)
            result = run_pipeline(self.args(paper=str(pdf), output_root=str(root / "output")))
            workspace = Path(result["workspace"])
            self.assertEqual(result["status"], "ready_for_claim_review")
            for relative in (
                "evidence/fulltext.md",
                "evidence/reading-map.md",
                "evidence/claims.json",
                "evidence/images_manifest.json",
                "evidence/pipeline.json",
            ):
                self.assertTrue((workspace / relative).is_file(), relative)

    def test_title_only_stops_at_source_gate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_pipeline(
                self.args(paper="An Ambiguous Paper Title", output_root=temp_dir, workspace_name="title-test")
            )
            self.assertEqual(result["status"], "needs_source")
            self.assertTrue(any(stage["stage"] == "fetch_source" for stage in result["stages"]))

    def test_resume_preserves_existing_claim_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pdf = root / "paper.pdf"
            self.create_pdf(pdf)
            first = run_pipeline(self.args(paper=str(pdf), output_root=str(root / "output")))
            workspace = Path(first["workspace"])
            claims_path = workspace / "evidence" / "claims.json"
            payload = json.loads(claims_path.read_text(encoding="utf-8"))
            payload["manual_marker"] = "preserve-me"
            claims_path.write_text(json.dumps(payload), encoding="utf-8")

            resumed = run_pipeline(self.args(resume_workspace=str(workspace), workspace_name=None))
            preserved = json.loads(claims_path.read_text(encoding="utf-8"))
            self.assertEqual(resumed["status"], "ready_for_claim_review")
            self.assertEqual(preserved["manual_marker"], "preserve-me")
            self.assertTrue(
                any(stage["stage"] == "prepare_claim_review" and stage["status"] == "reused_existing" for stage in resumed["stages"])
            )


if __name__ == "__main__":
    unittest.main()

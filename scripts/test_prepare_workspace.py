import argparse
import json
import tempfile
import unittest
from pathlib import Path

from prepare_workspace import classify_input, prepare_workspace, safe_slug


class PrepareWorkspaceTests(unittest.TestCase):
    def make_args(self, paper: str, output_root: str, **overrides):
        values = {
            "paper": paper,
            "output_root": output_root,
            "workspace_name": None,
            "title": None,
            "authors": None,
            "year": None,
            "source_url": None,
            "mode": "deep_read",
            "paper_type": "unclassified",
            "access_level": "unknown",
            "language": "follow_user",
            "template": None,
            "force": False,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_classifies_arxiv_and_doi(self):
        self.assertEqual(classify_input("https://arxiv.org/abs/2501.12345")["input_type"], "arxiv")
        self.assertEqual(classify_input("https://doi.org/10.1000/example")["input_type"], "doi")

    def test_slug_is_cross_platform_safe(self):
        self.assertEqual(safe_slug('A Study: Hume / AI? "Alignment"', "seed"), "A-Study-Hume-AI-Alignment")
        self.assertEqual(safe_slug("休谟 情感主义", "seed"), "休谟-情感主义")

    def test_local_pdf_creates_workspace_and_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pdf = root / "source.pdf"
            pdf.write_bytes(b"%PDF-1.4\n% test fixture\n")
            result = prepare_workspace(
                self.make_args(str(pdf), str(root / "output"), title="Test Paper", authors="A; B", year="2026")
            )
            workspace = Path(result["workspace"])
            self.assertTrue((workspace / "source" / "paper.pdf").is_file())
            self.assertTrue((workspace / "report.md").is_file())
            report = (workspace / "report.md").read_text(encoding="utf-8")
            self.assertIn("Research Question, Thesis, and Field Position", report)
            self.assertIn("Claim safety and wording boundary", report)
            metadata = json.loads((workspace / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["paper"]["authors"], ["A", "B"])
            self.assertEqual(metadata["paper"]["input_type"], "local_pdf")

    def test_refuses_to_overwrite_report_without_force(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            args = self.make_args("Example Paper", temp_dir, title="Example Paper")
            prepare_workspace(args)
            with self.assertRaises(FileExistsError):
                prepare_workspace(args)


if __name__ == "__main__":
    unittest.main()

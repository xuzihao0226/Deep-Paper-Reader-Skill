import argparse
import json
import tempfile
import unittest
from pathlib import Path

import fitz

from extract_text import classify_page_status, identify_repeated_margins, is_heading_candidate, extract_workspace
from prepare_workspace import prepare_workspace


class ExtractTextTests(unittest.TestCase):
    def test_alternating_headers_and_numbered_footnotes_are_not_sections(self):
        pages = []
        for index in range(6):
            header = f"{136 + index * 2} Henrik Bohlin" if index % 2 == 0 else "Sympathy and Hermeneutics"
            pages.append(
                {
                    "height": 792,
                    "blocks": [
                        {"text": header, "bbox": [48, 30, 200, 45]},
                        {"text": "Body text", "bbox": [48, 100, 500, 200]},
                    ],
                }
            )
        repeated = identify_repeated_margins(pages)
        self.assertIn("# henrik bohlin", repeated)
        self.assertIn("sympathy and hermeneutics", repeated)

        footnote = {
            "text": "3 For an interesting discussion, see the cited article.",
            "font_size_max": 8.5,
            "bold_ratio": 0.0,
        }
        heading = {
            "text": "3. Sympathy as empathetic understanding",
            "font_size_max": 10.0,
            "bold_ratio": 0.0,
        }
        self.assertFalse(is_heading_candidate(footnote, 9.0))
        self.assertTrue(is_heading_candidate(heading, 9.0))
        url = {"text": "https://example.org/paper", "font_size_max": 14.0, "bold_ratio": 0.0}
        self.assertFalse(is_heading_candidate(url, 9.0))

        pseudocode = {"text": "2 repeat", "font_size_max": 9.0, "bold_ratio": 1.0}
        formula = {"text": "v = r + γTv", "font_size_max": 12.0, "bold_ratio": 1.0}
        self.assertFalse(is_heading_candidate(pseudocode, 9.0))
        self.assertFalse(is_heading_candidate(formula, 9.0))

    def test_page_number_only_is_blank_not_failed_extraction(self):
        blocks = [{"text": "120"}]
        self.assertEqual(classify_page_status(blocks, image_count=0), ("blank_or_divider", 3))
        self.assertEqual(classify_page_status(blocks, image_count=1), ("low_text", 3))

    def prepare_workspace_with_pdf(self, root: Path, pdf: Path) -> Path:
        args = argparse.Namespace(
            paper=str(pdf),
            output_root=str(root),
            workspace_name="test-paper",
            title="Test Paper",
            authors=None,
            year=None,
            source_url=None,
            mode="deep_read",
            paper_type="unclassified",
            access_level="unknown",
            language="follow_user",
            template=None,
            force=False,
        )
        return Path(prepare_workspace(args)["workspace"])

    def create_text_pdf(self, path: Path) -> None:
        document = fitz.open()
        for number, heading in enumerate(["1 Introduction", "2 Method"], start=1):
            page = document.new_page(width=595, height=842)
            page.insert_text((72, 32), "REPEATED JOURNAL HEADER", fontsize=8)
            page.insert_text((72, 100), heading, fontsize=18)
            page.insert_text(
                (72, 145),
                f"This is the main paragraph on page {number}. It contains enough text for reliable extraction and evidence tracing.",
                fontsize=11,
            )
            page.insert_text((290, 820), str(number), fontsize=8)
        document.save(path)
        document.close()

    def test_extracts_page_blocks_and_heading_hints(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pdf = root / "paper.pdf"
            self.create_text_pdf(pdf)
            workspace = self.prepare_workspace_with_pdf(root / "output", pdf)
            summary = extract_workspace(workspace)

            self.assertEqual(summary["status"], "text_ready")
            self.assertEqual(summary["page_count"], 2)
            markdown = (workspace / "evidence" / "fulltext.md").read_text(encoding="utf-8")
            self.assertIn("P001-B", markdown)
            self.assertIn("### 1 Introduction", markdown)
            self.assertNotIn("REPEATED JOURNAL HEADER", markdown)

            payload = json.loads((workspace / "evidence" / "pages.json").read_text(encoding="utf-8"))
            self.assertEqual(len(payload["pages"]), 2)
            metadata = json.loads((workspace / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["extraction"]["status"], "text_ready")

    def test_can_keep_repeated_margins(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pdf = root / "paper.pdf"
            self.create_text_pdf(pdf)
            workspace = self.prepare_workspace_with_pdf(root / "output", pdf)
            extract_workspace(workspace, keep_repeated_margins=True)
            markdown = (workspace / "evidence" / "fulltext.md").read_text(encoding="utf-8")
            self.assertIn("REPEATED JOURNAL HEADER", markdown)

    def test_image_only_page_is_ocr_candidate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_image_pdf = fitz.open()
            source_page = source_image_pdf.new_page(width=200, height=200)
            source_page.draw_rect(fitz.Rect(20, 20, 180, 180), fill=(0.8, 0.8, 0.8))
            pixmap = source_page.get_pixmap()
            image_bytes = pixmap.tobytes("png")
            source_image_pdf.close()

            pdf = root / "scan.pdf"
            document = fitz.open()
            page = document.new_page(width=200, height=200)
            page.insert_image(page.rect, stream=image_bytes)
            document.save(pdf)
            document.close()

            workspace = self.prepare_workspace_with_pdf(root / "output", pdf)
            summary = extract_workspace(workspace)
            self.assertEqual(summary["status"], "needs_ocr")
            self.assertEqual(summary["ocr_candidate_pages"], [1])
            self.assertEqual(summary["access_level"], "partial_text")

    def test_missing_pdf_raises_clear_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "metadata.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(FileNotFoundError):
                extract_workspace(workspace)


if __name__ == "__main__":
    unittest.main()

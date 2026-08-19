import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fetch_source import FetchResponse, parse_landing_page, run_acquisition
from prepare_workspace import prepare_workspace


class FetchSourceTests(unittest.TestCase):
    def prepare(self, root: Path, paper: str, title: str = "Test Paper") -> Path:
        args = argparse.Namespace(
            paper=paper,
            output_root=str(root),
            workspace_name=None,
            title=title,
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

    def test_local_pdf_is_verified_as_full_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pdf = root / "paper.pdf"
            pdf.write_bytes(b"%PDF-1.4\nfixture")
            workspace = self.prepare(root / "output", str(pdf))
            result = run_acquisition(workspace, 5, "test-agent")
            self.assertEqual(result["status"], "full_text_ready")
            metadata = json.loads((workspace / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["reading"]["access_level"], "full_text")

    def test_direct_pdf_download_rejects_html_disguised_as_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self.prepare(Path(temp_dir), "https://example.org/paper.pdf")
            fake = FetchResponse("https://example.org/paper.pdf", 200, "text/html", b"<html>paywall</html>")
            with patch("fetch_source.http_get", return_value=fake):
                result = run_acquisition(workspace, 5, "test-agent")
            self.assertEqual(result["status"], "failed")
            self.assertFalse((workspace / "source" / "paper.pdf").exists())

    def test_landing_page_metadata_and_relative_pdf(self):
        html = b'''<html><head>
        <meta name="citation_title" content="A Useful Paper">
        <meta name="citation_author" content="Ada Example">
        <meta name="citation_pdf_url" content="/files/paper.pdf">
        <meta name="description" content="An abstract.">
        </head></html>'''
        parsed = parse_landing_page(html, "https://example.org/article/1")
        self.assertEqual(parsed["title"], "A Useful Paper")
        self.assertEqual(parsed["authors"], ["Ada Example"])
        self.assertEqual(parsed["pdf_url"], "https://example.org/files/paper.pdf")

    def test_web_page_downloads_citation_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self.prepare(Path(temp_dir), "https://example.org/article")
            html = FetchResponse(
                "https://example.org/article",
                200,
                "text/html",
                b'<meta name="citation_title" content="Resolved Title"><meta name="citation_pdf_url" content="/paper.pdf">',
            )
            pdf = FetchResponse("https://example.org/paper.pdf", 200, "application/pdf", b"%PDF-1.7\nfixture")
            with patch("fetch_source.http_get", side_effect=[html, pdf]):
                result = run_acquisition(workspace, 5, "test-agent")
            self.assertEqual(result["status"], "full_text_ready")
            metadata = json.loads((workspace / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["paper"]["title"], "Resolved Title")

    def test_title_only_requires_identity_search(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = self.prepare(Path(temp_dir), "An Ambiguous Paper Title")
            result = run_acquisition(workspace, 5, "test-agent")
            self.assertEqual(result["status"], "needs_authoritative_search")
            self.assertEqual(result["access_level"], "unknown")


if __name__ == "__main__":
    unittest.main()

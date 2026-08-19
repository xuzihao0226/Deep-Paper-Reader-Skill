import json
import tempfile
import unittest
from pathlib import Path

from validate_report import collect_math_issues, validate_report, validate_workspace


VALID_REPORT = """# Test Paper — Reading Report

## 1. Three-Minute Understanding

The paper asks whether stable evidence locations can improve academic review. It proposes page-and-block locators, reports that they reduce unsupported interpretation, and concludes that traceable reports are more auditable. The decisive support is a comparison reported on PDF page 4 at P004-B003, while the main limitation is that the test setting is small.

## 2. Paper Identity and Access Boundary

Full text was read from the supplied PDF. The available version and extraction limits are stated here.

## 3. Research Question, Thesis, and Field Position

The central question concerns traceable evidence in paper reading.

## 4. Essential Concepts and Terms

Stable locator means a repeatable page-and-block source address.

## 5. Method, Theory, or Argument Structure

The method extracts pages, assigns block identifiers, and verifies each report claim.

## 6. Central Claims and Evidence

| Claim ID | Authors' claim | Category | Source location | Evidence | Support | Largest gap | Verdict |
|---|---|---|---|---|---|---|---|
| C1 | Stable locators improve auditability. | explicit_author_claim | PDF page 4, P004-B003 | Controlled comparison | direct_but_limited | Small setting | partially_supported |

## 7. Key Figures, Tables, Formulas, or Passages

No figure is necessary for the judgment.

## 8. Contributions and Genuine Novelty

The contribution is a traceable reading workflow.

## 9. Limitations, Objections, and Open Questions

The evaluation covers only a small document set.

## 10. Final Judgment and Next Actions

The approach is useful, but broader validation is needed.

## 11. Evidence Index

| Evidence ID | Supports claim | Source type | Exact location | Notes |
|---|---|---|---|---|
| E1 | C1 | PDF text | PDF page 4, P004-B003 | Main comparison |

## Report Boundary

Author claims and report inferences are separated. Remaining uncertainty concerns external validity.
"""


class ValidateReportTests(unittest.TestCase):
    def test_valid_cross_disciplinary_report_passes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            errors, warnings, metrics = validate_report(
                VALID_REPORT, Path(temp_dir), {"reading": {"access_level": "full_text"}}, final=True
            )
            self.assertEqual(errors, [])
            self.assertEqual(metrics["claim_count"], 1)
            self.assertGreater(metrics["source_locator_count"], 0)

    def test_placeholder_and_missing_section_fail(self):
        report = VALID_REPORT.replace("## 8. Contributions and Genuine Novelty", "## 8. Notes") + "\n{{unfinished}}\n"
        with tempfile.TemporaryDirectory() as temp_dir:
            errors, _, _ = validate_report(report, Path(temp_dir), final=True)
            self.assertTrue(any("Missing required" in error for error in errors))
            self.assertTrue(any("placeholders" in error for error in errors))

    def test_claim_requires_source_locator(self):
        report = VALID_REPORT.replace("PDF page 4, P004-B003", "the results section")
        with tempfile.TemporaryDirectory() as temp_dir:
            errors, _, _ = validate_report(report, Path(temp_dir), final=True)
            self.assertTrue(any("C1" in error and "locator" in error for error in errors))

    def test_broken_local_image_fails(self):
        report = VALID_REPORT.replace("No figure is necessary for the judgment.", "![Result](images/missing.png)")
        with tempfile.TemporaryDirectory() as temp_dir:
            errors, _, metrics = validate_report(report, Path(temp_dir), final=True)
            self.assertEqual(metrics["broken_image_count"], 1)
            self.assertTrue(any("Broken local image" in error for error in errors))

    def test_duplicate_long_paragraph_fails(self):
        paragraph = "This duplicated paragraph is deliberately long enough to trigger the inherited duplicate detection rule. " * 3
        report = VALID_REPORT + f"\n{paragraph}\n\n{paragraph}\n"
        with tempfile.TemporaryDirectory() as temp_dir:
            errors, _, _ = validate_report(report, Path(temp_dir), final=True)
            self.assertTrue(any("duplicated paragraphs" in error for error in errors))

    def test_inherited_math_compatibility_check(self):
        issues = collect_math_issues("$$x = 1 \\tag{1}$$")
        self.assertTrue(any("tag" in issue for issue in issues))

    def test_abstract_only_requires_disclosure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            errors, _, _ = validate_report(
                VALID_REPORT, Path(temp_dir), {"reading": {"access_level": "abstract_only"}}, final=True
            )
            self.assertTrue(any("abstract_only" in error for error in errors))

    def test_workspace_writes_validation_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "report.md").write_text(VALID_REPORT, encoding="utf-8")
            (workspace / "metadata.json").write_text(
                json.dumps({"reading": {"access_level": "full_text"}}), encoding="utf-8"
            )
            result = validate_workspace(workspace, final=True)
            self.assertTrue(result["passed"])
            self.assertTrue((workspace / "evidence" / "validation.json").is_file())


if __name__ == "__main__":
    unittest.main()

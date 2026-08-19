#!/usr/bin/env python3
"""Resolve metadata and acquire an accessible source for one paper workspace."""

from __future__ import annotations

import argparse
import json
import sys
import tarfile
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen
from xml.etree import ElementTree


DEFAULT_USER_AGENT = "Deep-Paper-Reader-Skill/0.1 (+https://github.com/xuzihao0226/Deep-Paper-Reader-Skill)"
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024


@dataclass
class FetchResponse:
    url: str
    status: int
    content_type: str
    body: bytes


class CitationMetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, list[str]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "meta":
            return
        values = {key.lower(): value for key, value in attrs if value is not None}
        key = (values.get("name") or values.get("property") or "").lower()
        content = values.get("content")
        if key and content:
            self.meta.setdefault(key, []).append(unescape(content).strip())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def http_get(url: str, timeout: int, user_agent: str, accept: str = "*/*") -> FetchResponse:
    request = Request(url, headers={"User-Agent": user_agent, "Accept": accept})
    with urlopen(request, timeout=timeout) as response:
        length = response.headers.get("Content-Length")
        if length and int(length) > MAX_DOWNLOAD_BYTES:
            raise ValueError(f"Source exceeds {MAX_DOWNLOAD_BYTES} bytes: {url}")
        body = response.read(MAX_DOWNLOAD_BYTES + 1)
        if len(body) > MAX_DOWNLOAD_BYTES:
            raise ValueError(f"Source exceeds {MAX_DOWNLOAD_BYTES} bytes: {url}")
        return FetchResponse(
            url=response.geturl(),
            status=getattr(response, "status", 200),
            content_type=response.headers.get_content_type(),
            body=body,
        )


def is_pdf(response: FetchResponse) -> bool:
    return response.body.lstrip().startswith(b"%PDF-")


def save_pdf_response(response: FetchResponse, target: Path) -> str:
    if not is_pdf(response):
        raise ValueError(
            f"Expected a PDF but received {response.content_type or 'unknown content type'} from {response.url}"
        )
    target.write_bytes(response.body)
    return str(target)


def first(meta: dict[str, list[str]], key: str) -> str | None:
    values = meta.get(key.lower(), [])
    return values[0] if values else None


def parse_landing_page(body: bytes, base_url: str) -> dict[str, Any]:
    parser = CitationMetaParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    meta = parser.meta
    pdf_url = first(meta, "citation_pdf_url") or first(meta, "eprints.document_url")
    return {
        "title": first(meta, "citation_title") or first(meta, "dc.title") or first(meta, "og:title"),
        "authors": meta.get("citation_author", []),
        "year": first(meta, "citation_publication_date") or first(meta, "citation_date"),
        "doi": first(meta, "citation_doi") or first(meta, "dc.identifier"),
        "abstract": first(meta, "citation_abstract") or first(meta, "dc.description") or first(meta, "description"),
        "pdf_url": urljoin(base_url, pdf_url) if pdf_url else None,
    }


def apply_metadata(metadata: dict[str, Any], resolved: dict[str, Any]) -> None:
    paper = metadata["paper"]
    if resolved.get("title"):
        paper["title"] = resolved["title"]
    if resolved.get("authors"):
        paper["authors"] = resolved["authors"]
    if resolved.get("year"):
        paper["year"] = str(resolved["year"])[:4]
    if resolved.get("doi"):
        paper["doi"] = resolved["doi"]
    if resolved.get("abstract"):
        paper["abstract"] = resolved["abstract"]


def acquire_local_pdf(workspace: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    target = workspace / "source" / "paper.pdf"
    if not target.is_file() or not target.read_bytes()[:1024].lstrip().startswith(b"%PDF-"):
        raise ValueError(f"Local source is missing or is not a readable PDF: {target}")
    return {"status": "full_text_ready", "pdf_path": "source/paper.pdf", "final_url": None}


def acquire_direct_pdf(
    workspace: Path, metadata: dict[str, Any], timeout: int, user_agent: str
) -> dict[str, Any]:
    url = str(metadata["paper"]["normalized_input"])
    response = http_get(url, timeout, user_agent, "application/pdf")
    save_pdf_response(response, workspace / "source" / "paper.pdf")
    return {"status": "full_text_ready", "pdf_path": "source/paper.pdf", "final_url": response.url}


def acquire_arxiv(workspace: Path, metadata: dict[str, Any], timeout: int, user_agent: str) -> dict[str, Any]:
    arxiv_id = str(metadata["paper"]["identifier"])
    api_url = f"https://export.arxiv.org/api/query?id_list={quote(arxiv_id)}"
    api_response = http_get(api_url, timeout, user_agent, "application/atom+xml")
    (workspace / "source" / "arxiv-atom.xml").write_bytes(api_response.body)

    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    root = ElementTree.fromstring(api_response.body)
    entry = root.find("atom:entry", namespace)
    if entry is None:
        raise ValueError(f"arXiv returned no record for {arxiv_id}")
    resolved = {
        "title": " ".join((entry.findtext("atom:title", default="", namespaces=namespace)).split()),
        "authors": [
            " ".join(name.text.split())
            for name in entry.findall("atom:author/atom:name", namespace)
            if name.text
        ],
        "year": (entry.findtext("atom:published", default="", namespaces=namespace))[:4],
        "abstract": " ".join((entry.findtext("atom:summary", default="", namespaces=namespace)).split()),
    }
    apply_metadata(metadata, resolved)

    pdf_url = f"https://arxiv.org/pdf/{quote(arxiv_id)}.pdf"
    pdf_response = http_get(pdf_url, timeout, user_agent, "application/pdf")
    save_pdf_response(pdf_response, workspace / "source" / "paper.pdf")
    metadata["paper"]["arxiv_id"] = arxiv_id

    source_bundle = None
    source_errors = []
    source_url = f"https://arxiv.org/src/{quote(arxiv_id)}"
    try:
        source_response = http_get(source_url, timeout, user_agent, "application/x-eprint-tar,application/gzip")
        source_path = workspace / "source" / "arxiv-source.tar"
        source_path.write_bytes(source_response.body)
        if not tarfile.is_tarfile(source_path):
            source_path.unlink()
            raise ValueError(f"arXiv source response is not a readable tar archive: {source_response.url}")
        source_bundle = "source/arxiv-source.tar"
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        source_errors.append(str(exc))

    return {
        "status": "full_text_ready",
        "pdf_path": "source/paper.pdf",
        "source_record": "source/arxiv-atom.xml",
        "final_url": pdf_response.url,
        "source_bundle": source_bundle,
        "errors": source_errors,
    }


def crossref_to_resolved(message: dict[str, Any]) -> dict[str, Any]:
    authors = []
    for author in message.get("author", []):
        name = " ".join(part for part in [author.get("given"), author.get("family")] if part)
        if name:
            authors.append(name)
    date_parts = message.get("published-print", message.get("published-online", {})).get("date-parts", [])
    year = str(date_parts[0][0]) if date_parts and date_parts[0] else None
    titles = message.get("title", [])
    return {
        "title": titles[0] if titles else None,
        "authors": authors,
        "year": year,
        "doi": message.get("DOI"),
        "abstract": message.get("abstract"),
    }


def acquire_doi(workspace: Path, metadata: dict[str, Any], timeout: int, user_agent: str) -> dict[str, Any]:
    doi = str(metadata["paper"]["identifier"])
    crossref_url = f"https://api.crossref.org/works/{quote(doi, safe='')}"
    response = http_get(crossref_url, timeout, user_agent, "application/json")
    payload = json.loads(response.body.decode("utf-8"))
    (workspace / "source" / "crossref.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    message = payload.get("message", {})
    apply_metadata(metadata, crossref_to_resolved(message))

    candidates = []
    for link in message.get("link", []):
        url = link.get("URL")
        content_type = str(link.get("content-type", "")).lower()
        if url and ("pdf" in content_type or str(url).lower().split("?", 1)[0].endswith(".pdf")):
            candidates.append(url)

    errors = []
    for candidate in candidates:
        try:
            pdf_response = http_get(candidate, timeout, user_agent, "application/pdf")
            save_pdf_response(pdf_response, workspace / "source" / "paper.pdf")
            return {
                "status": "full_text_ready",
                "pdf_path": "source/paper.pdf",
                "source_record": "source/crossref.json",
                "final_url": pdf_response.url,
                "candidate_urls": candidates,
                "errors": errors,
            }
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            errors.append(f"{candidate}: {exc}")

    return {
        "status": "abstract_only" if metadata["paper"].get("abstract") else "metadata_only",
        "pdf_path": None,
        "source_record": "source/crossref.json",
        "final_url": message.get("URL") or f"https://doi.org/{doi}",
        "candidate_urls": candidates,
        "errors": errors,
    }


def acquire_web_page(
    workspace: Path, metadata: dict[str, Any], timeout: int, user_agent: str
) -> dict[str, Any]:
    url = str(metadata["paper"]["normalized_input"])
    response = http_get(url, timeout, user_agent, "text/html,application/xhtml+xml")
    (workspace / "source" / "landing-page.html").write_bytes(response.body)
    resolved = parse_landing_page(response.body, response.url)
    apply_metadata(metadata, resolved)
    pdf_url = resolved.get("pdf_url")
    errors = []
    if pdf_url:
        try:
            pdf_response = http_get(pdf_url, timeout, user_agent, "application/pdf")
            save_pdf_response(pdf_response, workspace / "source" / "paper.pdf")
            return {
                "status": "full_text_ready",
                "pdf_path": "source/paper.pdf",
                "source_record": "source/landing-page.html",
                "final_url": pdf_response.url,
                "candidate_urls": [pdf_url],
                "errors": errors,
            }
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            errors.append(f"{pdf_url}: {exc}")
    return {
        "status": "abstract_only" if resolved.get("abstract") else "metadata_only",
        "pdf_path": None,
        "source_record": "source/landing-page.html",
        "final_url": response.url,
        "candidate_urls": [pdf_url] if pdf_url else [],
        "errors": errors,
    }


def run_acquisition(workspace: Path, timeout: int, user_agent: str) -> dict[str, Any]:
    metadata_path = workspace / "metadata.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"metadata.json not found in workspace: {workspace}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    input_type = metadata["paper"]["input_type"]
    (workspace / "source").mkdir(parents=True, exist_ok=True)

    try:
        if input_type == "local_pdf":
            result = acquire_local_pdf(workspace, metadata)
        elif input_type == "direct_pdf_url":
            result = acquire_direct_pdf(workspace, metadata, timeout, user_agent)
        elif input_type == "arxiv":
            result = acquire_arxiv(workspace, metadata, timeout, user_agent)
        elif input_type == "doi":
            result = acquire_doi(workspace, metadata, timeout, user_agent)
        elif input_type == "web_page":
            result = acquire_web_page(workspace, metadata, timeout, user_agent)
        elif input_type == "paper_title":
            result = {
                "status": "needs_authoritative_search",
                "pdf_path": None,
                "final_url": None,
                "errors": ["A title-only input requires authoritative search and identity confirmation."],
            }
        else:
            raise ValueError(f"Unsupported input type: {input_type}")
    except (HTTPError, URLError, TimeoutError, ValueError, OSError, ElementTree.ParseError, json.JSONDecodeError) as exc:
        result = {"status": "failed", "pdf_path": None, "final_url": None, "errors": [str(exc)]}

    result["attempted_at"] = utc_now()
    result["input_type"] = input_type
    metadata["acquisition"] = result
    metadata["paper"]["source_url"] = result.get("final_url") or metadata["paper"].get("source_url")

    if result["status"] == "full_text_ready":
        metadata["reading"]["access_level"] = "full_text"
        metadata["extraction"]["status"] = "source_ready"
        metadata["extraction"]["source_copy"] = result.get("pdf_path")
    elif result["status"] == "abstract_only":
        metadata["reading"]["access_level"] = "abstract_only"
        metadata["extraction"]["status"] = "metadata_ready"
    else:
        metadata["reading"]["access_level"] = "unknown"
        metadata["extraction"]["status"] = "blocked"
    metadata["extraction"]["limitations"] = result.get("errors", [])
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "workspace": str(workspace),
        "status": result["status"],
        "access_level": metadata["reading"]["access_level"],
        "pdf_path": result.get("pdf_path"),
        "errors": result.get("errors", []),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, help="Paper workspace created by prepare_workspace.py")
    parser.add_argument("--timeout", type=int, default=30, help="Network timeout in seconds")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_acquisition(Path(args.workspace).expanduser().resolve(), args.timeout, args.user_agent)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] != "failed" else 2


if __name__ == "__main__":
    raise SystemExit(main())

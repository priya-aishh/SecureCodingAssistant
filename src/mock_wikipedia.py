"""Strict local fixture store for the mock Wikipedia MCP server."""

import json
from pathlib import Path
from urllib.parse import urlsplit


def wikipedia_article_url(url: str) -> bool:
    """Accept article URLs only; never use a supplied URL for a network request."""
    if not isinstance(url, str):
        return False
    try:
        parsed = urlsplit(url)
        return (parsed.scheme == "https" and parsed.hostname == "en.wikipedia.org"
                and parsed.port is None and not parsed.username and not parsed.password
                and parsed.path.startswith("/wiki/") and not parsed.query and not parsed.fragment)
    except ValueError:
        return False


class MockWikipedia:
    """Read only explicitly listed UTF-8 pages beneath a fixture directory."""

    def __init__(self, directory: Path):
        self.directory = directory.resolve(strict=True)
        manifest_path = (self.directory / "manifest.json").resolve(strict=True)
        if not manifest_path.is_relative_to(self.directory) or not manifest_path.is_file():
            raise ValueError("Mock Wikipedia manifest must be inside the fixture directory")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or not manifest:
            raise ValueError("Mock Wikipedia manifest must map article URLs to page files")
        self.pages: dict[str, Path] = {}
        for url, filename in manifest.items():
            if not wikipedia_article_url(url) or not isinstance(filename, str):
                raise ValueError(f"Invalid mock Wikipedia entry: {url!r}")
            path = (self.directory / filename).resolve(strict=True)
            if not path.is_relative_to(self.directory) or not path.is_file() or path.suffix != ".md":
                raise ValueError(f"Mock page must be a Markdown file inside {self.directory}: {filename}")
            if path.stat().st_size > 64_000:
                raise ValueError(f"Mock page is too large: {filename}")
            self.pages[url] = path

    def search(self, query: str) -> list[dict[str, str]]:
        if not isinstance(query, str) or not 1 <= len(query.strip()) <= 200:
            raise ValueError("Search query must contain 1 to 200 characters")
        terms = query.casefold().split()
        matches = []
        for url, path in self.pages.items():
            content = path.read_text(encoding="utf-8")
            if all(term in (url + " " + content).casefold() for term in terms):
                matches.append({"url": url, "title": content.splitlines()[0].lstrip("# ")})
        return matches[:20]

    def read(self, url: str) -> dict[str, str]:
        if not wikipedia_article_url(url) or url not in self.pages:
            raise ValueError("Article is not in the mock Wikipedia fixture set")
        return {"url": url, "content": self.pages[url].read_text(encoding="utf-8")}

#!/usr/bin/env python3
"""Index learning Markdown files in Meilisearch for the app-wide search box."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT_DIR / "docs"
MEILI_URL = os.getenv("MEILI_URL", "http://localhost:7700").rstrip("/")
MEILI_KEY = os.getenv("MEILI_MASTER_KEY", "")
INDEX_UID = "learning_documents"
LEARNING_DOC_IDS = {"03", "04", "05", "06", "07", "10-1", "10-2", "10-3", "11"}


def request(method: str, path: str, body: object | None = None) -> object:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if MEILI_KEY:
        headers["Authorization"] = f"Bearer {MEILI_KEY}"
    req = urllib.request.Request(f"{MEILI_URL}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw) if raw else {}


def clean_markdown(content: str) -> str:
    content = re.sub(r"```.*?```", " ", content, flags=re.DOTALL)
    content = re.sub(r"!?(\[[^\]]*\])\([^)]*\)", r"\1", content)
    content = re.sub(r"<[^>]+>", " ", content)
    content = re.sub(r"[#>*_`|]", " ", content)
    return re.sub(r"\s+", " ", content).strip()


def documents() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        if path.stem not in LEARNING_DOC_IDS:
            continue
        content = path.read_text(encoding="utf-8")
        title_match = re.search(r"^#\s+(.+)$", content, flags=re.MULTILINE)
        title = title_match.group(1).strip() if title_match else path.stem
        rows.append({"id": path.stem, "doc_id": path.stem, "title": title, "content": clean_markdown(content)})
    return rows


for attempt in range(30):
    try:
        request("GET", "/health")
        break
    except (urllib.error.URLError, urllib.error.HTTPError):
        if attempt == 29:
            raise
        time.sleep(2)

try:
    request("POST", "/indexes", {"uid": INDEX_UID, "primaryKey": "id"})
except urllib.error.HTTPError as exc:
    if exc.code != 409:
        raise

request("PATCH", f"/indexes/{INDEX_UID}/settings", {
    "searchableAttributes": ["title", "content"],
    "displayedAttributes": ["id", "doc_id", "title", "content"],
})
request("POST", f"/indexes/{INDEX_UID}/documents?primaryKey=id", documents())
print(f"Meilisearch 색인 완료: {len(documents())}개 문서")

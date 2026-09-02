#!/usr/bin/env bash
# docs/*.md 문서를 청크/벡터화하여 Qdrant 컬렉션에 업로드합니다.
# Ollama 임베딩 모델을 사용하므로, 질의 API와 동일한 모델로 색인해야 합니다.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCS_DIR="${DOCS_DIR:-$ROOT_DIR/docs}"
VECTORDB_PORT="${VECTORDB_PORT:-6333}"
QDRANT_URL="${QDRANT_URL:-http://localhost:${VECTORDB_PORT}}"
QDRANT_COLLECTION="${QDRANT_COLLECTION:-investment_docs}"
CHUNK_SIZE="${CHUNK_SIZE:-1200}"
CHUNK_OVERLAP="${CHUNK_OVERLAP:-200}"
BATCH_SIZE="${BATCH_SIZE:-64}"
RAG_EMBEDDING_URL="${RAG_EMBEDDING_URL:-http://localhost:11434/api/embed}"
RAG_EMBEDDING_MODEL="${RAG_EMBEDDING_MODEL:-embeddinggemma}"
RAG_EMBEDDING_PROVIDER="${RAG_EMBEDDING_PROVIDER:-ollama}"

usage() {
  cat <<EOF
Usage: $(basename "$0")

환경 변수:
  DOCS_DIR            Markdown 문서 폴더 (기본: ./docs)
  QDRANT_URL          Qdrant HTTP URL (기본: http://localhost:6333)
  QDRANT_COLLECTION   컬렉션 이름 (기본: investment_docs)
  CHUNK_SIZE          문서 청크 크기(문자 수, 기본: 1200)
  CHUNK_OVERLAP       청크 오버랩(문자 수, 기본: 200)
  BATCH_SIZE          업로드 배치 크기(기본: 64)
  RAG_EMBEDDING_URL   Ollama /api/embed 주소 (기본: http://localhost:11434/api/embed)
  RAG_EMBEDDING_MODEL 문서와 질의에 공통으로 쓸 Ollama 임베딩 모델 (기본: embeddinggemma)
  RAG_EMBEDDING_PROVIDER ollama(기본) 또는 hash. hash는 Ollama 없이 쓰는 호환 모드입니다.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

for cmd in curl python3; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[ERROR] $cmd 이(가) 설치되어 있지 않습니다."
    exit 1
  fi
done

if [[ ! -d "$DOCS_DIR" ]]; then
  echo "[ERROR] DOCS_DIR 폴더가 없습니다: $DOCS_DIR"
  exit 1
fi

echo "[STEP] Vector DB 연결/컬렉션 조회: $QDRANT_URL"
if ! curl -fsS "$QDRANT_URL/collections" >/dev/null; then
  echo "[ERROR] Qdrant 조회 실패: $QDRANT_URL/collections"
  exit 1
fi
echo "[OK] Vector DB 조회 성공"

python3 - \
  "$DOCS_DIR" "$QDRANT_URL" "$QDRANT_COLLECTION" \
  "$CHUNK_SIZE" "$CHUNK_OVERLAP" "$BATCH_SIZE" \
  "$RAG_EMBEDDING_URL" "$RAG_EMBEDDING_MODEL" "$RAG_EMBEDDING_PROVIDER" <<'PY'
import hashlib
import json
import math
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


class QdrantHTTPError(RuntimeError):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


def http_json(method: str, url: str, payload: dict | None = None) -> dict:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="ignore")
        raise QdrantHTTPError(exc.code, f"Qdrant API 오류({exc.code}): {method} {url} :: {err_body[:300]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Qdrant 연결 실패: {method} {url} :: {exc.reason}") from exc


def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    step = chunk_size - chunk_overlap
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start += step
    return chunks


_HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")


def split_by_heading(text: str) -> list[tuple[str, str]]:
    """마크다운을 (제목, 본문) 목록으로 나눈다. 첫 제목 이전 내용은 제목=''로 처리한다."""
    sections: list[tuple[str, list[str]]] = []
    current_heading = ""
    current_body: list[str] = []
    for line in text.split("\n"):
        match = _HEADING_RE.match(line)
        if match:
            if current_body or current_heading:
                sections.append((current_heading, current_body))
            current_heading = match.group(1)
            current_body = []
        else:
            current_body.append(line)
    sections.append((current_heading, current_body))
    return [(heading, "\n".join(body).strip()) for heading, body in sections]


def chunk_document(text: str, chunk_size: int, chunk_overlap: int) -> list[dict]:
    """제목 경계를 먼저 지키고, 긴 절만 슬라이딩 윈도우로 다시 나눈다.

    문서를 통째로 슬라이딩 윈도우로 자르면 서로 다른 절의 내용이 한 조각에
    섞여 출처를 부정확하게 표시할 수 있다. 제목 단위로 먼저 나누면 검색
    결과의 출처(어느 절인지)를 훨씬 정확하게 보여줄 수 있다.
    """
    pieces: list[dict] = []
    for heading, body in split_by_heading(text):
        if not body:
            continue
        for chunk in chunk_text(body, chunk_size, chunk_overlap):
            pieces.append({"section": heading, "text": chunk})
    return pieces


def ollama_embed(url: str, model: str, inputs: list[str]) -> list[list[float]]:
    payload = {"model": model, "input": inputs, "truncate": True}
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Ollama 임베딩 오류({exc.code}): {detail[:300]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama 임베딩 연결 실패: {url} :: {exc.reason}") from exc
    embeddings = result.get("embeddings", [])
    if len(embeddings) != len(inputs) or not embeddings or not embeddings[0]:
        raise RuntimeError("Ollama가 입력 수와 다른 빈 임베딩을 반환했습니다.")
    return [[float(value) for value in vector] for vector in embeddings]


def hash_embed(text: str, dim: int = 384) -> list[float]:
    vector = [0.0] * dim
    for token in re.findall(r"[0-9A-Za-z가-힣_]+", text.lower()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        vector[int.from_bytes(digest[:4], "big") % dim] += 1.0 if digest[4] & 1 == 0 else -1.0
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


# ── 인수 파싱 ─────────────────────────────────────────────────────────────────
docs_dir        = Path(sys.argv[1])
base_url        = sys.argv[2].rstrip("/")
collection      = sys.argv[3]
chunk_size      = int(sys.argv[4])
chunk_overlap   = int(sys.argv[5])
batch_size      = int(sys.argv[6])
embedding_url   = sys.argv[7]
embedding_model = sys.argv[8]
embedding_provider = sys.argv[9]

# ── 문서 청킹 ─────────────────────────────────────────────────────────────────
files = sorted(docs_dir.glob("*.md"))
if not files:
    raise SystemExit(f"[ERROR] markdown 파일이 없습니다: {docs_dir}")

records: list[dict] = []
for file_path in files:
    content = file_path.read_text(encoding="utf-8")
    pieces = chunk_document(content, chunk_size, chunk_overlap)
    for idx, piece in enumerate(pieces):
        records.append({"source_doc": file_path.name, "chunk_index": idx, "section": piece["section"], "text": piece["text"]})

if not records:
    raise SystemExit("[ERROR] 업로드할 문서 청크가 없습니다.")

print(f"[INFO] docs={len(files)}, chunks={len(records)}")

# ── 임베딩 ───────────────────────────────────────────────────────────────────
if embedding_provider == "ollama":
    print(f"[INFO] Ollama 임베딩 생성 중: model={embedding_model}")
    matrix: list[list[float]] = []
    for start in range(0, len(records), batch_size):
        batch = records[start:start + batch_size]
        matrix.extend(ollama_embed(embedding_url, embedding_model, [record["text"] for record in batch]))
        print(f"[INFO] embedded {min(start + batch_size, len(records))}/{len(records)}")
    embed_type = f"ollama/{embedding_model}"
elif embedding_provider == "hash":
    print("[INFO] 해시 임베딩 생성 중 (dim=384)...")
    matrix = [hash_embed(record["text"]) for record in records]
    embed_type = "hash/384"
else:
    raise SystemExit("[ERROR] RAG_EMBEDDING_PROVIDER는 ollama 또는 hash여야 합니다.")

dim = len(matrix[0])
print(f"[INFO] 임베딩 타입={embed_type}, dim={dim}")

# ── Qdrant 업로드 ─────────────────────────────────────────────────────────────
try:
    http_json("DELETE", f"{base_url}/collections/{collection}")
    print(f"[INFO] 기존 컬렉션 삭제: {collection}")
except QdrantHTTPError as exc:
    if exc.code != 404:
        raise

http_json(
    "PUT",
    f"{base_url}/collections/{collection}",
    {
        "vectors": {"size": dim, "distance": "Cosine"},
        "payload_schema": {},
    },
)

# 컬렉션 메타데이터에 임베딩 타입 기록 (벡터 검색에 사용할 타입 식별용)
try:
    http_json(
        "PUT",
        f"{base_url}/collections/{collection}/payload",
        {},
    )
except Exception:
    pass

for start in range(0, len(records), batch_size):
    end = min(len(records), start + batch_size)
    points = [
        {
            "id": i + 1,
            "vector": matrix[i],
            "payload": {**records[i], "embed_type": embed_type},
        }
        for i in range(start, end)
    ]
    http_json(
        "PUT",
        f"{base_url}/collections/{collection}/points?wait=true",
        {"points": points},
    )
    print(f"[INFO] upserted {end}/{len(records)}")

result = http_json("GET", f"{base_url}/collections/{collection}")
count = result.get("result", {}).get("points_count")
print(f"[OK] 업로드 완료: collection={collection}, embed_type={embed_type}, points_count={count}")
PY

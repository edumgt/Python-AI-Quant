#!/usr/bin/env bash
# 6개 공공 금융기관 사이트를 2단계 링크까지 수집해 DATA_ROOT에 텍스트로 저장합니다.
# 역할별 이미지: Scrapy(링크 탐색), Playwright(동적 시작 화면), Tesseract(이미지 OCR).
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_ROOT="${DATA_ROOT:-$REPO_ROOT/data/financial-sources}"
SCRAPY_IMAGE="${SCRAPY_IMAGE:-scrapinghub/scrapinghub-stack-scrapy:2.17}"
PLAYWRIGHT_IMAGE="${PLAYWRIGHT_IMAGE:-mcr.microsoft.com/playwright:v1.62.1-jammy}"
TESSERACT_IMAGE="${TESSERACT_IMAGE:-jitesoft/tesseract-ocr:latest}"
OCR_LANG="${OCR_LANG:-eng}"
MAX_FILES="${MAX_FILES:-20}"
RENDER_ROOTS="${RENDER_ROOTS:-1}"
RUN_OCR="${RUN_OCR:-1}"
RUN_SCRAPY="${RUN_SCRAPY:-1}"
DOCKER_NETWORK="${DOCKER_NETWORK:-bridge}"
SOURCE_NAMES="${SOURCE_NAMES:-}"

if [[ -z "$DATA_ROOT" || "$DATA_ROOT" == "/" ]]; then
  echo "DATA_ROOT must be a specific directory, not an empty path or /." >&2
  exit 2
fi

mkdir -p "$DATA_ROOT"
echo "Text output: $DATA_ROOT"
echo "Maximum scraped text files: $MAX_FILES"
echo "Docker network: $DOCKER_NETWORK"

docker image inspect "$SCRAPY_IMAGE" "$PLAYWRIGHT_IMAGE" "$TESSERACT_IMAGE" >/dev/null

if [[ "$RUN_SCRAPY" == "1" ]]; then
  echo "[1/3] Scrapy: public pages, same domain only, maximum two link depths"
  docker run --rm --network "$DOCKER_NETWORK" -v "$SCRIPT_DIR/financial_site_spider.py:/crawler/financial_site_spider.py:ro" -v "$DATA_ROOT:/data" "$SCRAPY_IMAGE" python3 /crawler/financial_site_spider.py --output /data --max-files "$MAX_FILES" --source-names "$SOURCE_NAMES"
else
  echo "[1/3] Scrapy: skipped (RUN_SCRAPY=$RUN_SCRAPY)"
fi

if [[ "$RENDER_ROOTS" == "1" ]]; then
  echo "[2/3] Playwright: rendered text for each institution's start page"
  docker run --rm \
    --network "$DOCKER_NETWORK" \
    -v "$SCRIPT_DIR/render_financial_roots.mjs:/crawler/render_financial_roots.mjs:ro" \
    -v "$DATA_ROOT:/data" \
    -e DATA_ROOT=/data \
    -e MAX_FILES="$MAX_FILES" \
    "$PLAYWRIGHT_IMAGE" \
    bash -lc 'npm install --no-save --prefix /crawler playwright@1.62.1 >/dev/null && node /crawler/render_financial_roots.mjs'
else
  echo "[2/3] Playwright: skipped (RENDER_ROOTS=$RENDER_ROOTS)"
fi

if [[ "$RUN_OCR" == "1" ]]; then
  echo "[3/3] Tesseract: OCR any PNG/JPG files already placed under DATA_ROOT (language: $OCR_LANG)"
  while IFS= read -r -d '' image_path; do
    relative_path="${image_path#"$DATA_ROOT"/}"
    output_base="${relative_path%.*}"
    mkdir -p "$DATA_ROOT/ocr/$(dirname "$output_base")"
    docker run --rm --entrypoint tesseract \
      --network "$DOCKER_NETWORK" \
      -v "$DATA_ROOT:/data" \
      "$TESSERACT_IMAGE" \
      "/data/$relative_path" "/data/ocr/$output_base" -l "$OCR_LANG" || true
  done < <(find "$DATA_ROOT" -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' \) -print0)
else
  echo "[3/3] Tesseract: skipped (RUN_OCR=$RUN_OCR)"
fi

echo "Finished. Text files are under: $DATA_ROOT"

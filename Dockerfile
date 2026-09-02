FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      bash \
      curl \
      fonts-nanum \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    grep -v '^torch$' requirements.txt > requirements.nogpu.txt \
    && pip install --index-url https://download.pytorch.org/whl/cpu torch \
    && pip install -r requirements.nogpu.txt

COPY app/ ./app/
RUN mkdir -p app/frontend/vendor \
    && python -c "import pathlib, urllib.request; pathlib.Path('app/frontend/vendor/mermaid.min.js').write_bytes(urllib.request.urlopen('https://cdn.jsdelivr.net/npm/mermaid@11.16.0/dist/mermaid.min.js', timeout=90).read())" \
    && test -s app/frontend/vendor/mermaid.min.js
COPY docs/ ./docs/
COPY image/ ./image/
COPY hyundai-results/ ./hyundai-results/
COPY lean-results/ ./lean-results/
COPY scripts/upload_docs_to_qdrant.sh ./scripts/upload_docs_to_qdrant.sh
COPY scripts/sync_learning_menu.py ./scripts/sync_learning_menu.py
COPY scripts/build_sidebar_partial.py ./scripts/build_sidebar_partial.py
COPY scripts/index_docs_meilisearch.py ./scripts/index_docs_meilisearch.py
RUN chmod +x ./scripts/upload_docs_to_qdrant.sh \
    && python ./scripts/sync_learning_menu.py \
    && python ./scripts/build_sidebar_partial.py

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=10 \
    CMD curl --fail http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

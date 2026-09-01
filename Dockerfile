FROM node:20.20.2-bookworm-slim@sha256:2cf067cfed83d5ea958367df9f966191a942351a2df77d6f0193e162b5febfc0 AS node_runtime

FROM mcr.microsoft.com/playwright/python:v1.43.0-jammy@sha256:153927658c515f20ace339566ba2136444dcdbedd80f1305066ccdb1ae9770ff

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    HOST=0.0.0.0 \
    PORT=10000 \
    AUDIT_BROWSER_HEADLESS=1 \
    AUDIT_PAGE_CONCURRENCY=2 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

COPY --from=node_runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node_runtime /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

COPY pyproject.toml uv.lock ./

RUN python -m pip install --no-cache-dir uv==0.9.28 \
    && UV_PYTHON_DOWNLOADS=never uv sync --python /usr/bin/python3 --frozen --no-dev --no-install-project \
    && npm install -g vercel@58.0.0 \
    && node --version \
    && vercel --version

COPY . .

RUN groupadd --system auditor \
    && useradd --system --gid auditor --home-dir /app --shell /usr/sbin/nologin auditor \
    && mkdir -p /app/shared/generated /app/shared/output \
    && chown -R auditor:auditor /app

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:${PATH}"

USER auditor

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.getenv(\"PORT\", \"10000\")}/health', timeout=5).read()"

CMD ["python", "-m", "src.ui.server"]

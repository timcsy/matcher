# matcher Web — 單一容器映像（feature 020）
# 基底自帶 Python 3.11 + uv；額外裝 WeasyPrint(pango/cairo)、pdftotext(poppler)、CJK 字體。
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

# WeasyPrint 渲染 + pdftotext 抽取 + 中文字體（與 CI 驗證過的清單一致）
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangocairo-1.0-0 libcairo2 \
        poppler-utils fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

# 先複製依賴宣告以利 layer 快取（不含 dev：pytest 不進 production）
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
RUN uv sync --frozen --no-dev

EXPOSE 8765

# --proxy-headers / --forwarded-allow-ips：為日後反向代理（https 網域）預留，
# 讓 OAuth 回呼能正確產生 https://<網域>/auth/callback（port-forward 走 http 不受影響）。
CMD ["uvicorn", "matcher.web.app:create_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8765", \
     "--proxy-headers", "--forwarded-allow-ips=*"]

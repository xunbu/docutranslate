# 阶段1: 构建阶段
FROM python:3.11-slim AS builder

ENV UV_HTTP_TIMEOUT=300 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1

WORKDIR /app

# 安装 uv
RUN pip install --no-cache-dir uv

# 创建虚拟环境并安装依赖
COPY pyproject.toml uv.lock ./
COPY docutranslate ./docutranslate
RUN uv venv && uv sync --frozen --extra mcp

# 阶段2: 运行阶段
FROM python:3.11-slim

LABEL authors="xunbu"

ENV PATH="/app/.venv/bin:$PATH" \
    DOCUTRANSLATE_PORT=8010

WORKDIR /app

# 只安装运行时必需的系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    pandoc \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* /root/.cache

# 从构建阶段复制虚拟环境
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/docutranslate /app/docutranslate

# 创建挂载点
RUN mkdir -p /app/output

EXPOSE 8010

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${DOCUTRANSLATE_PORT}/service/meta || exit 1

# 启动命令
ENTRYPOINT ["docutranslate", "-i", "--with-mcp"]

# docker build -t xunbu/docutranslate:latest .
# docker push xunbu/docutranslate:latest
# docker run -d -p 8010:8010 xunbu/docutranslate:latest
# Web UI: http://127.0.0.1:8010
# MCP SSE: http://127.0.0.1:8010/mcp/sse

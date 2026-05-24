FROM python:3.11-slim
LABEL authors="xunbu"

# 设置环境变量
ENV UV_HTTP_TIMEOUT=300 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    DOCUTRANSLATE_PORT=8010

WORKDIR /app

# 1. 安装系统依赖 + uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    pandoc \
    ca-certificates \
    curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && rm -rf /var/lib/apt/lists/* /root/.cache

ENV PATH="/root/.local/bin:$PATH"

# 2. 创建虚拟环境
RUN uv venv

# 3. 复制项目文件
COPY pyproject.toml uv.lock ./
COPY docutranslate ./docutranslate

# 4. 同步依赖
RUN uv sync --frozen --extra mcp

# 5. 创建挂载点
RUN mkdir -p /app/output

EXPOSE 8010

# 6. 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${DOCUTRANSLATE_PORT}/service/meta || exit 1

# 7. 启动命令
ENTRYPOINT ["docutranslate", "-i", "--with-mcp"]

# docker build -t xunbu/docutranslate:latest .
# docker push xunbu/docutranslate:latest
# docker run -d -p 8010:8010 xunbu/docutranslate:latest
# Web UI: http://127.0.0.1:8010
# MCP SSE: http://127.0.0.1:8010/mcp/sse

FROM python:3.11-slim
LABEL authors="xunbu"

# 设置环境变量
ENV UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV UV_HTTP_TIMEOUT=300
ENV UV_COMPILE_BYTECODE=1
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# 1. 安装系统依赖
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
    pandoc \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 2. 安装 uv
RUN pip install --no-cache-dir uv -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 创建虚拟环境
RUN uv venv /app/.venv

# 4. 复制项目文件
COPY pyproject.toml uv.lock ./
COPY docutranslate ./docutranslate

# 5. 安装依赖（本地构建）
RUN uv pip install -e ".[mcp]"

# 6. 创建挂载点
RUN mkdir -p /app/output

ENV DOCUTRANSLATE_PORT=8010
EXPOSE 8010

# 7. 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8010/service/meta || exit 1

# 8. 启动命令
ENTRYPOINT ["docutranslate", "-i", "--with-mcp"]

# docker build -t xunbu/docutranslate:latest .
# docker push xunbu/docutranslate:latest
# docker run -d -p 8010:8010 xunbu/docutranslate:latest
# Web UI: http://127.0.0.1:8010
# MCP SSE: http://127.0.0.1:8010/mcp/sse

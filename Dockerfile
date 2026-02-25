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
    && rm -rf /var/lib/apt/lists/*

# 2. 安装 uv
RUN pip install --no-cache-dir uv -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 创建虚拟环境
RUN uv venv /app/.venv

# 4. 精准安装：只装 docutranslate 的 mcp 扩展
# 使用 pip install 模式可以完全忽略 pyproject.toml 中的 dev 分组
ARG DOC_VERSION=latest
RUN if [ "$DOC_VERSION" = "latest" ]; then \
        uv pip install "docutranslate[mcp]"; \
    else \
        uv pip install "docutranslate[mcp]==${DOC_VERSION}"; \
    fi

# 5. 创建挂载点
RUN mkdir -p /app/output
VOLUME /app/output

ENV DOCUTRANSLATE_PORT=8010
EXPOSE 8010

# 6. 启动命令
# 注意：因为我们已经把 .venv/bin 加入了 PATH，直接运行 docutranslate 即可
# 这样不仅更快，而且绝对不会触发 uv sync 去下载 dev 依赖
ENTRYPOINT ["docutranslate", "-i", "--with-mcp"]

#docker build --build-arg DOC_VERSION=1.7.0a2 -t xunbu/docutranslate:v1.7.0a2 -t xunbu/docutranslate:latest .
#docker push xunbu/docutranslate:v1.6.0
#docker push xunbu/docutranslate:latest
#docker run -d -p 8010:8010 xunbu/docutranslate:v1.7.0a2
#docker run -d -p 8010:8010 xunbu/docutranslate:v1.7.0a2 --cors
#docker run -it -p 8010:8010 xunbu/docutranslate:v1.6.0
# Web UI: http://127.0.0.1:8010
# MCP SSE: http://127.0.0.1:8010/mcp/sse
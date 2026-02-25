FROM python:3.11-slim
LABEL authors="xunbu"

# 1. 定义构建参数
ARG DOC_VERSION=latest

# 设置工作目录
WORKDIR /app

# =======================
# 替换 Debian APT 源为阿里云镜像
# =======================
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
    pandoc \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# =======================
# 配置 UV 和 Pip 使用清华源
# =======================
ENV UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV UV_HTTP_TIMEOUT=300

# 安装 uv
RUN pip install --no-cache-dir uv -i https://pypi.tuna.tsinghua.edu.cn/simple

# 2. 安装逻辑：只安装 mcp 可选依赖，不安装 dev 和 docling
RUN if [ "$DOC_VERSION" = "latest" ]; then \
        uv add -U "docutranslate[mcp]"; \
    else \
        uv add -U "docutranslate[mcp]==${DOC_VERSION}"; \
    fi

# 创建挂载目录
RUN mkdir -p /app/output
VOLUME /app/output

# 设置环境变量
ENV DOCUTRANSLATE_PORT=8010

# 暴露端口
EXPOSE 8010

# 启动命令 - 只运行带 mcp 的版本
ENTRYPOINT ["uv", "run", "--no-dev", "docutranslate", "-i", "--with-mcp"]

# docker build --build-arg DOC_VERSION=1.7.0a2 -t xunbu/docutranslate:mcp-latest .
# docker run -d -p 8010:8010 xunbu/docutranslate:mcp-latest
# Web UI: http://127.0.0.1:8010
# MCP SSE: http://127.0.0.1:8010/mcp/sse
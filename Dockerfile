FROM python:3.11-slim
LABEL authors="xunbu"

# 1. 定义构建参数
ARG DOC_VERSION=latest

# 设置工作目录
WORKDIR /app

# =======================
# 【优化 1】替换 Debian APT 源为阿里云镜像（针对 Debian 12 Bookworm）
# 这一步能极大加速 apt-get update 和 install
# =======================
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
    pandoc \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# =======================
# 【优化 2】配置 UV 和 Pip 使用清华/阿里源
# 设置环境变量，uv 会自动读取该变量作为镜像源
# =======================
ENV UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV UV_Http_TIMEOUT=300

# 安装 uv (指定 -i 参数确保 pip 安装 uv 本身时也是走镜像)
RUN pip install --no-cache-dir uv -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN uv init

# 2. 安装逻辑：如果是 latest 则不指定版本，否则安装指定版本
# uv add 会自动使用上面配置的 UV_INDEX_URL
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

# 启动命令
# 注意：使用 uv run 会在隔离的虚拟环境中运行，这很好
ENTRYPOINT ["uv", "run", "--no-dev","--no-extra","docling","docutranslate", "-i", "--with-mcp"]


#docker build --build-arg DOC_VERSION=1.7.0a2 -t xunbu/docutranslate:v1.7.0a2 -t xunbu/docutranslate:latest .
#docker push xunbu/docutranslate:v1.6.0
#docker push xunbu/docutranslate:latest
#docker run -d -p 8010:8010 xunbu/docutranslate:v1.7.0a2
#docker run -d -p 8010:8010 xunbu/docutranslate:v1.7.0a2 --cors
#docker run -it -p 8010:8010 xunbu/docutranslate:v1.6.0
# Web UI: http://127.0.0.1:8010
# MCP SSE: http://127.0.0.1:8010/mcp/sse
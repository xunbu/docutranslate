FROM python:3.11-slim
LABEL authors="xunbu"

# 1. 定义构建参数，给一个默认值 'latest' 防止构建报错
ARG DOC_VERSION=latest

# 设置工作目录
WORKDIR /app

# 安装 uv
RUN pip install --no-cache-dir uv
RUN uv init

# 2. 安装逻辑：如果是 latest 则不指定版本，否则安装指定版本
RUN if [ "$DOC_VERSION" = "latest" ]; then \
        uv add -U docutranslate; \
    else \
        uv add -U docutranslate==${DOC_VERSION}; \
    fi

# 创建挂载目录（建议加上这一行，防止用户忘记挂载导致文件丢失）
RUN mkdir -p /app/output
VOLUME /app/output

# 设置环境变量
ENV DOCUTRANSLATE_PORT=8010

# 暴露端口
EXPOSE 8010

# 【核心修改】启动命令
# -i 是强制的，用户在 docker run 后面输入的任何参数都会追加到这行命令末尾
ENTRYPOINT ["uv", "run", "docutranslate", "-i"]


#docker build --build-arg DOC_VERSION=1.5.1 -t xunbu/docutranslate:v1.5.1 .
#docker push xunbu/docutranslate:v1.5.1
#docker run -d -p 8010:8010 xunbu/docutranslate:v1.5.4
#docker run -it -p 8010:8010 xunbu/docutranslate:v1.5.4
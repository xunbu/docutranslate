FROM python:3.11-slim
LABEL authors="xunbu"

# 1. 定义构建参数（ARG），可以设置一个默认值，比如 0.0.1
# 这个变量只在 docker build 过程中有效
ARG DOC_VERSION

# 设置工作目录
WORKDIR /app

# 安装 uv
RUN pip install --no-cache-dir uv
RUN uv init

# 2. 使用变量安装指定版本
# 注意：这里引用变量的语法是 ${变量名}
# 如果传入 1.5.1，这行命令就会变成 uv add -U docutranslate==1.5.1
RUN uv add -U docutranslate==${DOC_VERSION}

# 设置环境变量
ENV DOCUTRANSLATE_PORT=8010

# 暴露端口
EXPOSE 8010

# 启动命令
CMD ["uv", "run", "docutranslate", "-i"]

#docker build --build-arg DOC_VERSION=1.5.1 -t xunbu/docutranslate:v1.5.1 .
#docker push xunbu/docutranslate:v1.5.1
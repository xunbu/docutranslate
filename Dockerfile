FROM python:3.11-slim
LABEL authors="xunbu"

# 设置工作目录
WORKDIR /app

# 安装 DocuTranslate
RUN pip install --no-cache-dir uv
RUN uv init
RUN uv add -U docutranslate

# 设置环境变量
ENV DOCUTRANSLATE_PORT=8010

# 暴露端口（Web UI 默认端口）
EXPOSE 8010

# 启动命令
CMD ["uv" ,"run","docutranslate", "-i"]
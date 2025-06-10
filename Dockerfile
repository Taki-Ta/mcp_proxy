FROM ubuntu:22.04

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 安装uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY pyproject.toml ./
COPY main.py ./
COPY env.example ./.env

# 使用uv安装依赖
RUN uv pip install --system -e .

# 暴露端口
EXPOSE 5000

# 设置环境变量
ENV PYTHONPATH=/app
ENV PORT=5000

# 启动命令
CMD ["python3", "main.py"] 
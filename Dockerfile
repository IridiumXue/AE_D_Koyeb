# Dockerfile
FROM python:3.9-slim

WORKDIR /app
RUN pip install --upgrade pip
# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用程序文件
COPY app.py .
COPY aedemobg.png .  # 确保背景图片被复制

# 创建非root用户
RUN useradd -m -u 1000 user
USER user

# 设置环境变量
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONPATH=/app

WORKDIR $HOME/app
COPY --chown=user . $HOME/app

# 暴露端口
EXPOSE 7860

# 运行应用
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]
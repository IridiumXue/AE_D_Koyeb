# 使用更輕量的基礎鏡像
FROM python:3.9-slim

WORKDIR /app

# 安裝系統依賴（僅必需的）
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 優化pip安裝
RUN pip install --upgrade pip --no-cache-dir

# 分層安裝依賴以利用Docker緩存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用文件
COPY app.py .
COPY aedemobg.png .

# 創建非root用戶
RUN useradd -m -u 1000 user
USER user

# 設置環境變量
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONPATH=/app \
    MPLBACKEND=Agg

WORKDIR $HOME/app
COPY --chown=user . $HOME/app

# 暴露端口
EXPOSE 7860

# 健康檢查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:7860/_stcore/health || exit 1

# 運行應用
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0", "--server.maxUploadSize=1", "--server.enableCORS=false"]

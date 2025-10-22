# 使用Python官方镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production

# 设置pip配置（使用国内镜像）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/ \
    && pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn \
    && pip config set global.timeout 300 \
    && pip config set global.retries 3


# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p /var/zbw_flask_files/uploads && \
    mkdir -p /var/zbw_flask_files/logs && \
    chmod -R 755 /var/zbw_flask_files

# 暴露端口
EXPOSE 5000

# 启动命令 - 使用gunicorn启动，workers=1，支持WebSocket
CMD ["gunicorn", \
     "--worker-class", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", \
     "--workers", "1", \
     "--worker-connections", "1000", \
     "--bind", "0.0.0.0:5000", \
     "--timeout", "120", \
     "--access-logfile", "/var/zbw_flask_files/logs/access.log", \
     "--error-logfile", "/var/zbw_flask_files/logs/error.log", \
     "--log-level", "debug", \
     "--graceful-timeout", "30", \
     "--preload", \
     "scripts.run_linux:app"]


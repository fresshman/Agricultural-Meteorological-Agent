# ========== Stage 1: 构建前端 ==========
FROM node:20-alpine AS frontend-builder
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
# 国内构建环境直连 registry.npmjs.org 易超时，改用 npmmirror 镜像
RUN npm install --registry https://registry.npmmirror.com
COPY frontend/ ./
RUN npm run build

# ========== Stage 2: 运行时 ==========
FROM python:3.10-slim
WORKDIR /app

# 系统依赖：nginx（反代 + 静态托管）
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    && rm -rf /var/lib/apt/lists/*

    # Python 依赖（预编译 wheel，无需 build-essential）
    COPY backend/requirements.txt /app/backend/requirements.txt
    # 国内/ModelScope 构建环境直连 files.pythonhosted.org 经常超时，改用清华 PyPI 镜像并加大超时与重试
    ENV PIP_DEFAULT_TIMEOUT=120
    RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 120 --retries 10 -r /app/backend/requirements.txt

# 前端构建产物
COPY --from=frontend-builder /build/dist /app/frontend/dist

# 后端代码
COPY backend/ /app/backend/

# 业务代码（src / config / knowledge_bases / data）
COPY src/ /app/src/
COPY config/ /app/config/
COPY knowledge_bases/ /app/knowledge_bases/
COPY data/ /app/data/

# 运行时目录（日志 + 数据库）
RUN mkdir -p /app/logs /app/data

# nginx 配置（监听 7860，反代 /api → uvicorn:8000）
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
RUN rm -f /etc/nginx/sites-enabled/default

# 启动脚本（同时运行 uvicorn + nginx）
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 7860

CMD ["/app/start.sh"]

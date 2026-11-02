#!/bin/bash
# 容器启动脚本：同时运行 uvicorn 后端和 nginx 前端
# 注意：本文件必须保持 LF 换行。CRLF 会让首行变成 "#!/bin/bash\r"，
# 容器里直接报 "/app/start.sh: not found"（exit 127）。
set -e

cd /app

echo "Starting uvicorn backend on :8000..."
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 1 &
UVICORN_PID=$!

echo "Starting nginx on :7860..."
nginx -g "daemon off;" &
NGINX_PID=$!

trap "kill $UVICORN_PID $NGINX_PID 2>/dev/null; exit 0" INT TERM

wait -n $UVICORN_PID $NGINX_PID
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "A process exited with code $EXIT_CODE, shutting down..."
    kill $UVICORN_PID $NGINX_PID 2>/dev/null
    exit $EXIT_CODE
fi

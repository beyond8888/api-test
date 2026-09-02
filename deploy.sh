#!/bin/bash
# ApiTester 远程部署脚本
# 使用方法: 在远端服务器上执行 bash deploy.sh

set -e

APP_DIR="/opt/apitest"
DOMAIN="apitest.example.com"  # 替换为你的域名
HEALTH_RETRIES=5
HEALTH_DELAY=3

# ---- 动态 workers ----
CPU_COUNT=$(nproc 2>/dev/null || echo 2)
WORKERS=$(( (CPU_COUNT * 2 + 1) < 8 ? (CPU_COUNT * 2 + 1) : 8 ))
[ "$WORKERS" -lt 1 ] && WORKERS=1

echo "=== 1. 安装依赖 ==="
apt update && apt install -y python3 python3-venv python3-pip nginx curl

echo "=== 2. 部署后端 ==="
mkdir -p $APP_DIR/backend $APP_DIR/frontend

# 用 tar 管道复制，排除 venv/node_modules/dist 等会在部署机上重建的巨型目录
# （本机 venv 约 500MB、node_modules 约 250MB，cp -r 全量复制会极慢且浪费带宽）
tar -C backend --exclude=venv --exclude=.venv --exclude=__pycache__ --exclude='*.pyc' -cf - . | tar -C $APP_DIR/backend -xf -
tar -C frontend --exclude=node_modules --exclude=dist --exclude=.vite --exclude='*.tsbuildinfo' -cf - . | tar -C $APP_DIR/frontend -xf -

cd $APP_DIR/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 迁移数据库
python manage.py migrate

echo "=== 3. 构建前端 ==="
cd $APP_DIR/frontend

# 安装 Node.js (如果没有)
command -v node || (curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt install -y nodejs)

npm ci
npm run build  # 输出到 dist/

echo "=== 4. 配置 Uvicorn (ASGI) ==="
cat > /etc/systemd/system/apitest.service << EOF
[Unit]
Description=ApiTester Backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/apitest/backend
Environment="LOG_DIR=/var/log/apitest"
ExecStart=/opt/apitest/backend/venv/bin/uvicorn apitester.asgi:application \\
    --bind 127.0.0.1:8000 \\
    --workers ${WORKERS} \\
    --access-logfile - \\
    --error-logfile -
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable apitest
systemctl start apitest

echo "=== 5. 配置 Nginx ==="
cat > /etc/nginx/sites-available/apitest << NGXEOF
server {
    listen 80;
    server_name $DOMAIN;

    # 前端静态文件
    root /opt/apitest/frontend/dist;
    index index.html;

    # Vue SPA 路由
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # 后端 API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 75s;
    }

    # 健康检查端点
    location /api/v1/health/ {
        proxy_pass http://127.0.0.1:8000;
        access_log off;
    }
}
NGXEOF

ln -sf /etc/nginx/sites-available/apitest /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "=== 6. 健康检查 ==="
echo "等待服务启动..."
sleep 2

for i in $(seq 1 $HEALTH_RETRIES); do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/v1/health/ 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        echo "  [OK] 后端健康检查通过 (HTTP $HTTP_CODE)"
        break
    fi
    if [ "$i" = "$HEALTH_RETRIES" ]; then
        echo "  [FAIL] 后端健康检查失败 (HTTP $HTTP_CODE)，请检查 systemctl status apitest"
        exit 1
    fi
    echo "  等待重试 ($i/$HEALTH_RETRIES)..."
    sleep $HEALTH_DELAY
done

HTTP_FRONTEND=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/ 2>/dev/null || echo "000")
if [ "$HTTP_FRONTEND" = "200" ] || [ "$HTTP_FRONTEND" = "301" ] || [ "$HTTP_FRONTEND" = "302" ]; then
    echo "  [OK] 前端健康检查通过 (HTTP $HTTP_FRONTEND)"
else
    echo "  [WARN] 前端响应异常 (HTTP $HTTP_FRONTEND)，请检查 Nginx 配置"
fi

echo ""
echo "部署完成! 访问 http://$DOMAIN"
echo ""
echo "检查服务状态:"
echo "  systemctl status apitest"
echo "  systemctl status nginx"
echo "  tail -f /var/log/apitest/app.log"
echo "  tail -f /var/log/apitest/errors.log"
echo ""

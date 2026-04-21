#!/bin/bash
# ──────────────────────────────────────────────────────
# Script khởi động toàn bộ hệ thống VEX Auto Care
# Chạy: bash start.sh
# ──────────────────────────────────────────────────────

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   🚗 VEX Auto Care — Khởi động hệ thống         ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# 1. Khởi động API Server nền
echo "▶ [1/3] Khởi động API Server (port 8765)..."
python "$ROOT/server/app.py" &
API_PID=$!
sleep 2

curl -s http://localhost:8765/api/health > /dev/null 2>&1
if [ $? -eq 0 ]; then
  echo "   ✅ API Server đang chạy tại http://localhost:8765"
else
  echo "   ⚠️  API Server chưa sẵn sàng, kiểm tra lại..."
fi

# 2. Khởi động Web Frontend
WEB_DIR="$ROOT/khachhang_web"
echo ""
echo "▶ [2/3] Khởi động Web Frontend..."

if [ ! -d "$WEB_DIR/node_modules" ]; then
  echo "   📦 Chưa có node_modules, đang cài..."
  (cd "$WEB_DIR" && npm install)
fi

(cd "$WEB_DIR" && npm run dev) &
WEB_PID=$!
sleep 3

echo "   ✅ Web Frontend đang chạy tại http://localhost:5173"

# 3. Khởi động Desktop App
echo ""
echo "▶ [3/3] Khởi động Desktop App..."
python "$ROOT/main.py"

# Cleanup khi đóng desktop app
echo ""
echo "Đang tắt các service..."
kill $API_PID 2>/dev/null
kill $WEB_PID 2>/dev/null
echo "✅ Đã tắt xong."

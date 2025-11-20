#!/bin/bash

# BP Generation Agent Web UI 启动脚本

echo "=========================================="
echo "BP Generation Agent Web UI"
echo "=========================================="
echo ""

# 检查 API 服务器是否运行
API_URL="http://localhost:8000"
if curl -s "$API_URL/health" > /dev/null 2>&1; then
    echo "✓ API 服务器已在运行 ($API_URL)"
else
    echo "⚠ API 服务器未运行"
    echo ""
    echo "请先启动 API 服务器："
    echo "  python api_server.py"
    echo ""
    read -p "是否现在启动 API 服务器？(y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "正在启动 API 服务器..."
        python api_server.py &
        API_PID=$!
        echo "API 服务器已启动 (PID: $API_PID)"
        echo "等待服务器就绪..."
        sleep 3
    else
        echo "请手动启动 API 服务器后再使用 Web UI"
        exit 1
    fi
fi

echo ""
echo "正在启动 Web UI 服务器..."
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 检查文件是否存在
if [ ! -f "web_ui.html" ]; then
    echo "错误: 找不到 web_ui.html 文件"
    echo "当前目录: $(pwd)"
    exit 1
fi

# 启动简单的 HTTP 服务器
PORT=8080
echo "Web UI 地址: http://localhost:$PORT/web_ui.html"
echo "工作目录: $(pwd)"
echo ""
echo "按 Ctrl+C 停止服务器"
echo "=========================================="
echo ""

# 使用 Python 3 的 http.server
python3 -m http.server $PORT


#!/bin/bash
cd "$(dirname "$0")"

# 先检查是否已在运行
if lsof -t -i :8000 &>/dev/null; then
    echo "服务已在运行中: http://localhost:8000"
    read -p "按回车键退出..."
    exit 0
fi

source .venv/bin/activate
nohup python3 main.py > /dev/null 2>&1 &
echo "已启动，浏览器打开 http://localhost:8000"
echo "关闭请双击「关闭.command」"
read -p "按回车键退出（服务仍在后台运行）..."

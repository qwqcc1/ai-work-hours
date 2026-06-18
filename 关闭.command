#!/bin/bash
kill $(lsof -t -i :8000) 2>/dev/null && echo "已关闭" || echo "未找到正在运行的服务"
read -p "按回车键退出..."

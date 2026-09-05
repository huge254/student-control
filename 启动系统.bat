@echo off
chcp 65001 >nul
title 学生管理系统 - Web 服务
cd /d "%~dp0"

echo ============================================
echo   学生管理系统正在启动...
echo   启动后浏览器会自动打开
echo   关闭此窗口即可停止服务
echo ============================================

REM 延迟 2 秒后自动打开浏览器（等服务先就绪）
start "" powershell -WindowStyle Hidden -Command "Start-Sleep 2; Start-Process 'http://127.0.0.1:8000'"

python -m uvicorn main:app
pause

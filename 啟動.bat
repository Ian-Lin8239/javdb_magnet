@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在啟動 JavDB 磁力鏈接工具...
echo.
py run_javdb_magnet.py
pause


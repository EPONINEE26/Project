@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -c "import django, pandas" >nul 2>&1
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" scripts\prepare_db.py
if errorlevel 1 goto fail
echo.
echo 홈페이지: http://127.0.0.1:8000/
echo 종료: Ctrl+C
".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000
if errorlevel 1 goto fail
exit /b 0
:fail
echo 실행 중 오류가 발생했습니다. 위 내용을 확인해주세요.
pause
exit /b 1

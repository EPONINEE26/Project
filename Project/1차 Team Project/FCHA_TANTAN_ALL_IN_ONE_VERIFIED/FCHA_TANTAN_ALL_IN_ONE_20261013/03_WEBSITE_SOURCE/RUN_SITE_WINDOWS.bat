@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo ===============================================
echo  FCHA TANTAN - Django local startup (DEMO)
echo ===============================================
echo This version contains sample/demo statistics only.
where py >nul 2>&1
if not errorlevel 1 (
 set "PY=py -3.13"
 py -3.13 --version >nul 2>&1
 if errorlevel 1 (
  py -3.12 --version >nul 2>&1
  if not errorlevel 1 set "PY=py -3.12"
 )
) else (
 where python >nul 2>&1
 if errorlevel 1 (
  echo Python not found. Install Python 3.12 or 3.13 and retry.
  pause
  exit /b 1
 )
 set "PY=python"
)
if not exist ".venv\Scripts\python.exe" (
 echo [1/4] Creating isolated Python environment...
 %PY% -m venv .venv
 if errorlevel 1 goto :error
)
echo [2/4] Installing required packages (Internet required on first run)...
".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
if errorlevel 1 goto :error
echo [3/4] Preparing SQLite schema...
".venv\Scripts\python.exe" backend\manage.py migrate --noinput
if errorlevel 1 goto :error
REM Seed demo only if database has no brands; never modify existing user data.
".venv\Scripts\python.exe" -c "import os,sys;sys.path.insert(0,'backend');os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');import django;django.setup();from brands.models import Brand;sys.exit(0 if Brand.objects.exists() else 10)"
if errorlevel 10 (
 echo [4/4] Loading demonstration statistics...
 ".venv\Scripts\python.exe" backend\manage.py seed_demo
 if errorlevel 1 goto :error
)
echo.
echo Open in browser: http://127.0.0.1:8000
start "" "http://127.0.0.1:8000"
".venv\Scripts\python.exe" backend\manage.py runserver 127.0.0.1:8000
exit /b %errorlevel%
:error
echo.
echo Startup failed. Read 00_README_FIRST.txt and the error above.
pause
exit /b 1

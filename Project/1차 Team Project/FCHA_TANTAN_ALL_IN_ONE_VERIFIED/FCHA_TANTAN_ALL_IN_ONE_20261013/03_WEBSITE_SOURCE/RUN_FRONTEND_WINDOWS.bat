@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if not errorlevel 1 (
 set "PY=py -3"
) else (
 where python >nul 2>&1
 if errorlevel 1 (echo Python not found.&pause&exit /b 1)
 set "PY=python"
)
echo This mode displays DEMO JSON without Django or database.
echo Open http://127.0.0.1:8080
start "" "http://127.0.0.1:8080"
%PY% -m http.server 8080 --directory dist

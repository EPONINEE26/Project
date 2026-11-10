@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
title FCHA TANTAN - Local Server
pushd "%~dp0"
if errorlevel 1 goto fail
if not exist "scripts\start_windows.ps1" goto missing
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_windows.ps1"
set "START_RESULT=%ERRORLEVEL%"
if not "%START_RESULT%"=="0" goto fail
popd
exit /b 0
:missing
echo Please extract the entire ZIP before running start.bat.
:fail
echo.
echo Startup failed. See the message above and logs\startup.log.
echo Keep this window open or send logs\startup.log for diagnosis.
pause
exit /b 1

@echo off
setlocal
REM Usage: run_worker.bat 4
set WORKERS=%1
if "%WORKERS%"=="" set WORKERS=1
python run_worker.py --workers %WORKERS%

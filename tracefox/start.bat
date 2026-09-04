@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo TraceFox is not set up yet. Running setup first...
  call setup.bat
)
if not exist .venv\Scripts\python.exe exit /b 1
call .venv\Scripts\activate.bat
python app.py

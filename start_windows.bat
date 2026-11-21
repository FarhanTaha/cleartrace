@echo off
cd /d %~dp0
where python >nul 2>nul
if errorlevel 1 (
    echo Python is not installed. Get it from https://www.python.org/downloads/
    echo IMPORTANT: tick "Add python.exe to PATH" during install, then run this again.
    pause
    exit /b 1
)
if not exist venv (
    echo First run: setting up ClearTrace. This takes a minute or two...
    python -m venv venv
    venv\Scripts\python -m pip install --upgrade pip >nul
    venv\Scripts\python -m pip install -r requirements.txt
)
if not exist demo_folder venv\Scripts\python make_demo.py
echo Starting ClearTrace... it will open in your browser.
venv\Scripts\python -m streamlit run app.py
pause

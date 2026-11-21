#!/bin/bash
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
    echo "Python is not installed. Get it from https://www.python.org/downloads/"
    exit 1
fi
if [ ! -d venv ]; then
    echo "First run: setting up ClearTrace. This takes a minute or two..."
    python3 -m venv venv
    venv/bin/pip install --upgrade pip >/dev/null
    venv/bin/pip install -r requirements.txt
fi
[ -d demo_folder ] || venv/bin/python make_demo.py
echo "Starting ClearTrace... it will open in your browser."
venv/bin/python -m streamlit run app.py

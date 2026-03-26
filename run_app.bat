@echo off
cd /d "%~dp0"
python -m streamlit run "%~dp0app.py" --server.port 8501 --server.headless true

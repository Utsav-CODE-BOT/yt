@echo off
setlocal
cd /d "C:\Users\ud127\faceless-shorts-factory"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

:: Self-healing: Ensure Ollama local LLM service is running
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >NUL
if errorlevel 1 (
    start "" /B ollama serve
    timeout /t 4 /nobreak >NUL
)

:: Execute autonomous daily batch
"C:\Users\ud127\.faceless-shorts\venv\Scripts\python.exe" "C:\Users\ud127\faceless-shorts-factory\main.py" --daily >> "C:\Users\ud127\faceless-shorts-factory\workspace\logs\cron.log" 2>&1
endlocal

@echo off
setlocal
cd /d "C:\Users\ud127\faceless-shorts-factory"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
"C:\Users\ud127\.faceless-shorts\venv\Scripts\python.exe" "C:\Users\ud127\faceless-shorts-factory\main.py" --daily >> "C:\Users\ud127\faceless-shorts-factory\workspace\logs\cron.log" 2>&1
endlocal

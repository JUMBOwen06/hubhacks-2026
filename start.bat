@echo off
rem Double-click to run the Black History Hub: starts the backend and opens the app.
rem First run creates backend\.venv and installs requirements (needs Python 3.10+).
rem Close this window (or press Ctrl+C) to stop the server.
setlocal
cd /d "%~dp0"

set "PORT=8000"
set "PY=backend\.venv\Scripts\python.exe"

if not exist "%PY%" (
  echo Setting up backend\.venv for the first time...
  where py >nul 2>nul && (py -m venv backend\.venv) || (python -m venv backend\.venv)
  if not exist "%PY%" (
    echo Could not create the virtual environment. Is Python installed?
    pause
    exit /b 1
  )
  "%PY%" -m pip install -q -r backend\requirements.txt
)

rem Open the browser a few seconds after the server starts building the database.
start "" cmd /c "timeout /t 4 /nobreak >nul & start http://127.0.0.1:%PORT%/app/"

echo Starting the server at http://127.0.0.1:%PORT%/app/  (close this window to stop)
"%PY%" -m uvicorn app.main:app --app-dir backend --port %PORT%
pause

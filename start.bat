@echo off
rem Double-click to run the Black History Hub: starts the backend and opens the app.
rem First run creates backend\.venv and installs requirements (needs Python 3.10+).
rem Uses port 8000, or the next free port if 8000 is busy. Set PORT to prefer another.
rem Close this window (or press Ctrl+C) to stop the server.
setlocal
cd /d "%~dp0"

set "VENV=backend\.venv"
set "PY=%VENV%\Scripts\python.exe"

rem Recreate the virtual environment if it exists but its Python no longer runs.
if not exist "%PY%" goto create_venv
"%PY%" -c "import sys" >nul 2>nul && goto check_version
echo The virtual environment in %VENV% is broken. Recreating it...
rmdir /s /q "%VENV%"

:create_venv
echo Setting up %VENV% for the first time...
where py >nul 2>nul && (py -3 -m venv "%VENV%") || (python -m venv "%VENV%")
if not exist "%PY%" (
  echo Could not create the virtual environment. Install Python 3.10 or newer from https://www.python.org/downloads/ and try again.
  goto fail
)

:check_version
"%PY%" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
  echo Python 3.10 or newer is needed. Install it, delete the backend\.venv folder, and run start.bat again.
  goto fail
)

rem Install the requirements if any are missing, including after a failed first install.
"%PY%" -c "import fastapi, uvicorn" >nul 2>nul && goto run
echo Installing the backend requirements. This takes a minute...
"%PY%" -m pip install -q -r backend\requirements.txt
"%PY%" -c "import fastapi, uvicorn" >nul 2>nul && goto run
echo.
echo Could not install the backend requirements. Check your internet connection and run start.bat again.
goto fail

:run
rem launch.py picks a free port, starts the server and opens the browser once it answers.
"%PY%" backend\launch.py
pause
exit /b 0

:fail
pause
exit /b 1

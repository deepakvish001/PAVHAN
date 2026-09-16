@echo off
REM PAVHAN launcher for Windows.
REM
REM   run.bat         ONE PORT. Builds the app and serves everything from
REM                   http://localhost:8000 (the microphone works there).
REM   run.bat dev     Two ports with hot reload: API 8000, app 5173.
REM   run.bat test    Run the API smoke test against a running server.

setlocal
set ROOT=%~dp0
set MODE=%1
if "%MODE%"=="" set MODE=start

where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo   Python was not found. Install Python 3.10+ from https://python.org
  echo   and tick "Add Python to PATH" during setup.
  echo.
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo.
  echo   Node.js was not found. Install Node 18+ from https://nodejs.org
  echo.
  exit /b 1
)

cd /d "%ROOT%backend"
if not exist .venv (
  echo Creating the Python environment ^(first run only^)...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
echo Installing Python packages...
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt

if not exist app\ml\price_model.joblib (
  echo Training the pricing model ^(first run only, ~15s^)...
  python -m app.ml.train >nul
)

if "%MODE%"=="test" (
  python tests\smoke_test.py
  goto :eof
)

cd /d "%ROOT%frontend"
if not exist node_modules (
  echo Installing npm packages ^(first run only^)...
  call npm install
)

if "%MODE%"=="dev" (
  start "PAVHAN API" cmd /k "cd /d %ROOT%backend && call .venv\Scripts\activate.bat && python -m uvicorn app.main:app --reload --port 8000"
  timeout /t 4 >nul
  echo.
  echo   App on http://localhost:5173
  echo.
  call npm run dev
  goto :eof
)

echo Building the app...
call npm run build

cd /d "%ROOT%backend"
echo.
echo ========================================================
echo   PAVHAN is running.
echo.
echo     App   -^>  http://localhost:8000
echo     API   -^>  http://localhost:8000/docs
echo.
echo   Open it in Chrome or Edge. Use the localhost address
echo   exactly as printed - browsers switch the microphone
echo   off on any other address that is not https.
echo ========================================================
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

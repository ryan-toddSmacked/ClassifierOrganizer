@echo off
rem setup.bat - Create and prepare a .venv for ChipOrganizer (Windows CMD)
setlocal enableextensions enabledelayedexpansion

rem Try to locate Python (prefer py launcher then python)
set "PY_EXE="
for /f "delims=" %%I in ('where py 2^>nul') do if not defined PY_EXE set "PY_EXE=py"
if not defined PY_EXE (
    for /f "delims=" %%I in ('where python 2^>nul') do if not defined PY_EXE set "PY_EXE=python"
)

if not defined PY_EXE (
    echo [ERROR] No Python executable found on PATH. Install Python 3 and ensure 'python' or 'py' is available.
    exit /b 1
)

echo [INFO] Using launcher: %PY_EXE%

set "VENV_DIR=.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

if not exist "%VENV_DIR%" (
    echo [INFO] Creating virtual environment at %VENV_DIR%
    %PY_EXE% -3 -m venv "%VENV_DIR%" >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        exit /b 1
    )
) else (
    echo [INFO] Virtual environment already exists at %VENV_DIR%
)

if not exist "%VENV_PY%" (
    echo [ERROR] Virtual environment python not found at %VENV_PY%
    exit /b 1
)

echo [INFO] Upgrading pip, setuptools, wheel in virtual environment...
"%VENV_PY%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo [WARN] pip upgrade reported errors but continuing.
)

if exist requirements.txt (
    echo [INFO] Installing packages from requirements.txt...
    "%VENV_PY%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install requirements. Check output above.
        exit /b 1
    )
) else (
    echo [WARN] No requirements.txt found; skipping package installation.
)

echo
echo [INFO] Setup complete.
echo.
echo How to activate the virtual environment (PowerShell):
echo    & .\%VENV_DIR%\Scripts\Activate.ps1
echo.
echo How to activate the virtual environment (CMD):
echo    %VENV_DIR%\Scripts\activate.bat
echo.
echo How to run the app without activation:
echo    %VENV_DIR%\Scripts\python.exe .\main.py
echo.
echo After activating, run:
echo    python .\main.py
echo.
echo Notes:
echo - If PowerShell blocks Activate.ps1 due to execution policy, run:
echo     Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
echo - This script does not change execution policy.
endlocal

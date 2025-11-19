#!/usr/bin/env bash
# setup.sh - create and prepare a .venv for ChipOrganizer (POSIX shells)
set -euo pipefail

# Find python: prefer python3 then python
PYTHON=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON=$(command -v python3)
elif command -v python >/dev/null 2>&1; then
  PYTHON=$(command -v python)
else
  echo "[ERROR] No Python executable found on PATH. Install Python 3 and ensure 'python3' or 'python' is available." >&2
  exit 1
fi

echo "[INFO] Using Python: $PYTHON"

VENV_DIR=".venv"
VENV_PY="$VENV_DIR/bin/python"

if [ ! -d "$VENV_DIR" ]; then
  echo "[INFO] Creating virtual environment at $VENV_DIR"
  "$PYTHON" -m venv "$VENV_DIR"
else
  echo "[INFO] Virtual environment already exists at $VENV_DIR"
fi

if [ ! -x "$VENV_PY" ]; then
  echo "[ERROR] Virtual environment python not found at $VENV_PY" >&2
  exit 1
fi

echo "[INFO] Upgrading pip, setuptools, wheel in virtual environment..."
"$VENV_PY" -m pip install --upgrade pip setuptools wheel || echo "[WARN] pip upgrade reported errors but continuing."

if [ -f requirements.txt ]; then
  echo "[INFO] Installing packages from requirements.txt..."
  "$VENV_PY" -m pip install -r requirements.txt
else
  echo "[WARN] No requirements.txt found; skipping package installation."
fi

echo
echo "[INFO] Setup complete."

echo "How to activate the virtual environment (bash/zsh):"
echo "  source $VENV_DIR/bin/activate"
echo
echo "How to run the app without activating:"
echo "  $VENV_PY ./main.py"
echo
echo "After activating, run:"
echo "  python ./main.py"
echo
echo "Notes:" 
echo " - If you prefer, you can also use a system package manager to install dependencies globally, but a venv is recommended."

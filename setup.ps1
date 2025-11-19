<#
setup.ps1

Windows PowerShell helper script to create and prepare a Python virtual environment
for this project. It will:
 - find a Python executable (python, py, or python3)
 - create a `.venv` virtual environment (if it doesn't exist)
 - use the venv's python to upgrade pip
 - install `requirements.txt` if present
 - display how to activate/run the app

Run from the project root (where `main.py` lives):
    .\setup.ps1
#>

function Write-Info($msg) { Write-Host "[INFO]  " -ForegroundColor Cyan -NoNewline; Write-Host $msg }
function Write-Warn($msg) { Write-Host "[WARN]  " -ForegroundColor Yellow -NoNewline; Write-Host $msg }
function Write-Err($msg) { Write-Host "[ERROR] " -ForegroundColor Red -NoNewline; Write-Host $msg }

# Try to find python
$pythonCandidates = @('python', 'py', 'python3')
$pythonExe = $null
foreach ($c in $pythonCandidates) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd) {
        $pythonExe = $cmd.Source
        break
    }
}

if (-not $pythonExe) {
    Write-Err "No Python executable found on PATH. Please install Python 3.8+ and ensure 'python' or 'py' is available.";
    exit 1
}

Write-Info "Using Python: $pythonExe"

$venvDir = Join-Path -Path (Get-Location) -ChildPath '.venv'
$venvPython = Join-Path -Path $venvDir -ChildPath 'Scripts\python.exe'
$venvActivate = Join-Path -Path $venvDir -ChildPath 'Scripts\Activate.ps1'

# Create venv if missing
if (-not (Test-Path $venvDir)) {
    Write-Info "Creating virtual environment at $venvDir"
    & $pythonExe -m venv $venvDir
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Failed to create virtual environment (exit $LASTEXITCODE)."
        exit 1
    }
} else {
    Write-Info "Virtual environment already exists at $venvDir"
}

if (-not (Test-Path $venvPython)) {
    Write-Err "Virtual environment does not seem to have a Python executable at $venvPython"
    exit 1
}

# Upgrade pip
Write-Info "Upgrading pip in virtual environment..."
& $venvPython -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) {
    Write-Warn "pip upgrade reported errors (exit $LASTEXITCODE). Continuing to attempt package install."
}

# Install requirements if file exists
if (Test-Path 'requirements.txt') {
    Write-Info "Installing requirements from requirements.txt"
    & $venvPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Failed to install requirements (exit $LASTEXITCODE). Check the output above for details."
        exit 1
    }
} else {
    Write-Warn "No requirements.txt found in project root. Skipping package installation."
}

# Done
Write-Info "Setup complete."

Write-Host "`nHow to activate the virtual environment (PowerShell):" -ForegroundColor Green
Write-Host "  & .\\.venv\\Scripts\\Activate.ps1" -ForegroundColor White

Write-Host "`nHow to run the app (without activating):" -ForegroundColor Green
Write-Host "  .\\.venv\\Scripts\\python.exe .\\main.py" -ForegroundColor White

Write-Host "`nOr, after activating, run:" -ForegroundColor Green
Write-Host "  python .\\main.py" -ForegroundColor White

Write-Host "`nNotes:" -ForegroundColor Green
Write-Host " - If PowerShell refuses to run the Activate script due to execution policy, run this once (as admin or CurrentUser):" -ForegroundColor White
Write-Host "     Set-ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor White
Write-Host " - You can also run the app directly using the venv python executable as shown above." -ForegroundColor White

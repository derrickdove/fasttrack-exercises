# Windows PowerShell 5.1: powershell -ExecutionPolicy Bypass -File tools\run.ps1 d05
param([string]$Id)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
try {
    Set-Location -LiteralPath $root
    $sets = @(Get-ChildItem -LiteralPath (Join-Path $root 'sets') -Directory | Select-Object -ExpandProperty Name)
    $gates = @(Get-ChildItem -LiteralPath (Join-Path $root 'gates') -Directory | Where-Object { $_.Name -match '^b[1-6]$' } | Select-Object -ExpandProperty Name)
    $targets = @()
    if ($sets -contains $Id) {
        $targets = @("sets/$Id")
        Remove-Item Env:FT_REPORT_MODE -ErrorAction SilentlyContinue
    } elseif ($gates -contains $Id) {
        for ($number = 1; $number -le [int]$Id.Substring(1); $number++) {
            $target = "gates/b$number"
            if (-not (Test-Path -LiteralPath $target -PathType Container)) { throw "Missing earlier gate b$number. Get the latest sets with git pull." }
            $targets += $target
        }
        $env:FT_REPORT_MODE = 'checks'
        if (-not $env:FT_CAPSTONE) { $env:FT_CAPSTONE = Join-Path $root 'capstone' }
    } else {
        Write-Host "No set or gate named '$Id'. Choose one of these:"
        Write-Host "Sets: $($sets -join ', ')"
        Write-Host "Gates: $($gates -join ', ') (available as blocks are added)"
        exit 1
    }
    $python = Join-Path $root '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) {
        Write-Host 'Creating .venv (your local Python environment) ...'
        # FT_PYTHON may name an interpreter outside PATH. No activation is needed.
        $candidates = @()
        if ($env:FT_PYTHON) { $candidates += $env:FT_PYTHON }
        $candidates += 'py', 'python', 'python3'
        $created = $false
        foreach ($candidate in $candidates) {
            if (-not (Get-Command $candidate -ErrorAction SilentlyContinue)) { continue }
            $prefix = @()
            if ($candidate -eq 'py') { $prefix = @('-3') }
            & $candidate @prefix -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' 2>$null
            if ($LASTEXITCODE -ne 0) { continue }
            & $candidate @prefix -m venv (Join-Path $root '.venv')
            if ($LASTEXITCODE -ne 0) { throw 'Could not create .venv. Check the Python installation and folder permissions.' }
            $created = $true
            break
        }
        if (-not $created) { throw 'Python 3.12+ was not found. Install Python, enable Add Python to PATH, then reopen VS Code.' }
    }
    & $python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'This .venv needs Python 3.12+. Delete .venv and run again with Python 3.12+ installed.' }
    $requirements = Join-Path $root 'requirements.txt'
    $stamp = Join-Path $root '.venv\requirements.stamp'
    if (-not (Test-Path -LiteralPath $stamp) -or (Get-Item -LiteralPath $requirements).LastWriteTimeUtc -gt (Get-Item -LiteralPath $stamp).LastWriteTimeUtc) {
        Write-Host 'Installing the exercise tools (the first run can take a few minutes) ...'
        & $python -m pip install --disable-pip-version-check -r $requirements
        if ($LASTEXITCODE -ne 0) { throw 'The tools could not be installed. Check your internet connection, then run again.' }
        [IO.File]::WriteAllText($stamp, 'Requirements installed successfully.')
    }
    $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
    $env:PYTEST_ADDOPTS = ''
    & $python -m pytest @targets -p tools.ft_report -q --no-header --rootdir $root
    if ($LASTEXITCODE -eq 0) { exit 0 }
    exit 1
} catch {
    Write-Host $_.Exception.Message
    exit 1
}

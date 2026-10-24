$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$pythonExe = if (Test-Path .venv\Scripts\python.exe) { '.\.venv\Scripts\python.exe' } else { 'python' }
& $pythonExe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Regression tests failed.' }

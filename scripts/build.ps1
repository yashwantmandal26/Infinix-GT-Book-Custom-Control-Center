$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$pythonExe = if (Test-Path .venv\Scripts\python.exe) { '.\.venv\Scripts\python.exe' } else { 'python' }
& $pythonExe -m PyInstaller --noconfirm InfinixGTToolkit.spec
if ($LASTEXITCODE -ne 0) { throw 'EXE build failed.' }
& $pythonExe scripts\package-release.py --exe dist\InfinixGTToolkit.exe --sync-launcher
if ($LASTEXITCODE -ne 0) { throw 'Release packaging failed.' }
Write-Host 'Main launcher updated. Shareable files are in release/. Exit any running older copy before reopening.'

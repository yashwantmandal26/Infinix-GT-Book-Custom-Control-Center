$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$pythonExe = if (Test-Path .venv\Scripts\python.exe) { '.\.venv\Scripts\python.exe' } else { 'python' }
& $pythonExe -m pytest test_rear_arcade.py test_lighting_reliability.py test_app_runtime.py test_update_service.py test_keyboard_motion.py -q
if ($LASTEXITCODE -ne 0) { throw 'Focused regression tests failed.' }

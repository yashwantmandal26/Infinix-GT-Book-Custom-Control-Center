# Infinix GT Book Custom Control Center

Unofficial Windows control center for the Infinix GT Book GL613 / BYD N16.
Editable Python source and a standalone Windows executable are included in this
Desktop package. This is a community project, not an official Infinix release.

## Use the app

1. Extract the portable ZIP to a normal folder.
2. Close other lighting/control-center instances to avoid competing hardware writes.
3. Open `InfinixGTToolkit.exe` and accept the Windows administrator prompt.

The packaged EXE includes the latest local change: **Battle & Arcade · Beta is
greyed out and disabled**. Other lighting categories remain available. Saved
arcade selections migrate to Always On; arcade imports cannot activate them.
The EXE is unsigned. Python is not required to run it.

## Included features

- Four-zone keyboard lighting and rear-bar firmware/software lighting controls.
- Performance-mode and fan controls, monitoring, profiles and automation.
- GitHub release update checking with SHA-256 download verification.

Hardware behaviour has been investigated on GL613. Compatibility with other
models and every firmware revision has not been established. Arcade per-LED
choreography is unavailable; it is not advertised as working.

## Edit and build

Install 64-bit Python 3.12 and Git. In PowerShell opened in this folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-dev.ps1
.\.venv\Scripts\python.exe infinix_toolkit.py
powershell -ExecutionPolicy Bypass -File .\scripts\test.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\build.ps1
```

Run the source from an administrator terminal when using hardware controls.
Builds go to `dist/`; ready-to-share assets go to `release/`.
The root EXE is the bundled snapshot; rebuilding does not silently replace it.

## Project map

| File | Purpose |
| --- | --- |
| `infinix_toolkit.py` | App, hardware engines, version and update repository |
| `backzone_ui.py` | Rear lighting and disabled Arcade Beta section |
| `studio_ui.py`, `neon_ui.py`, `color_studio.py` | Lighting UI and colours |
| `app_runtime.py`, `hardware_runtime.py`, `automation_policy.py` | Runtime and automation |
| `update_service.py` | GitHub update discovery and installation |
| `test_*.py` | Automated checks |
| `InfinixGTToolkit.spec`, `version_info.txt` | Executable packaging |
| `assets/` | App artwork |
| `.github/workflows/release.yml` | Windows build and release workflow |

## Publish and share

See [PUBLISHING.md](PUBLISHING.md). Commit source to GitHub and distribute the
EXE/portable ZIP through **GitHub Releases**, not normal Git commits. The Desktop
project ZIP contains the bundled EXE as well as source. Neither ZIP is published
automatically by preparing this folder.

This bundled snapshot still identifies itself as **4.5.0**. Before publishing an
update for existing 4.5.0 users, bump the version and rebuild; merely renaming a
release tag will not make the update checker work correctly.

## Validation and known limitations

See [docs/VALIDATION.md](docs/VALIDATION.md). Targeted unit checks and the Beta UI
check pass; the complete suite has existing failures that are documented, not
hidden. No guarantee of every hardware feature on every GT Book is implied.

## License

Project code: [MIT](LICENSE). Third-party packages keep their own licenses; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and `third_party_licenses/`.
Infinix product names and artwork do not imply affiliation or trademark rights.

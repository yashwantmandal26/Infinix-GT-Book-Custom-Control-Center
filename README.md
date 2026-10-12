# Infinix GT Book Custom Control Center

An open-source Windows control center for the **Infinix GT Book**, built for owners who want one place to control lighting, performance, cooling, profiles, and live hardware monitoring.

[Download the latest release](https://github.com/yashwantmandal26/Infinix-GT-Book-Custom-Control-Center/releases/latest) · [Report an issue](https://github.com/yashwantmandal26/Infinix-GT-Book-Custom-Control-Center/issues) · MIT licensed

## Screenshots

### Lighting Studio

![Lighting Studio with four-zone keyboard controls](docs/images/lighting-studio.png)

### Rear Mecha Bar

![Rear Mecha Bar controls with Battle and Arcade marked as Beta](docs/images/rear-light-bar.png)

## Main features

- **Four-zone keyboard RGB** with independent colours, brightness, speed, direction, and effect controls.
- **Rear Mecha Bar control** for supported firmware, animated, audio-reactive, and system-reactive modes.
- **Performance controls** for operating modes, CPU/GPU settings, and fan behaviour.
- **Live mini monitor** for temperatures, load, memory, battery, fan, and power data.
- **Profiles and presets** with import/export support and startup automation.
- **Built-in update checks** with release manifest and SHA-256 verification.
- **Dark and light themes** in a single portable desktop application.

> **Battle & Arcade is currently Beta and disabled.** The laptop accepts OEM effects, but its custom per-LED animation protocol is not fully verified. The section is greyed out so users do not select effects that the hardware cannot reproduce correctly.

## How it is made

- **Python 3.12 + CustomTkinter** power the desktop interface.
- Keyboard lighting communicates with the GT Book's **USB HID controller (`340E:8002`)**.
- Rear lighting communicates with the internal **COM/ACPI lighting controller**.
- Performance and telemetry use the available **Windows WMI, EC, power, and sensor interfaces**.
- **PyInstaller** produces the portable Windows executable.
- **pytest and GitHub Actions** validate core behaviour and build tagged releases.

## Supported setup

- Windows 10 or Windows 11
- Infinix GT Book hardware; developed and tested primarily on **GL613 / BYD N16-class hardware**
- Administrator access for hardware controls
- Close the official Infinix Control Center before using this app, so both programs do not compete for the same controller

Hardware revisions may expose different interfaces. Use the diagnostic page when a device is not detected.

## Install and run

1. Open [Releases](https://github.com/yashwantmandal26/Infinix-GT-Book-Custom-Control-Center/releases/latest).
2. Download the portable ZIP and extract it.
3. Run `InfinixGTToolkit.exe` as administrator.

Windows may show an unsigned-app warning because this community build does not currently use a commercial code-signing certificate.

## Edit or build it yourself

```powershell
git clone https://github.com/yashwantmandal26/Infinix-GT-Book-Custom-Control-Center.git
cd Infinix-GT-Book-Custom-Control-Center
powershell -ExecutionPolicy Bypass -File .\scripts\setup-dev.ps1
.\.venv\Scripts\python.exe infinix_toolkit.py
```

Build the executable:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build.ps1
```

Run the focused verification suite:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test.ps1
```

## Project map

| Path | Purpose |
|---|---|
| `infinix_toolkit.py` | Main application, hardware engines, version, and update settings |
| `backzone_ui.py` | Rear Mecha Bar interface and its available effect categories |
| `studio_ui.py`, `neon_ui.py`, `color_studio.py` | Lighting interface and colour controls |
| `app_runtime.py`, `hardware_runtime.py`, `automation_policy.py` | Runtime and automation services |
| `test_*.py` | Automated tests and hardware-safe protocol checks |
| `scripts/` | Setup, build, test, packaging, and release helpers |
| `docs/` | Screenshots and supporting project material |
| `.github/workflows/` | Automated tagged-release build and publishing |

## Project status

- Current release: **v4.5.1**
- Focused validation: **51 tests passed, including 9 protocol subtests**
- The project is community-made and is not affiliated with Infinix
- Contributions, hardware observations, and reproducible bug reports are welcome

## License

Released under the [MIT License](LICENSE). Third-party components retain their own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

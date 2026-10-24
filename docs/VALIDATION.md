# Validation

v4.5.5 validation (13 October 2026): **121 tests and 25 subtests passed**
in the final full run (`python -m pytest -q -o faulthandler_timeout=45`).
The final run was performed after packaging completed. Earlier overlapping
build/test runs encountered intermittent local Tk initialization errors.
This includes fractional-frame continuity, loop seams, direction mirroring,
matching-color inputs, and replacement of a locked main launcher with rollback
on installation failure. Hardware animation appearance still requires user review.

`scripts/test.ps1` and the release workflow run
the complete suite, including offline UI, layout, user controls, GPU selection,
lighting, automation, runtime, and update checks.

The AC-profile test doubles now include the live-information refresh method.
The keyboard preview footer uses a single flow-layout label, so its help text
does not overlap the Undo/Redo row. The offline UI test covers both themes
and every page. Battle & Arcade remains greyed out and disabled.

The sidebar now uses a fixed frame, with smaller navigation buttons and compact
CPU/GPU/RAM/battery cards. Its laptop banner has been removed. A geometry check
verifies that every navigation button and live metric remains visible at the
minimum 1100 x 760 window size with 100%, 125%, and 150% scaling.
Navigation labels no longer repeat numeric prefixes, and the live metrics use
flat rows with thin progress bars instead of nested bordered cards.

The build command synchronizes the main-folder launcher and manifest with the
release. A mapped older EXE is preserved under `build/previous-launcher/` without
terminating the running app. Choose **Exit Toolkit** from its tray menu before
opening the updated launcher; X can leave the older instance running. The new
sidebar displays v4.5.5 to distinguish it from earlier local builds.

Profiles & settings and its preset management, import/export, sign-in and close
preference controls have been removed from the interface. The five remaining
pages use Alt+1 through Alt+5, with About on Alt+5. Old references to the removed
page fall back to Lighting studio. Existing saved configuration is retained.
About and executable metadata credit Yashwant Mandal from Jharkhand, India.

About and System monitor now use one cached sensor snapshot. Queries explicitly
filter temperature and fan sensor types; load, clock and voltage readings cannot
be displayed as temperatures. CPU/GPU/fan/SSD/ambient values remain "Not reported"
when no source exposes them. Windows thermal-zone readings appear separately as
ACPI, since a thermal zone is not necessarily a CPU-core measurement; see
[Microsoft's thermal-zone documentation](https://learn.microsoft.com/en-us/windows-hardware/drivers/devtest/pwrtest-thermal-scenario).
NVIDIA temperature queries use pointer-safe NVML declarations; see the
[NVIDIA device-query API](https://docs.nvidia.com/deploy/nvml-api/latest/api/group__nvmlDeviceQueries.html).

Read-only verification on this laptop reported 85.8% battery health, 14.2%
capacity loss, 60.1 / 70.0 Wh, 79% charge, AC connected, and approximately 45°C
for an ACPI thermal zone. CPU/GPU core temperatures and fan RPM were not exposed
by the available providers at that time. The battery-age formula was removed:
capacity loss cannot establish a manufacture date or elapsed battery age.
Reported zero cycle counts are preserved. Unavailable health and capacity clear
old cached values rather than falling back to invented percentages/capacities.
AC power does not imply fast charging. RAM uses GiB consistently in the live
readouts; memory-module capacities and device names come from WMI.

Sixteen telemetry tests cover shared snapshots, type filtering, missing/invalid
values, cache isolation, 64-bit NVML handles, battery figures, and refresh overlap.
Populated About cards fit at 1100, 1280, and 1665-pixel window widths in both
themes. The live grid uses two or four columns according to available space.

All four custom motions use continuous loops, saturated color handoffs, and a
visible ambient floor. Magnetic Slingshot crosses two ribbons; Chromatic Relay
passes a broad color crest; Time Fracture eases through a pause and rewind;
Orbital Eclipse moves a soft shadow between luminous edges. No full-keyboard
white flashes are generated. The UI descriptions match the revised motions.

Hardware tests use mocks; passing tests do not establish physical compatibility
with every hardware revision. Runtime configuration is not bundled.


### Sidebar refresh — 4.5.6

Replaced neon sidebar surfaces with flat navigation, a muted blue active state, a compact GT brand mark and a grouped system overview directly beneath navigation. Removed redundant CPU/GPU/RAM emoji and the large gap above metrics. Fixed sidebar remains scroll-free. Existing geometry checks cover minimum window size and 100%, 125%, and 150% scaling. Full suite: 121 tests and 25 subtests passed.

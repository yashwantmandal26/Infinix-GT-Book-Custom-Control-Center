# Validation

The included Arcade Beta change passed 47 focused tests plus 9 subtests across
`test_rear_arcade.py`, `test_lighting_reliability.py`, and `test_app_runtime.py`.
The updated `test_control_center.py::ControlCenterTests::test_offline_ui` passed
separately and its screenshot was inspected: the Beta tab is grey and disabled.

The broad control-center suite has three previously observed failures:
- Two AC-profile test doubles lack `_about_refresh_live`.
- The layout test failed loading Tk's menu.tcl in the local test environment.

The focused CI command is deliberately scoped; it is not a claim that the full
suite passes. Run `python -m pytest -q` to inspect the complete suite.
Hardware tests use mocks; the bundle was not revalidated for every physical
feature on other machines. Runtime configuration is not bundled.

Standalone Desktop package verification: 50 tests and 9 subtests passed using
`scripts/test.ps1` (also includes update-service tests). EXE hash matched the
latest dist-arcade-beta build. Release ZIP and project ZIP integrity checked.

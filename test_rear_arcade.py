"""Regression coverage for arcade dispatch; no real hardware writes."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import backzone_ui
import infinix_toolkit as toolkit


def make_app(mode):
    app = SimpleNamespace(
        bz_mode=mode, bz_color1=(35, 232, 0), bz_color2=(255, 0, 120),
        bz_brightness=75, bz_speed=4, running=True,
        _suspended=False, _rear_test_active=False,
        _backzone_allowed=lambda: True,
        _ui_dispatch=lambda *args: None, _set_hardware_status=lambda *args: None,
    )
    app._apply_backzone_hardware = lambda: toolkit.InfinixGTToolkitApp._apply_backzone_hardware(app)
    return app


@pytest.mark.parametrize("mode", range(201, 211))
def test_saved_arcade_selection_uses_safe_static_mode(mode):
    app = make_app(mode)
    with patch.object(toolkit.SerialEngine, "send_backzone_rgb", return_value=True) as send, \
         patch.object(toolkit, "render_backzone_effect", side_effect=AssertionError("Must not average LEDs")):
        assert app._apply_backzone_hardware()
    args = send.call_args.kwargs
    assert args["effect"] == 1
    assert app.bz_mode == 1
    assert (args["r1"], args["g1"], args["b1"]) == app.bz_color1
    assert (args["r2"], args["g2"], args["b2"]) == app.bz_color2
    assert args["bright"] == args["bright2"] == 75


def test_arcade_power_rule_still_sends_off():
    app = make_app(202)
    app._backzone_allowed = lambda: False
    with patch.object(toolkit.SerialEngine, "send_backzone_rgb", return_value=True) as send:
        assert app._apply_backzone_hardware()
    assert send.call_args.kwargs["effect"] == 15


def test_worker_does_not_restart_motion_and_retries_failed_changes():
    app = make_app(6)
    ticks = 0

    def sleep(_seconds):
        nonlocal ticks
        ticks += 1
        if ticks == 3:
            app.bz_color2 = (0, 30, 255)
        if ticks == 6:
            app.running = False

    def thread(*, target, daemon):
        return SimpleNamespace(start=target)

    with patch.object(toolkit.threading, "Thread", side_effect=thread), \
         patch.object(toolkit.time, "sleep", side_effect=sleep), \
         patch.object(toolkit.SerialEngine, "send_backzone_rgb", side_effect=[True, False, True]) as send, \
         patch.object(toolkit, "render_backzone_effect", side_effect=AssertionError("Must not average LEDs")):
        toolkit.InfinixGTToolkitApp._start_backzone_effects_worker(app)
    assert send.call_count == 3
    assert all(c.kwargs["effect"] == 6 for c in send.call_args_list)
    assert send.call_args_list[-1].kwargs["b2"] == 255


@pytest.mark.parametrize("mode", range(201, 211))
def test_beta_cannot_be_selected_or_imported(mode):
    app = make_app(6)
    view = SimpleNamespace(app=app, current_category="Firmware")
    backzone_ui.BackZoneView._select_mode(view, mode)
    backzone_ui.BackZoneView._on_dropdown_mode_selected(view, backzone_ui.BACKZONE_MODE_NAMES[mode])
    backzone_ui.BackZoneView._select_category(view, "Battle & Arcade")
    assert app.bz_mode == 6
    assert view.current_category == "Firmware"
    with pytest.raises(ValueError, match="Beta"):
        backzone_ui.BackZoneView._apply_preset(view, {
            "mode": mode, "color1": [255, 0, 0], "color2": [0, 0, 255],
            "brightness": 80, "speed": 4,
        })
    assert app.bz_mode == 6

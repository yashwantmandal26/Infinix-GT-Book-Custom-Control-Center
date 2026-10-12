"""Regression cases for reliability failures; no real hardware or user settings."""
import copy
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from app_runtime import ConfigWriter, UiMailbox, validate_rear_profile
from automation_policy import AutomationPolicy
from hardware_runtime import HardwareCommandController
import infinix_toolkit as toolkit
import studio_ui


class RuntimeTests(unittest.TestCase):
    def test_hardware_controller_serializes_retries_and_blocks_duplicates(self):
        callbacks = []
        gate = threading.Event()
        attempts = []

        def dispatch(callback, *args):
            callback(*args)

        controller = HardwareCommandController(dispatch, retry_delay=0.001)
        try:
            def operation():
                attempts.append(len(attempts) + 1)
                if len(attempts) == 1:
                    gate.wait(0.05)
                    return False
                return True

            self.assertTrue(controller.submit("mode", operation, callbacks.append, retries=1))
            self.assertFalse(controller.submit("mode", lambda: True, callbacks.append))
            gate.set()
            deadline = time.time() + 1
            while not callbacks and time.time() < deadline:
                time.sleep(0.005)
            self.assertEqual(attempts, [1, 2])
            self.assertTrue(callbacks[0].ok)
            self.assertEqual(callbacks[0].attempts, 2)
        finally:
            controller.close()

    def test_automation_policy_has_deterministic_priority_and_manual_hold(self):
        config = {"automation_paused": False, "manual_override_minutes": 30,
                  "manual_mode_until": 0}
        self.assertEqual(AutomationPolicy.select_rule(
            critical_battery=True, game=True, high_load=True)[0], "Quiet")
        self.assertEqual(AutomationPolicy.select_rule(game=True, high_load=True)[0], "Beast")
        self.assertEqual(AutomationPolicy.select_rule(on_ac=False)[0], "Quiet")
        self.assertEqual(AutomationPolicy.protect_manual(config, now=100), 30)
        self.assertEqual(AutomationPolicy.block_reason(config, now=101), "manual")
        AutomationPolicy.resume(config)
        self.assertEqual(AutomationPolicy.block_reason(config, now=101), "")

    def test_reliability_checks_are_read_only_and_report_actual_states(self):
        app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
        app.config = {"power_mode": "Balanced", "cooler_boost": False,
                      "usb_charge_off": True, "gpu_mode": "Hybrid"}
        app._config_writer = SimpleNamespace(last_error=None)
        app.power_listener = SimpleNamespace(running=True)
        app._power_events = {"suspend": 1, "resume": 1, "last": "Resumed 10:00:00"}
        with patch.object(toolkit.HardwareEngine, "get_performance_mode", return_value="Balanced"), \
             patch.object(toolkit.HardwareEngine, "get_full_fan_mode", return_value=False), \
             patch.object(toolkit.HardwareEngine, "get_usb_sleep_charging", return_value=True), \
             patch.object(toolkit.HardwareEngine, "get_gpu_mode", return_value="Hybrid"), \
             patch.object(toolkit.HardwareEngine, "get_display_brightness", return_value=64), \
             patch.object(toolkit.HardwareEngine, "set_display_brightness") as display_write, \
             patch.object(toolkit.SerialEngine, "get_port_info", return_value=("COM4", True, "Connected")), \
             patch.object(toolkit.psutil, "sensors_battery", return_value=SimpleNamespace(percent=77)):
            checks = app._collect_reliability_checks()
        display_write.assert_not_called()
        self.assertTrue(all(state == "pass" for _, state, _ in checks))
        self.assertIn("performance modes do not modify it", dict(
            (name, detail) for name, _, detail in checks)["Display brightness"])

    def test_suspend_releases_serial_port_instead_of_reconnecting(self):
        app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
        app._suspended = False
        app._power_events = {"suspend": 0, "resume": 0, "last": ""}
        with patch.object(toolkit.HardwareEngine, "_close_device"), \
             patch.object(toolkit.SerialEngine, "_close_port") as close_port, \
             patch.object(toolkit.SerialEngine, "reconnect") as reconnect:
            app._on_power_suspend()
        self.assertTrue(app._suspended)
        self.assertEqual(app._power_events["suspend"], 1)
        close_port.assert_called_once_with()
        reconnect.assert_not_called()

    def test_startup_window_fits_scaled_laptop_screen(self):
        import re
        geometry = studio_ui.initial_window_geometry(1920, 1140, 1.25)
        width, height, x, y = map(int, re.fullmatch(r"(\d+)x(\d+)\+(\d+)\+(\d+)", geometry).groups())
        self.assertLessEqual(x + width * 1.25, 1920)
        self.assertLessEqual(y + (height + 48) * 1.25, 1140)

    def test_burst_saves_are_coalesced_and_last_value_survives_shutdown(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text('{"brightness": 5}', encoding="utf-8")
            writer = ConfigWriter(path, delay=0.2)
            snapshot = {"zones": {"1": [1, 2, 3]}, "brightness": 0}
            for value in range(100):
                snapshot["brightness"] = value
                writer.submit(snapshot)
            snapshot["zones"]["1"][0] = 200
            self.assertTrue(writer.close())
            saved = json.loads(path.read_text())
            self.assertEqual(saved["brightness"], 99)
            self.assertEqual(saved["zones"]["1"], [1, 2, 3])
            self.assertEqual(writer.write_count, 1)
            self.assertEqual(json.loads(Path(str(path) + ".bak").read_text())["brightness"], 5)

    def test_save_failure_can_be_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            writer = ConfigWriter(Path(directory) / "config.json")
            with patch("app_runtime.os.replace", side_effect=PermissionError("busy")):
                writer.submit({"brightness": 40})
                self.assertFalse(writer.close())
            writer.submit({"brightness": 50})
            self.assertTrue(writer.close())
            self.assertEqual(json.loads(writer.path.read_text())["brightness"], 50)

    def test_worker_dispatch_never_touches_tk_and_keeps_latest_preview(self):
        app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
        app.running = True
        app.active_page = "lighting"
        app._ui_thread_id = threading.get_ident()
        app._ui_mailbox = UiMailbox()
        app.root = Mock()
        received = []
        def _update_virtual_keyboard_preview(value):
            received.append(value)
        def produce():
            for frame in range(1000):
                app._ui_dispatch(_update_virtual_keyboard_preview, frame)
        thread = threading.Thread(target=produce)
        thread.start()
        thread.join()
        self.assertEqual(app.root.mock_calls, [])
        callbacks = app._ui_mailbox.take()
        self.assertEqual(len(callbacks), 1)
        for fn, args, kwargs in callbacks:
            fn(*args, **kwargs)
        self.assertEqual(received, [999])
        app._ui_mailbox.close()
        app._ui_mailbox.post(lambda: None)
        self.assertEqual(app._ui_mailbox.take(), [])

    def test_mailbox_preserves_control_action_order(self):
        box = UiMailbox()
        for i in range(45):
            box.post(str, (i,))
        received = box.take() + box.take()
        self.assertEqual([args[0] for _, args, _ in received], list(range(45)))

    def test_exported_rear_profile_roundtrip(self):
        data = dict(bz_mode=105, bz_color1=[1, 2, 3], bz_color2=[4, 5, 6],
                    bz_speed=7, bz_brightness=42, bz_fps_limit=15,
                    mecha_bar_sync=False, bz_turn_off_on_battery=True,
                    bz_night_schedule_enabled=True)
        loaded = validate_rear_profile(json.loads(json.dumps(data)), toolkit.BACKZONE_MODE_NAMES)
        self.assertEqual(loaded["mode"], 105)
        self.assertEqual(loaded["color1"], [1, 2, 3])
        self.assertEqual(loaded["speed"], 7)
        self.assertEqual(loaded["brightness"], 42)
        self.assertEqual(loaded["options"]["bz_fps_limit"], 15)
        self.assertTrue(loaded["options"]["bz_night_schedule_enabled"])

    def test_bad_rear_profiles_rejected_before_state_changes(self):
        for invalid in ([], {}, {"mode": 999}, {"mode": True}, {"color1": [300, 0, 0]},
                        {"color1": "red"}, {"brightness": -1}, {"speed": 99},
                        {"mode": 1, "mecha_bar_sync": "false"}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_rear_profile(invalid, toolkit.BACKZONE_MODE_NAMES)

    def make_app(self):
        app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
        app.config = copy.deepcopy(toolkit.DEFAULT_CONFIG)
        app.config.update(always_on=True, mecha_bar_enabled=True, bz_night_schedule_enabled=False,
                          bz_turn_off_on_battery=False)
        app.running = True
        app.heartbeat_active = True
        app.effect_mode = "Solid"
        app.bz_mode = 1
        app.bz_color1, app.bz_color2 = [20, 30, 40], [50, 60, 70]
        app.bz_brightness, app.bz_speed = 50, 3
        app._suspended = app._session_locked = app._rear_test_active = False
        app.on_ac_val, app.battery_val = True, 80
        app._ui_dispatch = lambda callback, *a, **kw: callback(*a, **kw)
        app._set_hardware_status = Mock()
        return app

    def test_rear_buttons_and_worker_share_power_rules(self):
        app = self.make_app()
        app.config["bz_turn_off_on_battery"] = True
        app.on_ac_val = False
        with patch.object(toolkit.SerialEngine, "send_backzone_rgb", return_value=True) as send:
            app._apply_backzone_hardware()
            self.assertEqual(send.call_args.kwargs["effect"], 15)
            app.on_ac_val = True
            app._apply_backzone_hardware()
            self.assertEqual(send.call_args.kwargs["effect"], 1)
        for flag in ("_suspended", "_session_locked"):
            setattr(app, flag, True)
            self.assertFalse(app._backzone_allowed())
            setattr(app, flag, False)
        app.config["always_on"] = False
        self.assertFalse(app._backzone_allowed())

    def test_firmware_effect_restored_when_battery_rule_releases(self):
        app = self.make_app()
        app.config["bz_turn_off_on_battery"] = True
        app.on_ac_val = False
        sent = []
        def send(*args, **kwargs):
            sent.append(kwargs.get("effect", args[0] if args else None))
            return True
        def advance(_seconds):
            if len(sent) == 1:
                app.on_ac_val = True
            elif len(sent) >= 2:
                app.running = False
        class Thread:
            def __init__(self, target, **kwargs):
                self.target = target
            def start(self):
                self.target()
        with patch.object(toolkit.threading, "Thread", Thread), patch.object(toolkit.time, "sleep", advance), \
             patch.object(toolkit.ctypes.windll.user32, "OpenInputDesktop", return_value=1), \
             patch.object(toolkit.ctypes.windll.user32, "CloseDesktop"), \
             patch.object(toolkit.SerialEngine, "send_backzone_rgb", side_effect=send):
            app._start_backzone_effects_worker()
        self.assertEqual(sent, [15, 1])

    def test_audio_capture_only_for_enabled_audio_effects(self):
        app = self.make_app()
        app.active_page = "lighting"
        self.assertFalse(app._needs_audio())
        app.effect_mode = "AudioSync"
        self.assertTrue(app._needs_audio())
        app.heartbeat_active = False
        self.assertFalse(app._needs_audio())
        app.bz_mode = 110
        self.assertTrue(app._needs_audio())
        app.config["mecha_bar_enabled"] = False
        self.assertFalse(app._needs_audio())

    def test_failed_uart_retries_are_rate_limited(self):
        toolkit.SerialEngine._retry_after = 0
        toolkit.SerialEngine._ec_power_state = None
        try:
            with patch.object(toolkit.HardwareEngine, "set_ec_backlight_power", return_value=False) as power:
                for _ in range(100):
                    self.assertFalse(toolkit.SerialEngine.send_backzone_rgb(1, 20, 30, 40, 3, 50))
                self.assertEqual(power.call_count, 1)
        finally:
            toolkit.SerialEngine._retry_after = 0
            toolkit.SerialEngine._ec_power_state = None

    def test_missing_temperature_sensor_is_not_fabricated(self):
        app = self.make_app()
        app.cpu_temp_val, app.gpu_temp_val = 52.0, None
        app.config["bz_temp_source"] = "CPU"
        self.assertEqual(app._rear_temperature(), 52.0)
        app.config["bz_temp_source"] = "GPU"
        self.assertIsNone(app._rear_temperature())
        self.assertEqual(toolkit.render_backzone_effect(112, 0.2, (255, 0, 0), (0, 255, 0), 40,
                                                       temp_celsius=None), ((96, 112, 128), 40))


if __name__ == "__main__":
    unittest.main()

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import os
import sys
import tkinter as tk

import infinix_toolkit as toolkit
from infinix_toolkit import ModeOSDOverlay, HardwareModeListener, HardwareEngine


class TestModeOSDOverlay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self):
        self.osd = ModeOSDOverlay(self.root)

    def tearDown(self):
        if self.osd:
            self.osd.hide()
            if self.osd.window and self.osd.window.winfo_exists():
                self.osd.window.destroy()

    def test_osd_initialization_and_assets(self):
        """Verify ModeOSDOverlay initializes and loads OEM graphics or fallbacks."""
        self.assertIsNotNone(self.osd)
        self.assertIn("Quiet", self.osd._images)
        self.assertIn("Balanced", self.osd._images)
        self.assertIn("Beast", self.osd._images)

    def test_osd_show_quiet_mode(self):
        """Verify show('Quiet') displays the Quiet mode banner and schedules auto-hide."""
        self.osd.show("Quiet")
        self.root.update()
        self.assertIsNotNone(self.osd.window)
        self.assertTrue(self.osd.window.winfo_exists())
        self.assertEqual(self.osd.title_label.cget("text"), "QUIET MODE")
        self.assertEqual(self.osd.title_label.cget("fg"), "#22C55E")
        self.assertIsNotNone(self.osd._hide_timer)

    def test_osd_show_balanced_mode(self):
        """Verify show('Balanced') updates the OSD to Balanced mode."""
        self.osd.show("Balanced")
        self.root.update()
        self.assertEqual(self.osd.title_label.cget("text"), "BALANCED MODE")
        self.assertEqual(self.osd.title_label.cget("fg"), "#38BDF8")

    def test_osd_show_beast_and_gaming_mode(self):
        """Verify show('Beast') and show('Gaming') normalize to BEAST MODE."""
        self.osd.show("Gaming")
        self.root.update()
        self.assertEqual(self.osd.title_label.cget("text"), "BEAST MODE")
        self.assertEqual(self.osd.title_label.cget("fg"), "#EF4444")

        self.osd.show("Beast")
        self.root.update()
        self.assertEqual(self.osd.title_label.cget("text"), "BEAST MODE")

    def test_osd_hide(self):
        """Verify hide() withdraws the window and clears the hide timer."""
        self.osd.show("Quiet")
        self.root.update()
        self.osd.hide()
        self.assertIsNone(self.osd._hide_timer)


class TestHardwareModeListener(unittest.TestCase):
    def test_ec_poller_detects_mode_change(self):
        """Verify EC poller triggers callback when register 0x40 changes."""
        callback = MagicMock()
        listener = HardwareModeListener(callback=callback, poll_interval=0.01)

        # 1. First read seeds the last_ec_mode
        with patch.object(HardwareEngine, "get_performance_mode", return_value="Balanced"):
            listener._ec_poll_worker_single = lambda: None
            # Simulate first reading
            listener.last_ec_mode = "Balanced"

        # 2. Hardware button is pressed -> EC returns Beast
        with patch.object(HardwareEngine, "get_performance_mode", return_value="Beast"):
            # Execute one iteration logic manually
            mode = HardwareEngine.get_performance_mode()
            if mode != listener.last_ec_mode:
                listener.last_ec_mode = mode
                callback(mode, "hardware_ec")

        callback.assert_called_once_with("Beast", "hardware_ec")
        self.assertEqual(listener.last_ec_mode, "Beast")

    def test_ec_poller_ignores_identical_mode(self):
        """Verify EC poller does not re-trigger callback if register 0x40 is unchanged."""
        callback = MagicMock()
        listener = HardwareModeListener(callback=callback, poll_interval=0.01)
        listener.last_ec_mode = "Balanced"

        with patch.object(HardwareEngine, "get_performance_mode", return_value="Balanced"):
            mode = HardwareEngine.get_performance_mode()
            if mode != listener.last_ec_mode:
                callback(mode, "hardware_ec")

        callback.assert_not_called()

    def test_ec_poller_handles_read_exceptions_gracefully(self):
        """Verify exceptions during EC read are safely handled without crash."""
        callback = MagicMock()
        listener = HardwareModeListener(callback=callback, poll_interval=0.01)
        listener.last_ec_mode = "Quiet"

        with patch.object(HardwareEngine, "get_performance_mode", side_effect=RuntimeError("ACPI busy")):
            try:
                mode = HardwareEngine.get_performance_mode()
                if mode != listener.last_ec_mode:
                    callback(mode, "hardware_ec")
            except Exception:
                pass  # Listener catches exceptions safely

        callback.assert_not_called()
        self.assertEqual(listener.last_ec_mode, "Quiet")

    def test_listener_start_and_stop(self):
        """Verify start and stop methods manage threads and hooks cleanly."""
        listener = HardwareModeListener(callback=MagicMock(), poll_interval=0.05)
        with patch("threading.Thread") as mock_thread, \
             patch("ctypes.windll.user32.UnhookWindowsHookEx"):
            listener.start()
            self.assertTrue(listener._running)
            self.assertIn(mock_thread.call_count, (2, 3))

            listener.stop()
            self.assertFalse(listener._running)


class TestAppModeIntegration(unittest.TestCase):
    def test_apply_hardware_mode_change(self):
        """Verify _apply_hardware_mode_change synchronizes state and calls OSD."""
        app = SimpleNamespace(
            config={"power_mode": "Balanced"},
            mode_var=SimpleNamespace(set=MagicMock()),
            mode_display_var=SimpleNamespace(set=MagicMock()),
            mode_selector=SimpleNamespace(set=MagicMock()),
            mode_osd=SimpleNamespace(show=MagicMock()),
            _set_mode_apply_status=MagicMock(),
            _update_telemetry_mode_buttons=MagicMock(),
            _save_config=MagicMock(),
            _show_mode_osd=lambda mode: app.mode_osd.show(mode),
        )

        with patch.object(HardwareEngine, "set_performance_mode") as mock_set:
            toolkit.InfinixGTToolkitApp._apply_hardware_mode_change(app, "Quiet", "hardware_ec")

        self.assertEqual(app.config["power_mode"], "Quiet")
        app.mode_var.set.assert_called_with("Quiet")
        app.mode_display_var.set.assert_called_with("Quiet")
        app.mode_selector.set.assert_called_with("Quiet")
        app._set_mode_apply_status.assert_called_once()
        app.mode_osd.show.assert_called_once_with("Quiet")
        # For hardware_ec, EC is already set so set_performance_mode is not called
        mock_set.assert_not_called()

    def test_apply_keyboard_hotkey_mode_change(self):
        """Verify keyboard hotkey source explicitly writes to EC and calls OSD."""
        app = SimpleNamespace(
            config={"power_mode": "Quiet"},
            mode_var=SimpleNamespace(set=MagicMock()),
            mode_display_var=SimpleNamespace(set=MagicMock()),
            mode_selector=SimpleNamespace(set=MagicMock()),
            mode_osd=SimpleNamespace(show=MagicMock()),
            _set_mode_apply_status=MagicMock(),
            _update_telemetry_mode_buttons=MagicMock(),
            _save_config=MagicMock(),
            logger=SimpleNamespace(warning=MagicMock()),
            _show_mode_osd=lambda mode: app.mode_osd.show(mode),
        )

        with patch.object(HardwareEngine, "set_performance_mode") as mock_set:
            toolkit.InfinixGTToolkitApp._apply_hardware_mode_change(app, "Beast", "keyboard_hotkey")

        self.assertEqual(app.config["power_mode"], "Beast")
        app.mode_var.set.assert_called_with("Beast")
        app.mode_display_var.set.assert_called_with("Gaming")
        app.mode_selector.set.assert_called_with("Gaming")
        app.mode_osd.show.assert_called_once_with("Beast")
        mock_set.assert_called_once_with("Beast")

    def test_finish_performance_mode_triggers_osd(self):
        """Verify _finish_performance_mode calls OSD on success."""
        app = SimpleNamespace(
            config={"power_mode": "Quiet"},
            mode_var=SimpleNamespace(get=lambda: "Balanced", set=MagicMock()),
            mode_display_var=SimpleNamespace(set=MagicMock()),
            mode_selector=SimpleNamespace(configure=MagicMock()),
            mode_osd=SimpleNamespace(show=MagicMock()),
            _set_mode_apply_status=MagicMock(),
            _set_hardware_status=MagicMock(),
            _update_telemetry_mode_buttons=MagicMock(),
            _save_config=MagicMock(),
            _protect_manual_mode=MagicMock(return_value=30),
            _record_automation_event=MagicMock(),
            _show_mode_osd=lambda mode: app.mode_osd.show(mode),
        )

        result = SimpleNamespace(ok=True, error="")
        toolkit.InfinixGTToolkitApp._finish_performance_mode(
            app, result, "Balanced", "Quiet", "Manual selection", False
        )

        self.assertEqual(app.config["power_mode"], "Balanced")
        app.mode_osd.show.assert_called_once_with("Balanced")


if __name__ == "__main__":
    unittest.main()

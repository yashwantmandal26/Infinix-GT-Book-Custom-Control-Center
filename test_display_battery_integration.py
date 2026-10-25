"""Unit and integration tests for Phase 2: Display Refresh Rate & Battery Intelligence in InfinixGTToolkitApp."""
import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

import infinix_toolkit as toolkit
import display_battery_engine


class DisplayBatteryIntegrationTests(unittest.TestCase):

    def setUp(self):
        self.app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
        self.app.config = {
            "auto_refresh_rate_on_battery": True,
            "battery_charge_alert_80": True,
            "target_refresh_rate_ac": 120,
            "target_refresh_rate_battery": 60,
            "auto_switch_on_ac": True,
        }
        self.app._current_refresh_rate = 120
        self.app._supported_refresh_rates = [60, 120]
        self.app._bat_alert_80_fired = False
        self.app._last_battery_watts = 0.0

        # UI mock references
        self.app.rf_live_badge = MagicMock(winfo_exists=lambda: True)
        self.app.rf_mode_var = MagicMock()
        self.app.bat_stat_lbl = MagicMock(winfo_exists=lambda: True)
        self.app.bat_bar = MagicMock(winfo_exists=lambda: True)
        self.app.telemetry_bat_sub_lbl = MagicMock(winfo_exists=lambda: True)
        self.app.side_bat_lbl = MagicMock(winfo_exists=lambda: True)
        self.app.mode_var = MagicMock()
        self.app.cpu_temp_val = 50.0
        self.app.gpu_temp_val = 55.0

        # Helper mocks
        self.app._save_config = MagicMock()
        self.app._show_windows_toast = MagicMock()
        self.app._about_refresh_live = MagicMock()
        self.app._automatic_mode_change_blocked = MagicMock(return_value=False)
        self.app._on_mode_selected = MagicMock()
        self.app._refresh_automation_status = MagicMock()
        self.app._compute_live_system_status = MagicMock(return_value=("LIVE", "#22C55E", "Optimal"))
        self.app._ui_dispatch = lambda func, *args, **kwargs: func(*args, **kwargs)

    def test_on_refresh_rate_changed_manual(self):
        """User selecting 60 Hz on the segmented button updates display and UI badge."""
        with patch.object(display_battery_engine.DisplayRefreshEngine, "set_refresh_rate", return_value=True) as mock_set:
            self.app._on_refresh_rate_changed("60 Hz")
            mock_set.assert_called_once_with(60, persistent=True)
            self.assertEqual(self.app._current_refresh_rate, 60)
            self.app.rf_live_badge.configure.assert_called()
            badge_text = self.app.rf_live_badge.configure.call_args.kwargs["text"]
            self.assertIn("60 Hz", badge_text)
            self.app.rf_mode_var.set.assert_called_with("60 Hz")

    def test_ac_connected_auto_refresh_rate(self):
        """Plugging in AC should auto-switch refresh rate to 120Hz if configured."""
        self.app._current_refresh_rate = 60
        with patch.object(self.app, "_set_display_refresh_rate") as mock_set:
            self.app._on_ac_connected()
            mock_set.assert_called_once_with(120, silent=True)
            self.assertFalse(self.app._bat_alert_80_fired)
            self.app.mode_var.set.assert_called_with("Beast")

    def test_battery_disconnected_auto_refresh_rate(self):
        """Unplugging AC should auto-switch refresh rate to 60Hz to conserve power."""
        self.app._current_refresh_rate = 120
        with patch.object(self.app, "_set_display_refresh_rate") as mock_set:
            self.app._on_battery_disconnected()
            mock_set.assert_called_once_with(60, silent=True)
            self.assertFalse(self.app._bat_alert_80_fired)
            self.app.mode_var.set.assert_called_with("Quiet")

    def test_auto_refresh_rate_toggle_saves_config(self):
        """Toggling auto refresh rate option updates config and calls save."""
        self.app.auto_rf_var = SimpleNamespace(get=lambda: False)
        self.app._on_auto_rf_toggled()
        self.assertFalse(self.app.config["auto_refresh_rate_on_battery"])
        self.app._save_config.assert_called_once()

    def test_battery_alert_80_toggle_saves_config(self):
        """Toggling 80% charge alert option updates config and calls save."""
        self.app.alert_80_var = SimpleNamespace(get=lambda: False)
        self.app._on_alert_80_toggled()
        self.assertFalse(self.app.config["battery_charge_alert_80"])
        self.app._save_config.assert_called_once()

    def test_telemetry_ui_displays_wattage_formatting(self):
        """_update_telemetry_ui accurately presents live wattage and battery metrics."""
        self.app._last_battery_watts = 25.4
        self.app._update_telemetry_ui(
            cpu_p=15.0, ram_p=30.0, ram_used_gb=6.0, ram_total_gb=16.0,
            bat_pct=75, on_ac=True
        )
        self.app.bat_stat_lbl.configure.assert_called()
        bat_lbl_text = self.app.bat_stat_lbl.configure.call_args.kwargs["text"]
        self.assertIn("Charging @ 25.4W", bat_lbl_text)
        self.assertIn("75%", bat_lbl_text)

        # Discharge scenario
        self.app._last_battery_watts = -16.2
        self.app._update_telemetry_ui(
            cpu_p=15.0, ram_p=30.0, ram_used_gb=6.0, ram_total_gb=16.0,
            bat_pct=50, on_ac=False
        )
        bat_lbl_text = self.app.bat_stat_lbl.configure.call_args.kwargs["text"]
        self.assertIn("Discharging @ 16.2W", bat_lbl_text)
        self.assertIn("50%", bat_lbl_text)


if __name__ == "__main__":
    unittest.main()

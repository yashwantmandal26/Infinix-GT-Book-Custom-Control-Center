"""Unit & integration tests for Phase 3 Game Automation & In-Game HUD integration in InfinixGTToolkitApp."""
import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

import infinix_toolkit as toolkit
import game_automation_engine


class GameAutomationIntegrationTests(unittest.TestCase):

    def setUp(self):
        self.app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
        self.app.config = {
            "ai_game_detector": True,
            "hud_overlay_enabled": True,
            "game_profiles": [],
            "gpu_gaming_alert": False,
        }
        self.app.game_governor = game_automation_engine.GameAutomationGovernor()
        self.app.hud_overlay = MagicMock()
        self.app.hud_overlay.is_visible = False

        # UI mocks
        self.app.mode_var = MagicMock()
        self.app.winlock_var = MagicMock()
        self.app.always_on_var = MagicMock()
        self.app.active_game_chip = MagicMock(winfo_exists=lambda: True)
        self.app._on_mode_selected = MagicMock()
        self.app._on_fan_control_mode_changed = MagicMock()
        self.app._set_display_refresh_rate = MagicMock()
        self.app._on_winlock_toggled = MagicMock()
        self.app._on_always_on_toggled = MagicMock()
        self.app._save_config = MagicMock()
        self.app._automatic_mode_change_blocked = MagicMock(return_value=False)

    def test_on_game_launched_full_activation(self):
        """Game launch triggers Beast mode, Aggressive fan, 120Hz, Win-Lock and HUD."""
        profile = game_automation_engine.GameProfile(
            exe_name="cyberpunk2077.exe",
            display_name="Cyberpunk 2077",
            power_mode="Beast",
            fan_profile="Aggressive",
            target_refresh_rate=120,
            winlock=True,
            auto_hud=True
        )
        transition_data = {
            "profile": profile,
            "target_power_mode": "Beast",
            "target_fan_mode": "Aggressive",
            "target_refresh_rate": 120,
            "winlock": True,
            "auto_hud": True,
        }

        self.app._on_game_launched(transition_data)

        self.app.mode_var.set.assert_called_with("Gaming")
        self.app._on_fan_control_mode_changed.assert_called_with("Aggressive")
        self.app._set_display_refresh_rate.assert_called_with(120, silent=True)
        self.app.winlock_var.set.assert_called_with(True)
        self.app.hud_overlay.show.assert_called_once()
        self.app.active_game_chip.configure.assert_called()
        chip_text = self.app.active_game_chip.configure.call_args.kwargs["text"]
        self.assertIn("Cyberpunk 2077", chip_text)

    def test_on_game_closed_full_restoration(self):
        """Game exit cleanly restores pre-game power mode, fan curve, refresh rate, and hides HUD."""
        exit_data = {
            "restore_state": {
                "power_mode": "Quiet",
                "fan_mode": "curve_balanced",
                "refresh_rate": 60,
                "winlock": False,
                "bz_mode": 1
            }
        }

        self.app._on_game_closed(exit_data)

        self.app.mode_var.set.assert_called_with("Quiet")
        self.app._on_fan_control_mode_changed.assert_called_with("curve_balanced")
        self.app._set_display_refresh_rate.assert_called_with(60, silent=True)
        self.app.winlock_var.set.assert_called_with(False)
        self.app.hud_overlay.hide.assert_called_once()
        self.app.active_game_chip.configure.assert_called()
        chip_text = self.app.active_game_chip.configure.call_args.kwargs["text"]
        self.assertIn("Monitoring", chip_text)

    def test_hud_overlay_toggle_and_test_button(self):
        """Toggling test HUD calls toggle_visibility and feeds current telemetry."""
        self.app.hud_overlay.is_visible = True
        self.app.cpu_temp_val = 66.0
        self.app.gpu_temp_val = 60.0
        self.app.fan_rpm_val = 3700
        self.app.battery_val = 80
        self.app.on_ac_val = True
        self.app.mode_var.get = lambda: "Balanced"
        self.app._current_refresh_rate = 120
        self.app._last_battery_watts = 25.0

        self.app._toggle_test_hud()

        self.app.hud_overlay.toggle_visibility.assert_called_once()
        self.app.hud_overlay.update_telemetry.assert_called_once()

    def test_on_ai_game_and_hud_toggled_save_config(self):
        """Toggling AI game sensing and HUD switches updates config and calls save."""
        self.app.ai_game_var = SimpleNamespace(get=lambda: False)
        self.app._on_ai_game_toggled()
        self.assertFalse(self.app.config["ai_game_detector"])
        self.app._save_config.assert_called()

        self.app.hud_switch_var = SimpleNamespace(get=lambda: False)
        self.app._on_hud_overlay_toggled()
        self.assertFalse(self.app.config["hud_overlay_enabled"])
        self.app.hud_overlay.hide.assert_called_once()


if __name__ == "__main__":
    unittest.main()

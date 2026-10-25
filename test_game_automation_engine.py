"""Unit tests for Game Automation Engine & In-Game Floating HUD."""
import unittest
from unittest.mock import MagicMock, patch
import tkinter as tk

from game_automation_engine import (
    GameProfile,
    GameAutomationGovernor,
    InGameHUDOverlay,
    DEFAULT_KNOWN_GAMES
)


class GameAutomationEngineTests(unittest.TestCase):

    def test_game_profile_serialization(self):
        """GameProfile correctly serializes to and from dictionary."""
        prof = GameProfile(
            exe_name="witcher3.exe",
            display_name="The Witcher 3",
            power_mode="Beast",
            fan_profile="Aggressive",
            target_refresh_rate=120,
            winlock=True,
            auto_hud=True
        )
        d = prof.to_dict()
        self.assertEqual(d["exe_name"], "witcher3.exe")
        self.assertEqual(d["power_mode"], "Beast")

        reconstructed = GameProfile.from_dict(d)
        self.assertEqual(reconstructed.exe_name, "witcher3.exe")
        self.assertEqual(reconstructed.display_name, "The Witcher 3")
        self.assertEqual(reconstructed.target_refresh_rate, 120)

    def test_governor_crud_and_defaults(self):
        """Governor initializes with built-in titles and supports CRUD."""
        gov = GameAutomationGovernor()
        self.assertIsNotNone(gov.get_profile("gta5.exe"))
        self.assertIsNotNone(gov.get_profile("cyberpunk2077.exe"))

        # Add custom profile
        custom = GameProfile(
            exe_name="my_indie_game.exe",
            display_name="My Indie Game",
            power_mode="Balanced",
            fan_profile="Quiet",
            target_refresh_rate=60
        )
        gov.set_profile(custom)
        self.assertEqual(gov.get_profile("MY_INDIE_GAME.EXE").display_name, "My Indie Game")

        # Delete profile
        self.assertTrue(gov.delete_profile("my_indie_game.exe"))
        self.assertIsNone(gov.get_profile("my_indie_game.exe"))

    def test_governor_scan_for_game(self):
        """scan_for_game matches running game exes and filters out ignored system processes."""
        gov = GameAutomationGovernor()

        # System background tasks should be ignored
        procs = ["explorer.exe", "svchost.exe", "taskmgr.exe", "chrome.exe"]
        self.assertIsNone(gov.scan_for_game(procs))

        # Adding a known game matches
        procs_with_game = ["explorer.exe", "Cyberpunk2077.exe", "discord.exe"]
        match = gov.scan_for_game(procs_with_game)
        self.assertIsNotNone(match)
        self.assertEqual(match.exe_name, "cyberpunk2077.exe")
        self.assertEqual(match.display_name, "Cyberpunk 2077")

    def test_governor_launch_and_exit_transitions(self):
        """Governor captures state on launch and cleanly restores state on exit."""
        gov = GameAutomationGovernor()

        pre_state = {
            "power_mode": "Quiet",
            "fan_mode": "curve_balanced",
            "refresh_rate": 60,
            "winlock": False,
            "bz_mode": 1
        }

        # Step 1: Launch game
        event, data = gov.evaluate_game_transition(["gta5.exe"], pre_state)
        self.assertEqual(event, "LAUNCH")
        self.assertEqual(data["target_power_mode"], "Beast")
        self.assertEqual(data["target_refresh_rate"], 120)
        self.assertTrue(data["winlock"])
        self.assertTrue(gov.is_in_game)
        self.assertEqual(gov.active_game.exe_name, "gta5.exe")

        # Step 2: Still playing (no state change)
        event2, data2 = gov.evaluate_game_transition(["gta5.exe", "discord.exe"], pre_state)
        self.assertIsNone(event2)
        self.assertIsNone(data2)

        # Step 3: Game exited
        event3, data3 = gov.evaluate_game_transition(["discord.exe"], pre_state)
        self.assertEqual(event3, "EXIT")
        self.assertEqual(data3["restore_state"]["power_mode"], "Quiet")
        self.assertEqual(data3["restore_state"]["refresh_rate"], 60)
        self.assertFalse(gov.is_in_game)
        self.assertIsNone(gov.active_game)

    def test_ingame_hud_overlay_creation_and_telemetry(self):
        """HUD overlay initializes and formats live telemetry safely."""
        root = tk._default_root
        if root is None:
            root = tk.Tk()
            root.withdraw()

        with patch("keyboard.add_hotkey"):
            hud = InGameHUDOverlay(root, hotkey="ctrl+shift+o")
            hud.show()
            self.assertTrue(hud.is_visible)

            # Update telemetry with gaming stats
            hud.update_telemetry(
                cpu_temp=72.0, cpu_usage=45.0,
                gpu_temp=68.0, gpu_usage=88.0,
                fan_rpm=4100, power_mode="Beast",
                refresh_rate=120, battery_pct=90,
                on_ac=True, battery_watts=42.5
            )

            self.assertIn("72°C", hud.lbl_cpu.cget("text"))
            self.assertIn("68°C", hud.lbl_gpu.cget("text"))
            self.assertIn("4,100 RPM", hud.lbl_fan.cget("text"))
            self.assertIn("BEAST 120Hz", hud.lbl_mode.cget("text"))

            hud.hide()
            self.assertFalse(hud.is_visible)
            if hud.window:
                hud.window.destroy()


if __name__ == "__main__":
    unittest.main()

"""Unit and integration tests for Phase 4 Lighting Innovations & Presets in InfinixGTToolkitApp."""
import os
import json
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

import infinix_toolkit as toolkit
import lighting_engine


class LightingIntegrationTests(unittest.TestCase):

    def setUp(self):
        self.app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
        self.app.config = {
            "effect_mode": "Solid",
            "brightness": 100,
            "zones": {
                "1": [56, 189, 248],
                "2": [167, 139, 250],
                "3": [56, 189, 248],
                "4": [167, 139, 250],
            },
            "mecha_bar_color": [167, 139, 250],
            "mecha_bar_sync": True,
            "bz_mode": 1,
            "bz_color1": [56, 189, 248],
            "bz_color2": [167, 139, 250],
            "audio_eq_mode": "spectrum",
            "audio_mecha_beat": True,
        }
        self.app.zones = dict(self.app.config["zones"])
        self.app.brightness = 100
        self.app.effect_mode = "Solid"
        self.app.mecha_color = [167, 139, 250]
        self.app.bz_mode = 1
        self.app.bz_color1 = [56, 189, 248]
        self.app.bz_color2 = [167, 139, 250]

        # UI mocks
        self.app.bright_slider = MagicMock()
        self.app.bright_lbl = MagicMock()
        self.app.effect_var = MagicMock()
        self.app.mecha_sync_var = MagicMock()
        self.app._save_config = MagicMock()
        self.app._apply_lighting_hardware = MagicMock()
        self.app._apply_backzone_hardware = MagicMock()
        self.app._show_mode_osd = MagicMock()
        self.app._show_windows_toast = MagicMock()

    def test_apply_builtin_preset_cyberpunk(self):
        """Applying 'Cyberpunk 2077' preset updates zones, hardware, and triggers OSD."""
        self.app._apply_builtin_preset("Cyberpunk 2077")

        expected = lighting_engine.BUILTIN_LIGHTING_PRESETS["Cyberpunk 2077"]
        self.assertEqual(self.app.zones["1"], expected["zones"]["1"])
        self.assertEqual(self.app.zones["2"], expected["zones"]["2"])
        self.assertEqual(self.app.config["zones"]["1"], expected["zones"]["1"])
        self.app._save_config.assert_called_once()
        self.app._apply_lighting_hardware.assert_called_once()
        self.app._apply_backzone_hardware.assert_called_once()
        self.app._show_mode_osd.assert_called_with("Applied: Cyberpunk 2077")

    def test_apply_preset_data_custom(self):
        """Custom preset data dictionary applies cleanly and configures sliders."""
        custom_data = {
            "name": "Custom Green",
            "brightness": 75,
            "effect_mode": "Aurora",
            "zones": {
                "1": [0, 255, 0],
                "2": [0, 200, 0],
                "3": [0, 150, 0],
                "4": [0, 100, 0],
            },
            "mecha_bar_color": [0, 255, 0],
            "bz_mode": 2,
            "bz_color1": [0, 255, 0],
            "bz_color2": [0, 180, 0],
        }

        self.app._apply_preset_data(custom_data)

        self.assertEqual(self.app.brightness, 75)
        self.assertEqual(self.app.effect_mode, "Aurora")
        self.assertEqual(self.app.zones["1"], [0, 255, 0])
        self.app.bright_slider.set.assert_called_with(75)
        self.app.bright_lbl.configure.assert_called_with(text="75%")
        self.app.effect_var.set.assert_called_with("Aurora")

    def test_export_and_import_lighting_preset_flow(self):
        """End-to-end export and re-import via mock file dialogs."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            temp_path = tf.name

        try:
            # Test Export
            with patch("tkinter.filedialog.asksaveasfilename", return_value=temp_path):
                self.app._export_lighting_preset()
                self.assertTrue(os.path.exists(temp_path))
                self.app._show_windows_toast.assert_called()

            # Mutate state
            self.app.brightness = 40
            self.app.zones["1"] = [1, 2, 3]

            # Test Import
            with patch("tkinter.filedialog.askopenfilename", return_value=temp_path):
                self.app._import_lighting_preset()
                self.assertEqual(self.app.brightness, 100)
                self.assertEqual(self.app.zones["1"], [56, 189, 248])
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_audio_eq_controls_toggle(self):
        """Audio EQ mode and Mecha Bar beat toggles update config and save."""
        self.app._on_audio_eq_mode_changed("Theme Reactive")
        self.assertEqual(self.app.config["audio_eq_mode"], "theme_reactive")
        self.app._save_config.assert_called()

        self.app.audio_mecha_beat_var = SimpleNamespace(get=lambda: False)
        self.app._on_audio_mecha_beat_toggled()
        self.assertFalse(self.app.config["audio_mecha_beat"])


if __name__ == "__main__":
    unittest.main()

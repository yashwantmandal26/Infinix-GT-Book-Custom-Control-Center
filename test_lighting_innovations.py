"""Unit tests for Phase 4: Lighting Innovations & Audio Equalizer 2.0 Engine."""
import os
import json
import tempfile
import unittest
from unittest.mock import MagicMock

from lighting_engine import (
    BUILTIN_LIGHTING_PRESETS,
    LightingPresetManager,
    AdvancedAudioEqualizer,
    LowOverheadScreenSync
)


class LightingInnovationsEngineTests(unittest.TestCase):

    def test_builtin_presets_integrity(self):
        """All built-in presets have valid structure and RGB ranges."""
        self.assertGreaterEqual(len(BUILTIN_LIGHTING_PRESETS), 6)
        expected_presets = ["Cyberpunk 2077", "Esports Crimson", "Ocean Abyss", "Synthwave 80s", "Nordic Aurora", "Matrix Digital"]
        for name in expected_presets:
            self.assertIn(name, BUILTIN_LIGHTING_PRESETS)
            p = BUILTIN_LIGHTING_PRESETS[name]
            self.assertEqual(len(p["zones"]), 4)
            for zid in ("1", "2", "3", "4"):
                rgb = p["zones"][zid]
                self.assertEqual(len(rgb), 3)
                for val in rgb:
                    self.assertTrue(0 <= val <= 255)

    def test_preset_export_and_import(self):
        """Lighting preset exports to JSON and safely re-imports with value sanitization."""
        test_cfg = {
            "effect_mode": "Solid",
            "brightness": 85,
            "animation_speed": "Fast",
            "zones": {
                "1": [255, 50, 50],
                "2": [0, 200, 255],
                "3": [255, 200, 0],
                "4": [180, 0, 255],
            },
            "mecha_bar_enabled": True,
            "mecha_bar_sync": False,
            "mecha_bar_color": [0, 200, 255],
            "bz_mode": 1,
            "bz_color1": [255, 50, 50],
            "bz_color2": [180, 0, 255],
            "bz_speed": 4,
            "bz_brightness": 90,
        }

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            temp_path = tf.name

        try:
            # Export
            ok = LightingPresetManager.export_preset(test_cfg, temp_path, "Custom Test Preset")
            self.assertTrue(ok)
            self.assertTrue(os.path.exists(temp_path))

            # Import
            imported = LightingPresetManager.import_preset(temp_path)
            self.assertIsNotNone(imported)
            self.assertEqual(imported["name"], "Custom Test Preset")
            self.assertEqual(imported["brightness"], 85)
            self.assertEqual(imported["zones"]["1"], [255, 50, 50])
            self.assertEqual(imported["zones"]["2"], [0, 200, 255])
            self.assertEqual(imported["mecha_bar_color"], [0, 200, 255])
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_import_corrupted_preset_sanitization(self):
        """Malformed or out-of-range JSON inputs are clamped and sanitized."""
        malformed = {
            "brightness": 250, # Out of range
            "zones": {
                "1": [999, -50, 300], # Out of range
                "2": "not_a_list",     # Invalid
            }
        }
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as tf:
            json.dump(malformed, tf)
            temp_path = tf.name

        try:
            sanitized = LightingPresetManager.import_preset(temp_path)
            self.assertIsNotNone(sanitized)
            self.assertEqual(sanitized["brightness"], 100) # Clamped to 100
            self.assertEqual(sanitized["zones"]["1"], [255, 0, 255]) # Clamped to [0, 255]
            self.assertEqual(sanitized["zones"]["2"], [56, 189, 248]) # Fallback default
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_audio_equalizer_spectrum_mode(self):
        """AdvancedAudioEqualizer generates 4-zone spectrum colors and Mecha Bar bass punch."""
        levels = [0.85, 0.60, 0.40, 0.20]
        beat = 0.90
        step = 12.5

        zones, mecha_rgb = AdvancedAudioEqualizer.render_equalizer_frame(
            levels, beat, step, mode="spectrum"
        )

        self.assertEqual(len(zones), 4)
        for zid in ("1", "2", "3", "4"):
            rgb = zones[zid]
            self.assertEqual(len(rgb), 3)
            for c in rgb:
                self.assertTrue(0 <= c <= 255)

        # On heavy beat (0.90), Mecha Bar should punch with intense flash (red channel dominant)
        self.assertGreater(mecha_rgb[0], 150)

    def test_audio_equalizer_theme_reactive_mode(self):
        """Theme reactive mode modulates user custom colors based on frequency energy."""
        base_zones = {
            "1": [200, 100, 50],
            "2": [100, 200, 50],
            "3": [50, 100, 200],
            "4": [200, 50, 100],
        }
        levels = [0.70, 0.50, 0.30, 0.10]
        beat = 0.20
        step = 5.0

        zones, mecha_rgb = AdvancedAudioEqualizer.render_equalizer_frame(
            levels, beat, step, mode="theme_reactive", base_zones=base_zones
        )

        self.assertEqual(len(zones), 4)
        # Zone 1 (WASD) with 0.70 bass should have high brightness relative to base
        self.assertGreater(zones["1"][0], 120)

    def test_audio_equalizer_silence_graceful_blend(self):
        """When audio is silent, zones gracefully blend with base user colors."""
        base_zones = {
            "1": [10, 20, 30],
            "2": [40, 50, 60],
            "3": [70, 80, 90],
            "4": [100, 110, 120],
        }
        silent_levels = [0.0, 0.0, 0.0, 0.0]
        beat = 0.0

        zones, _ = AdvancedAudioEqualizer.render_equalizer_frame(
            silent_levels, beat, step=0.0, mode="spectrum", base_zones=base_zones
        )

        # Under total silence (tot_energy == 0), color should equal base_zones exactly
        self.assertEqual(zones["1"], (10, 20, 30))
        self.assertEqual(zones["2"], (40, 50, 60))

    def test_low_overhead_screen_sync(self):
        """Low-overhead screen sampler returns valid 4-zone spatial and unified RGB values."""
        mock_mss = MagicMock()
        # Mock grab returning synthetic byte array (e.g., 100x100 pixels in RGB = 30000 bytes)
        fake_pixels = bytes([120, 180, 240] * 2000)
        mock_grab = MagicMock()
        mock_grab.rgb = fake_pixels
        mock_mss.grab.return_value = mock_grab

        mon_info = {"width": 1920, "height": 1200, "top": 0, "left": 0}

        # Spatial
        spatial_zones = LowOverheadScreenSync.sample_screen_colors(mock_mss, mon_info, "Spatial")
        self.assertEqual(len(spatial_zones), 4)
        for zid in ("1", "2", "3", "4"):
            self.assertEqual(len(spatial_zones[zid]), 3)
            self.assertEqual(spatial_zones[zid], (120, 180, 240))

        # Unified
        unified_zones = LowOverheadScreenSync.sample_screen_colors(mock_mss, mon_info, "Unified")
        self.assertEqual(len(unified_zones), 4)
        for zid in ("1", "2", "3", "4"):
            self.assertEqual(unified_zones[zid], (120, 180, 240))


if __name__ == "__main__":
    unittest.main()

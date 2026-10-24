"""Unit tests for manual live exhaust fan speed controls and real-time RPM telemetry."""
import unittest
from unittest.mock import MagicMock, patch, call
from types import SimpleNamespace

import infinix_toolkit as toolkit
import telemetry_data


class ExhaustFanControlTests(unittest.TestCase):

    def test_hardware_engine_set_manual_fan_speed_auto(self):
        """Speed 0 should set EC register 0x41 to 0 (dynamic auto thermal curve)."""
        mock_acpi = MagicMock()
        with patch.object(toolkit.HardwareEngine, "_get_acpi_method_provider", return_value=mock_acpi), \
             patch.object(toolkit.HardwareEngine, "_ec_write_ram", return_value=True) as mock_write, \
             patch.object(toolkit.HardwareEngine, "_verify_ec_value", return_value=0):
            res = toolkit.HardwareEngine.set_manual_fan_speed(0)
            self.assertTrue(res)
            mock_write.assert_called_once_with(mock_acpi, 0x41, 0)

    def test_hardware_engine_set_manual_fan_speed_positive(self):
        """Speed > 0 should set EC register 0x41 to 1 and write proportional CPU/GPU duty cycles."""
        mock_acpi = MagicMock()
        with patch.object(toolkit.HardwareEngine, "_get_acpi_method_provider", return_value=mock_acpi), \
             patch.object(toolkit.HardwareEngine, "_ec_write_ram", return_value=True) as mock_write, \
             patch.object(toolkit.HardwareEngine, "_verify_ec_value", return_value=1):
            res = toolkit.HardwareEngine.set_manual_fan_speed(75)
            self.assertTrue(res)
            # Verify writes: 0x41 to 1, 0x4C (CPU), 0x4D (GPU)
            # CPU duty: round(35 + (144 - 35) * 0.75) = 35 + round(81.75) = 117
            # GPU duty: round(45 + (183 - 45) * 0.75) = 45 + round(103.5) = 148 or 149
            expected_cpu = int(round(35 + (144 - 35) * 0.75))
            expected_gpu = int(round(45 + (183 - 45) * 0.75))
            mock_write.assert_any_call(mock_acpi, 0x41, 1)
            mock_write.assert_any_call(mock_acpi, 0x4C, expected_cpu)
            mock_write.assert_any_call(mock_acpi, 0x4D, expected_gpu)

    def test_hardware_engine_set_manual_fan_speed_full_boost(self):
        """Speed 100 should map to maximum boost duty cycles (144 CPU, 183 GPU)."""
        mock_acpi = MagicMock()
        with patch.object(toolkit.HardwareEngine, "_get_acpi_method_provider", return_value=mock_acpi), \
             patch.object(toolkit.HardwareEngine, "_ec_write_ram", return_value=True) as mock_write, \
             patch.object(toolkit.HardwareEngine, "_verify_ec_value", return_value=1):
            res = toolkit.HardwareEngine.set_manual_fan_speed(100)
            self.assertTrue(res)
            mock_write.assert_any_call(mock_acpi, 0x41, 1)
            mock_write.assert_any_call(mock_acpi, 0x4C, 144)
            mock_write.assert_any_call(mock_acpi, 0x4D, 183)

    def test_hardware_engine_get_fan_rpm_from_ec(self):
        """EC registers 0x08 and 0x09 should be multiplied by 100 to yield true RPM."""
        mock_acpi = MagicMock()
        def mock_read(obj, reg):
            if reg == 0x08:
                return 32  # 3200 RPM
            if reg == 0x09:
                return 36  # 3600 RPM
            return 0

        with patch.object(toolkit.HardwareEngine, "_get_acpi_method_provider", return_value=mock_acpi), \
             patch.object(toolkit.HardwareEngine, "_ec_read_ram", side_effect=mock_read):
            readings = toolkit.HardwareEngine.get_fan_rpm()
            self.assertEqual(readings["cpu_fan"], 3200)
            self.assertEqual(readings["gpu_fan"], 3600)
            self.assertEqual(readings["fan_rpm"], 3600)

    def test_hardware_engine_get_fan_control_mode(self):
        """Should detect Manual vs Auto mode from register 0x41."""
        with patch.object(toolkit.HardwareEngine, "get_full_fan_mode", return_value=True):
            self.assertEqual(toolkit.HardwareEngine.get_fan_control_mode(), "Manual")
        with patch.object(toolkit.HardwareEngine, "get_full_fan_mode", return_value=False):
            self.assertEqual(toolkit.HardwareEngine.get_fan_control_mode(), "Auto")

    def test_app_fan_slider_moving_updates_label_instantly(self):
        """Moving the slider updates the percentage label immediately."""
        app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
        app.fan_slider_val_lbl = MagicMock()
        app.fan_preset_btns = {}
        app.fan_control_mode = "auto"
        app.config = {}
        app._fan_debounce_job = None
        app.root = MagicMock()

        app._on_fan_slider_moving(68.0)
        self.assertEqual(app.manual_fan_speed, 68)
        app.fan_slider_val_lbl.configure.assert_called_with(text="68%")
        self.assertEqual(app.fan_control_mode, "manual")

    def test_app_apply_fan_preset_applies_and_syncs_cooler_boost(self):
        """Applying preset updates slider, mode, and cooler_boost config."""
        app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
        app.config = {}
        app.fan_speed_slider = MagicMock()
        app.fan_slider_val_lbl = MagicMock()
        app.fan_mode_display_var = MagicMock()
        app.fan_speed_var = MagicMock()
        app.fan_preset_btns = {}
        app.fan_status_chip = MagicMock()
        app.cooler_var = MagicMock()
        app._save_config = MagicMock()
        app.mode_var = SimpleNamespace(get=lambda: "Balanced")

        with patch.object(toolkit.InfinixGTToolkitApp, "_submit_hardware_command") as mock_submit:
            app._apply_fan_preset(100)
            self.assertEqual(app.manual_fan_speed, 100)
            self.assertEqual(app.fan_control_mode, "manual")
            self.assertTrue(app.config["cooler_boost"])
            app.cooler_var.set.assert_called_with(True)
            mock_submit.assert_called_once()

    def test_app_on_cooler_boost_toggled_synchronizes_preset(self):
        """Toggling cooler boost ON sets 100% preset; toggling OFF returns to Auto."""
        app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
        app.config = {}
        app.cooler_var = SimpleNamespace(get=lambda: True)
        app._apply_fan_preset = MagicMock()
        app._on_fan_mode_selected = MagicMock()

        app._on_cooler_boost_toggled()
        app._apply_fan_preset.assert_called_once_with(100)

        app.cooler_var = SimpleNamespace(get=lambda: False)
        app._on_cooler_boost_toggled()
        app._on_fan_mode_selected.assert_called_once_with("Auto (Dynamic EC Curve)")

    def test_app_update_telemetry_ui_updates_fan_rpm_widgets(self):
        """_update_telemetry_ui updates tachometer pills and badges with live RPM."""
        app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
        app._refresh_automation_status = MagicMock()
        app._compute_live_system_status = MagicMock(return_value=("LIVE", "green", "Optimal"))
        app.cpu_temp_val = 50.0
        app.gpu_temp_val = 60.0
        app.fan_live_rpm_badge = MagicMock(winfo_exists=lambda: True)
        app.cpu_fan_rpm_chip = MagicMock(winfo_exists=lambda: True)
        app.gpu_fan_rpm_chip = MagicMock(winfo_exists=lambda: True)
        app.telemetry_fan_speed_pill = MagicMock(winfo_exists=lambda: True)

        app._update_telemetry_ui(
            cpu_p=30.0, ram_p=40.0, ram_used_gb=8.0, ram_total_gb=16.0,
            bat_pct=95, on_ac=True,
            cpu_fan_rpm=3200, gpu_fan_rpm=3400, fan_rpm=3400
        )

        self.assertEqual(app.fan_rpm_val, 3400)
        self.assertEqual(app.cpu_fan_rpm, 3200)
        self.assertEqual(app.gpu_fan_rpm, 3400)

        app.fan_live_rpm_badge.configure.assert_called()
        self.assertIn("3,400 RPM", app.fan_live_rpm_badge.configure.call_args.kwargs["text"])
        app.cpu_fan_rpm_chip.configure.assert_called_with(text="💻 CPU Fan: 3,200 RPM")
        app.gpu_fan_rpm_chip.configure.assert_called_with(text="🎮 GPU Fan: 3,400 RPM")
        app.telemetry_fan_speed_pill.configure.assert_called_with(text="🌪️ Fan: 3,400 RPM")


if __name__ == "__main__":
    unittest.main()

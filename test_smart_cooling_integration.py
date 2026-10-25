"""Unit tests for Smart Cooling Fan Curve Engine Integration."""
import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

import infinix_toolkit as toolkit
import fan_curve_engine


class SmartCoolingIntegrationTests(unittest.TestCase):

    def test_independent_fan_speed_auto(self):
        """Zero values for both CPU and GPU fans should set 0x41=0 (auto curve)."""
        mock_acpi = MagicMock()
        with patch.object(toolkit.HardwareEngine, "_get_acpi_method_provider", return_value=mock_acpi), \
             patch.object(toolkit.HardwareEngine, "_ec_write_ram", return_value=True) as mock_write, \
             patch.object(toolkit.HardwareEngine, "_verify_ec_value", return_value=0):
            res = toolkit.HardwareEngine.set_independent_fan_speed(0, 0)
            self.assertTrue(res)
            mock_write.assert_called_once_with(mock_acpi, 0x41, 0)

    def test_independent_fan_speed_asymmetric(self):
        """Asymmetric duty cycles should write independent registers 0x4C (CPU) and 0x4D (GPU)."""
        mock_acpi = MagicMock()
        with patch.object(toolkit.HardwareEngine, "_get_acpi_method_provider", return_value=mock_acpi), \
             patch.object(toolkit.HardwareEngine, "_ec_write_ram", return_value=True) as mock_write, \
             patch.object(toolkit.HardwareEngine, "_verify_ec_value", return_value=1):
            res = toolkit.HardwareEngine.set_independent_fan_speed(50, 80, mode="Balanced")
            self.assertTrue(res)
            # Balanced limits: CPU 144, GPU 183
            # CPU duty: max(40, round(35 + (144 - 35) * 0.50)) = round(35 + 54.5) = 90
            # GPU duty: max(45, round(45 + (183 - 45) * 0.80)) = round(45 + 110.4) = 155
            expected_cpu = int(round(35 + (144 - 35) * 0.50))
            expected_gpu = int(round(45 + (183 - 45) * 0.80))
            mock_write.assert_any_call(mock_acpi, 0x41, 1)
            mock_write.assert_any_call(mock_acpi, 0x4C, expected_cpu)
            mock_write.assert_any_call(mock_acpi, 0x4D, expected_gpu)

    def test_on_fan_control_mode_changed_auto(self):
        """Selecting Auto mode should reset governor and set speed 0."""
        app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
        app.config = {}
        app.fan_governor = fan_curve_engine.FanCurveGovernor()
        app._save_config = MagicMock()
        app._sync_fan_control_ui_visibility = MagicMock()
        app._update_fan_chips_ui = MagicMock()
        app._refresh_fan_curve_graph_ui = MagicMock()
        app._submit_fan_speed_command = MagicMock()

        app._on_fan_control_mode_changed("Auto (OEM)")
        self.assertEqual(app.fan_control_mode, "auto")
        self.assertEqual(app.config["fan_control_mode"], "auto")
        app._submit_fan_speed_command.assert_called_with(0)

    def test_on_fan_control_mode_changed_balanced(self):
        """Selecting Balanced curve mode sets curve_balanced and applies evaluated speed."""
        app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
        app.config = {}
        app.cpu_temp_val = 65.0
        app.gpu_temp_val = 60.0
        app.fan_governor = fan_curve_engine.FanCurveGovernor()
        app._save_config = MagicMock()
        app._sync_fan_control_ui_visibility = MagicMock()
        app._update_fan_chips_ui = MagicMock()
        app._refresh_fan_curve_graph_ui = MagicMock()
        app._submit_fan_speed_command = MagicMock()

        app._on_fan_control_mode_changed("Balanced")
        self.assertEqual(app.fan_control_mode, "curve_balanced")
        self.assertEqual(app.config["fan_control_mode"], "curve_balanced")
        app._submit_fan_speed_command.assert_called()

    def test_on_fan_control_mode_changed_custom(self):
        """Selecting Custom Curve mode sets curve_custom and uses custom curve points."""
        app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
        custom_pts = [[40.0, 30.0], [50.0, 45.0], [65.0, 65.0], [75.0, 85.0], [85.0, 100.0]]
        app.config = {"fan_curve_custom": custom_pts}
        app.cpu_temp_val = 50.0
        app.gpu_temp_val = None
        app.fan_governor = fan_curve_engine.FanCurveGovernor()
        app._save_config = MagicMock()
        app._sync_fan_control_ui_visibility = MagicMock()
        app._update_fan_chips_ui = MagicMock()
        app._refresh_fan_curve_graph_ui = MagicMock()
        app._submit_fan_speed_command = MagicMock()

        app._on_fan_control_mode_changed("Custom Curve")
        self.assertEqual(app.fan_control_mode, "curve_custom")
        self.assertEqual(app.config["fan_control_mode"], "curve_custom")
        app._submit_fan_speed_command.assert_called()

    def test_custom_curve_node_modification(self):
        """Modifying a custom curve node slider updates config and schedules apply."""
        app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
        initial_pts = [[40.0, 25.0], [50.0, 40.0], [65.0, 60.0], [75.0, 80.0], [85.0, 95.0]]
        app.config = {"fan_curve_custom": initial_pts}
        app._refresh_fan_curve_graph_ui = MagicMock()
        app._curve_save_job = None
        app.root = MagicMock()
        app.root.after = MagicMock(return_value=999)

        app._on_custom_curve_node_changed(1, 55.0)
        self.assertEqual(app.config["fan_curve_custom"][1][1], 55.0)
        app._refresh_fan_curve_graph_ui.assert_called_once()
        self.assertEqual(app._curve_save_job, 999)

    def test_reset_custom_curve_to_default(self):
        """Resetting custom curve restores default setpoints."""
        app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
        app.config = {"fan_curve_custom": [[40.0, 90.0], [50.0, 95.0]]}
        app.fan_control_mode = "curve_custom"
        app._save_config = MagicMock()
        app._refresh_fan_curve_graph_ui = MagicMock()
        app._apply_custom_curve_update = MagicMock()

        app._reset_custom_curve_to_default()
        default_pts = [list(p) for p in fan_curve_engine.FAN_CURVE_PRESETS["custom_default"]]
        self.assertEqual(app.config["fan_curve_custom"], default_pts)
        app._refresh_fan_curve_graph_ui.assert_called_once()
        app._apply_custom_curve_update.assert_called_once()


if __name__ == "__main__":
    unittest.main()

"""Unit tests for Display Refresh Rate and Battery Intelligence Engine."""
import unittest
from unittest.mock import MagicMock, patch
import ctypes

import display_battery_engine as dbe


class DisplayRefreshEngineTests(unittest.TestCase):

    def test_get_current_refresh_rate(self):
        """Should query active refresh rate from ENUM_CURRENT_SETTINGS."""
        def mock_enum(dev, idx, ref):
            dm = ref._obj
            dm.dmDisplayFrequency = 120
            dm.dmPelsWidth = 1920
            dm.dmPelsHeight = 1200
            return 1

        with patch.object(ctypes.windll.user32, "EnumDisplaySettingsW", side_effect=mock_enum):
            rate = dbe.DisplayRefreshEngine.get_current_refresh_rate()
            self.assertEqual(rate, 120)

    def test_get_supported_refresh_rates_deduplicated(self):
        """Should return unique, sorted refresh rates matching current resolution."""
        def mock_enum(dev, idx, ref):
            dm = ref._obj
            if idx == -1:  # Current
                dm.dmPelsWidth = 1920
                dm.dmPelsHeight = 1200
                dm.dmDisplayFrequency = 120
                return 1
            modes = [
                (1920, 1200, 60),
                (1920, 1200, 120),
                (1920, 1080, 144),  # Different resolution, should be ignored
                (1920, 1200, 60),   # Duplicate
            ]
            if 0 <= idx < len(modes):
                w, h, hz = modes[idx]
                dm.dmPelsWidth = w
                dm.dmPelsHeight = h
                dm.dmDisplayFrequency = hz
                return 1
            return 0

        with patch.object(ctypes.windll.user32, "EnumDisplaySettingsW", side_effect=mock_enum):
            rates = dbe.DisplayRefreshEngine.get_supported_refresh_rates()
            self.assertEqual(rates, [60, 120])

    def test_set_refresh_rate_same_rate_no_op(self):
        """Setting the same refresh rate should return True immediately."""
        def mock_enum(dev, idx, ref):
            dm = ref._obj
            dm.dmDisplayFrequency = 120
            dm.dmPelsWidth = 1920
            dm.dmPelsHeight = 1200
            return 1

        with patch.object(ctypes.windll.user32, "EnumDisplaySettingsW", side_effect=mock_enum), \
             patch.object(ctypes.windll.user32, "ChangeDisplaySettingsExW") as mock_change:
            res = dbe.DisplayRefreshEngine.set_refresh_rate(120)
            self.assertTrue(res)
            mock_change.assert_not_called()

    def test_set_refresh_rate_success(self):
        """Setting new refresh rate should invoke ChangeDisplaySettingsExW with DISP_CHANGE_SUCCESSFUL."""
        def mock_enum(dev, idx, ref):
            dm = ref._obj
            if idx == -1:
                dm.dmDisplayFrequency = 120
                dm.dmPelsWidth = 1920
                dm.dmPelsHeight = 1200
                return 1
            if idx == 0:
                dm.dmDisplayFrequency = 60
                dm.dmPelsWidth = 1920
                dm.dmPelsHeight = 1200
                return 1
            return 0

        with patch.object(ctypes.windll.user32, "EnumDisplaySettingsW", side_effect=mock_enum), \
             patch.object(ctypes.windll.user32, "ChangeDisplaySettingsExW", return_value=0) as mock_change:
            res = dbe.DisplayRefreshEngine.set_refresh_rate(60, persistent=True)
            self.assertTrue(res)
            mock_change.assert_called()


class BatteryIntelligenceEngineTests(unittest.TestCase):

    def test_battery_metrics_discharging(self):
        """Discharging battery metrics should compute negative wattage and runtime estimation."""
        mock_status = MagicMock(
            PowerOnline=False, Charging=False, Discharging=True,
            Voltage=11800, RemainingCapacity=36000, ChargeRate=0, DischargeRate=12000
        )
        mock_full = MagicMock(FullChargedCapacity=60000)
        mock_static = MagicMock(DesignedCapacity=70000)

        mock_s_wmi = MagicMock()
        mock_s_wmi.ExecQuery.side_effect = lambda query: {
            "SELECT PowerOnline, Charging, Discharging, Voltage, RemainingCapacity, ChargeRate, DischargeRate FROM BatteryStatus": [mock_status],
            "SELECT FullChargedCapacity FROM BatteryFullChargedCapacity": [mock_full],
            "SELECT DesignedCapacity FROM BatteryStaticData": [mock_static],
        }.get(query, [])

        mock_locator = MagicMock()
        mock_locator.ConnectServer.return_value = mock_s_wmi

        with patch("win32com.client.Dispatch", return_value=mock_locator):
            m = dbe.BatteryIntelligenceEngine.get_battery_power_metrics()
            self.assertFalse(m["power_online"])
            self.assertTrue(m["is_discharging"])
            self.assertEqual(m["voltage_v"], 11.8)
            self.assertEqual(m["level_pct"], 60)  # 36000 / 60000
            self.assertEqual(m["discharge_rate_w"], 12.0)
            self.assertEqual(m["power_watts"], -12.0)
            # Remaining hours = 36000 / 12000 = 3h 00m
            self.assertIn("3h 00m remaining", m["remaining_time_str"])
            self.assertAlmostEqual(m["health_pct"], 85.7, places=1)

    def test_battery_metrics_charging(self):
        """Charging battery metrics should compute positive wattage and time to full."""
        mock_status = MagicMock(
            PowerOnline=True, Charging=True, Discharging=False,
            Voltage=12600, RemainingCapacity=45000, ChargeRate=30000, DischargeRate=0
        )
        mock_full = MagicMock(FullChargedCapacity=60000)
        mock_static = MagicMock(DesignedCapacity=70000)

        mock_s_wmi = MagicMock()
        mock_s_wmi.ExecQuery.side_effect = lambda query: {
            "SELECT PowerOnline, Charging, Discharging, Voltage, RemainingCapacity, ChargeRate, DischargeRate FROM BatteryStatus": [mock_status],
            "SELECT FullChargedCapacity FROM BatteryFullChargedCapacity": [mock_full],
            "SELECT DesignedCapacity FROM BatteryStaticData": [mock_static],
        }.get(query, [])

        mock_locator = MagicMock()
        mock_locator.ConnectServer.return_value = mock_s_wmi

        with patch("win32com.client.Dispatch", return_value=mock_locator):
            m = dbe.BatteryIntelligenceEngine.get_battery_power_metrics()
            self.assertTrue(m["power_online"])
            self.assertTrue(m["is_charging"])
            self.assertEqual(m["charge_rate_w"], 30.0)
            self.assertEqual(m["power_watts"], 30.0)
            # Needed mwh = 15000, charge rate = 30000 -> 0.5 hours = 30 mins
            self.assertIn("30m to full", m["remaining_time_str"])


if __name__ == "__main__":
    unittest.main()

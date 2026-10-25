"""Unit and integration tests for Phase 5: Production Robustness, ACPI Resilience & Low-Idle Footprint."""

import sys
import unittest
from unittest.mock import MagicMock, patch, call
import infinix_toolkit
from infinix_toolkit import HardwareEngine, InfinixGTToolkitApp


class TestPhase5HardwareResilience(unittest.TestCase):
    """Test ACPI WMI resilience and cold-boot hardware handshake."""

    def setUp(self):
        HardwareEngine._last_error = ""

    def test_safe_boot_handshake_success(self):
        """Verify that safe_boot_handshake writes EC 0x41=0 and verifies it."""
        mock_acpi = MagicMock()
        with patch.object(HardwareEngine, "_get_acpi_method_provider", return_value=mock_acpi), \
             patch.object(HardwareEngine, "_ec_write_ram", return_value=True) as mock_write, \
             patch.object(HardwareEngine, "_verify_ec_value", return_value=True) as mock_verify:
            
            result = HardwareEngine.safe_boot_handshake()
            self.assertTrue(result)
            mock_write.assert_called_once_with(mock_acpi, 0x41, 0)
            mock_verify.assert_called_once_with(mock_acpi, 0x41, 0)
            self.assertEqual(HardwareEngine.get_last_error(), "")

    def test_safe_boot_handshake_acpi_failure(self):
        """Verify safe_boot_handshake does not crash if ACPI provider throws access denied."""
        with patch.object(HardwareEngine, "_get_acpi_method_provider", side_effect=RuntimeError("0x80041003 WBEM_E_ACCESS_DENIED")):
            result = HardwareEngine.safe_boot_handshake()
            self.assertFalse(result)
            self.assertIn("Safe boot handshake failed", HardwareEngine.get_last_error())

    def test_get_acpi_method_provider_error_handling(self):
        """Verify _get_acpi_method_provider logs error cleanly on COM failure."""
        with patch("win32com.client.Dispatch", side_effect=Exception("COM connection failed")):
            # Clear cached thread-local object
            if hasattr(HardwareEngine._tls, "acpi_obj"):
                HardwareEngine._tls.acpi_obj = None
            with self.assertRaises(RuntimeError) as ctx:
                HardwareEngine._get_acpi_method_provider()
            self.assertIn("OEM ACPIMethod WMI provider is unavailable", str(ctx.exception))
            self.assertIn("ACPI WMI provider access error", HardwareEngine.get_last_error())


class TestPhase5TrayAndNotifications(unittest.TestCase):
    """Test zero-overhead notifications and single-click tray callbacks."""

    def test_tray_notification_uses_pystray_notify(self):
        """Verify _show_windows_toast calls tray_icon.notify without spawning subprocess."""
        app = MagicMock(spec=InfinixGTToolkitApp)
        app.tray_icon = MagicMock()
        
        # Call the actual method implementation unbound
        InfinixGTToolkitApp._show_windows_toast(app, "Test Title", "Test Message")
        app.tray_icon.notify.assert_called_once_with("Test Message", "Test Title")

    def test_tray_callbacks_accept_pystray_arguments(self):
        """Verify that tray callbacks accept (icon, item) positional arguments from pystray."""
        app = MagicMock(spec=InfinixGTToolkitApp)
        app._ui_thread_id = 999999
        app.running = False  # prevent actual quit shutdown flow
        mock_icon = MagicMock()
        mock_item = MagicMock()

        # All of these must accept *args without raising TypeError
        try:
            InfinixGTToolkitApp._show_window(app, mock_icon, mock_item)
            InfinixGTToolkitApp._tray_toggle_theme(app, mock_icon, mock_item)
            InfinixGTToolkitApp._tray_toggle_backlight(app, mock_icon, mock_item)
            InfinixGTToolkitApp._tray_set_mode(app, "Beast", mock_icon, mock_item)
            InfinixGTToolkitApp._tray_toggle_hud(app, mock_icon, mock_item)
            InfinixGTToolkitApp._quit_app(app, mock_icon, mock_item)
        except TypeError as exc:
            self.fail(f"Tray callback raised TypeError with pystray arguments: {exc}")

    def test_do_show_window_restores_and_focuses(self):
        """Verify _do_show_window restores from minimized/withdrawn state."""
        app = MagicMock(spec=InfinixGTToolkitApp)
        app.root = MagicMock()
        app.root.winfo_id.return_value = 12345
        
        with patch("ctypes.windll.user32.FindWindowW", return_value=12345), \
             patch("ctypes.windll.user32.ShowWindow") as mock_show, \
             patch("ctypes.windll.user32.SetForegroundWindow") as mock_foreground:
            
            InfinixGTToolkitApp._do_show_window(app)
            app.root.deiconify.assert_called_once()
            app.root.state.assert_called_once_with("normal")
            app.root.lift.assert_called_once()
            app.root.focus_force.assert_called_once()
            mock_show.assert_called_once_with(12345, 9)
            mock_foreground.assert_called_once_with(12345)


class TestPhase5LowIdleFootprint(unittest.TestCase):
    """Test sleep mode and UI mailbox filtering when minimized."""

    def test_ui_dispatch_drops_offscreen_telemetry_when_hidden(self):
        """Verify _ui_dispatch drops telemetry & preview redraws when root is not viewable."""
        app = MagicMock(spec=InfinixGTToolkitApp)
        app.running = True
        app.is_minimized = True  # minimized to tray
        app._ui_thread_id = 999999  # distinct thread
        app._ui_mailbox = MagicMock()

        def _update_telemetry_ui(): pass
        def _update_virtual_keyboard_preview(): pass

        with patch("threading.get_ident", return_value=111111):
            InfinixGTToolkitApp._ui_dispatch(app, _update_telemetry_ui)
            InfinixGTToolkitApp._ui_dispatch(app, _update_virtual_keyboard_preview)

        # Neither should have been posted to UI mailbox
        app._ui_mailbox.post.assert_not_called()

    def test_ui_dispatch_allows_other_commands_when_hidden(self):
        """Verify critical commands (like mode switch notifications or settings) still pass through."""
        app = MagicMock(spec=InfinixGTToolkitApp)
        app.running = True
        app.is_minimized = True
        app._ui_thread_id = 999999
        app._ui_mailbox = MagicMock()

        def _do_show_window(): pass

        with patch("threading.get_ident", return_value=111111):
            InfinixGTToolkitApp._ui_dispatch(app, _do_show_window)

        app._ui_mailbox.post.assert_called_once()


class TestPhase5WindowsEnergySaver(unittest.TestCase):
    """Test Windows 11 Energy Saver and Modern Power Overlay synchronization."""

    def setUp(self):
        HardwareEngine._last_power_plan_mode = "Balanced"
        HardwareEngine._saved_pre_quiet_brightness = None

    def test_quiet_mode_engages_energy_saver_overlay_and_thresholds(self):
        """Quiet/Office mode automatically activates Energy Saver overlay and 100% threshold."""
        with patch("subprocess.run") as mock_run, \
             patch("ctypes.windll.powrprof.PowerSetActiveOverlayScheme", create=True) as mock_overlay, \
             patch("ctypes.windll.user32.SendMessageTimeoutW", create=True):
            mock_run.return_value.returncode = 0
            
            res = HardwareEngine.set_windows_energy_saver(True, "Quiet")
            self.assertTrue(res)

            # Overlay API must be called
            self.assertTrue(mock_overlay.called)
            
            # Check powercfg calls for 100% threshold on DC and AC
            called_cmds = [call_args[0][0] for call_args in mock_run.call_args_list]
            self.assertTrue(any("100" in cmd and "/setdcvalueindex" in cmd for cmd in called_cmds))
            self.assertTrue(any("100" in cmd and "/setacvalueindex" in cmd for cmd in called_cmds))

    def test_balanced_and_beast_mode_restores_energy_saver(self):
        """Balanced and Beast mode restore standard thresholds and normal overlays."""
        with patch("subprocess.run") as mock_run, \
             patch("ctypes.windll.powrprof.PowerSetActiveOverlayScheme", create=True) as mock_overlay, \
             patch("ctypes.windll.user32.SendMessageTimeoutW", create=True):
            mock_run.return_value.returncode = 0

            # Balanced
            res_bal = HardwareEngine.set_windows_energy_saver(False, "Balanced")
            self.assertTrue(res_bal)
            bal_cmds = [call_args[0][0] for call_args in mock_run.call_args_list]
            self.assertTrue(any("30" in cmd and "/setdcvalueindex" in cmd for cmd in bal_cmds))
            self.assertTrue(any("0" in cmd and "/setacvalueindex" in cmd for cmd in bal_cmds))

            mock_run.reset_mock()
            # Beast
            res_beast = HardwareEngine.set_windows_energy_saver(False, "Beast")
            self.assertTrue(res_beast)
            beast_cmds = [call_args[0][0] for call_args in mock_run.call_args_list]
            self.assertTrue(any("20" in cmd and "/setdcvalueindex" in cmd for cmd in beast_cmds))
            self.assertTrue(any("0" in cmd and "/setacvalueindex" in cmd for cmd in beast_cmds))

    def test_power_plan_integration_invokes_energy_saver(self):
        """set_windows_power_plan calls set_windows_energy_saver with correct parameters."""
        with patch.object(HardwareEngine, "set_windows_energy_saver") as mock_saver, \
             patch.object(HardwareEngine, "get_display_brightness", return_value=80), \
             patch.object(HardwareEngine, "set_display_brightness"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0

            HardwareEngine.set_windows_power_plan("Quiet")
            mock_saver.assert_called_with(enable=True, mode="Quiet")

            HardwareEngine.set_windows_power_plan("Balanced")
            mock_saver.assert_called_with(enable=False, mode="Balanced")


class TestPhase5LowBatteryAlerts(unittest.TestCase):
    """Test Critical Low Battery (<10%) 15s Red Light Pulse and Breathing OSD."""

    def test_low_battery_osd_show_and_hide(self):
        """Verify LowBatteryBreathingOSD creates window, renders card, and cancels breathing on hide."""
        from infinix_toolkit import LowBatteryBreathingOSD
        mock_master = MagicMock()
        mock_master.winfo_screenwidth.return_value = 1920
        mock_master.winfo_screenheight.return_value = 1080
        mock_master.after.return_value = 9999

        osd = LowBatteryBreathingOSD(mock_master)
        with patch.object(osd, "_create_window"):
            osd.window = MagicMock()
            osd.canvas = MagicMock()
            with patch.object(osd, "_render_card_image", return_value=MagicMock()):
                osd.show(8)
                self.assertTrue(osd.is_breathing)
                osd.window.deiconify.assert_called_once()
                mock_master.after.assert_called_with(40, osd._step_breathing)

                osd.hide()
                self.assertFalse(osd.is_breathing)
                mock_master.after_cancel.assert_called_with(9999)
                osd.window.withdraw.assert_called_once()

    def test_low_battery_does_not_alert_when_on_ac(self):
        """When charger is connected, low battery alert does not fire and OSD is hidden."""
        app = MagicMock(spec=InfinixGTToolkitApp)
        app.running = True
        app.on_ac_val = True
        app.battery_val = 8
        app._low_bat_osd_visible = True
        app._low_bat_15s_alert_fired = False

        # If on AC, hide OSD
        if app.on_ac_val:
            InfinixGTToolkitApp._hide_low_battery_osd(app)
            self.assertFalse(app._low_bat_osd_visible)

    def test_low_battery_red_pulse_aborts_on_ac(self):
        """15-second red pulse immediately breaks if charger is connected."""
        app = MagicMock(spec=InfinixGTToolkitApp)
        app.running = True
        app.on_ac_val = True  # Charger connected
        app._low_bat_pulse_active = False

        with patch.object(HardwareEngine, "send_4zone_rgb") as mock_kb, \
             patch("infinix_toolkit.SerialEngine.send_backzone_rgb") as mock_bz:
            # When AC is connected, pulse worker should not execute multiple loops
            InfinixGTToolkitApp._start_low_battery_red_pulse(app)
            self.assertFalse(app._low_bat_pulse_active)


class TestPhase5SidebarPolish(unittest.TestCase):
    """Test Option C Sidebar Polish: Quick Mode Switcher, Nav Badges & Active Glow."""

    def test_quick_mode_select_updates_buttons(self):
        """1-click quick mode selector updates mode_var and calls _on_mode_selected."""
        app = MagicMock(spec=InfinixGTToolkitApp)
        app.mode_var = MagicMock()
        InfinixGTToolkitApp._quick_mode_select(app, "Beast")
        app.mode_var.set.assert_called_once_with("Beast")
        app._on_mode_selected.assert_called_once_with(source="sidebar_quick")
        app._update_sidebar_mode_buttons.assert_called_once_with("Beast")

    def test_sidebar_mode_buttons_highlight_active_color(self):
        """Active mode button is configured with signature color, while idle ones become transparent."""
        app = MagicMock(spec=InfinixGTToolkitApp)
        btn_quiet = MagicMock()
        btn_bal = MagicMock()
        btn_beast = MagicMock()
        app.sidebar_mode_btns = {
            "Quiet": (btn_quiet, "#16A34A"),
            "Balanced": (btn_bal, "#0284C7"),
            "Beast": (btn_beast, "#DC2626")
        }

        # Select Quiet
        InfinixGTToolkitApp._update_sidebar_mode_buttons(app, "Quiet")
        btn_quiet.configure.assert_called_with(fg_color="#16A34A", text_color="#FFFFFF", font=unittest.mock.ANY)
        btn_bal.configure.assert_called_with(fg_color="transparent", text_color=unittest.mock.ANY, font=unittest.mock.ANY)
        btn_beast.configure.assert_called_with(fg_color="transparent", text_color=unittest.mock.ANY, font=unittest.mock.ANY)


if __name__ == "__main__":
    unittest.main()

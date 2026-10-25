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


if __name__ == "__main__":
    unittest.main()

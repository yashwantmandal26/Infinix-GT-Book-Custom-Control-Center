from types import SimpleNamespace
from unittest.mock import Mock, patch
import infinix_toolkit as toolkit


def test_successful_request_keeps_active_selection():
    app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
    app.config = {"gpu_mode": "Hybrid"}
    app.gpu_mode_var = Mock()
    app.gpu_mode_selector = Mock()
    app.gpu_mode_status = Mock()
    app.telemetry_gpu_mode_value = Mock()
    app._save_config = Mock()
    app._set_hardware_status = Mock()
    app._prompt_gpu_restart = Mock()
    app._finish_gpu_mode_change(SimpleNamespace(ok=True), "iGPU only", "Hybrid")
    app.gpu_mode_var.set.assert_called_with("Hybrid")
    assert app.config["gpu_mode"] == "Hybrid"
    assert app.config["gpu_mode_pending"] == "iGPU only"
    app.telemetry_gpu_mode_value.configure.assert_called_with(text="●  Hybrid")


def test_click_reverts_highlight_before_hardware_request():
    app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
    app.config = {}
    app._active_gpu_mode = "Hybrid"
    app.gpu_mode_var = Mock()
    app.gpu_mode_selector = Mock()
    app.gpu_mode_status = Mock()
    with patch.object(toolkit.InfinixGTToolkitApp, "_submit_hardware_command", return_value=True):
        app._on_gpu_mode_changed("dGPU only")
    app.gpu_mode_var.set.assert_called_with("Hybrid")

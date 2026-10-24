"""Accuracy checks: unavailable data must never become plausible fake readings."""
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
import infinix_toolkit as toolkit
import telemetry_data as data


def sensor(kind, identifier, value, name=""):
    props = dict(SensorType=kind, Identifier=identifier, Value=value, Name=name)
    return SimpleNamespace(Properties_=lambda key: SimpleNamespace(Value=props[key]))


def test_sensor_types_and_units_are_kept_separate():
    readings = dict.fromkeys(data.SENSOR_KEYS)
    data.merge_monitor_sensors(readings, [
        sensor("Load", "/intelcpu/0/load/0", 100),
        sensor("Voltage", "/intelcpu/0/voltage/0", 1.2),
        sensor("Temperature", "/intelcpu/0/temperature/0", 51),
        sensor("Temperature", "/intelcpu/0/temperature/1", 56),
        sensor("Temperature", "/gpu-nvidia/0/temperature/0", 64),
        sensor("Temperature", "/nvme/0/temperature/0", 42),
        sensor("Temperature", "/board/temperature/0", 25, "Ambient"),
        sensor("Fan", "/board/fan/0", 3200),
        sensor("Control", "/gpu-nvidia/0/control/0", 50),
        sensor("Temperature", "/intelcpu/0/temperature/2", float("nan")),
        sensor("Temperature", "/intelcpu/0/temperature/3", 255),
    ])
    assert readings == dict(CPU=56, GPU=64, SSD=42, Ambient=25, Fan=3200, ACPI=None)
    assert data.sensor_text("Fan", readings["Fan"]) == "3200 RPM"
    assert data.sensor_text("CPU", readings["CPU"]) == "56°C"


@pytest.mark.parametrize("value", (None, float("nan"), float("inf"), -1, 255, True, "missing"))
def test_invalid_temperature_values_are_not_reported(value):
    assert data.sensor_text("CPU", value) == data.UNAVAILABLE


def test_battery_wear_is_measured_loss_not_an_age_estimate():
    result = data.battery_capacity(60060, 70000, 0)
    assert result["bat_health"] == "85.8%"
    assert result["bat_wear"] == "14.2% of design"
    assert result["bat_cap"] == "60.1 Wh / 70.0 Wh"
    assert result["bat_cycles"] == "0 cycles"
    assert "bat_age" not in result
    assert data.battery_capacity(71000, 70000, None)["bat_wear"] == "0.0% of design"
    missing = data.battery_capacity(None, 0, None)
    assert missing["bat_health_pct"] is None
    assert missing["bat_cycles"] == data.UNAVAILABLE


def test_ac_connection_does_not_claim_fast_charging():
    assert data.power_text(79, True) == "AC connected"
    assert data.power_text(79, False) == "On battery"
    assert data.power_text(None, True) == data.UNAVAILABLE
    assert data.uptime_text(1000, 1000 + 90061) == "1d 1h 1m"
    assert data.uptime_text(1000, 999) == "0m"


def test_nvml_query_preserves_64_bit_handle_and_shuts_down():
    nvml = SimpleNamespace(nvmlInit_v2=Mock(return_value=0), nvmlShutdown=Mock(),
                           nvmlDeviceGetHandleByIndex_v2=Mock(), nvmlDeviceGetTemperature=Mock())
    def handle(index, output):
        output._obj.value = 0x123456789
        return 0
    def temperature(device, sensor_type, output):
        assert device.value == 0x123456789
        output._obj.value = 68
        return 0
    nvml.nvmlDeviceGetHandleByIndex_v2.side_effect = handle
    nvml.nvmlDeviceGetTemperature.side_effect = temperature
    with patch.object(data.ctypes, "CDLL", return_value=nvml):
        assert data._nvidia_temperature() == 68
    nvml.nvmlShutdown.assert_called_once()


def test_nvml_unavailable_temperature_is_not_zero():
    nvml = SimpleNamespace(nvmlInit_v2=Mock(return_value=0), nvmlShutdown=Mock(),
                           nvmlDeviceGetHandleByIndex_v2=Mock(return_value=3), nvmlDeviceGetTemperature=Mock())
    with patch.object(data.ctypes, "CDLL", return_value=nvml):
        assert data._nvidia_temperature() is None
    nvml.nvmlDeviceGetTemperature.assert_not_called()
    nvml.nvmlShutdown.assert_called_once()


def test_concurrent_readers_share_snapshot_and_cannot_mutate_cache(monkeypatch):
    monkeypatch.setattr(data, "_cached", None)
    monkeypatch.setattr(data, "_expires", 0)
    collect = Mock(return_value=dict(CPU=None, GPU=None, SSD=None, Ambient=None, Fan=None, ACPI=45))
    monkeypatch.setattr(data, "_collect_sensors", collect)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: data.get_sensor_readings(), range(8)))
    assert collect.call_count == 1
    assert results[0]["CPU"] is None  # ACPI must not masquerade as a CPU reading.
    results[0]["ACPI"] = 99
    assert data.get_sensor_readings()["ACPI"] == 45


def label():
    return Mock(winfo_exists=Mock(return_value=True))


def test_about_and_monitor_share_all_sensor_readings_and_clear_missing_values():
    app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
    app.sensor_labels = {key: label() for key in data.SENSOR_KEYS}
    app._about_live_labels = {key: label() for key in ("cpu_temp", "gpu_temp", "fan_speed")}
    app._apply_sensor_readings(dict(CPU=52, GPU=65, Fan=3300, SSD=41, ACPI=45))
    app.sensor_labels["CPU"].configure.assert_called_with(text="52°C")
    app._about_live_labels["cpu_temp"].configure.assert_called_with(text="52°C")
    app._about_live_labels["gpu_temp"].configure.assert_called_with(text="65°C")
    app._about_live_labels["fan_speed"].configure.assert_called_with(text="3300 RPM")
    app._apply_sensor_readings({})
    assert app.cpu_temp_val is None
    app.sensor_labels["CPU"].configure.assert_called_with(text=data.UNAVAILABLE)
    app._about_live_labels["cpu_temp"].configure.assert_called_with(text=data.UNAVAILABLE)


def test_missing_battery_refresh_clears_old_health_without_inventing_80_percent():
    app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
    app.config = {"cached_bat_health_pct": 85.8}
    app._cached_bat_health_pct = 85.8
    app._about_live_labels = {}
    app.telemetry_bat_health_badge = label()
    app._about_apply_live(dict(bat_health=data.UNAVAILABLE, bat_cap=data.UNAVAILABLE, bat_health_pct=None))
    assert app._cached_bat_health_pct is None
    assert app.config["cached_bat_health_pct"] is None
    assert app._cached_cap_info == data.UNAVAILABLE
    assert "Good" not in app.telemetry_bat_health_badge.configure.call_args.kwargs["text"]


def test_refresh_is_single_flight_and_fast_stats_keep_about_live():
    app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
    app._about_live_labels = {key: label() for key in ("ram_used", "bat_charge", "bat_status", "uptime")}
    with patch.object(toolkit.threading, "Thread") as thread:
        app._about_refresh_live(silent=True)
        app._about_refresh_live(silent=True)
        thread.assert_called_once()
    with patch.object(toolkit.psutil, "boot_time", return_value=1000), patch.object(data.time, "time", return_value=1061):
        app._update_about_fast_stats(10.5, 15.6, 67.3, 79, True)
    app._about_live_labels["ram_used"].configure.assert_called_with(text="10.5 GiB / 15.6 GiB (67.3%)")
    app._about_live_labels["bat_status"].configure.assert_called_with(text="AC connected")
    app._about_live_labels["uptime"].configure.assert_called_with(text="1m")

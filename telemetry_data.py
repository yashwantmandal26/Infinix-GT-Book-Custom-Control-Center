"""Read-only sensor collection and honest formatting for the monitoring pages."""
import ctypes
import math
import os
from pathlib import Path
import threading
import time

SENSOR_KEYS = ("CPU", "GPU", "SSD", "Ambient", "Fan", "ACPI")
UNAVAILABLE = "Not reported"
_lock = threading.Lock()
_cached = None
_expires = 0.0


def number(value, low=0, high=float("inf")):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) and low <= result <= high else None
    except (TypeError, ValueError, OverflowError):
        return None


def sensor_text(key, value):
    value = number(value, 0, 20000 if key == "Fan" else 125)
    return UNAVAILABLE if value is None else f"{value:.0f}{' RPM' if key == 'Fan' else '°C'}"


def battery_capacity(full, design, cycles):
    full, design = number(full, 1), number(design, 1)
    result = {"bat_health": UNAVAILABLE, "bat_health_pct": None,
              "bat_wear": UNAVAILABLE, "bat_cap": UNAVAILABLE}
    if full is not None and design is not None:
        health = round(full / design * 100, 1)
        result.update(bat_health=f"{health:.1f}%", bat_health_pct=health,
                      bat_wear=f"{max(0, round(100 - health, 1)):.1f}% of design",
                      bat_cap=f"{full / 1000:.1f} Wh / {design / 1000:.1f} Wh")
    cycles = number(cycles, 0, 100000)
    result["bat_cycles"] = f"{int(cycles)} cycles" if cycles is not None and cycles.is_integer() else UNAVAILABLE
    return result


def power_text(percent, plugged):
    if number(percent, 0, 100) is None or plugged is None:
        return UNAVAILABLE
    return "AC connected" if plugged else "On battery"


def uptime_text(boot, now=None):
    seconds = max(0, int((time.time() if now is None else now) - boot))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes = seconds // 60
    return f"{days}d {hours}h {minutes}m" if days else f"{hours}h {minutes}m" if hours else f"{minutes}m"


def merge_monitor_sensors(readings, sensors):
    """Ignore load, clock and voltage sensors even when their values look like °C."""
    for sensor in sensors:
        try:
            kind = str(sensor.Properties_("SensorType").Value)
            identity = str(sensor.Properties_("Identifier").Value or "").lower()
            name = str(sensor.Properties_("Name").Value or "").lower()
            key = None
            if kind == "Fan":
                key = "Fan"
            elif kind == "Temperature":
                if "cpu" in identity:
                    key = "CPU"
                elif "gpu" in identity:
                    key = "GPU"
                elif any(part in identity for part in ("nvme", "hdd", "ssd")):
                    key = "SSD"
                elif "ambient" in name:
                    key = "Ambient"
            value = number(sensor.Properties_("Value").Value, 0, 20000 if key == "Fan" else 125)
            if key and value is not None:
                previous = readings.get(key)
                readings[key] = max(previous, value) if previous is not None else value
        except Exception:
            continue


def _nvidia_temperature():
    # Use the installed driver, with pointer-safe declarations on 64-bit Windows.
    try:
        path = Path(os.environ.get("WINDIR", "C:/Windows")) / "System32" / "nvml.dll"
        nvml = ctypes.CDLL(str(path))
        nvml.nvmlInit_v2.argtypes = []
        nvml.nvmlInit_v2.restype = ctypes.c_int
        nvml.nvmlShutdown.argtypes = []
        nvml.nvmlShutdown.restype = ctypes.c_int
        nvml.nvmlDeviceGetHandleByIndex_v2.argtypes = [ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p)]
        nvml.nvmlDeviceGetHandleByIndex_v2.restype = ctypes.c_int
        nvml.nvmlDeviceGetTemperature.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_uint)]
        nvml.nvmlDeviceGetTemperature.restype = ctypes.c_int
        if nvml.nvmlInit_v2() != 0:
            return None
        try:
            handle, value = ctypes.c_void_p(), ctypes.c_uint()
            if nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(handle)) == 0:
                if nvml.nvmlDeviceGetTemperature(handle, 0, ctypes.byref(value)) == 0:
                    return number(value.value, 0, 125)
        finally:
            nvml.nvmlShutdown()
    except (AttributeError, OSError):
        pass
    return None


def _collect_sensors():
    readings = dict.fromkeys(SENSOR_KEYS)
    try:
        import pythoncom
        import win32com.client
        hr = ctypes.windll.ole32.CoInitialize(None)
        locator = services = rows = None
        try:
            locator = win32com.client.Dispatch("WbemScripting.SWbemLocator")
            for namespace in (r"root\LibreHardwareMonitor", r"root\OpenHardwareMonitor"):
                try:
                    services = locator.ConnectServer(".", namespace)
                    rows = services.ExecQuery("SELECT Identifier, Name, SensorType, Value FROM Sensor WHERE SensorType='Temperature' OR SensorType='Fan'")
                    merge_monitor_sensors(readings, rows)
                except Exception:
                    continue
            # Firmware thermal zones provide hardware ACPI & EC CPU package temperatures
            try:
                services = locator.ConnectServer(".", r"root\cimv2")
                rows = services.ExecQuery("SELECT Name, Temperature FROM Win32_PerfFormattedData_Counters_ThermalZoneInformation")
                for row in rows:
                    name = str(row.Properties_("Name").Value or "").upper()
                    kelvin = number(row.Properties_("Temperature").Value, 273.15, 398.15)
                    if kelvin is not None:
                        celsius = kelvin - 273.15
                        readings["ACPI"] = max(readings["ACPI"] or 0, celsius)
                        if "EC0" in name or "TZRZ" in name:
                            readings["CPU"] = max(readings["CPU"] or 0, celsius)
                row = None
            except Exception:
                pass
            if readings["CPU"] is None and readings.get("ACPI") is not None:
                readings["CPU"] = readings["ACPI"]
        finally:
            # Release COM objects on their creating thread before uninitializing.
            rows = services = locator = None
            if hr == 0:
                try:
                    ctypes.windll.ole32.CoUninitialize()
                except Exception:
                    pass
    except Exception:
        pass
    if readings["GPU"] is None:
        readings["GPU"] = _nvidia_temperature()
    return readings


def get_sensor_readings(force=False):
    """Both pages share one cached snapshot; UI refreshes cannot race providers."""
    global _cached, _expires
    with _lock:
        if force or _cached is None or time.monotonic() >= _expires:
            _cached = _collect_sensors()
            _expires = time.monotonic() + (5 if any(v is not None for v in _cached.values()) else 30)
        return dict(_cached)

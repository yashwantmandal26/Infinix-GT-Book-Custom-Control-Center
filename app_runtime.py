"""Runtime primitives with no GUI or device dependencies."""
from collections import deque
import copy
import json
import os
from pathlib import Path
import shutil
import threading
import time


class LightingHistory:
    """Bounded, independent lighting snapshots; a slider drag is one edit."""
    keys = ("zones", "brightness", "effect_mode", "animation_speed",
            "animation_direction", "current_color", "current_theme",
            "screen_sync_mode", "always_on")

    def __init__(self, config, limit=40):
        self.states = [self.snapshot(config)]
        self.index = 0
        self.limit = limit
        self.last_change = set()
        self.last_time = 0

    @classmethod
    def snapshot(cls, config):
        return copy.deepcopy({k: config[k] for k in cls.keys if k in config})

    def record(self, config, now=None):
        state = self.snapshot(config)
        current = self.states[self.index]
        changed = {k for k in set(state) | set(current) if state.get(k) != current.get(k)}
        if not changed:
            return
        now = time.monotonic() if now is None else now
        coalesce = (self.index == len(self.states)-1 and self.index > 0
                    and changed == self.last_change == {"brightness"}
                    and now-self.last_time < .75)
        del self.states[self.index+1:]
        if coalesce:
            self.states[self.index] = state
        else:
            self.states.append(state)
            self.states = self.states[-self.limit:]
            self.index = len(self.states)-1
        self.last_change, self.last_time = changed, now

    def move(self, delta):
        target = self.index + delta
        if not 0 <= target < len(self.states):
            return None
        self.index = target
        self.last_change = set()
        return copy.deepcopy(self.states[target])


class UiMailbox:
    """Workers enqueue Python values; only the UI thread drains callbacks."""
    def __init__(self):
        self._lock = threading.Lock()
        self._events = deque()
        self._latest = {}
        self.closed = False

    def post(self, callback, args=(), kwargs=None, key=None):
        with self._lock:
            if self.closed:
                return
            item = (callback, args, kwargs or {})
            if key is None:
                self._events.append(item)
            else:
                self._latest[key] = item

    def take(self, limit=32):
        with self._lock:
            result = [self._events.popleft() for _ in range(min(limit, len(self._events)))]
            for key in list(self._latest)[:max(0, limit - len(result))]:
                result.append(self._latest.pop(key))
            return result

    def close(self):
        with self._lock:
            self.closed = True
            self._events.clear()
            self._latest.clear()


class ConfigWriter:
    """Coalesce slider changes; serialize durable writes away from Tk's thread."""
    def __init__(self, path, on_error=None, delay=0.35):
        self.path = Path(path)
        self.on_error = on_error
        self.delay = delay
        self._condition = threading.Condition()
        self._pending = None
        self._deadline = 0.0
        self._closing = False
        self._thread = None
        self.write_count = 0
        self.last_error = None

    def submit(self, config):
        snapshot = copy.deepcopy(config)
        with self._condition:
            if self._closing:
                return
            self._pending = snapshot
            self._deadline = time.monotonic() + self.delay
            if self._thread is None:
                self._thread = threading.Thread(target=self._run, name="SettingsWriter", daemon=True)
                self._thread.start()
            self._condition.notify()

    def _write(self, snapshot):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with temporary.open("w", encoding="utf-8") as stream:
                json.dump(snapshot, stream, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            if self.path.exists():
                shutil.copy2(self.path, str(self.path) + ".bak")
            os.replace(temporary, self.path)
            self.write_count += 1
            self.last_error = None
        except Exception as error:
            self.last_error = str(error)
            if self.on_error:
                self.on_error(str(error))

    def _run(self):
        while True:
            with self._condition:
                while self._pending is None and not self._closing:
                    self._condition.wait()
                if self._pending is None:
                    return
                wait = self._deadline - time.monotonic()
                if wait > 0 and not self._closing:
                    self._condition.wait(wait)
                    continue
                snapshot, self._pending = self._pending, None
            self._write(snapshot)

    def close(self, timeout=3.0):
        """Flush the final snapshot before normal process shutdown."""
        with self._condition:
            self._closing = True
            self._condition.notify()
        if self._thread:
            self._thread.join(timeout)
        finished = self._thread is None or not self._thread.is_alive()
        if finished and self.last_error:
            with self._condition:
                self._closing = False
                self._thread = None
        return not self.last_error and finished


def validate_rear_profile(data, modes):
    """Accept saved presets and exported profiles, rejecting invalid files atomically."""
    if not isinstance(data, dict):
        raise ValueError("A rear-light profile must be a JSON object.")
    result = {}
    defaults = dict(mode=1, color1=[56, 189, 248], color2=[167, 139, 250], speed=4, brightness=100)
    if not any(key in data or "bz_" + key in data for key in defaults):
        raise ValueError("This file does not contain a rear-light profile.")
    for key, default in defaults.items():
        result[key] = copy.deepcopy(data.get(key, data.get("bz_" + key, default)))
    for key in ("color1", "color2"):
        color = result[key]
        if not isinstance(color, (list, tuple)) or len(color) != 3 or any(
            type(channel) is not int or not 0 <= channel <= 255 for channel in color
        ):
            raise ValueError(f"{key} must contain three RGB values from 0 to 255.")
        result[key] = list(color)
    for key, low, high in (("speed", 1, 9), ("brightness", 0, 100)):
        if type(result[key]) is not int or not low <= result[key] <= high:
            raise ValueError(f"{key} must be an integer from {low} to {high}.")
    if type(result["mode"]) is not int or result["mode"] not in modes:
        raise ValueError("Unknown rear-light effect.")
    options = {}
    for key in ("mecha_bar_sync", "bz_turn_off_on_battery", "bz_night_schedule_enabled"):
        if key in data:
            if type(data[key]) is not bool:
                raise ValueError(f"{key} must be true or false.")
            options[key] = data[key]
    if "bz_fps_limit" in data:
        if type(data["bz_fps_limit"]) is not int or not 10 <= data["bz_fps_limit"] <= 30:
            raise ValueError("Frame rate must be between 10 and 30.")
        options["bz_fps_limit"] = data["bz_fps_limit"]
    result["options"] = options
    return result

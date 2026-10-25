"""Smart Fan Curve & Thermal Governor Engine for Infinix GT Book.

Provides dynamic temperature-to-RPM curves, hysteresis filtering, and visual
Canvas graph rendering for custom exhaust fan tuning.
"""
from typing import Dict, List, Optional, Tuple
import math
import threading

FAN_CURVE_PRESETS: Dict[str, List[Tuple[float, float]]] = {
    "quiet": [
        (45.0, 0.0),
        (55.0, 30.0),
        (68.0, 45.0),
        (78.0, 65.0),
        (88.0, 80.0),
    ],
    "balanced": [
        (40.0, 0.0),
        (50.0, 38.0),
        (65.0, 55.0),
        (75.0, 75.0),
        (85.0, 90.0),
    ],
    "aggressive": [
        (38.0, 35.0),
        (50.0, 55.0),
        (65.0, 75.0),
        (75.0, 90.0),
        (82.0, 100.0),
    ],
    "custom_default": [
        (40.0, 25.0),
        (50.0, 40.0),
        (65.0, 60.0),
        (75.0, 80.0),
        (85.0, 95.0),
    ],
}


def normalize_curve_points(points) -> List[Tuple[float, float]]:
    """Sanitize and sort curve node pairs to strictly monotonic temperatures."""
    result = []
    if isinstance(points, (list, tuple)):
        for item in points:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                try:
                    t = max(20.0, min(105.0, float(item[0])))
                    p = max(0.0, min(100.0, float(item[1])))
                    result.append((t, p))
                except (ValueError, TypeError):
                    continue
    if len(result) < 2:
        return list(FAN_CURVE_PRESETS["balanced"])
    result.sort(key=lambda pair: pair[0])
    return result


def interpolate_fan_speed(temp: float, curve_points: List[Tuple[float, float]]) -> int:
    """Linearly interpolate target exhaust fan duty cycle from a temperature."""
    pts = normalize_curve_points(curve_points)
    if not pts:
        return 0
    t_val = float(temp)
    if t_val <= pts[0][0]:
        return int(round(pts[0][1]))
    if t_val >= pts[-1][0]:
        return int(round(pts[-1][1]))

    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        if x1 <= t_val <= x2:
            if math.isclose(x2, x1):
                return int(round(y1))
            ratio = (t_val - x1) / (x2 - x1)
            interpolated = y1 + ratio * (y2 - y1)
            return int(round(max(0.0, min(100.0, interpolated))))
    return int(round(pts[-1][1]))


class FanCurveGovernor:
    """Autonomous thermal governor that smoothly commands fan duty cycles."""

    def __init__(self, hysteresis_c: float = 3.0, deadband_pct: int = 2):
        self._lock = threading.Lock()
        self.hysteresis_c = max(1.0, float(hysteresis_c))
        self.deadband_pct = max(1, int(deadband_pct))
        self._temp_history: List[float] = []
        self._max_history = 4
        self.current_smoothed_temp: Optional[float] = None
        self.last_commanded_speed: Optional[int] = None
        self._high_watermark_temp: float = 0.0

    def feed_sample(self, cpu_temp: Optional[float], gpu_temp: Optional[float]) -> Optional[float]:
        """Record and smooth live sensor temperatures using a moving-average filter."""
        with self._lock:
            valid = [float(v) for v in (cpu_temp, gpu_temp) if v is not None and 10.0 <= float(v) <= 120.0]
            if not valid:
                return self.current_smoothed_temp
            sample = max(valid)
            self._temp_history.append(sample)
            if len(self._temp_history) > self._max_history:
                self._temp_history.pop(0)
            self.current_smoothed_temp = sum(self._temp_history) / float(len(self._temp_history))
            return self.current_smoothed_temp

    def get_curve_points_for_mode(self, mode: str, custom_points: Optional[list] = None) -> Optional[List[Tuple[float, float]]]:
        if mode == "quiet":
            return FAN_CURVE_PRESETS["quiet"]
        elif mode == "balanced":
            return FAN_CURVE_PRESETS["balanced"]
        elif mode == "aggressive":
            return FAN_CURVE_PRESETS["aggressive"]
        elif mode == "custom":
            return normalize_curve_points(custom_points) if custom_points else FAN_CURVE_PRESETS["custom_default"]
        return None

    def evaluate(
        self,
        cpu_temp: Optional[float],
        gpu_temp: Optional[float],
        mode: str,
        custom_points: Optional[list] = None,
    ) -> Optional[int]:
        """Evaluate if an EC fan speed update should be dispatched."""
        with self._lock:
            if mode in ("auto", "oem"):
                if self.last_commanded_speed is not None and self.last_commanded_speed != 0:
                    self.last_commanded_speed = 0
                    return 0
                return None

            if mode == "manual":
                return None

            curve = self.get_curve_points_for_mode(mode, custom_points)
            if not curve:
                return None

            valid = [float(v) for v in (cpu_temp, gpu_temp) if v is not None and 10.0 <= float(v) <= 120.0]
            if not valid:
                current = self.current_smoothed_temp
            else:
                sample = max(valid)
                self._temp_history.append(sample)
                if len(self._temp_history) > self._max_history:
                    self._temp_history.pop(0)
                self.current_smoothed_temp = sum(self._temp_history) / float(len(self._temp_history))
                current = self.current_smoothed_temp

            if current is None:
                return None

            raw_target = interpolate_fan_speed(current, curve)

            # Anti-hunting Hysteresis:
            # If temperature is rising, update high watermark immediately and scale up instantly.
            # If temperature is falling, require a temperature drop >= hysteresis_c before downscaling fan.
            if self.last_commanded_speed is None:
                self._high_watermark_temp = current
                self.last_commanded_speed = raw_target
                return raw_target

            if current > self._high_watermark_temp:
                self._high_watermark_temp = current
                if raw_target > self.last_commanded_speed and (raw_target - self.last_commanded_speed) >= self.deadband_pct:
                    self.last_commanded_speed = raw_target
                    return raw_target
            elif current < (self._high_watermark_temp - self.hysteresis_c):
                # Safe downward step
                self._high_watermark_temp = current
                if raw_target < self.last_commanded_speed and (self.last_commanded_speed - raw_target) >= self.deadband_pct:
                    self.last_commanded_speed = raw_target
                    return raw_target

            return None

    def reset(self):
        with self._lock:
            self._temp_history.clear()
            self.current_smoothed_temp = None
            self.last_commanded_speed = None
            self._high_watermark_temp = 0.0


def _resolve_color(val, dark_mode: bool = True, default: str = "#181A20") -> str:
    """Resolve theme colors that may be a (light, dark) tuple into a single Tkinter hex string."""
    if not val:
        return default
    if isinstance(val, (tuple, list)):
        return str(val[1] if dark_mode else val[0])
    return str(val)


def render_curve_graph(
    canvas,
    width: int,
    height: int,
    curve_points: List[Tuple[float, float]],
    current_temp: Optional[float] = None,
    active_speed_pct: Optional[int] = None,
    mode_name: str = "Balanced Curve",
    colors: Optional[dict] = None,
    dark_mode: bool = True,
):
    """Render a modern visual fan curve graph onto a Tkinter Canvas widget."""
    try:
        canvas.delete("all")
    except Exception:
        return

    c_bg = _resolve_color(colors.get("card_sub_bg") if colors else None, dark_mode, "#181A20")
    c_line = _resolve_color(colors.get("accent_blue") if colors else None, dark_mode, "#38BDF8")
    c_grid = _resolve_color(colors.get("card_border") if colors else None, dark_mode, "#272A34")
    c_text = _resolve_color(colors.get("text_muted") if colors else None, dark_mode, "#64748B")
    c_active = _resolve_color(colors.get("accent_amber") if colors else None, dark_mode, "#F59E0B")
    c_point = _resolve_color(colors.get("accent_purple") if colors else None, dark_mode, "#A78BFA")

    margin_left = 34
    margin_right = 16
    margin_top = 18
    margin_bottom = 22

    plot_w = max(10, width - margin_left - margin_right)
    plot_h = max(10, height - margin_top - margin_bottom)

    min_t, max_t = 30.0, 100.0
    min_p, max_p = 0.0, 100.0

    def to_canvas(t, p):
        x = margin_left + ((t - min_t) / (max_t - min_t)) * plot_w
        y = margin_top + (1.0 - ((p - min_p) / (max_p - min_p))) * plot_h
        return max(margin_left, min(width - margin_right, x)), max(margin_top, min(height - margin_bottom, y))

    # Background rounded container
    canvas.create_rectangle(0, 0, width, height, fill=c_bg, outline=c_grid, width=1)

    # Horizontal Gridlines (0%, 25%, 50%, 75%, 100%)
    for pct in (25, 50, 75, 100):
        _, y = to_canvas(min_t, pct)
        canvas.create_line(margin_left, y, width - margin_right, y, fill=c_grid, dash=(2, 4))
        canvas.create_text(margin_left - 6, y, text=f"{pct}%", fill=c_text, font=("Segoe UI", 8), anchor="e")

    # Vertical Gridlines (40°C, 60°C, 80°C, 100°C)
    for t_deg in (40, 60, 80, 100):
        x, _ = to_canvas(t_deg, 0)
        canvas.create_line(x, margin_top, x, height - margin_bottom, fill=c_grid, dash=(2, 4))
        canvas.create_text(x, height - margin_bottom + 10, text=f"{t_deg}°C", fill=c_text, font=("Segoe UI", 8), anchor="n")

    # Curve Line Plot
    pts = normalize_curve_points(curve_points)
    coords = []
    # Smooth step interpolation along temperature range
    step = 2.0
    curr_t = min_t
    while curr_t <= max_t:
        p_val = interpolate_fan_speed(curr_t, pts)
        cx, cy = to_canvas(curr_t, p_val)
        coords.extend([cx, cy])
        curr_t += step

    if len(coords) >= 4:
        # Subtle filled under-curve area
        poly_coords = [margin_left, height - margin_bottom] + coords + [width - margin_right, height - margin_bottom]
        try:
            poly_fill = "#1E293B" if dark_mode else "#E2E8F0"
            canvas.create_polygon(poly_coords, fill=poly_fill, outline="")
        except Exception:
            pass
        canvas.create_line(coords, fill=c_line, width=2, smooth=True)

    # Node Points
    for pt in pts:
        px, py = to_canvas(pt[0], pt[1])
        canvas.create_oval(px - 4, py - 4, px + 4, py + 4, fill=c_point, outline="#FFFFFF", width=1.5)

    # Real-Time Live Temperature & Commanded Fan Needle
    if current_temp is not None and 20.0 <= current_temp <= 110.0:
        actual_temp = float(current_temp)
        c_pct = active_speed_pct if active_speed_pct is not None else interpolate_fan_speed(actual_temp, pts)
        nx, ny = to_canvas(actual_temp, c_pct)
        # Vertical needle
        canvas.create_line(nx, margin_top, nx, height - margin_bottom, fill=c_active, width=1.5, dash=(3, 2))
        # Pulsing live indicator dot
        canvas.create_oval(nx - 6, ny - 6, nx + 6, ny + 6, fill=c_active, outline="#FFFFFF", width=2)
        # Badge
        badge_text = f"Live: {actual_temp:.0f}°C • {c_pct}%"
        badge_x = min(width - margin_right - 45, max(margin_left + 45, nx))
        badge_bg = "#0F172A" if dark_mode else "#FFFFFF"
        canvas.create_rectangle(badge_x - 38, margin_top + 2, badge_x + 38, margin_top + 18, fill=badge_bg, outline=c_active, width=1)
        canvas.create_text(badge_x, margin_top + 10, text=badge_text, fill=c_active, font=("Segoe UI", 8, "bold"))

import unittest
from fan_curve_engine import (
    FAN_CURVE_PRESETS,
    normalize_curve_points,
    interpolate_fan_speed,
    FanCurveGovernor,
    render_curve_graph,
    _resolve_color,
)


class FanCurveEngineTests(unittest.TestCase):

    def test_normalize_curve_points(self):
        # Empty or invalid should fallback to balanced preset
        pts = normalize_curve_points([])
        self.assertEqual(pts, FAN_CURVE_PRESETS["balanced"])

        # Unsorted input should be sorted by temperature
        unsorted_input = [[70, 75], [40, 20], [50, 40]]
        normalized = normalize_curve_points(unsorted_input)
        self.assertEqual(normalized, [(40.0, 20.0), (50.0, 40.0), (70.0, 75.0)])

    def test_interpolation_boundary_clamps(self):
        curve = [(40.0, 20.0), (60.0, 50.0), (80.0, 90.0)]
        # Below lower bound
        self.assertEqual(interpolate_fan_speed(30.0, curve), 20)
        self.assertEqual(interpolate_fan_speed(40.0, curve), 20)

        # Above upper bound
        self.assertEqual(interpolate_fan_speed(80.0, curve), 90)
        self.assertEqual(interpolate_fan_speed(100.0, curve), 90)

        # Exact midpoint
        self.assertEqual(interpolate_fan_speed(50.0, curve), 35)

    def test_governor_feed_sample_smoothing(self):
        gov = FanCurveGovernor()
        # Feed sequence of temperatures
        gov.feed_sample(50.0, 45.0)
        self.assertEqual(gov.current_smoothed_temp, 50.0)

        gov.feed_sample(60.0, 55.0)
        self.assertEqual(gov.current_smoothed_temp, 55.0)  # avg of 50 and 60

    def test_governor_hysteresis_behavior(self):
        gov = FanCurveGovernor(hysteresis_c=3.0, deadband_pct=2)
        # 1. Initial evaluation triggers command
        initial_speed = gov.evaluate(cpu_temp=60.0, gpu_temp=None, mode="balanced")
        self.assertIsNotNone(initial_speed)
        self.assertEqual(gov.last_commanded_speed, initial_speed)

        # 2. Slight drop (1°C) within hysteresis window should NOT downshift
        no_change = gov.evaluate(cpu_temp=59.0, gpu_temp=None, mode="balanced")
        self.assertIsNone(no_change)
        self.assertEqual(gov.last_commanded_speed, initial_speed)

        # 3. Increase in temperature should scale up immediately
        higher_speed = gov.evaluate(cpu_temp=78.0, gpu_temp=None, mode="balanced")
        self.assertIsNotNone(higher_speed)
        self.assertGreater(higher_speed, initial_speed)

        # 4. Large drop exceeding 3°C hysteresis should downshift
        lower_speed = gov.evaluate(cpu_temp=45.0, gpu_temp=None, mode="balanced")
        self.assertIsNotNone(lower_speed)
        self.assertLess(lower_speed, higher_speed)

    def test_governor_oem_auto_and_manual_modes(self):
        gov = FanCurveGovernor()
        # In manual mode, governor does not evaluate curves
        self.assertIsNone(gov.evaluate(70.0, 70.0, mode="manual"))

        # Transitioning to auto should yield 0 once to restore dynamic EC curve
        gov.last_commanded_speed = 75
        res = gov.evaluate(70.0, 70.0, mode="auto")
        self.assertEqual(res, 0)
        # Next auto check should be None
        self.assertIsNone(gov.evaluate(70.0, 70.0, mode="auto"))


    def test_resolve_color_helper(self):
        # Tuple resolution
        self.assertEqual(_resolve_color(("#F3F7FC", "#0B1828"), dark_mode=True), "#0B1828")
        self.assertEqual(_resolve_color(("#F3F7FC", "#0B1828"), dark_mode=False), "#F3F7FC")
        # Direct string
        self.assertEqual(_resolve_color("#123456", dark_mode=True), "#123456")
        # Fallback default
        self.assertEqual(_resolve_color(None, dark_mode=True, default="#DEFAULT"), "#DEFAULT")

    def test_render_curve_graph_with_tuple_theme_colors(self):
        import tkinter as tk
        root = tk._default_root
        if root is None:
            root = tk.Tk()
            root.withdraw()
        canvas = tk.Canvas(root, width=600, height=155)
        theme_mock = {
            "card_sub_bg": ("#F3F7FC", "#0B1828"),
            "accent_blue": ("#0875B3", "#25C7FF"),
            "card_border": ("#CAD8EA", "#246296"),
            "text_muted": ("#5D7088", "#7894B5"),
            "accent_amber": ("#D97706", "#FBBF24"),
            "accent_purple": ("#7C3AED", "#A78BFA"),
        }
        # Should not raise _tkinter.TclError: invalid color name "#F3F7FC #0B1828"
        render_curve_graph(
            canvas, width=600, height=155,
            curve_points=FAN_CURVE_PRESETS["balanced"],
            current_temp=62.0, active_speed_pct=50,
            colors=theme_mock, dark_mode=True
        )
        render_curve_graph(
            canvas, width=600, height=155,
            curve_points=FAN_CURVE_PRESETS["aggressive"],
            current_temp=45.0, active_speed_pct=40,
            colors=theme_mock, dark_mode=False
        )
        canvas.destroy()


if __name__ == "__main__":
    unittest.main()

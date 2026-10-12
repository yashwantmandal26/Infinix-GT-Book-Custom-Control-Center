"""Behavioural checks for the four-zone keyboard motion effects."""

import unittest

from keyboard_motion import CUSTOM_MOTION_EFFECTS, render_custom_motion


class KeyboardMotionTests(unittest.TestCase):
    def setUp(self):
        self.primary = (0, 220, 255)
        self.secondary = (255, 30, 120)
        self.direction = "➡️ Left to Right"

    def frame(self, effect, step, direction=None):
        return render_custom_motion(
            effect, step, direction or self.direction, self.primary, self.secondary)

    def test_all_effects_have_four_bounded_independent_zones_and_motion(self):
        for effect in CUSTOM_MOTION_EFFECTS:
            with self.subTest(effect=effect):
                frames = [self.frame(effect, step) for step in (0, 15, 32, 44, 58, 72)]
                for frame in frames:
                    self.assertEqual(set(frame), {"1", "2", "3", "4"})
                    self.assertTrue(all(0 <= channel <= 255 for rgb in frame.values() for channel in rgb))
                self.assertGreater(len({tuple(frame.values()) for frame in frames}), 3)
                self.assertTrue(any(len(set(frame.values())) > 1 for frame in frames))

    def test_direction_mirrors_each_animation(self):
        for effect in CUSTOM_MOTION_EFFECTS:
            with self.subTest(effect=effect):
                forward = self.frame(effect, 17)
                reverse = self.frame(effect, 17, "⬅️ Right to Left")
                self.assertEqual(tuple(forward[str(i)] for i in range(1, 5)),
                                 tuple(reverse[str(i)] for i in range(4, 0, -1)))

    def test_phase_signatures_are_distinct(self):
        slingshot = self.frame("MagneticSlingshot", 45)
        self.assertGreater(sum(slingshot["2"]), sum(slingshot["1"]))
        relay_start = self.frame("ChromaticRelay", 0)
        relay_handoff = self.frame("ChromaticRelay", 20)
        self.assertGreater(sum(relay_start["1"]), sum(relay_start["2"]))
        self.assertGreater(sum(relay_handoff["2"]), sum(relay_handoff["1"]))
        self.assertEqual(self.frame("TimeFracture", 37), self.frame("TimeFracture", 43))
        eclipse = self.frame("OrbitalEclipse", 48)
        self.assertNotEqual(eclipse["2"], eclipse["4"])


if __name__ == "__main__":
    unittest.main()

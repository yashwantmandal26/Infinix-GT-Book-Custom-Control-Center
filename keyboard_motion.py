"""Four-zone motion effects for the GT Book keyboard controller."""

import colorsys
import math


CUSTOM_MOTION_EFFECTS = (
    "MagneticSlingshot",
    "ChromaticRelay",
    "TimeFracture",
    "OrbitalEclipse",
)

MOTION_PERIODS = {
    "MagneticSlingshot": 120.0, "ChromaticRelay": 160.0,
    "TimeFracture": 144.0, "OrbitalEclipse": 160.0,
}


def _clamp(value):
    return max(0, min(255, int(round(value))))


def _mix(left, right, amount):
    amount = max(0.0, min(1.0, amount))
    return tuple(_clamp(a * (1.0 - amount) + b * amount) for a, b in zip(left, right))


def _scale(color, amount):
    return tuple(_clamp(channel * amount) for channel in color)


def _glow(position, centre, width=0.55):
    return math.exp(-0.5 * ((position - centre) / width) ** 2)


def _accent(primary, secondary):
    if sum(abs(a - b) for a, b in zip(primary, secondary)) >= 100:
        return secondary
    hue, saturation, value = colorsys.rgb_to_hsv(*(channel / 255.0 for channel in primary))
    return tuple(_clamp(channel * 255) for channel in colorsys.hsv_to_rgb(
        (hue + 0.48) % 1.0, max(0.7, saturation), max(0.7, value)))


def _ease(value):
    return value ** 3 * (value * (value * 6.0 - 15.0) + 10.0)


def _color_flow(primary, secondary, amount):
    """Blend around the hue wheel to keep the handoff saturated."""
    h1, s1, v1 = colorsys.rgb_to_hsv(*(c / 255.0 for c in primary))
    h2, s2, v2 = colorsys.rgb_to_hsv(*(c / 255.0 for c in secondary))
    if s1 < 0.01:
        h1 = h2
    if s2 < 0.01:
        h2 = h1
    distance = (h2 - h1 + 0.5) % 1.0 - 0.5
    return tuple(_clamp(c * 255) for c in colorsys.hsv_to_rgb(
        (h1 + distance * amount) % 1.0,
        s1 + (s2 - s1) * amount, v1 + (v2 - v1) * amount))


def _time_position(phase):
    # Forward sweep, suspended crest, rewind, release, then return home.
    beats = ((0, 0), (48, 3), (60, 3), (84, 1), (108, 3), (144, 0))
    for (start, left), (end, right) in zip(beats, beats[1:]):
        if phase <= end:
            return left + (right - left) * _ease((phase - start) / (end - start))
    return 0.0


def render_custom_motion(effect, step, direction, primary, secondary):
    """Return four RGB zones with continuous loops and no full-keyboard flashes."""
    if effect not in CUSTOM_MOTION_EFFECTS:
        raise ValueError(f"Unsupported custom motion effect: {effect}")
    primary = tuple(primary)
    secondary = _accent(primary, tuple(secondary))
    reverse = "Right to Left" in direction
    zones = {}

    period = MOTION_PERIODS[effect]
    phase = step % period
    angle = math.tau * phase / period

    if effect == "MagneticSlingshot":
        # Two ribbons cross and trade sides, braking gently at the edges.
        left = 1.5 - 1.5 * math.cos(angle)
        right = 3.0 - left
        collision = math.exp(-0.5 * (math.cos(angle) / 0.22) ** 2)
        for index in range(4):
            a, b = _glow(index, left, 0.72), _glow(index, right, 0.72)
            color = _color_flow(primary, secondary, b / max(0.001, a + b))
            intensity = 0.18 + 0.72 * max(a, b)
            intensity += 0.10 * collision * _glow(index, 1.5, 0.85)
            zones[str(index + 1)] = _scale(color, intensity)

    elif effect == "ChromaticRelay":
        # A broad saturated ribbon passes color smoothly between hardware zones.
        for index in range(4):
            local = angle - index * math.pi / 2.0
            handoff = (1.0 + math.cos(local)) / 2.0
            crest = ((1.0 + math.cos(local - 0.55)) / 2.0) ** 2
            color = _color_flow(primary, secondary, handoff)
            zones[str(index + 1)] = _scale(color, 0.28 + 0.72 * crest)

    elif effect == "TimeFracture":
        position = _time_position(phase)
        echo = _time_position((phase - 12.0) % period)
        for index in range(4):
            crest = _glow(index, position, 0.62)
            trail = _glow(index, echo, 0.85)
            color = _color_flow(primary, secondary, crest / max(0.001, crest + trail * 0.65))
            zones[str(index + 1)] = _scale(color, 0.18 + 0.62 * crest + 0.20 * trail)

    else:  # OrbitalEclipse
        # Circular distance keeps the last-to-first shadow handoff continuous.
        blend = (1.0 - math.cos(angle)) / 2.0
        background = _color_flow(primary, secondary, blend)
        rim_color = _color_flow(secondary, primary, blend)
        centre = phase * 4.0 / period
        for index in range(4):
            distance = (index - centre + 2.0) % 4.0 - 2.0
            shadow = _glow(distance, 0.0, 0.48)
            rim = max(_glow(distance, -0.85, 0.42), _glow(distance, 0.85, 0.42))
            color = _scale(background, 0.60 - 0.44 * shadow)
            zones[str(index + 1)] = _mix(color, rim_color, 0.88 * rim)

    if reverse:
        return {str(index + 1): zones[str(4 - index)] for index in range(4)}
    return zones

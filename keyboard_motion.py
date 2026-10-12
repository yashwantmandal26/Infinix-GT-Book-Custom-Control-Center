"""Four-zone motion effects for the GT Book keyboard controller."""

import colorsys
import math


CUSTOM_MOTION_EFFECTS = (
    "MagneticSlingshot",
    "ChromaticRelay",
    "TimeFracture",
    "OrbitalEclipse",
)


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


def render_custom_motion(effect, step, direction, primary, secondary):
    """Return four RGB zones; step advances once per keyboard animation frame."""
    if effect not in CUSTOM_MOTION_EFFECTS:
        raise ValueError(f"Unsupported custom motion effect: {effect}")
    primary = tuple(primary)
    secondary = _accent(primary, tuple(secondary))
    reverse = "Right to Left" in direction
    zones = {}

    if effect == "MagneticSlingshot":
        phase = step % 96.0
        swapped = int(step // 96.0) % 2 == 1
        left_color, right_color = (secondary, primary) if swapped else (primary, secondary)
        if phase < 40:
            distance = 1.5 * (1.0 - phase / 40.0)
            left, right = 1.5 - distance, 1.5 + distance
            flash = 0.0
        elif phase < 50:
            left = right = 1.5
            flash = math.sin(math.pi * (phase - 40.0) / 10.0)
        elif phase < 78:
            distance = 2.2 * (phase - 50.0) / 28.0
            left, right = 1.5 - distance, 1.5 + distance
            left_color, right_color = right_color, left_color
            flash = 0.0
        else:
            left, right, flash = -1.0, 4.0, 0.0
        for index in range(4):
            luma_left = _glow(index, left)
            luma_right = _glow(index, right)
            color = _mix(_scale(left_color, 0.06), left_color, luma_left)
            color = tuple(_clamp(a + b * luma_right) for a, b in zip(color, right_color))
            zones[str(index + 1)] = _mix(color, (255, 255, 255), flash * _glow(index, 1.5, 0.9))

    elif effect == "ChromaticRelay":
        phase = step % 144.0
        leg = min(5, int(phase / 24.0))
        progress = (phase % 24.0) / 24.0
        path = (0, 1, 2, 3, 2, 1, 0)
        source = path[leg]
        target = path[leg + 1]
        handoff = progress * progress * (3.0 - 2.0 * progress)
        source_color = _mix(primary, secondary, leg / 6.0)
        target_color = _mix(primary, secondary, (leg + 1) / 6.0)
        for index in range(4):
            ambient = _scale(_mix(primary, secondary, index / 3.0), 0.09)
            if index == source:
                ambient = _mix(ambient, source_color, 0.92 * (1.0 - handoff))
            if index == target:
                ambient = _mix(ambient, target_color, 0.92 * handoff)
            zones[str(index + 1)] = ambient

    elif effect == "TimeFracture":
        phase = step % 96.0
        if phase < 36:
            position = 3.0 * phase / 36.0
            flash = 0.0
        elif phase < 48:
            position = 3.0
            flash = 0.50 if int(phase / 3.0) % 2 == 0 else 0.0
        elif phase < 64:
            position = 3.0 - 2.0 * (phase - 48.0) / 16.0
            flash = 0.0
        elif phase < 78:
            position = 1.0 + 2.0 * (phase - 64.0) / 14.0
            flash = 0.0
        else:
            position = 3.0 + (phase - 78.0) / 5.0
            flash = 0.0
        for index in range(4):
            base = _scale(primary, 0.07)
            crest = _glow(index, position, 0.48)
            trail = _glow(index, position - 0.9, 0.7) * 0.33
            color = _mix(base, secondary, min(1.0, crest + trail))
            zones[str(index + 1)] = _mix(color, (255, 255, 255), flash * crest)

    else:  # OrbitalEclipse
        phase = step % 96.0
        position = -1.2 + 5.4 * phase / 96.0
        background = primary if int(step // 96.0) % 2 == 0 else secondary
        rim_color = secondary if background == primary else primary
        for index in range(4):
            shadow = _glow(index, position, 0.62)
            rim = max(_glow(index, position - 0.83, 0.34),
                      _glow(index, position + 0.83, 0.34))
            color = _scale(background, 0.38 * (1.0 - shadow) + 0.025)
            zones[str(index + 1)] = _mix(color, rim_color, min(1.0, rim * 0.95))

    if reverse:
        return {str(index + 1): zones[str(4 - index)] for index in range(4)}
    return zones

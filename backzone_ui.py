"""
Infinix GT Book - Rear Mecha Bar (Chassis Lighting) Module
==========================================================
Complete subsystem for the rear adaptive LED interface:
- 12 Software & Reactive effects + 7 OEM Firmware modes
- Categorized effect cards: Firmware, Animated, Audio, System
- Live animated visual preview canvas
- Dynamic contextual controls
- Audio loopback integration (Volume, Bass, Bands)
- Temperature & Battery reactive lighting
- Preset management with JSON export/import
- Time-of-day scheduling, Turn off on battery, and UART FPS throttling
"""

import os
import time
import math
import json
import random
import colorsys
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox
from typing import Dict, Tuple, List, Optional, Any
import customtkinter as ctk
import neon_ui
import color_studio
from app_runtime import validate_rear_profile

# ---------------------------------------------------------------------------
# Color Math & Processing Helpers
# ---------------------------------------------------------------------------

def vivid_rgb(rgb) -> Tuple[int, int, int]:
    """Force chromatic colors to full saturation while preserving brightness."""
    r, g, b = (max(0, min(255, int(v))) for v in rgb)
    if max(r, g, b) == 0 or max(r, g, b) == min(r, g, b):
        return r, g, b
    hue, _sat, value = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    return tuple(int(round(v * 255)) for v in colorsys.hsv_to_rgb(hue, 1.0, value))


def interpolate_hue_shortest(c1: Tuple[int, int, int], c2: Tuple[int, int, int], blend: float) -> Tuple[int, int, int]:
    """Interpolate between two RGB colors along the shortest arc in HSV hue space."""
    blend = max(0.0, min(1.0, float(blend)))
    h1, s1, v1 = colorsys.rgb_to_hsv(*(v / 255.0 for v in c1))
    h2, s2, v2 = colorsys.rgb_to_hsv(*(v / 255.0 for v in c2))
    
    # Shortest circular path on hue circle [0.0, 1.0)
    dh = (h2 - h1 + 0.5) % 1.0 - 0.5
    h = (h1 + dh * blend) % 1.0
    s = s1 + (s2 - s1) * blend
    v = v1 + (v2 - v1) * blend
    
    return tuple(int(round(x * 255)) for x in colorsys.hsv_to_rgb(h, max(0.0, min(1.0, s)), max(0.0, min(1.0, v))))


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    r, g, b = (max(0, min(255, int(v))) for v in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def hex_to_rgb(hex_str: str) -> Optional[Tuple[int, int, int]]:
    hex_str = hex_str.strip().lstrip("#")
    if len(hex_str) == 6:
        try:
            return (int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# Mode Definitions and Metadata
# ---------------------------------------------------------------------------

BACKZONE_MODE_NAMES: Dict[int, str] = {
    # Firmware Modes
    1: "Always On",
    2: "Breath",
    3: "Music Rhythm",
    4: "Music Jump",
    5: "Game Loop",
    6: "Game Cover",
    15: "Off",

    # Animated Software Effects
    101: "Full Spectrum",
    102: "Dual-Color Morph",
    105: "Aurora Flow",
    106: "Lava Flow",
    107: "Ocean Pulse",
    108: "Heartbeat",
    109: "Lightning",

    # Audio-Reactive Software Effects
    110: "Audio Pulse",
    111: "Audio Color Cycle",

    # System-Reactive Software Effects
    112: "Temperature Reactive",
    113: "Battery / Charging Status",
    114: "Game Mode Reactive",
    
    # Battle & Arcade Choreographed 36-LED Effects
    201: "Team Clash 2.0",
    202: "Beam Struggle",
    203: "Sumo Knockout",
    204: "Retro Pac-Man",
    205: "Breakout",
    206: "Newton's Cradle",
    207: "Capacitor Arc",
    208: "Quantum Tunneling",
    209: "Cyber-Centipede",
    210: "Mitosis",

    # Legacy aliases
    103: "Comet Pulse",
    104: "Cyber Strobe",
}

# Rich metadata per effect for UI cards and dynamic controls
EFFECT_METADATA: Dict[int, Dict[str, Any]] = {
    # FIRMWARE
    1: {
        "category": "Firmware",
        "name": "Always On",
        "badge": "Firmware",
        "icon": "💡",
        "description": "Solid stationary illumination powered by OEM microcontroller.",
        "has_speed": False,
        "has_color1": True,
        "has_color2": False,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    2: {
        "category": "Firmware",
        "name": "Breath",
        "badge": "Firmware",
        "icon": "🫁",
        "description": "Smooth hardware breathing cycle with selectable speed.",
        "has_speed": True,
        "has_color1": True,
        "has_color2": False,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    3: {
        "category": "Firmware",
        "name": "Music Rhythm",
        "badge": "Firmware",
        "icon": "🎵",
        "description": "Hardware-level acoustic rhythm effect using dual colors.",
        "has_speed": True,
        "has_color1": True,
        "has_color2": True,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    4: {
        "category": "Firmware",
        "name": "Music Jump",
        "badge": "Firmware",
        "icon": "🎶",
        "description": "Firmware beat-jumping effect with color alternation.",
        "has_speed": True,
        "has_color1": True,
        "has_color2": True,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    5: {
        "category": "Firmware",
        "name": "Game Loop",
        "badge": "Firmware",
        "icon": "🎮",
        "description": "OEM gaming light sequence with dual-color sweep.",
        "has_speed": True,
        "has_color1": True,
        "has_color2": True,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    6: {
        "category": "Firmware",
        "name": "Game Cover",
        "badge": "Firmware",
        "icon": "🕹️",
        "description": "OEM game cover animation utilizing firmware color registers.",
        "has_speed": True,
        "has_color1": True,
        "has_color2": True,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    15: {
        "category": "Firmware",
        "name": "Off",
        "badge": "Firmware",
        "icon": "🌑",
        "description": "Rear light bar power cut / zero brightness.",
        "has_speed": False,
        "has_color1": False,
        "has_color2": False,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },

    # ANIMATED
    101: {
        "category": "Animated",
        "name": "Full Spectrum",
        "badge": "Software",
        "icon": "🌈",
        "description": "Smooth continuous red-through-violet rainbow cycle across strip.",
        "has_speed": True,
        "has_color1": False,
        "has_color2": False,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    102: {
        "category": "Animated",
        "name": "Dual-Color Morph",
        "badge": "Software",
        "icon": "🔮",
        "description": "Shortest-path hue interpolation smoothly blending Primary & Secondary.",
        "has_speed": True,
        "has_color1": True,
        "has_color2": True,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    105: {
        "category": "Animated",
        "name": "Aurora Flow",
        "badge": "Software",
        "icon": "🌌",
        "description": "Luminescent green, cyan, deep blue, and violet polar aurora transitions.",
        "has_speed": True,
        "has_color1": False,
        "has_color2": False,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    106: {
        "category": "Animated",
        "name": "Lava Flow",
        "badge": "Software",
        "icon": "🌋",
        "description": "Deep crimson, magma orange, and ember yellow with fluid thermal brightness.",
        "has_speed": True,
        "has_color1": False,
        "has_color2": False,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    107: {
        "category": "Animated",
        "name": "Ocean Pulse",
        "badge": "Software",
        "icon": "🌊",
        "description": "Submerged deep blues, turquoise, and marine cyan with layered slow tides.",
        "has_speed": True,
        "has_color1": False,
        "has_color2": False,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    108: {
        "category": "Animated",
        "name": "Heartbeat",
        "badge": "Software",
        "icon": "💓",
        "description": "Cardiovascular double-pulse (lub-dub) rhythm with configurable tempo.",
        "has_speed": True,
        "has_color1": True,
        "has_color2": False,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    109: {
        "category": "Animated",
        "name": "Lightning",
        "badge": "Software",
        "icon": "⚡",
        "description": "Sudden electric white/blue lightning discharges followed by exponential decay.",
        "has_speed": True,
        "has_color1": True,
        "has_color2": True,
        "has_audio": False,
        "has_temp": False,
        "warning": "⚠️ Photosensitivity Warning: Contains rapid flashing lights.",
    },

    # AUDIO
    110: {
        "category": "Audio",
        "name": "Audio Pulse",
        "badge": "Audio",
        "icon": "🔊",
        "description": "Reacts to real Windows playback. Overall volume drives brightness with bass peaks.",
        "has_speed": False,
        "has_color1": True,
        "has_color2": True,
        "has_audio": True,
        "has_temp": False,
        "warning": None,
    },
    111: {
        "category": "Audio",
        "name": "Audio Color Cycle",
        "badge": "Audio",
        "icon": "🎛️",
        "description": "Bass, mids, and treble frequency bands modulate strip hue dynamically.",
        "has_speed": False,
        "has_color1": False,
        "has_color2": False,
        "has_audio": True,
        "has_temp": False,
        "warning": None,
    },

    # SYSTEM
    112: {
        "category": "System",
        "name": "Temperature Reactive",
        "badge": "Reactive",
        "icon": "🌡️",
        "description": "Cyan when cool (<50°C), green under normal load, orange warm, red hot (>82°C).",
        "has_speed": False,
        "has_color1": False,
        "has_color2": False,
        "has_audio": False,
        "has_temp": True,
        "warning": None,
    },
    113: {
        "category": "System",
        "name": "Battery / Charging Status",
        "badge": "Reactive",
        "icon": "🔋",
        "description": "Green charging breath on AC; amber (<25%) and pulsing red (<15%) alerts on DC.",
        "has_speed": True,
        "has_color1": False,
        "has_color2": False,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    114: {
        "category": "System",
        "name": "Game Mode Reactive",
        "badge": "Reactive",
        "icon": "🎯",
        "description": "Automatically triggers high-performance lighting profile when games launch.",
        "has_speed": True,
        "has_color1": True,
        "has_color2": True,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    
    # Legacy fallbacks
    103: {
        "category": "Animated",
        "name": "Comet Pulse",
        "badge": "Software",
        "icon": "☄️",
        "description": "Sinusoidal brightness surge and decay.",
        "has_speed": True,
        "has_color1": True,
        "has_color2": False,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    104: {
        "category": "Animated",
        "name": "Cyber Strobe",
        "badge": "Software",
        "icon": "⚡",
        "description": "Rapid alternating strobe between two colors.",
        "has_speed": True,
        "has_color1": True,
        "has_color2": True,
        "has_audio": False,
        "has_temp": False,
        "warning": "⚠️ Photosensitivity Warning: Rapid strobe effects.",
    },
    201: {
        "category": "Battle & Arcade",
        "name": "Team Clash 2.0",
        "badge": "Choreographed",
        "icon": "⚔️",
        "description": "Matter vs Anti-matter: Dual armies advance, collide, and spark at center.",
        "has_speed": True,
        "has_color1": True,
        "has_color2": True,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    202: {
        "category": "Battle & Arcade",
        "name": "Beam Struggle",
        "badge": "Choreographed",
        "icon": "💥",
        "description": "Dragon Ball Z energy clash: Opposing laser beams wrestle for territory.",
        "has_speed": True,
        "has_color1": True,
        "has_color2": True,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    203: {
        "category": "Battle & Arcade",
        "name": "Sumo Knockout",
        "badge": "Choreographed",
        "icon": "🥊",
        "description": "Heavy kinetic pods collide at center, recoil, and battle for the edge.",
        "has_speed": True,
        "has_color1": True,
        "has_color2": True,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    204: {
        "category": "Battle & Arcade",
        "name": "Retro Pac-Man",
        "badge": "Choreographed",
        "icon": "👾",
        "description": "Pac-Man munches illuminated pellets along the strip, chased by a ghost.",
        "has_speed": True,
        "has_color1": True,
        "has_color2": True,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    205: {
        "category": "Battle & Arcade",
        "name": "Breakout",
        "badge": "Choreographed",
        "icon": "🧱",
        "description": "Bouncing light ball destroys a wall of colored brick segments one by one.",
        "has_speed": True,
        "has_color1": True,
        "has_color2": True,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    206: {
        "category": "Battle & Arcade",
        "name": "Newton's Cradle",
        "badge": "Choreographed",
        "icon": "⚖️",
        "description": "Kinetic energy transfer: Resting core passes momentum from edge to edge.",
        "has_speed": True,
        "has_color1": True,
        "has_color2": False,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    207: {
        "category": "Battle & Arcade",
        "name": "Capacitor Arc",
        "badge": "Choreographed",
        "icon": "⚡",
        "description": "Energy stacks cell-by-cell until a blinding high-voltage electric discharge.",
        "has_speed": True,
        "has_color1": True,
        "has_color2": True,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    208: {
        "category": "Battle & Arcade",
        "name": "Quantum Tunneling",
        "badge": "Choreographed",
        "icon": "🌌",
        "description": "Particles approach an impenetrable barrier, flicker, and teleport through.",
        "has_speed": True,
        "has_color1": True,
        "has_color2": True,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    209: {
        "category": "Battle & Arcade",
        "name": "Cyber-Centipede",
        "badge": "Choreographed",
        "icon": "🐛",
        "description": "Segmented cybernetic serpent slithers, pauses at corners, and crawls back.",
        "has_speed": True,
        "has_color1": True,
        "has_color2": True,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    },
    210: {
        "category": "Battle & Arcade",
        "name": "Mitosis",
        "badge": "Choreographed",
        "icon": "🧬",
        "description": "Core cell stretches, divides into child droplets, rebounds, and reunites.",
        "has_speed": True,
        "has_color1": True,
        "has_color2": True,
        "has_audio": False,
        "has_temp": False,
        "warning": None,
    }
}

# The OEM UART exposes autonomous two-colour motion (5/6), not a verified
# per-pixel upload command. Arcade drawings remain concept previews; never
# flatten them into a solid-colour hardware frame.
ARCADE_FIRMWARE_MODES = {
    201: 6, 202: 6, 203: 6, 204: 5, 205: 5,
    206: 5, 207: 6, 208: 5, 209: 5, 210: 6,
}
for _mode, _firmware_mode in ARCADE_FIRMWARE_MODES.items():
    EFFECT_METADATA[_mode]["warning"] = (
        f"Hardware: {BACKZONE_MODE_NAMES[_firmware_mode]} with both colours. "
        "The animation above is a concept preview; individual LED choreography "
        "is not available through the verified OEM protocol."
    )

ARCADE_BETA_MODES = frozenset(range(201, 211))


def available_rear_mode(mode):
    """Migrate unavailable beta selections to the safe static firmware mode."""
    return 1 if mode in ARCADE_BETA_MODES else mode


CATEGORIES = ["Firmware", "Animated", "Battle & Arcade", "Audio", "System"]

# Default Presets
DEFAULT_REAR_PRESETS: Dict[str, Dict[str, Any]] = {
    "Gaming Beast": {
        "mode": 109,  # Lightning
        "color1": [56, 189, 248],
        "color2": [244, 63, 94],
        "speed": 6,
        "brightness": 100,
    },
    "Cyberpunk Neon": {
        "mode": 102,  # Dual-Color Morph
        "color1": [236, 72, 153],  # Hot pink
        "color2": [6, 182, 212],   # Cyan
        "speed": 4,
        "brightness": 95,
    },
    "Deep Ocean": {
        "mode": 107,  # Ocean Pulse
        "color1": [14, 165, 233],
        "color2": [20, 184, 166],
        "speed": 3,
        "brightness": 80,
    },
    "Audio Rave": {
        "mode": 110,  # Audio Pulse
        "color1": [168, 85, 247],
        "color2": [236, 72, 153],
        "speed": 5,
        "brightness": 100,
    },
    "Battery Saver": {
        "mode": 1,    # Always On (low brightness)
        "color1": [34, 197, 94],
        "color2": [0, 0, 0],
        "speed": 1,
        "brightness": 20,
    },
}

# ---------------------------------------------------------------------------
# Core Software Render Engine
# ---------------------------------------------------------------------------

# Multi-stage color palettes
AURORA_PALETTE = [
    (16, 185, 129),   # Emerald green
    (6, 182, 212),    # Cyan
    (59, 130, 246),   # Cobalt blue
    (99, 102, 241),   # Indigo
    (139, 92, 246),   # Violet
    (16, 185, 129),   # Emerald green loop
]

LAVA_PALETTE = [
    (153, 27, 27),    # Dark red
    (220, 38, 38),    # Crimson
    (234, 88, 12),    # Orange
    (245, 158, 11),   # Amber
    (252, 211, 77),   # Bright yellow
    (234, 88, 12),    # Orange loop
]

OCEAN_PALETTE = [
    (15, 23, 42),     # Deep abyss
    (30, 58, 138),    # Royal navy
    (14, 165, 233),   # Ocean blue
    (45, 212, 191),   # Turquoise
    (14, 165, 233),   # Ocean blue loop
]


def sample_palette(palette: List[Tuple[int, int, int]], phase: float) -> Tuple[int, int, int]:
    """Sample an interpolated color from a list of RGB waypoints smoothly."""
    p = (phase % 1.0) * (len(palette) - 1)
    idx = int(p)
    frac = p - idx
    c1 = palette[idx]
    c2 = palette[min(idx + 1, len(palette) - 1)]
    return interpolate_hue_shortest(c1, c2, frac)



def render_backzone_strip_leds(
    mode: int,
    phase: float,
    color1,
    color2,
    brightness: int = 100,
    num_leds: int = 36,
    audio_volume: float = 0.0,
    audio_levels: Optional[List[float]] = None,
    audio_beat: float = 0.0,
    temp_celsius: float = 45.0,
    bat_pct: int = 100,
    on_ac: bool = True,
    audio_sensitivity: float = 1.0,
    audio_decay: float = 0.85,
    audio_attack: float = 0.5
) -> List[Tuple[int, int, int]]:
    """Generate per-LED RGB array (length num_leds) for rich 36-segment Mecha Bar animations."""
    c1 = vivid_rgb(color1) if color1 else (56, 189, 248)
    c2 = vivid_rgb(color2) if color2 else (167, 139, 250)
    leds = [(0, 0, 0)] * num_leds
    t = phase % 1.0

    # 201: Team Clash 2.0 (Matter vs Anti-Matter)
    if mode == 201:
        cycle = (t * 3.0) % 1.0
        mid = num_leds // 2
        if cycle < 0.70:
            pos = int((cycle / 0.70) * mid)
            if 0 <= pos < num_leds:
                leds[pos] = c1
            if 0 <= pos - 2 < num_leds:
                leds[pos - 2] = tuple(int(v * 0.7) for v in c1)
            r_pos = num_leds - 1 - pos
            if 0 <= r_pos < num_leds:
                leds[r_pos] = c2
            if 0 <= r_pos + 2 < num_leds:
                leds[r_pos + 2] = tuple(int(v * 0.7) for v in c2)
        elif cycle < 0.82:
            leds[mid - 1] = (255, 255, 255)
            leds[mid] = (255, 255, 255)
            if mid - 2 >= 0:
                leds[mid - 2] = (255, 220, 140)
            if mid + 1 < num_leds:
                leds[mid + 1] = (255, 220, 140)

    # 202: Beam Struggle (Dragon Ball Z Clash)
    elif mode == 202:
        jitter = math.sin(t * math.tau * 7.7) * 1.5
        base_shift = math.sin(t * math.tau * 2.0) * 7.0
        cp = int((num_leds / 2.0) + base_shift + jitter)
        cp = max(4, min(num_leds - 5, cp))
        for i in range(0, cp - 1):
            leds[i] = c1
        for i in range(cp + 2, num_leds):
            leds[i] = c2
        leds[cp] = (255, 255, 255)
        if cp - 1 >= 0:
            leds[cp - 1] = (220, 240, 255) if int(t * 40) % 2 == 0 else (255, 255, 255)
        if cp + 1 < num_leds:
            leds[cp + 1] = (255, 230, 180) if int(t * 40) % 2 == 0 else (255, 255, 255)

    # 203: Sumo Knockout (Kinetic Recoil)
    elif mode == 203:
        mid = num_leds // 2
        if t < 0.42:
            progress = t / 0.42
            pos = int(progress * (mid - 2))
            for i in range(pos, min(pos + 3, num_leds)):
                leds[i] = c1
            r_start = num_leds - 1 - pos
            for i in range(max(0, r_start - 2), r_start + 1):
                leds[i] = c2
        elif t < 0.52:
            for i in range(max(0, mid - 3), min(num_leds, mid + 3)):
                leds[i] = (255, 255, 255)
        elif t < 0.90:
            recoil_p = (t - 0.52) / 0.38
            pos = int((1.0 - math.sqrt(recoil_p)) * (mid - 2))
            for i in range(pos, min(pos + 3, num_leds)):
                leds[i] = c1
            r_start = num_leds - 1 - pos
            for i in range(max(0, r_start - 2), r_start + 1):
                leds[i] = c2

    # 204: Retro Pac-Man (Pac-Man & Dot Eater)
    elif mode == 204:
        if t < 0.65:
            pos = int((t / 0.65) * num_leds)
            for i in range(0, num_leds, 3):
                if i > pos:
                    leds[i] = (120, 100, 20)
            if 0 <= pos < num_leds:
                leds[pos] = (255, 220, 0)
                if pos - 1 >= 0:
                    leds[pos - 1] = (180, 150, 0)
        else:
            p2 = (t - 0.65) / 0.35
            ghost_pos = int(num_leds - 1 - p2 * (num_leds + 5))
            pac_pos = max(0, ghost_pos - 6)
            if 0 <= ghost_pos < num_leds:
                leds[ghost_pos] = (255, 20, 20)
                if ghost_pos + 1 < num_leds:
                    leds[ghost_pos + 1] = (180, 10, 10)
            if 0 <= pac_pos < num_leds:
                leds[pac_pos] = (255, 220, 0)

    # 205: Breakout (Brick Breaker)
    elif mode == 205:
        broken_count = min(8, int(t * 8.0))
        wall_start = 28 + broken_count
        for i in range(wall_start, num_leds):
            hue = 0.85 - (i - 28) * 0.05
            leds[i] = tuple(int(round(v * 255)) for v in colorsys.hsv_to_rgb(hue % 1.0, 1.0, 1.0))
        leds[0] = c1
        leds[1] = c1
        bounce_cycle = (t * 4.0) % 1.0
        max_dist = max(2, wall_start - 2)
        ball_pos = int(abs(math.sin(bounce_cycle * math.pi)) * max_dist) + 2
        if 0 <= ball_pos < num_leds:
            leds[ball_pos] = (255, 255, 255)

    # 206: Newton's Cradle (Kinetic Transfer)
    elif mode == 206:
        mid = num_leds // 2
        core_start = mid - 3
        core_end = mid + 3
        for i in range(core_start, core_end):
            leds[i] = tuple(int(v * 0.40) for v in c1)
        sub = (t * 2.0) % 1.0
        if t < 0.50:
            if sub < 0.50:
                pos = int(4 + (sub / 0.50) * (core_start - 5))
                if 0 <= pos < num_leds:
                    leds[pos] = c1
            else:
                pos = int(core_end + ((sub - 0.50) / 0.50) * (num_leds - core_end - 4))
                if 0 <= pos < num_leds:
                    leds[pos] = c1
        else:
            if sub < 0.50:
                pos = int((num_leds - 5) - (sub / 0.50) * (num_leds - core_end - 4))
                if 0 <= pos < num_leds:
                    leds[pos] = c1
            else:
                pos = int((core_start - 1) - ((sub - 0.50) / 0.50) * (core_start - 5))
                if 0 <= pos < num_leds:
                    leds[pos] = c1

    # 207: Capacitor Arc (Overcharge & Lightning Flash)
    elif mode == 207:
        mid = num_leds // 2
        if t < 0.72:
            fill_count = int((t / 0.72) * mid)
            ratio = t / 0.72
            col = interpolate_hue_shortest((255, 140, 20), (180, 50, 255), ratio)
            for i in range(0, fill_count):
                leds[i] = col
            for i in range(num_leds - fill_count, num_leds):
                leds[i] = col
        elif t < 0.84:
            flicker = (255, 255, 255) if int(t * 60) % 2 == 0 else (200, 80, 255)
            for i in range(num_leds):
                leds[i] = flicker
        elif t < 0.90:
            for i in range(num_leds):
                leds[i] = (255, 255, 255)
        else:
            decay = max(0.0, 1.0 - (t - 0.90) / 0.10)
            col = tuple(int(255 * decay) for _ in range(3))
            for i in range(num_leds):
                leds[i] = col

    # 208: Quantum Tunneling (The Glitch Portal)
    elif mode == 208:
        mid = num_leds // 2
        for i in range(mid - 2, mid + 2):
            leds[i] = (220, 20, 40)
        if t < 0.40:
            pos = int((t / 0.40) * (mid - 3))
            if 0 <= pos < num_leds:
                leds[pos] = (34, 211, 238)
                if pos - 1 >= 0:
                    leds[pos - 1] = (15, 110, 130)
        elif t < 0.55:
            flicker = (255, 255, 255) if int(t * 40) % 2 == 0 else (34, 211, 238)
            leds[mid - 3] = flicker
            for i in range(mid - 2, mid + 2):
                leds[i] = (255, 60, 80)
        else:
            tunnel_p = (t - 0.55) / 0.45
            pos = int((mid + 2) + tunnel_p * (num_leds - mid - 3))
            if 0 <= pos < num_leds:
                leds[pos] = (34, 211, 238)
                if pos - 1 >= 0 and pos - 1 >= mid + 2:
                    leds[pos - 1] = (15, 110, 130)

    # 209: Cyber-Centipede (Mecha-Serpent Crawl)
    elif mode == 209:
        head_pos = (num_leds / 2.0) + (num_leds / 2.0 - 5.0) * math.sin(phase * math.tau)
        direction = math.cos(phase * math.tau)
        sign = 1 if direction >= 0 else -1
        for seg in range(7):
            p = int(round(head_pos - seg * sign * 1.2))
            if 0 <= p < num_leds:
                if seg == 0:
                    leds[p] = (255, 255, 255)
                elif seg <= 4:
                    blend = seg / 4.0
                    col = interpolate_hue_shortest(c1, c2, blend)
                    dim = 1.0 - (seg * 0.12)
                    leds[p] = tuple(int(v * dim) for v in col)
                else:
                    dim = max(0.1, 0.4 - (seg - 4) * 0.15)
                    leds[p] = tuple(int(v * dim) for v in c2)

    # 210: Mitosis (Cell Split & Reunion)
    elif mode == 210:
        mid = num_leds // 2
        if t < 0.20:
            pulse = 0.5 + 0.5 * math.sin(t / 0.20 * math.pi)
            core_col = interpolate_hue_shortest(c1, (255, 255, 255), pulse)
            leds[mid - 1] = core_col
            leds[mid] = core_col
        elif t < 0.60:
            split_p = (t - 0.20) / 0.40
            spread = split_p * (mid - 3)
            p1 = max(0, int(mid - 1 - spread))
            p2 = min(num_leds - 1, int(mid + spread))
            leds[p1] = c1
            leds[p2] = c2
        elif t < 0.85:
            return_p = (t - 0.60) / 0.25
            spread = (1.0 - return_p) * (mid - 3)
            p1 = max(0, int(mid - 1 - spread))
            p2 = min(num_leds - 1, int(mid + spread))
            leds[p1] = c1
            leds[p2] = c2
        else:
            splash = (1.0 - (t - 0.85) / 0.15)
            splash_col = interpolate_hue_shortest(c2, (255, 255, 255), splash)
            for i in range(max(0, mid - 2), min(num_leds, mid + 2)):
                leds[i] = splash_col

    # Fallback for standard/continuous modes (Full Spectrum, Aurora, Dual Morph)
    else:
        base_rgb, _ = render_backzone_effect_v2(
            mode, phase, color1, color2, brightness,
            audio_volume=audio_volume, audio_levels=audio_levels, audio_beat=audio_beat,
            temp_celsius=temp_celsius, bat_pct=bat_pct, on_ac=on_ac
        )
        if mode == 101: # Full Spectrum spatial rainbow
            for i in range(num_leds):
                h = (phase + (i / float(num_leds))) % 1.0
                leds[i] = tuple(int(round(v * 255)) for v in colorsys.hsv_to_rgb(h, 1.0, 1.0))
        elif mode == 102: # Dual-Color wave
            for i in range(num_leds):
                b = (math.sin(phase * math.tau + (i / float(num_leds)) * math.pi) + 1.0) / 2.0
                leds[i] = interpolate_hue_shortest(c1, c2, b)
        else:
            for i in range(num_leds):
                leds[i] = base_rgb

    return leds

def render_backzone_effect_v2(
    mode: int,
    phase: float,
    color1,
    color2,
    brightness: int,
    audio_volume: float = 0.0,
    audio_levels: Optional[List[float]] = None,
    audio_beat: float = 0.0,
    temp_celsius: float = 45.0,
    bat_pct: int = 100,
    on_ac: bool = True,
    audio_sensitivity: float = 1.0,
    audio_decay: float = 0.85,
    audio_attack: float = 0.5
) -> Tuple[Tuple[int, int, int], int]:
    """
    Renders one deterministic (RGB, brightness) frame for rear Mecha Bar.
    Guarantees RGB channels in [0, 255] and brightness in [0, 100].
    """
    brightness = max(0, min(100, int(brightness)))
    c1 = vivid_rgb(color1) if color1 else (56, 189, 248)
    c2 = vivid_rgb(color2) if color2 else (167, 139, 250)

    # 201-210: Battle & Arcade Choreographed Effects (Aggregate for physical hardware)
    if 201 <= mode <= 210:
        strip = render_backzone_strip_leds(
            mode, phase, color1, color2, brightness, num_leds=36,
            audio_volume=audio_volume, audio_levels=audio_levels, audio_beat=audio_beat,
            temp_celsius=temp_celsius, bat_pct=bat_pct, on_ac=on_ac
        )
        whites = [col for col in strip if col[0] > 240 and col[1] > 240 and col[2] > 240]
        if whites:
            return (255, 255, 255), brightness
        lit = [col for col in strip if max(col) > 20]
        if lit:
            avg_r = int(sum(c[0] for c in lit) / len(lit))
            avg_g = int(sum(c[1] for c in lit) / len(lit))
            avg_b = int(sum(c[2] for c in lit) / len(lit))
            return (avg_r, avg_g, avg_b), brightness
        return (0, 0, 0), 0

    # 101: Full Spectrum (Rainbow sweep)
    if mode == 101:
        rgb = tuple(int(round(v * 255)) for v in colorsys.hsv_to_rgb(phase % 1.0, 1.0, 1.0))
        return rgb, brightness

    # 102: Dual-Color Morph (Shortest-path hue interpolation)
    if mode == 102:
        blend = (math.sin(phase * math.tau) + 1.0) / 2.0
        rgb = interpolate_hue_shortest(c1, c2, blend)
        return rgb, brightness

    # 105: Aurora Flow
    if mode == 105:
        rgb = sample_palette(AURORA_PALETTE, phase)
        # Gentle natural luminous breathing
        lume = 0.82 + 0.18 * math.sin(phase * math.tau * 1.5)
        return rgb, max(1, min(100, int(round(brightness * lume))))

    # 106: Lava Flow
    if mode == 106:
        rgb = sample_palette(LAVA_PALETTE, phase)
        # Irregular flicker / bubbling heat movement
        flicker = 0.70 + 0.18 * math.sin(phase * 17.3) + 0.12 * math.cos(phase * 31.7)
        flicker = max(0.40, min(1.0, flicker))
        return rgb, max(1, min(100, int(round(brightness * flicker))))

    # 107: Ocean Pulse
    if mode == 107:
        rgb = sample_palette(OCEAN_PALETTE, phase)
        # Layered slow deep-sea swells
        wave = (math.sin(phase * math.tau) * 0.5 + math.sin(phase * math.tau * 2.0) * 0.25 + 0.75) / 1.5
        wave = max(0.15, min(1.0, wave))
        return rgb, max(1, min(100, int(round(brightness * wave))))

    # 108: Heartbeat
    if mode == 108:
        # Standard ECG-style lub-dub waveform over period [0.0, 1.0)
        t = phase % 1.0
        val = 0.08
        if 0.10 <= t < 0.22:
            val += 0.85 * math.sin((t - 0.10) / 0.12 * math.pi)
        elif 0.28 <= t < 0.42:
            val += 0.95 * math.sin((t - 0.28) / 0.14 * math.pi)
        val = max(0.05, min(1.0, val))
        return c1, max(1, min(100, int(round(brightness * val))))

    # 109: Lightning
    if mode == 109:
        # Pseudo-random episodic strikes followed by exponential fade
        cycle = phase * 6.0
        sub_t = cycle % 1.0
        cycle_idx = int(cycle)
        # Seed by cycle index to ensure deterministic frame rendering
        rand_val = (math.sin(cycle_idx * 9301.0 + 49297.0) * 233280.0) % 1.0
        if rand_val > 0.40:
            if sub_t < 0.12:
                # Sudden strike: electric white/blue flash
                flash_blend = max(0.0, 1.0 - sub_t / 0.12)
                rgb = interpolate_hue_shortest(c2, (255, 255, 255), flash_blend)
                return rgb, brightness
            else:
                # Exponential decay to low ambient glow
                decay = math.exp(-6.0 * (sub_t - 0.12))
                rgb = interpolate_hue_shortest(c1, c2, decay)
                return rgb, max(5, int(round(brightness * (0.05 + 0.95 * decay))))
        else:
            # Low resting glow between storms
            return c1, max(3, int(round(brightness * 0.08)))

    # 110: Audio Pulse
    if mode == 110:
        vol = max(0.0, min(1.0, audio_volume * audio_sensitivity))
        beat = max(0.0, min(1.0, audio_beat))
        # Overall volume sets base illumination, bass beat adds strong punch
        audio_factor = min(1.0, vol * 0.70 + beat * 0.50)
        effective_bright = max(5, int(round(brightness * (0.10 + 0.90 * audio_factor))))
        # When punchy bass strikes, blend towards secondary color
        rgb = interpolate_hue_shortest(c1, c2, beat)
        return rgb, effective_bright

    # 111: Audio Color Cycle
    if mode == 111:
        bands = audio_levels if audio_levels and len(audio_levels) >= 4 else [0.0, 0.0, 0.0, 0.0]
        bass = min(1.0, bands[0] * audio_sensitivity)
        mids = min(1.0, ((bands[1] + bands[2]) / 2.0) * audio_sensitivity)
        treble = min(1.0, bands[3] * audio_sensitivity)

        # Spectral mapping: Bass -> Red/Magenta (0.95-1.0), Mids -> Cyan/Blue (0.50-0.65), Treble -> Green/Amber (0.15-0.35)
        total_energy = bass + mids + treble + 1e-4
        w_bass = bass / total_energy
        w_mids = mids / total_energy
        w_treb = treble / total_energy
        
        target_hue = (w_bass * 0.95 + w_mids * 0.58 + w_treb * 0.22) % 1.0
        rgb = tuple(int(round(v * 255)) for v in colorsys.hsv_to_rgb(target_hue, 1.0, 1.0))
        lum = min(1.0, max(0.15, total_energy * 0.8))
        return rgb, max(5, int(round(brightness * lum)))

    # 112: Temperature Reactive
    if mode == 112:
        if temp_celsius is None:
            return (96, 112, 128), brightness
        # Cyan cool (<50C), green normal (50-70C), orange warm (70-82C), red hot (>82C)
        temp = max(30.0, min(100.0, float(temp_celsius)))
        if temp < 50.0:
            # 30C..50C: Cyan (0.50) to Green (0.33)
            frac = (temp - 30.0) / 20.0
            rgb = interpolate_hue_shortest((6, 182, 212), (34, 197, 94), frac)
        elif temp < 70.0:
            # 50C..70C: Green (0.33) to Yellow (0.16)
            frac = (temp - 50.0) / 20.0
            rgb = interpolate_hue_shortest((34, 197, 94), (234, 179, 8), frac)
        elif temp < 85.0:
            # 70C..85C: Yellow (0.16) to Orange/Red (0.05)
            frac = (temp - 70.0) / 15.0
            rgb = interpolate_hue_shortest((234, 179, 8), (239, 68, 68), frac)
        else:
            # > 85C: Hot pulsing crimson red
            pulse = 0.70 + 0.30 * math.sin(phase * math.tau * 4.0)
            return (255, 10, 10), max(10, int(round(brightness * pulse)))
        return rgb, brightness

    # 113: Battery / Charging Status
    if mode == 113:
        if on_ac:
            # Green gentle charging breath
            pulse = 0.40 + 0.60 * ((math.sin(phase * math.tau) + 1.0) / 2.0)
            return (34, 197, 94), max(10, int(round(brightness * pulse)))
        else:
            if bat_pct <= 15:
                # Critical battery red pulse
                pulse = 0.20 + 0.80 * ((math.sin(phase * math.tau * 3.0) + 1.0) / 2.0)
                return (239, 68, 68), max(10, int(round(brightness * pulse)))
            elif bat_pct <= 25:
                # Low battery amber warning
                return (245, 158, 11), brightness
            else:
                # Normal battery: Cool blue breath
                pulse = 0.50 + 0.50 * ((math.sin(phase * math.tau) + 1.0) / 2.0)
                return (56, 189, 248), max(15, int(round(brightness * pulse)))

    # 114: Game Mode Reactive
    if mode == 114:
        # High-energy dynamic neon pulse between c1 and c2
        blend = (math.sin(phase * math.tau * 2.0) + 1.0) / 2.0
        rgb = interpolate_hue_shortest(c1, c2, blend)
        return rgb, brightness

    # Legacy: 103 Comet Pulse
    if mode == 103:
        pulse = max(0.08, math.sin((phase % 1.0) * math.pi) ** 5)
        return c1, max(1, int(round(brightness * pulse)))

    # Legacy: 104 Cyber Strobe
    if mode == 104:
        return (c1 if int(phase * 8) % 2 == 0 else c2), brightness

    # Mode 15: Off
    if mode == 15:
        return (0, 0, 0), 0

    # Default / Firmware fallback
    return c1, brightness


# ---------------------------------------------------------------------------
# UI View Component: BackZoneView
# ---------------------------------------------------------------------------

class BackZoneView:
    """
    Complete UI and state controller for Tab 02: Rear light bar.
    Integrates directly with the parent InfinixGTToolkitApp.
    """

    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.theme = getattr(app, "theme_colors", {})
        
        # Debounce tracking
        self._last_slider_time = 0.0
        self._debounce_job = None
        self._preview_job = None
        if hasattr(self, "root") and self.root:
            self.root.bind("<Destroy>", lambda e: self.close() if e.widget == self.root else None, add="+")
        
        # UI state
        self.current_category = "Firmware"
        self.card_buttons: Dict[int, ctk.CTkFrame] = {}
        
    def build_page(self, container: ctk.CTkFrame) -> ctk.CTkScrollableFrame:
        """Construct the full Rear light bar page inside container."""
        scroll = ctk.CTkScrollableFrame(container, fg_color="transparent")
        self.scroll_frame = scroll

        # 1. Top Hero Card: Connection, Master Switch, Live Strip Preview
        self._create_hero_card(scroll)

        # 2. Category Tab Switcher
        self._create_category_tabs(scroll)

        # 3. Effect Cards Catalog Grid
        self._create_effects_catalog(scroll)

        # 4. Split 2-Column Section: Controls on Left, Presets & Rules on Right
        self._create_controls_and_presets(scroll)

        # 5. Compatibility / Diagnostics Banner
        self._create_diagnostics_banner(scroll)

        # Trigger initial dynamic visibility
        self.update_dynamic_controls()
        
        # Start live preview loop
        self._update_live_preview()

        return scroll

    # -----------------------------------------------------------------------
    # Top Hero Card & Live Preview
    # -----------------------------------------------------------------------
    def _create_hero_card(self, parent):
        hero = neon_ui.Frame(
            parent, fg_color=self.theme.get("card_bg", "#181A20"),
            corner_radius=14, border_width=1.5,
            border_color=self.theme.get("card_border", "#282B33")
        )
        hero.pack(fill="x", padx=4, pady=(8, 6))

        # Top Bar inside Hero: Title, Connection Status, Master On/Off
        top_row = neon_ui.Frame(hero, fg_color="transparent")
        top_row.pack(fill="x", padx=16, pady=(12, 4))

        title_box = neon_ui.Frame(top_row, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(
            title_box, text="Rear light bar", image=neon_ui.icon('rear',size=28), compound='left', padx=12,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.theme.get("text_primary", "#FFFFFF")
        ).pack(side="left", padx=(0, 10))

        # Port status pill
        self.port_badge = ctk.CTkLabel(
            title_box, text="Checking connection…",
            fg_color=self.theme.get("pill_bg", "#222630"),
            corner_radius=10, padx=10, pady=3,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.theme.get("accent_blue", "#38BDF8")
        )
        self.port_badge.pack(side="left")

        # Master On/Off Switch
        switch_box = neon_ui.Frame(top_row, fg_color="transparent")
        switch_box.pack(side="right")
        
        self.master_switch_var = self.app.mecha_var
        self.master_switch = ctk.CTkSwitch(
            switch_box, text="Power",
            variable=self.master_switch_var,
            command=self._on_master_toggled,
            font=ctk.CTkFont(size=14, weight="bold"),
            progress_color=self.theme.get("accent_blue", "#38BDF8"),
            text_color=self.theme.get("text_primary", "#FFFFFF")
        )
        self.master_switch.pack(side="right")
        self.hero_description = ctk.CTkLabel(hero, text=EFFECT_METADATA.get(self.app.bz_mode, EFFECT_METADATA[1])['description'],
                     font=ctk.CTkFont(size=12),text_color=self.theme['text_secondary'],anchor='w')
        self.hero_description.pack(fill='x',padx=65)

        # Live Canvas Preview: Styled Rear Exhaust Bar
        preview_container = neon_ui.Frame(
            hero, fg_color="#0A0C10",
            corner_radius=12, border_width=1,
            border_color="#214677", height=58
        )
        preview_container.pack(fill="x", padx=16, pady=8)
        preview_container.pack_propagate(False)

        self.preview_canvas = tk.Canvas(
            preview_container, bg="#0A0C10",
            highlightthickness=0, bd=0
        )
        self.preview_canvas.pack(fill="both", expand=True, padx=8, pady=6)
        self.preview_canvas.bind("<Configure>", lambda e: self._redraw_preview_strip())

        # Subtitle Status Line
        self.status_line = ctk.CTkLabel(
            hero, text="Initializing · 100% brightness",
            font=ctk.CTkFont(size=13, weight="normal"),
            text_color=self.theme.get("text_secondary", "#94A3B8")
        )
        self.status_line.pack(anchor="w", padx=18, pady=(0, 9))

    def _redraw_preview_strip(self, hex_color: str = "#38BDF8", brightness: int = 100, led_colors: Optional[List[str]] = None):
        """Draws a sleek simulated rear mecha strip with 36 individual addressable LED segments."""
        canvas = self.preview_canvas
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w <= 10 or h <= 10:
            return

        canvas.delete("all")
        
        # If disabled or mode 15, show powered-off dark appearance
        is_powered = self.app._backzone_allowed() and (getattr(self.app, "bz_mode", 1) != 15)
        if not is_powered:
            canvas.create_rectangle(4, h//2 - 6, w - 4, h//2 + 6, fill="#13161C", outline="#1E222A", width=1)
            canvas.create_text(w//2, h//2, text="STRIP POWER OFF", fill="#475569", font=("Segoe UI", 11, "bold"))
            return

        # Metallic chassis slot background
        slot_y1 = max(4, h//2 - 10)
        slot_y2 = min(h - 4, h//2 + 10)
        canvas.create_rectangle(4, slot_y1, w - 4, slot_y2, fill="#0F1218", outline="#252A36", width=1)

        n_leds = 36
        padding = 10
        available_w = w - 2 * padding
        gap = 2
        block_w = max(2.0, (available_w - (n_leds - 1) * gap) / n_leds)

        glow_y1 = max(6, h//2 - 7)
        glow_y2 = min(h - 6, h//2 + 7)
        core_y1 = max(8, h//2 - 3)
        core_y2 = min(h - 8, h//2 + 3)

        for i in range(n_leds):
            x1 = padding + i * (block_w + gap)
            x2 = x1 + block_w
            col = led_colors[i] if (led_colors and i < len(led_colors)) else hex_color
            if col and col not in ("#000000", "#0F1218", "#11141A", "#13161C"):
                rgb = tuple(int(col[j:j+2],16) for j in (1,3,5))
                for spread, strength in ((7,.07),(5,.15),(3,.28)):
                    glow = '#%02x%02x%02x' % tuple(int(v*strength) for v in rgb)
                    canvas.create_rectangle(x1-1,glow_y1-spread,x2+1,glow_y2+spread,fill=glow,outline='',width=0)
                canvas.create_rectangle(x1, glow_y1, x2, glow_y2, fill=col, outline="", width=0)
                canvas.create_rectangle(x1, core_y1, x2, core_y2, fill=col, outline="", width=0)
            else:
                canvas.create_rectangle(x1, core_y1, x2, core_y2, fill="#13161C", outline="#1C212B", width=1)

    # -----------------------------------------------------------------------
    # Category Tabs & Effect Cards
    # -----------------------------------------------------------------------
    def _create_category_tabs(self, parent):
        tab_frame = neon_ui.Frame(parent, fg_color="transparent")
        tab_frame.pack(fill="x", padx=0, pady=(6, 6))

        self.cat_buttons = {}
        icons = {
            "Firmware": "Firmware",
            "Animated": "Animated",
            "Battle & Arcade": "Battle & Arcade · Beta",
            "Audio": "Audio reactive",
            "System": "System reactive"
        }
        
        for cat in CATEGORIES:
            button_type = ctk.CTkButton if cat == "Battle & Arcade" else neon_ui.Button
            btn = button_type(
                tab_frame, text=icons.get(cat, cat), image=neon_ui.icon({'Firmware':'cpu','Animated':'lighting','Battle & Arcade':'game','Audio':'bars','System':'settings'}[cat],size=23),
                height=46, corner_radius=11,
                font=ctk.CTkFont(size=14, weight="bold"),
                fg_color=self.theme.get("accent_blue", "#38BDF8") if cat == self.current_category else self.theme.get("button_bg", "#222630"),
                text_color="#000000" if cat == self.current_category else self.theme.get("text_primary", "#FFFFFF"),
                hover_color=self.theme.get("accent_blue", "#38BDF8"),
                command=lambda c=cat: self._select_category(c)
            )
            if cat == "Battle & Arcade":
                btn.configure(state="disabled", fg_color=("#E5E7EB", "#252B34"),
                              text_color_disabled=("#737985", "#858B96"), image=None)
            btn.pack(side="left", padx=4, expand=True, fill="x")
            self.cat_buttons[cat] = btn

    def _select_category(self, cat: str):
        if cat == "Battle & Arcade":
            return
        self.current_category = cat
        for c, btn in self.cat_buttons.items():
            if c == "Battle & Arcade":
                continue
            if c == cat:
                btn.configure(
                    fg_color=self.theme.get("accent_blue", "#38BDF8"),
                    text_color="#000000"
                )
            else:
                btn.configure(
                    fg_color=self.theme.get("button_bg", "#222630"),
                    text_color=self.theme.get("text_primary", "#FFFFFF")
                )
        self._populate_effect_cards()

    def _create_effects_catalog(self, parent):
        catalog_card = neon_ui.Frame(
            parent, fg_color=self.theme.get("card_bg", "#181A20"),
            corner_radius=14, border_width=1.5,
            border_color=self.theme.get("card_border", "#282B33")
        )
        catalog_card.pack(fill="x", padx=4, pady=6)

        c_hdr = neon_ui.Frame(catalog_card, fg_color="transparent")
        c_hdr.pack(fill="x", padx=16, pady=(10, 2))
        ctk.CTkLabel(
            c_hdr, text="Choose an effect", image=neon_ui.icon('lighting',size=26), compound='left', padx=12,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.theme.get("text_primary", "#FFFFFF")
        ).pack(side="left")

        # Hidden or styled compatibility dropdown for test_offline_ui
        # test_offline_ui expects self.app.bz_mode_seg.cget('values') to include "Spectrum Flow"
        all_mode_names = [name for mode, name in BACKZONE_MODE_NAMES.items()
                          if mode not in ARCADE_BETA_MODES]
        if "Spectrum Flow" not in all_mode_names:
            all_mode_names.append("Spectrum Flow")
        
        self.app.bz_mode_var = ctk.StringVar(value=BACKZONE_MODE_NAMES.get(self.app.bz_mode, "Always On"))
        self.app.bz_mode_seg = ctk.CTkOptionMenu(
            c_hdr, values=all_mode_names, variable=self.app.bz_mode_var,
            command=self._on_dropdown_mode_selected,
            width=180, height=28,
            fg_color=self.theme.get("button_bg", "#222630"),
            button_color=self.theme.get("accent_purple", "#A78BFA"),
            font=ctk.CTkFont(size=13)
        )
        # Kept as a compatibility control for integrations that address it
        # directly. The visible card picker is the single source of choice.

        # Container for card grid
        self.cards_grid_frame = neon_ui.Frame(catalog_card, fg_color="transparent")
        self.cards_grid_frame.pack(fill="x", padx=12, pady=(3, 5))

        self.effect_help = ctk.CTkLabel(
            catalog_card, text="", anchor="w", justify="left",
            font=ctk.CTkFont(size=12),
            text_color=self.theme.get("text_secondary", "#94A3B8")
        )
        self.effect_help.pack(fill="x", padx=18, pady=(0, 10))

        self._populate_effect_cards()

    def _populate_effect_cards(self):
        """Populate effect cards matching the currently selected category."""
        for widget in self.cards_grid_frame.winfo_children():
            widget.destroy()

        self.card_buttons.clear()
        
        # Filter modes belonging to active category
        matching_modes = [
            (mode, meta) for mode, meta in EFFECT_METADATA.items()
            if meta.get("category") == self.current_category and mode != 15
        ]

        # Compact four-column picker keeps controls above the fold while each
        # category remains easy to scan.
        cols = 4
        for i, (mode, meta) in enumerate(matching_modes):
            row = i // cols
            col = i % cols

            is_selected = (self.app.bz_mode == mode)
            
            card = neon_ui.Frame(
                self.cards_grid_frame,
                fg_color=self.theme.get("card_border", "#282B33") if is_selected else self.theme.get("card_bg", "#181A20"),
                corner_radius=9,
                border_width=2 if is_selected else 1,
                border_color=self.theme.get("accent_blue", "#38BDF8") if is_selected else self.theme.get("card_border", "#282B33"),
                cursor="hand2", height=72
            )
            card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            card.pack_propagate(False)
            self.cards_grid_frame.grid_columnconfigure(col, weight=1, uniform='rear_effects')

            # Top of card: Icon + Name + Badge
            chdr = neon_ui.Frame(card, fg_color="transparent")
            chdr.pack(fill="x", padx=10, pady=(8,0))

            ctk.CTkLabel(
                chdr, text=meta['name'], image=neon_ui.icon('game' if 'Game' in meta['name'] else 'bars' if 'Music' in meta['name'] else 'lighting',size=22), compound='left', padx=9,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=self.theme.get("accent_blue", "#38BDF8") if is_selected else self.theme.get("text_primary", "#FFFFFF")
            ).pack(side="left")

            if is_selected:
                ctk.CTkLabel(
                    chdr, text="Selected", corner_radius=6,
                    fg_color=self.theme.get("pill_bg", "#222630"),
                    text_color=self.theme.get("accent_blue", "#38BDF8"),
                    font=ctk.CTkFont(size=11, weight="bold"), padx=6, pady=2
                ).pack(side="right")
            descriptions = {'Always On':'Solid stationary illumination','Breath':'Smooth breathing effect',
                            'Music Rhythm':'Sync with music rhythm','Music Jump':'Reactive jumping effect',
                            'Game Loop':'Loop with game scenarios','Game Cover':'Show game cover effects'}
            caption = ctk.CTkLabel(card,text=descriptions.get(meta['name'],meta['description'].split('.')[0]),
                                   font=ctk.CTkFont(size=11),text_color=self.theme['text_secondary'],height=18,anchor='w')
            caption.pack(fill='x',padx=(43,8),pady=(0,7))
            caption.bind('<Configure>',lambda e,w=caption:w.configure(wraplength=max(90,e.width-3)))
            caption.bind('<Button-1>',lambda e,m=mode:self._select_mode(m))

            # Click binding to select effect
            for w in (card, chdr, *chdr.winfo_children()):
                w.bind("<Button-1>", lambda e, m=mode: self._select_mode(m))

            self.card_buttons[mode] = card

        selected_meta = EFFECT_METADATA.get(getattr(self.app, "bz_mode", 1), EFFECT_METADATA[1])
        detail = selected_meta["description"]
        if selected_meta.get("warning"):
            detail = f"{detail}  {selected_meta['warning']}"
        self.effect_help.configure(text=detail)
        self.hero_description.configure(text=selected_meta['description'])

    def _select_mode(self, mode: int):
        """Set the active rear effect mode and re-render."""
        if mode in ARCADE_BETA_MODES:
            return
        self.app.bz_mode = mode
        self.app.config["bz_mode"] = mode
        self.app.bz_mode_var.set(BACKZONE_MODE_NAMES.get(mode, "Always On"))
        self.app._save_config()

        # Update card highlight
        self._populate_effect_cards()
        self.update_dynamic_controls()

        # Apply to hardware
        self.app._apply_backzone_hardware()

    def _on_dropdown_mode_selected(self, val: str):
        # Support fallback or legacy names
        name_to_mode = {name: m for m, name in BACKZONE_MODE_NAMES.items()}
        name_to_mode["Spectrum Flow"] = 101
        m = name_to_mode.get(val, 1)
        if m in ARCADE_BETA_MODES:
            return
        
        # Switch category tab if needed
        meta = EFFECT_METADATA.get(m)
        if meta and meta.get("category") != self.current_category:
            self.current_category = meta["category"]
            self._select_category(self.current_category)
        self._select_mode(m)

    # -----------------------------------------------------------------------
    # Split 2-Column Controls & Presets
    # -----------------------------------------------------------------------
    def _create_controls_and_presets(self, parent):
        row = neon_ui.Frame(parent, fg_color="transparent")
        row.pack(fill="x", padx=4, pady=6)
        row.grid_columnconfigure(0, weight=1, uniform='rear_controls')
        row.grid_columnconfigure(1, weight=1, uniform='rear_controls')

        # Left Column: Effect Controls
        self.controls_card = neon_ui.Frame(
            row, fg_color=self.theme.get("card_bg", "#181A20"),
            corner_radius=14, border_width=1.5,
            border_color=self.theme.get("card_border", "#282B33")
        )
        self.controls_card.grid(row=0, column=0, padx=(0, 6), sticky="nsew")

        # Right Column: Presets & Automation
        self.presets_card = neon_ui.Frame(
            row, fg_color=self.theme.get("card_bg", "#181A20"),
            corner_radius=14, border_width=1.5,
            border_color=self.theme.get("card_border", "#282B33")
        )
        self.presets_card.grid(row=0, column=1, padx=(6, 0), sticky="nsew")

        self._build_effect_controls(self.controls_card)
        self._build_presets_and_rules(self.presets_card)

    def _build_effect_controls(self, card):
        hdr = neon_ui.Frame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(12, 6))
        ctk.CTkLabel(
            hdr, text="Customize effect", image=neon_ui.icon('settings',size=26), compound='left', padx=12,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.theme.get("text_primary", "#FFFFFF")
        ).pack(side="left")

        # Dynamic warning banner inside controls
        self.controls_warning_lbl = ctk.CTkLabel(
            card, text="",
            wraplength=560, justify="left",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.theme.get("accent_rose", "#F43F5E")
        )
        self.controls_warning_lbl.pack(anchor="w", padx=16, pady=(0, 4))

        # --- A. Dual Colors Section ---
        self.color_section = neon_ui.Frame(card, fg_color="transparent")
        self.color_section.pack(fill="x", padx=16, pady=(0, 8))

        c_row = neon_ui.Frame(self.color_section, fg_color="transparent")
        c_row.pack(fill="x", pady=4)

        # Primary Color
        self.c1_container = neon_ui.Frame(c_row, fg_color="transparent")
        self.c1_container.pack(side="left", padx=(0, 16))
        ctk.CTkLabel(
            self.c1_container, text="Primary color",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.theme.get("text_secondary", "#94A3B8")
        ).pack(anchor="w", pady=(0, 2))

        c1_sub = neon_ui.Frame(self.c1_container, fg_color="transparent")
        c1_sub.pack(side="left")
        
        c1_hex = rgb_to_hex(self.app.bz_color1)
        self.app.bz_c1_swatch = tk.Frame(c1_sub, bg=c1_hex, width=38, height=30, cursor="hand2", relief="ridge", bd=1)
        self.app.bz_c1_swatch.pack(side="left", padx=(0, 6))
        self.app.bz_c1_swatch.bind("<Button-1>", lambda e: self._open_color_picker(1))

        self.c1_hex_entry = ctk.CTkEntry(c1_sub, width=78, height=30, font=ctk.CTkFont(size=13))
        self.c1_hex_entry.insert(0, c1_hex)
        self.c1_hex_entry.pack(side="left")
        self.c1_hex_entry.bind("<Return>", lambda e: self._on_hex_entered(1))

        # Secondary Color
        self.c2_container = neon_ui.Frame(c_row, fg_color="transparent")
        self.c2_container.pack(side="left", padx=(0, 10))
        ctk.CTkLabel(
            self.c2_container, text="Secondary color",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.theme.get("text_secondary", "#94A3B8")
        ).pack(anchor="w", pady=(0, 2))

        c2_sub = neon_ui.Frame(self.c2_container, fg_color="transparent")
        c2_sub.pack(side="left")

        c2_hex = rgb_to_hex(self.app.bz_color2)
        self.app.bz_c2_swatch = tk.Frame(c2_sub, bg=c2_hex, width=38, height=30, cursor="hand2", relief="ridge", bd=1)
        self.app.bz_c2_swatch.pack(side="left", padx=(0, 6))
        self.app.bz_c2_swatch.bind("<Button-1>", lambda e: self._open_color_picker(2))

        self.c2_hex_entry = ctk.CTkEntry(c2_sub, width=78, height=30, font=ctk.CTkFont(size=13))
        self.c2_hex_entry.insert(0, c2_hex)
        self.c2_hex_entry.pack(side="left")
        self.c2_hex_entry.bind("<Return>", lambda e: self._on_hex_entered(2))

        # Color Tools: Swap & Randomize
        tools_box = neon_ui.Frame(c_row, fg_color="transparent")
        self.color_tools_box = tools_box
        tools_box.pack(side="left", padx=(6, 0), pady=(16, 0))

        neon_ui.Button(
            tools_box, text="⇄", width=34, height=30,
            fg_color=self.theme.get("button_bg", "#222630"),
            hover_color=self.theme.get("accent_blue", "#38BDF8"),
            command=self._swap_colors
        ).pack(side="left", padx=2)

        neon_ui.Button(
            tools_box, text="🎲", width=34, height=30,
            fg_color=self.theme.get("button_bg", "#222630"),
            hover_color=self.theme.get("accent_purple", "#A78BFA"),
            command=self._randomize_colors
        ).pack(side="left", padx=2)

        # --- B. Animation Speed Section ---
        self.speed_section = neon_ui.Frame(card, fg_color="transparent")
        self.speed_section.pack(fill="x", padx=16, pady=4)

        sp_top = neon_ui.Frame(self.speed_section, fg_color="transparent")
        sp_top.pack(fill="x", pady=(2, 2))

        ctk.CTkLabel(
            sp_top, text="Animation speed",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.theme.get("text_primary", "#FFFFFF")
        ).pack(side="left")

        self.speed_val_lbl = ctk.CTkLabel(
            sp_top, text=f"Level {self.app.bz_speed}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.theme.get("accent_purple", "#A78BFA")
        )
        self.speed_val_lbl.pack(side="right")

        # Named speed presets
        presets_bar = neon_ui.Frame(self.speed_section, fg_color="transparent")
        presets_bar.pack(fill="x", pady=(0, 4))
        for name, val in (("Slow", 1), ("Normal", 4), ("Fast", 7), ("Turbo", 9)):
            neon_ui.Button(
                presets_bar, text=name, width=60, height=24,
                corner_radius=6, font=ctk.CTkFont(size=12, weight="bold"),
                fg_color=self.theme.get("button_bg", "#222630"),
                hover_color=self.theme.get("accent_purple", "#A78BFA"),
                command=lambda v=val: self._set_speed(v)
            ).pack(side="left", padx=2)

        self.app.bz_speed_slider = neon_ui.Slider(
            self.speed_section, from_=1, to=9, number_of_steps=8,
            command=self._on_speed_slider_changed,
            progress_color=self.theme.get("accent_purple", "#A78BFA"),
            button_color=self.theme.get("accent_purple", "#A78BFA"),
            fg_color=self.theme.get("progress_bg", "#222630")
        )
        self.app.bz_speed_slider.set(self.app.bz_speed)
        self.app.bz_speed_slider.pack(fill="x", pady=(2, 6))

        # --- C. Brightness Section ---
        self.bright_section = neon_ui.Frame(card, fg_color="transparent")
        self.bright_section.pack(fill="x", padx=16, pady=4)

        br_top = neon_ui.Frame(self.bright_section, fg_color="transparent")
        br_top.pack(fill="x", pady=(2, 2))

        ctk.CTkLabel(
            br_top, text="Brightness",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.theme.get("text_primary", "#FFFFFF")
        ).pack(side="left")

        self.bright_val_lbl = ctk.CTkLabel(
            br_top, text=f"{self.app.bz_brightness}%",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.theme.get("accent_blue", "#38BDF8")
        )
        self.bright_val_lbl.pack(side="right")

        self.app.bz_bright_slider = neon_ui.Slider(
            self.bright_section, from_=0, to=100, number_of_steps=100,
            command=self._on_brightness_slider_changed,
            progress_color=self.theme.get("accent_blue", "#38BDF8"),
            button_color=self.theme.get("accent_blue", "#38BDF8"),
            fg_color=self.theme.get("progress_bg", "#222630")
        )
        self.app.bz_bright_slider.set(self.app.bz_brightness)
        self.app.bz_bright_slider.pack(fill="x", pady=(2, 6))

        # --- D. Audio Reactive Controls (Dynamic) ---
        self.audio_section = neon_ui.Frame(card, fg_color="transparent")
        self.audio_section.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(
            self.audio_section, text="Audio response",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.theme.get("accent_green", "#22C55E")
        ).pack(anchor="w", pady=(2, 2))

        aud_grid = neon_ui.Frame(self.audio_section, fg_color="transparent")
        aud_grid.pack(fill="x")

        # Sensitivity
        self.audio_sens_slider = neon_ui.Slider(
            aud_grid, from_=0.2, to=3.0,
            command=self._on_audio_sens_changed,
            progress_color=self.theme.get("accent_green", "#22C55E")
        )
        self.audio_sens_slider.set(self.app.config.get("bz_audio_sensitivity", 1.0))
        self.audio_sens_slider.pack(fill="x", pady=2)

        # Decay
        ctk.CTkLabel(
            self.audio_section, text="Decay Rate (Falloff):",
            font=ctk.CTkFont(size=12),
            text_color=self.theme.get("text_secondary", "#94A3B8")
        ).pack(anchor="w")

        self.audio_decay_slider = neon_ui.Slider(
            self.audio_section, from_=0.5, to=0.98,
            command=self._on_audio_decay_changed,
            progress_color=self.theme.get("accent_green", "#22C55E")
        )
        self.audio_decay_slider.set(self.app.config.get("bz_audio_decay", 0.85))
        self.audio_decay_slider.pack(fill="x", pady=(0, 6))

        # --- E. Thermal Reactive Controls (Dynamic) ---
        self.temp_section = neon_ui.Frame(card, fg_color="transparent")
        self.temp_section.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(
            self.temp_section, text="Temperature source",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.theme.get("accent_rose", "#F43F5E")
        ).pack(anchor="w", pady=(2, 2))

        temp_row = neon_ui.Frame(self.temp_section, fg_color="transparent")
        temp_row.pack(fill="x")
        self.temp_source_var = ctk.StringVar(value=self.app.config.get("bz_temp_source", "CPU"))
        ctk.CTkOptionMenu(
            temp_row, values=["CPU Package", "GPU 3D Engine"],
            variable=self.temp_source_var, command=self._on_temp_source_changed,
            width=160, height=28
        ).pack(side="left")

        # --- F. Hardware Action Buttons ---
        btn_bar = neon_ui.Frame(card, fg_color="transparent")
        self.actions_bar = btn_bar
        btn_bar.pack(fill="x", padx=16, pady=(10, 14))

        neon_ui.Button(
            btn_bar, text="Apply now",
            fg_color=self.theme.get("accent_blue", "#38BDF8"),
            text_color="#000000", font=ctk.CTkFont(size=13, weight="bold"),
            hover_color=self.theme.get("accent_purple", "#A78BFA"),
            command=self.app._apply_backzone_hardware
        ).pack(side="left", padx=(0, 6))

        neon_ui.Button(
            btn_bar, text="Test light",
            fg_color=self.theme.get("button_bg", "#222630"),
            text_color=self.theme.get("text_primary", "#FFFFFF"),
            font=ctk.CTkFont(size=13),
            command=self._test_hardware_cycle
        ).pack(side="left", padx=4)

        neon_ui.Button(
            btn_bar, text="Restore firmware",
            fg_color=self.theme.get("button_bg", "#222630"),
            text_color=self.theme.get("text_secondary", "#94A3B8"),
            font=ctk.CTkFont(size=13),
            command=self._restore_firmware
        ).pack(side="left", padx=4)

    def _build_presets_and_rules(self, card):
        hdr = neon_ui.Frame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(12, 6))
        ctk.CTkLabel(
            hdr, text="Quick presets",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.theme.get("text_primary", "#FFFFFF")
        ).pack(side="left")

        # Quick Presets Buttons
        presets_box = neon_ui.Frame(card, fg_color="transparent")
        presets_box.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(
            presets_box, text="Apply a complete look",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.theme.get("text_secondary", "#94A3B8")
        ).pack(anchor="w", pady=(0, 4))

        # Default Presets
        preset_grid = neon_ui.Frame(presets_box, fg_color="transparent")
        preset_grid.pack(fill="x")
        for i, (pname, pcfg) in enumerate(DEFAULT_REAR_PRESETS.items()):
            p_row = neon_ui.Frame(preset_grid, fg_color="transparent")
            p_row.grid(row=i // 2, column=i % 2, sticky="ew", padx=(0, 4) if i % 2 == 0 else (4, 0), pady=3)
            preset_grid.grid_columnconfigure(i % 2, weight=1)
            neon_ui.Button(
                p_row, text=pname, height=30,
                fg_color=self.theme.get("button_bg", "#222630"),
                hover_color=self.theme.get("accent_blue", "#38BDF8"),
                text_color=self.theme.get("text_primary", "#FFFFFF"),
                font=ctk.CTkFont(size=13),
                anchor="w",
                command=lambda cfg=pcfg: self._apply_preset(cfg)
            ).pack(side="left", fill="x", expand=True)

        # Custom presets management
        mgmt_row = neon_ui.Frame(card, fg_color="transparent")
        mgmt_row.pack(fill="x", padx=16, pady=(8, 4))

        neon_ui.Button(
            mgmt_row, text="+ Save Current", width=95, height=26,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=self.theme.get("accent_purple", "#A78BFA"),
            text_color="#000000",
            command=self._save_custom_preset
        ).pack(side="left", padx=(0, 4))

        neon_ui.Button(
            mgmt_row, text="Export JSON", width=80, height=26,
            font=ctk.CTkFont(size=12),
            fg_color=self.theme.get("button_bg", "#222630"),
            command=self._export_profile
        ).pack(side="left", padx=2)

        neon_ui.Button(
            mgmt_row, text="Import JSON", width=80, height=26,
            font=ctk.CTkFont(size=12),
            fg_color=self.theme.get("button_bg", "#222630"),
            command=self._import_profile
        ).pack(side="left", padx=2)

        saved_row = neon_ui.Frame(card, fg_color="transparent")
        saved_row.pack(fill="x", padx=16, pady=(8, 4))
        names = list(self.app.config.get("bz_custom_presets", {}))
        self.custom_preset_menu = ctk.CTkOptionMenu(saved_row, values=names or ["No saved presets"],
                                                   fg_color=self.theme.get("button_bg", "#222630"),
                                                   text_color=self.theme.get("text_primary", "#FFFFFF"))
        self.custom_preset_menu.pack(side="left", fill="x", expand=True, padx=(0, 6))
        neon_ui.Button(saved_row, text="Load", width=60, command=self._load_custom_preset).pack(side="right")

        # Automation Rules
        ctk.CTkLabel(
            card, text="Automation",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.theme.get("text_primary", "#FFFFFF")
        ).pack(anchor="w", padx=16, pady=(10, 4))

        rules_box = neon_ui.Frame(card, fg_color="transparent")
        rules_box.pack(fill="x", padx=16, pady=2)

        # 1. Sync with Keyboard Zone 1
        self.sync_var = self.app.mecha_sync_var
        ctk.CTkCheckBox(
            rules_box, text="Match keyboard zone 1",
            variable=self.sync_var, command=self._on_sync_toggled,
            font=ctk.CTkFont(size=13),
            fg_color=self.theme.get("accent_purple", "#A78BFA")
        ).pack(anchor="w", pady=3)

        # 2. Turn off on Battery (DC)
        self.dc_off_var = ctk.BooleanVar(value=self.app.config.get("bz_turn_off_on_battery", False))
        ctk.CTkCheckBox(
            rules_box, text="Turn off on battery",
            variable=self.dc_off_var, command=self._on_dc_off_toggled,
            font=ctk.CTkFont(size=13),
            fg_color=self.theme.get("accent_blue", "#38BDF8")
        ).pack(anchor="w", pady=3)

        # 3. Night Schedule
        self.sched_var = ctk.BooleanVar(value=self.app.config.get("bz_night_schedule_enabled", False))
        ctk.CTkCheckBox(
            rules_box, text="Night mode · 11 PM–7 AM",
            variable=self.sched_var, command=self._on_sched_toggled,
            font=ctk.CTkFont(size=13),
            fg_color=self.theme.get("accent_amber", "#F59E0B")
        ).pack(anchor="w", pady=3)

        # 4. UART Frame Rate Limiter
        fps_row = neon_ui.Frame(card, fg_color="transparent")
        fps_row.pack(fill="x", padx=16, pady=(8, 12))

        ctk.CTkLabel(
            fps_row, text="Animation quality",
            font=ctk.CTkFont(size=13),
            text_color=self.theme.get("text_secondary", "#94A3B8")
        ).pack(side="left", padx=(0, 8))

        self.fps_var = ctk.StringVar(value=f"{self.app.config.get('bz_fps_limit', 20)} FPS")
        ctk.CTkOptionMenu(
            fps_row, values=["10 FPS (Eco)", "15 FPS", "20 FPS (Standard)", "25 FPS", "30 FPS (Smooth)"],
            variable=self.fps_var, command=self._on_fps_changed,
            width=140, height=26, font=ctk.CTkFont(size=12)
        ).pack(side="left")

    def _create_diagnostics_banner(self, parent):
        self.diag_banner = neon_ui.Frame(
            parent, fg_color=self.theme.get("card_bg", "#181A20"),
            corner_radius=10, border_width=1,
            border_color=self.theme.get("card_border", "#282B33")
        )
        self.diag_banner.pack(fill="x", padx=16, pady=(4, 16))

        self.diag_lbl = ctk.CTkLabel(
            self.diag_banner, text="Telemetry: Ready · ACPI PNP0501 active",
            font=ctk.CTkFont(size=12),
            text_color=self.theme.get("text_secondary", "#94A3B8")
        )
        self.diag_lbl.pack(side="left", padx=12, pady=6)

        self.diag_retry_btn = neon_ui.Button(
            self.diag_banner, text="Reconnect UART", width=110, height=24,
            font=ctk.CTkFont(size=12),
            fg_color=self.theme.get("button_bg", "#222630"),
            command=self._reconnect_uart
        )
        self.diag_retry_btn.pack(side="right", padx=12, pady=4)

    # -----------------------------------------------------------------------
    # Dynamic Visibility & Control Management
    # -----------------------------------------------------------------------
    def update_dynamic_controls(self):
        """Show or hide controls dynamically based on the active mode."""
        mode = getattr(self.app, "bz_mode", 1)
        meta = EFFECT_METADATA.get(mode, EFFECT_METADATA[1])

        # Speed visibility
        if meta["has_speed"]:
            self.speed_section.pack(fill="x", padx=16, pady=4, before=self.bright_section)
        else:
            self.speed_section.pack_forget()

        # Primary Color visibility
        if meta["has_color1"]:
            self.c1_container.pack(side="left", padx=(0, 16), before=self.c2_container if self.c2_container.winfo_manager() else self.color_tools_box)
        else:
            self.c1_container.pack_forget()

        # Secondary Color visibility
        if meta["has_color2"]:
            self.c2_container.pack(side="left", padx=(0, 10), before=self.color_tools_box)
        else:
            self.c2_container.pack_forget()

        # Full color section visibility
        if meta["has_color1"] or meta["has_color2"]:
            self.color_section.pack(fill="x", padx=16, pady=(0, 8), before=self.speed_section if self.speed_section.winfo_manager() else self.bright_section)
        else:
            self.color_section.pack_forget()

        # Audio controls visibility
        if meta["has_audio"]:
            self.audio_section.pack(fill="x", padx=16, pady=4, before=self.actions_bar)
        else:
            self.audio_section.pack_forget()

        # Temperature controls visibility
        if meta["has_temp"]:
            self.temp_section.pack(fill="x", padx=16, pady=4, before=self.actions_bar)
        else:
            self.temp_section.pack_forget()

        # Photosensitivity warning
        if meta.get("warning"):
            self.controls_warning_lbl.configure(text=meta["warning"])
        else:
            self.controls_warning_lbl.configure(text="")

    # -----------------------------------------------------------------------
    # Event Handlers & Control Callbacks
    # -----------------------------------------------------------------------
    def _on_master_toggled(self):
        self.app._on_mecha_toggled()
        # Powering back on should always produce visible light, even when an
        # older profile stored the legacy "Off" effect.
        if self.master_switch_var.get() and getattr(self.app, "bz_mode", 1) == 15:
            self._select_mode(1)
        self._redraw_preview_strip()

    def _open_color_picker(self, idx: int):
        init_color = tuple(self.app.bz_color1 if idx == 1 else self.app.bz_color2)
        title = f"Choose {'primary' if idx == 1 else 'secondary'} Rear Bar color"

        def on_apply(rgb):
            rgb_vivid = vivid_rgb(rgb)
            hex_str = rgb_to_hex(rgb_vivid)
            if idx == 1:
                self.app.bz_color1 = list(rgb_vivid)
                self.app.config["bz_color1"] = self.app.bz_color1
                if hasattr(self.app, 'bz_c1_swatch'):
                    self.app.bz_c1_swatch.configure(bg=hex_str)
                if hasattr(self, 'c1_hex_entry'):
                    self.c1_hex_entry.delete(0, "end")
                    self.c1_hex_entry.insert(0, hex_str)
            else:
                self.app.bz_color2 = list(rgb_vivid)
                self.app.config["bz_color2"] = self.app.bz_color2
                if hasattr(self.app, 'bz_c2_swatch'):
                    self.app.bz_c2_swatch.configure(bg=hex_str)
                if hasattr(self, 'c2_hex_entry'):
                    self.c2_hex_entry.delete(0, "end")
                    self.c2_hex_entry.insert(0, hex_str)
            if hasattr(self.app, '_add_recent_color'):
                self.app._add_recent_color(hex_str)
            self.app._save_config()
            self.app._apply_backzone_hardware()

        color_studio.ColorPickerDialog(
            parent=self.root,
            initial_rgb=init_color,
            title=title,
            theme_colors=self.theme,
            on_apply=on_apply,
            recent_colors=getattr(self.app, 'recent_colors', None)
        )

    def _on_hex_entered(self, idx: int):
        entry = self.c1_hex_entry if idx == 1 else self.c2_hex_entry
        val = entry.get()
        rgb = hex_to_rgb(val)
        if rgb:
            rgb = vivid_rgb(rgb)
            hex_str = rgb_to_hex(rgb)
            if idx == 1:
                self.app.bz_color1 = list(rgb)
                self.app.config["bz_color1"] = self.app.bz_color1
                self.app.bz_c1_swatch.configure(bg=hex_str)
            else:
                self.app.bz_color2 = list(rgb)
                self.app.config["bz_color2"] = self.app.bz_color2
                self.app.bz_c2_swatch.configure(bg=hex_str)
            self.app._save_config()
            self.app._apply_backzone_hardware()

    def _swap_colors(self):
        c1, c2 = list(self.app.bz_color1), list(self.app.bz_color2)
        self.app.bz_color1, self.app.bz_color2 = c2, c1
        self.app.config["bz_color1"] = self.app.bz_color1
        self.app.config["bz_color2"] = self.app.bz_color2
        
        hex1, hex2 = rgb_to_hex(self.app.bz_color1), rgb_to_hex(self.app.bz_color2)
        self.app.bz_c1_swatch.configure(bg=hex1)
        self.c1_hex_entry.delete(0, "end")
        self.c1_hex_entry.insert(0, hex1)
        
        self.app.bz_c2_swatch.configure(bg=hex2)
        self.c2_hex_entry.delete(0, "end")
        self.c2_hex_entry.insert(0, hex2)

        self.app._save_config()
        self.app._apply_backzone_hardware()

    def _randomize_colors(self):
        h1 = random.random()
        h2 = (h1 + 0.35 + random.random() * 0.3) % 1.0
        c1 = tuple(int(round(v * 255)) for v in colorsys.hsv_to_rgb(h1, 1.0, 1.0))
        c2 = tuple(int(round(v * 255)) for v in colorsys.hsv_to_rgb(h2, 1.0, 1.0))

        self.app.bz_color1 = list(c1)
        self.app.bz_color2 = list(c2)
        self.app.config["bz_color1"] = self.app.bz_color1
        self.app.config["bz_color2"] = self.app.bz_color2

        hex1, hex2 = rgb_to_hex(c1), rgb_to_hex(c2)
        self.app.bz_c1_swatch.configure(bg=hex1)
        self.c1_hex_entry.delete(0, "end")
        self.c1_hex_entry.insert(0, hex1)

        self.app.bz_c2_swatch.configure(bg=hex2)
        self.c2_hex_entry.delete(0, "end")
        self.c2_hex_entry.insert(0, hex2)

        self.app._save_config()
        self.app._apply_backzone_hardware()

    def _set_speed(self, val: int):
        self.app.bz_speed = int(val)
        self.app.config["bz_speed"] = self.app.bz_speed
        self.app.bz_speed_slider.set(self.app.bz_speed)
        self.speed_val_lbl.configure(text=f"Level {self.app.bz_speed}")
        self.app._save_config()
        self.app._apply_backzone_hardware()

    def _on_speed_slider_changed(self, value):
        val = max(1, min(9, int(round(value))))
        self.app.bz_speed = val
        self.app.config["bz_speed"] = val
        self.speed_val_lbl.configure(text=f"Level {val}")
        self._debounce_apply()

    def _on_brightness_slider_changed(self, value):
        val = max(0, min(100, int(round(value))))
        self.app.bz_brightness = val
        self.app.config["bz_brightness"] = val
        self.bright_val_lbl.configure(text=f"{val}%")
        self._debounce_apply()

    def _debounce_apply(self):
        if self._debounce_job is not None:
            self.root.after_cancel(self._debounce_job)
        
        # Debounce to prevent flooding serial UART
        self._debounce_job = self.root.after(40, self._apply_debounced)

    def _apply_debounced(self):
        self._debounce_job = None
        self.app._save_config()
        self.app._apply_backzone_hardware()

    def _on_audio_sens_changed(self, val):
        self.app.config["bz_audio_sensitivity"] = float(val)
        self.app._save_config()

    def _on_audio_decay_changed(self, val):
        self.app.config["bz_audio_decay"] = float(val)
        self.app._save_config()

    def _on_temp_source_changed(self, val):
        self.app.config["bz_temp_source"] = "GPU" if "GPU" in str(val) else "CPU"
        self.app._save_config()

    def _on_sync_toggled(self):
        self.app._on_mecha_sync_toggled()

    def _on_dc_off_toggled(self):
        val = self.dc_off_var.get()
        self.app.config["bz_turn_off_on_battery"] = val
        self.app._save_config()
        self.app._apply_backzone_hardware()

    def _on_sched_toggled(self):
        val = self.sched_var.get()
        self.app.config["bz_night_schedule_enabled"] = val
        self.app._save_config()
        self.app._apply_backzone_hardware()

    def _on_fps_changed(self, val):
        try:
            if isinstance(val, (int, float)):
                fps = int(val)
            else:
                fps = int(str(val).split()[0])
            self.app.config["bz_fps_limit"] = max(10, min(60, fps))
            self.app._save_config()
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Presets, Profile Import / Export & Hardware Actions
    # -----------------------------------------------------------------------
    def _apply_preset(self, cfg: Dict[str, Any]):
        cfg = validate_rear_profile(cfg, BACKZONE_MODE_NAMES)
        if cfg["mode"] in ARCADE_BETA_MODES:
            raise ValueError("Battle & Arcade is Beta and temporarily unavailable. Choose another effect.")
        self.app.bz_mode = cfg.get("mode", 1)
        self.app.bz_color1 = list(cfg.get("color1", [56, 189, 248]))
        self.app.bz_color2 = list(cfg.get("color2", [167, 139, 250]))
        self.app.bz_speed = cfg.get("speed", 4)
        self.app.bz_brightness = cfg.get("brightness", 100)

        self.app.config["bz_mode"] = self.app.bz_mode
        self.app.config["bz_color1"] = self.app.bz_color1
        self.app.config["bz_color2"] = self.app.bz_color2
        self.app.config["bz_speed"] = self.app.bz_speed
        self.app.config["bz_brightness"] = self.app.bz_brightness
        self.app.config.update(cfg["options"])
        self.sync_var.set(self.app.config.get("mecha_bar_sync", True))
        self.dc_off_var.set(self.app.config.get("bz_turn_off_on_battery", False))
        self.sched_var.set(self.app.config.get("bz_night_schedule_enabled", False))
        self.fps_var.set(f"{self.app.config.get('bz_fps_limit', 20)} FPS")
        self.app.bz_mode_seg.set(BACKZONE_MODE_NAMES[self.app.bz_mode])
        
        # Update UI controls
        self.app.bz_speed_slider.set(self.app.bz_speed)
        self.speed_val_lbl.configure(text=f"Level {self.app.bz_speed}")
        self.app.bz_bright_slider.set(self.app.bz_brightness)
        self.bright_val_lbl.configure(text=f"{self.app.bz_brightness}%")
        
        hex1, hex2 = rgb_to_hex(self.app.bz_color1), rgb_to_hex(self.app.bz_color2)
        self.app.bz_c1_swatch.configure(bg=hex1)
        self.c1_hex_entry.delete(0, "end")
        self.c1_hex_entry.insert(0, hex1)
        self.app.bz_c2_swatch.configure(bg=hex2)
        self.c2_hex_entry.delete(0, "end")
        self.c2_hex_entry.insert(0, hex2)

        meta = EFFECT_METADATA.get(self.app.bz_mode)
        if meta and meta["category"] != self.current_category:
            self._select_category(meta["category"])
        else:
            self._populate_effect_cards()
            self.update_dynamic_controls()

        self.app._save_config()
        self.app._apply_backzone_hardware()

    def _save_custom_preset(self):
        pname = f"Custom Preset {len(self.app.config.get('bz_custom_presets', {})) + 1}"
        cfg = {
            "mode": self.app.bz_mode,
            "color1": list(self.app.bz_color1),
            "color2": list(self.app.bz_color2),
            "speed": self.app.bz_speed,
            "brightness": self.app.bz_brightness,
        }
        if "bz_custom_presets" not in self.app.config:
            self.app.config["bz_custom_presets"] = {}
        self.app.config["bz_custom_presets"][pname] = cfg
        self.custom_preset_menu.configure(values=list(self.app.config["bz_custom_presets"]))
        self.custom_preset_menu.set(pname)
        self.app._save_config()
        messagebox.showinfo("Preset Saved", f"Saved current light configuration as '{pname}'!")

    def _load_custom_preset(self):
        cfg = self.app.config.get("bz_custom_presets", {}).get(self.custom_preset_menu.get())
        if cfg is not None:
            try:
                self._apply_preset(cfg)
            except ValueError as error:
                messagebox.showerror("Invalid preset", str(error))

    def _export_profile(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Export Mecha Bar Profile"
        )
        if path:
            data = {
                "bz_mode": self.app.bz_mode,
                "bz_color1": self.app.bz_color1,
                "bz_color2": self.app.bz_color2,
                "bz_speed": self.app.bz_speed,
                "bz_brightness": self.app.bz_brightness,
                "bz_fps_limit": self.app.config.get("bz_fps_limit", 20),
                "mecha_bar_sync": self.app.config.get("mecha_bar_sync", True),
                "bz_turn_off_on_battery": self.app.config.get("bz_turn_off_on_battery", False),
                "bz_night_schedule_enabled": self.app.config.get("bz_night_schedule_enabled", False),
            }
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                messagebox.showinfo("Profile Exported", "Profile exported successfully!")
            except Exception as e:
                messagebox.showerror("Export Failed", str(e))

    def _import_profile(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")],
            title="Import Mecha Bar Profile"
        )
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._apply_preset(data)
                messagebox.showinfo("Profile Imported", "Profile imported and applied!")
            except Exception as e:
                messagebox.showerror("Import Failed", str(e))

    def _test_hardware_cycle(self):
        """Run an automated hardware cycle test (Red -> Green -> Blue -> White -> Restore)."""
        if self.app._rear_test_active:
            return
        self.app._rear_test_active = True
        def run_test():
            try:
                for col in ((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)):
                    if not self.app.running:
                        return
                    if not self.app.SerialEngine.send_backzone_rgb(
                        effect=1, r1=col[0], g1=col[1], b1=col[2], speed=1, bright=80
                    ):
                        self.app._ui_dispatch(self.app._set_hardware_status, False, "Rear test", self.app.SerialEngine.get_last_error())
                        break
                    time.sleep(0.35)
            finally:
                self.app._rear_test_active = False
                self.app._ui_dispatch(self.app._apply_backzone_hardware)

        import threading
        threading.Thread(target=run_test, daemon=True).start()

    def _restore_firmware(self):
        """Re-initializes the firmware registers by re-sending Mode 1 packet."""
        ok = self.app.SerialEngine.send_backzone_rgb(
            effect=1, r1=self.app.bz_color1[0], g1=self.app.bz_color1[1], b1=self.app.bz_color1[2],
            speed=self.app.bz_speed, bright=self.app.bz_brightness
        )
        if ok:
            messagebox.showinfo("Firmware Restored", "Firmware state re-synchronized!")
        else:
            messagebox.showerror("Restore Failed", self.app.SerialEngine.get_last_error())

    def _reconnect_uart(self):
        """Forces UART port re-discovery and re-connection."""
        self.app.SerialEngine.reconnect()
        ok = self.app._apply_backzone_hardware()
        self._update_port_status()

    def _update_port_status(self):
        """Update port label and connection state badge."""
        port = getattr(self.app.SerialEngine, "_last_port", None)
        err = self.app.SerialEngine.get_last_error()
        if port and not err:
            self.port_badge.configure(
                text=f"● Connected • {port}",
                text_color=self.theme.get("accent_green", "#22C55E")
            )
            self.diag_lbl.configure(text=f"UART Port: {port} (115200 baud, 17-byte OEM protocol) · Normal")
        else:
            self.port_badge.configure(
                text="○ Disconnected",
                text_color=self.theme.get("accent_rose", "#F43F5E")
            )
            self.diag_lbl.configure(text=f"UART Status: {err or 'Port not acquired'}")

    # -----------------------------------------------------------------------
    # Live Visualizer Canvas Loop
    # -----------------------------------------------------------------------
    def _update_live_preview(self):
        """Tick function called periodically to animate the on-screen preview."""
        if not getattr(self.app, "running", True):
            return
        try:
            if not hasattr(self, "root") or not self.root or not self.root.winfo_exists():
                return
            if self.app.active_page != "backzone" or not self.root.winfo_viewable():
                self._preview_job = self.root.after(250, self._update_live_preview)
                return
        except Exception:
            return
        try:
            is_active = self.app._backzone_allowed()
            mode = getattr(self.app, "bz_mode", 1)
            bright = getattr(self.app, "bz_brightness", 100)
            led_hexes = ["#11141A"] * 36

            # Determine rendered frame
            if not is_active or mode == 15:
                hex_color = "#11141A"
                disp_bright = 0
                status_txt = "Powered off"
            else:
                phase = (time.monotonic() * (0.2 + 0.15 * getattr(self.app, "bz_speed", 3))) % 1.0
                audio_vol = getattr(self.app, "audio_volume", 0.0)
                audio_levels = getattr(self.app, "audio_levels", [0.0]*4)
                audio_beat = getattr(self.app, "audio_beat", 0.0)
                
                # Fetch temperature
                temp_c = self.app._rear_temperature()
                bat = getattr(self.app, "battery_val", 100)
                on_ac = getattr(self.app, "on_ac_val", True)

                rgb, disp_bright = render_backzone_effect_v2(
                    mode, phase, self.app.bz_color1, self.app.bz_color2, bright,
                    audio_volume=audio_vol, audio_levels=audio_levels, audio_beat=audio_beat,
                    temp_celsius=temp_c, bat_pct=bat, on_ac=on_ac
                )
                hex_color = rgb_to_hex(rgb)
                led_rgbs = render_backzone_strip_leds(
                    mode, phase, self.app.bz_color1, self.app.bz_color2, bright,
                    num_leds=36, audio_volume=audio_vol, audio_levels=audio_levels, audio_beat=audio_beat,
                    temp_celsius=temp_c, bat_pct=bat, on_ac=on_ac
                )
                led_hexes = [rgb_to_hex(c) for c in led_rgbs]

                mode_name = BACKZONE_MODE_NAMES.get(mode, "Active")
                meta = EFFECT_METADATA.get(mode, {})
                cat = meta.get("category", "")
                
                status_info = f"{mode_name} · {disp_bright}% brightness"
                if cat == "Audio":
                    status_info += f" · Audio {int(audio_vol*100)}%"
                elif mode == 112:
                    status_info += f" · Thermal: {int(temp_c)}°C" if temp_c is not None else " · Temperature sensor unavailable"
                elif cat == "Battle & Arcade":
                    native_name = BACKZONE_MODE_NAMES[ARCADE_FIRMWARE_MODES[mode]]
                    status_info += f" · Concept preview · Hardware: {native_name} (dual colour)"
                status_txt = status_info

            self._redraw_preview_strip(hex_color, disp_bright, led_hexes)
            self.status_line.configure(text=status_txt)
            self._update_port_status()

        except Exception:
            pass

        # Schedule next preview frame at ~25 FPS
        try:
            if getattr(self.app, "running", True) and hasattr(self, "root") and self.root and self.root.winfo_exists():
                self._preview_job = self.root.after(40, self._update_live_preview)
        except Exception:
            pass

    def close(self):
        for name in ("_preview_job", "_debounce_job"):
            job = getattr(self, name, None)
            if job is not None:
                try:
                    if hasattr(self, "root") and self.root:
                        self.root.after_cancel(job)
                except Exception:
                    pass
                setattr(self, name, None)

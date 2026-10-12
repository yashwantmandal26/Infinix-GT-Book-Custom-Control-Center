"""
Infinix GT Toolkit v4.5.2
=============================
Commercial-grade, eye-pleasing hardware control suite & intelligent automation engine
crafted specifically for the Infinix GT Book (Model GL613 / BYD N16 chassis).

Key Highlights:
- Eye-Pleasing Nordic Dark Palette & Gradient Styling (Zero Eye Strain)
- Anti-Timeout Heartbeat Engine (permanently eliminates 10s hardware sleep)
- 🧠 AI Smart Dynamic Governor (Intelligent Auto-Scaling between Quiet & Beast modes)
- 🌅 AI Circadian Auto-Lighting (24-Hour natural light temperature adaptation)
- 🎮 AI Game & Studio Auto-Detector (Auto-activates Beast & Win-Lock on game launch)
- 🎛️ Precision RGB Matrix: 4-Zone Interactive Map, R/G/B Sliders (0-255) & Hex Input
- 💾 Custom User Preset Library (Save, Name, and Load custom layouts anytime)
- ⚡ Hardware Thermal Curves & 100% Extreme Cooler Boost
- 📊 Real-Time Hardware Telemetry (CPU load, RAM GB/%, Battery infrastructure)
- 🔌 OEM USB Sleep Charging & Smart Inactivity Dimmer
- 🔒 Mutex-protected thread-safe HID engine & Custom Cyber-Mecha Application Icon
"""

import os
import sys

if "TCL_LIBRARY" not in os.environ or "TK_LIBRARY" not in os.environ:
    _py_base = sys.base_prefix.replace("\\", "/")
    _tcl_cand = f"{_py_base}/tcl/tcl8.6"
    _tk_cand = f"{_py_base}/tcl/tk8.6"
    if os.path.isdir(_tcl_cand):
        os.environ["TCL_LIBRARY"] = _tcl_cand
    if os.path.isdir(_tk_cand):
        os.environ["TK_LIBRARY"] = _tk_cand

import time
import json
import math
import random
import copy
import shutil
import traceback
import datetime
import ctypes
from ctypes import wintypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
import colorsys
import re
import subprocess
import threading
import mss
import keyboard
import wmi
from typing import Dict, Tuple, List, Optional, Any

import hid
import serial
import psutil
import soundcard as sc
import numpy as np
import customtkinter as ctk
import neon_ui
import tkinter as tk
from tkinter import colorchooser, messagebox
from PIL import Image, ImageDraw
import pystray
import backzone_ui
import studio_ui
from app_runtime import ConfigWriter, UiMailbox, LightingHistory
from hardware_runtime import HardwareCommandController, CommandResult, format_reliability_report
from automation_policy import AutomationPolicy
from update_service import GitHubUpdateService
import color_studio
from keyboard_motion import CUSTOM_MOTION_EFFECTS, render_custom_motion
from color_studio import (
    ColorPickerDialog, normalize_hex_color, rgb_to_hex, hex_to_rgb,
    rgb_to_hsv_display, hsv_display_to_rgb, best_text_color,
    validate_rgb_channels, validate_hsv_channels
)

# ---------------------------------------------------------------------------
# Path & Directory Configuration
# ---------------------------------------------------------------------------
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Infinix.GTBook.ControlCenter.Toolkit.v4")
except Exception:
    pass

APP_DIR = os.path.dirname(os.path.abspath(__file__)) if not getattr(sys, 'frozen', False) else os.path.dirname(sys.executable)

def _find_app_icon():
    candidates = [
        getattr(sys, '_MEIPASS', None),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Programs\InfinixGTToolkit"),
        os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else None,
        os.path.dirname(os.path.abspath(__file__)),
    ]
    for c in candidates:
        if c:
            p = os.path.join(c, "infinix_gt_icon.ico")
            if os.path.exists(p):
                return os.path.abspath(p)
    return os.path.join(APP_DIR, "infinix_gt_icon.ico")

ICON_PATH = _find_app_icon()
ASSET_DIR = os.path.join(APP_DIR, "assets")
CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "InfinixGTToolkit")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config_v4.json")
CRASH_LOG_FILE = os.path.join(CONFIG_DIR, "crash.log")
STARTUP_DIR = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
SHORTCUT_PATH = os.path.join(STARTUP_DIR, "InfinixGTToolkit.lnk")
APP_VERSION = "4.5.2"
BUILD_CHANNEL = "Stable"
BUILD_DATE = "2026-10-12"
UPDATE_REPOSITORY = "yashwantmandal26/Infinix-GT-Book-Custom-Control-Center"


def startup_command_target():
    """Return the Task Scheduler command used for a silent background launch."""
    root_exe = os.path.join(APP_DIR, "InfinixGTToolkit.exe")
    if os.path.exists(root_exe):
        launch = f'"{root_exe}"'
    elif getattr(sys, "frozen", False):
        launch = f'"{sys.executable}"'
    else:
        python_w = sys.executable.replace("python.exe", "pythonw.exe")
        if not os.path.exists(python_w):
            python_w = sys.executable
        launch = f'"{python_w}" "{os.path.abspath(__file__)}"'
    return f"{launch} --minimized"


def log_crash_exception(exc_type, exc_value, exc_traceback, context: str = "Unhandled Exception"):
    """Atomically append uncaught exception information to crash.log for non-crashing diagnosis."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(CRASH_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n[{ts}] [{context}]\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
            f.flush()
    except Exception:
        pass


def global_excepthook(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    log_crash_exception(exc_type, exc_value, exc_traceback, context="sys.excepthook")


sys.excepthook = global_excepthook

# ---------------------------------------------------------------------------
# Vivid Saturated Color Presets (Neon & High-Energy)
# ---------------------------------------------------------------------------
SOFT_COLOR_PRESETS = [
    # Row 1 — Warm & Energetic
    ("🔴 Pure Red",       "#FF0000", (255,   0,   0)),
    ("🌹 Blood Rose",     "#FF0032", (255,   0,  50)),
    ("🟠 Neon Orange",    "#FF3C00", (255,  60,   0)),
    ("🌟 Cyber Yellow",   "#FFB400", (255, 180,   0)),
    ("🍑 Pastel Peach",   "#FF6450", (255, 100,  80)),
    ("🩷 Hot Pink",       "#FF0078", (255,   0, 120)),
    ("🔮 Magenta Flash",  "#FF00FF", (255,   0, 255)),
    ("💜 Plasma Purple",  "#8C00FF", (140,   0, 255)),
    # Row 2 — Cool & Serene
    ("🌌 Deep Indigo",    "#5000FF", ( 80,   0, 255)),
    ("⚡ Pure Blue",      "#0000FF", (  0,   0, 255)),
    ("🌤️ Sky Blue",       "#00A0FF", (  0, 160, 255)),
    ("🔵 Arctic Cyan",    "#00FFFF", (  0, 255, 255)),
    ("🌿 Mint Jolt",      "#00FF64", (  0, 255, 100)),
    ("🟢 Matrix Green",   "#00FF00", (  0, 255,   0)),
    ("☢️ Toxic Lime",     "#8CFF00", (140, 255,   0)),
    ("❄️ Ice White",      "#FFFFFF", (255, 255, 255)),
]

# ---------------------------------------------------------------------------
# High-Visibility Modern Dual-Theme Design Tokens (Light & Dark)
# Tuple format: (Light Mode Color, Dark Mode Color)
# ---------------------------------------------------------------------------
THEME = {
    # Surfaces & Backgrounds (Refined Slate Dark Mode - Less Harsh/Dark)
    "root_bg": ("#F8FAFC", "#171B24"),        # Crisp light slate vs comfortable dark slate
    "sidebar_bg": ("#FFFFFF", "#1C2230"),     # Pure white vs refined dark slate
    "sidebar_border": ("#E2E8F0", "#2A3548"), # Subtle divider
    "topbar_bg": ("#FFFFFF", "#1F2636"),      # Clean elevated header
    "topbar_border": ("#E2E8F0", "#2A3548"),  # Header divider

    # Elevated Cards & Sub-Panels
    "card_bg": ("#FFFFFF", "#232B3B"),        # High-visibility elevated slate card
    "card_border": ("#E2E8F0", "#344158"),    # Crisp modern border outline
    "card_sub_bg": ("#F1F5F9", "#1C2330"),    # Nested inset tile
    "card_sub_border": ("#E2E8F0", "#2E3A4F"),# Tile border

    # Typography
    "text_primary": ("#0F172A", "#F8FAFC"),   # 100% deep contrast dark slate vs clean bright white
    "text_secondary": ("#475569", "#A0AEC0"), # Readable slate text
    "text_muted": ("#64748B", "#718096"),     # Muted caption text

    # Interactive Controls & Buttons
    "button_bg": ("#F1F5F9", "#2D374B"),      # Clearly visible button background
    "button_hover": ("#E2E8F0", "#394660"),   # Button hover state
    "button_text": ("#1E293B", "#F8FAFC"),    # High-contrast button text
    "entry_bg": ("#FFFFFF", "#1E2533"),       # Text input background
    "entry_border": ("#CBD5E1", "#3B4962"),   # Text input border

    # Navigation Pills
    "nav_idle_bg": "transparent",
    "nav_idle_text": ("#475569", "#A0AEC0"),
    "nav_hover": ("#F1F5F9", "#262F40"),
    "nav_active_bg": ("#E0F2FE", "#1E3A5F"),  # Soft sky pill vs deep blue pill
    "nav_active_text": ("#0284C7", "#38BDF8"),# Crisp sky text
    "nav_active_border": ("#0284C7", "#38BDF8"),

    # Accent Badges & Sliders
    "accent_blue": ("#0284C7", "#38BDF8"),    # Sky blue
    "accent_cyan": ("#0891B2", "#22D3EE"),    # Cyan for GPU
    "accent_purple": ("#7C3AED", "#A78BFA"),  # Violet
    "accent_green": ("#059669", "#34D399"),   # Emerald
    "accent_amber": ("#D97706", "#FBBF24"),   # Amber
    "accent_rose": ("#E11D48", "#FB7185"),    # Rose / Coral

    # Progress & Status Bars
    "progress_bg": ("#E2E8F0", "#2C374A"),
    "pill_bg": ("#F1F5F9", "#232C3C"),
    "pill_border": ("#E2E8F0", "#35435B"),
}

# Shared Fluent-inspired surfaces, readable secondary text, restrained accents.
THEME.update({
    "root_bg": ("#F2F6FC", "#07111F"),
    "sidebar_bg": ("#F9FBFF", "#0D1B2D"),
    "sidebar_border": ("#CAD8EA", "#2B6AA4"),
    "topbar_bg": ("#F2F6FC", "#07111F"),
    "topbar_border": ("#F2F6FC", "#07111F"),
    "card_bg": ("#FFFFFF", "#0C1A2B"),
    "card_border": ("#CAD8EA", "#246296"),
    "card_sub_bg": ("#F3F7FC", "#0B1828"),
    "card_sub_border": ("#D6E0EC", "#1D3853"),
    "button_bg": ("#E8F0FA", "#152943"),
    "button_hover": ("#D6E8FA", "#203B5D"),
    "entry_bg": ("#F8FAFD", "#091522"),
    "entry_border": ("#AFC4DC", "#31567A"),
    "text_secondary": ("#4D6078", "#A8BFDA"),
    "text_muted": ("#5D7088", "#7894B5"),
    "nav_active_bg": ("#DCEEFF", "#1467D9"),
    "nav_active_border": ("#45B8FF", "#27C8FF"),
    "nav_active_text": ("#075C91", "#F4FAFF"),
    "accent_blue": ("#0875B3", "#25C7FF"),
    "accent_cyan": ("#0891B2", "#22D3EE"),
    "pill_bg": ("#EAF1FA", "#10233A"),
    "pill_border": ("#CAD8EA", "#243F61"),
    "progress_bg": ("#D6E2F0", "#142A44"),
})

ANIMATION_DIRECTIONS = ("➡️ Left to Right", "⬅️ Right to Left")
LEGACY_ANIMATION_DIRECTIONS = {
    "🔄 Clockwise": ANIMATION_DIRECTIONS[0],
    "🔁 Counter-CW": ANIMATION_DIRECTIONS[1],
}
DIRECTIONAL_EFFECTS = {"Aurora", "AllAurora", "Wave", "ColorShift", "RainbowPrism", "BlazingFire", *CUSTOM_MOTION_EFFECTS}
SPEED_CONTROLLED_EFFECTS = {"Aurora", "AllAurora", "Wave", "RandomMorph", "BreathingPulse", "ColorShift", "RainbowPrism", "BlazingFire", *CUSTOM_MOTION_EFFECTS}

EFFECT_DISPLAY_NAMES = {
    "Solid": "🌈 Solid Calm",
    "Aurora": "🌌 Aurora Borealis",
    "AllAurora": "↔️ left-rigt-left",
    "RainbowPrism": "🌈 Rainbow Prism",
    "BlazingFire": "🔥 Blazing Fire",
    "Wave": "🌊 Wave Sweep",
    "RandomMorph": "🎲 Random Morph",
    "BreathingPulse": "🫁 Breathing Pulse",
    "ColorShift": "🎨 Color Shift",
    "ScreenSync": "🎬 Screen Sync",
    "ReactiveTyping": "⚡ Reactive Typing",
    "AudioSync": "🎵 Audio Visualizer",
    "MagneticSlingshot": "🧲 Magnetic Slingshot",
    "ChromaticRelay": "🧬 Chromatic Relay",
    "TimeFracture": "⏳ Time Fracture",
    "OrbitalEclipse": "🪐 Orbital Eclipse",
}

def render_all_aurora(
    step: float,
    direction: str,
    base_color: Optional[Tuple[int, int, int]] = None
) -> Dict[str, Tuple[int, int, int]]:
    """
    Render a single consistent color moving smoothly from start to end (Left to Right)
    and vice versa (Right to Left) across all 4 zones without changing into any other color.
    """
    if base_color is None:
        base_color = (255, 0, 0)

    # Smooth continuous ping-pong oscillation: 0.0 (Zone 1) to 3.0 (Zone 4) and back
    phase = step * 0.068
    is_rtl = "Right to Left" in direction
    if is_rtl:
        pos = 1.5 + 1.5 * math.cos(phase)
    else:
        pos = 1.5 - 1.5 * math.cos(phase)

    colors = {}
    r_base, g_base, b_base = base_color
    for i, zid in enumerate(("1", "2", "3", "4")):
        dist = abs(i - pos)
        beam = math.exp(-(dist * dist) / (2.0 * 0.65 * 0.65))
        # Keep an elegant 10% ambient floor so non-active zones softly glow
        intensity = min(1.0, max(0.10, 0.10 + 0.90 * beam))
        colors[zid] = (
            int(round(r_base * intensity)),
            int(round(g_base * intensity)),
            int(round(b_base * intensity))
        )
    return colors


def render_aurora(step: float, direction: str) -> Dict[str, Tuple[int, int, int]]:
    """Render classic multi-hue Aurora Borealis (cyan-blue-magenta wave)."""
    zones = {}
    for i, zid in enumerate(("1", "2", "3", "4")):
        if "Right to Left" in direction:
            idx_offset = (3 - i) * 0.6
        else:
            idx_offset = i * 0.6
        hue = 0.44 + 0.32 * ((math.sin(step * 0.035 + idx_offset) + 1.0) / 2.0)
        r, g, b = [int(round(c * 255)) for c in colorsys.hsv_to_rgb(hue, 1.0, 1.0)]
        zones[zid] = (r, g, b)
    return zones


# 7 Spectral ROYGBIV colors calibrated for high luminous vibrancy on keyboard LEDs
ROYGBIV_PALETTE: List[Tuple[int, int, int]] = [
    (255, 0, 0),      # Red
    (255, 127, 0),    # Orange
    (255, 230, 0),    # Yellow
    (0, 255, 0),      # Green
    (0, 110, 255),    # Blue
    (75, 0, 130),     # Indigo
    (155, 0, 220),    # Violet
]


def render_rainbow_prism(step: float, direction: str) -> Dict[str, Tuple[int, int, int]]:
    """
    Render true 7-color spectral wave (Red, Orange, Yellow, Green, Blue, Indigo, Violet)
    gliding across 4 zones one after another with smooth cosine blending, just like Aurora Borealis.
    """
    zones = {}
    is_rtl = "Right to Left" in direction
    num_colors = len(ROYGBIV_PALETTE)
    for i, zid in enumerate(("1", "2", "3", "4")):
        idx_offset = (3 - i) * 0.75 if is_rtl else i * 0.75
        pos = (step * 0.065 + idx_offset) % num_colors
        idx1 = int(pos)
        idx2 = (idx1 + 1) % num_colors
        frac = pos - idx1
        blend = 0.5 - 0.5 * math.cos(frac * math.pi)
        c1 = ROYGBIV_PALETTE[idx1]
        c2 = ROYGBIV_PALETTE[idx2]
        r = int(round(c1[0] + (c2[0] - c1[0]) * blend))
        g = int(round(c1[1] + (c2[1] - c1[1]) * blend))
        b = int(round(c1[2] + (c2[2] - c1[2]) * blend))
        zones[zid] = (min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b)))
    return zones


def render_blazing_fire(step: float, direction: str = "") -> Dict[str, Tuple[int, int, int]]:
    """
    Render ultra-high brightness blazing fire / inferno across 4 zones.
    Combines multi-frequency harmonic turbulence with high-luma crimson, amber, gold,
    and white-hot solar flares to maximize physical LED brightness.
    """
    zones = {}
    is_rtl = "Right to Left" in direction
    for i, zid in enumerate(("1", "2", "3", "4")):
        offset = (3 - i) * 0.85 if is_rtl else i * 0.85
        # Multi-frequency turbulent harmonic flame heat
        w1 = math.sin(step * 0.045 + offset)
        w2 = 0.5 * math.sin(step * 0.095 - offset * 1.3)
        w3 = 0.25 * math.sin(step * 0.18 + offset * 2.1)
        raw_heat = (w1 + w2 + w3 + 1.75) / 3.5
        heat = max(0.0, min(1.0, raw_heat))
        
        # Fire heat gradient: Deep Crimson (255, 30, 0) -> Orange (255, 120, 0) -> Gold (255, 210, 10) -> White-Hot (255, 255, 180)
        r = 255
        g = int(round(30 + 195 * (heat ** 1.3)))
        b = int(round(180 * max(0.0, (heat - 0.75) / 0.25) ** 1.5))
        zones[zid] = (min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b)))
    return zones


def process_screen_pixel(sr: int, sg: int, sb: int) -> Tuple[int, int, int]:
    """Converts raw screen pixel to faithful keyboard LED RGB without garish hue or saturation distortion."""
    h_val, s_val, v_val = colorsys.rgb_to_hsv(sr / 255.0, sg / 255.0, sb / 255.0)
    if s_val > 0.12:
        # Subtle LED vibrancy boost preserving true hue
        s_out = min(1.0, s_val * 1.25)
        v_out = max(0.12, min(1.0, v_val * 1.10))
        return tuple(int(round(c * 255)) for c in colorsys.hsv_to_rgb(h_val, s_out, v_out))
    else:
        # Clean neutral preservation (whites, grays, silvers, blacks)
        v_out = max(0.10, v_val)
        factor = v_out / max(0.01, v_val) if v_val > 0.01 else 1.0
        return (
            min(255, int(round(sr * factor))),
            min(255, int(round(sg * factor))),
            min(255, int(round(sb * factor)))
        )


# Physical key-to-zone mappings for 4-zone keyboard
KEY_TO_ZONE = {
    # Zone 1: WASD / Left Modifiers
    'esc': '1', 'escape': '1', '`': '1', '~': '1',
    '1': '1', '2': '1', '3': '1', '4': '1',
    'f1': '1', 'f2': '1', 'f3': '1', 'f4': '1',
    'tab': '1', 'q': '1', 'w': '1', 'e': '1', 'r': '1',
    'caps lock': '1', 'caps_lock': '1', 'capslock': '1',
    'a': '1', 's': '1', 'd': '1', 'f': '1',
    'left shift': '1', 'shift': '1',
    'z': '1', 'x': '1', 'c': '1', 'v': '1',
    'left ctrl': '1', 'ctrl': '1',
    'left windows': '1', 'windows': '1', 'win': '1',
    'left alt': '1', 'alt': '1',

    # Zone 2: Center Alpha & Space
    '5': '2', '6': '2', '7': '2', '8': '2', '9': '2',
    'f5': '2', 'f6': '2', 'f7': '2', 'f8': '2',
    't': '2', 'y': '2', 'u': '2', 'i': '2', 'o': '2',
    'g': '2', 'h': '2', 'j': '2', 'k': '2', 'l': '2',
    'b': '2', 'n': '2', 'm': '2',
    ',': '2', '<': '2', '.': '2', '>': '2',
    'space': '2', 'spacebar': '2',

    # Zone 3: Right Alphas, Navigation & Arrows
    '0': '3', '-': '3', '_': '3', '=': '3', '+': '3',
    'f9': '3', 'f10': '3', 'f11': '3', 'f12': '3',
    'backspace': '3', 'delete': '3', 'del': '3',
    'p': '3', '[': '3', '{': '3', ']': '3', '}': '3', '\\': '3', '|': '3',
    ';': '3', ':': '3', "'": '3', '"': '3',
    'enter': '3', 'return': '3',
    '/': '3', '?': '3',
    'right shift': '3', 'right alt': '3', 'alt gr': '3', 'right ctrl': '3',
    'menu': '3', 'apps': '3',
    'up': '3', 'down': '3', 'left': '3', 'right': '3',
    'insert': '3', 'ins': '3', 'home': '3', 'end': '3',
    'page up': '3', 'pageup': '3', 'page down': '3', 'pagedown': '3',

    # Zone 4: Numpad
    'num lock': '4', 'numlock': '4', 'num_lock': '4',
    'decimal': '4', 'add': '4', 'subtract': '4', 'multiply': '4', 'divide': '4',
    'clear': '4',
    'numpad 0': '4', 'numpad 1': '4', 'numpad 2': '4', 'numpad 3': '4', 'numpad 4': '4',
    'numpad 5': '4', 'numpad 6': '4', 'numpad 7': '4', 'numpad 8': '4', 'numpad 9': '4',
    'numpad0': '4', 'numpad1': '4', 'numpad2': '4', 'numpad3': '4', 'numpad4': '4',
    'numpad5': '4', 'numpad6': '4', 'numpad7': '4', 'numpad8': '4', 'numpad9': '4',
    'num 0': '4', 'num 1': '4', 'num 2': '4', 'num 3': '4', 'num 4': '4',
    'num 5': '4', 'num 6': '4', 'num 7': '4', 'num 8': '4', 'num 9': '4',
    'num_0': '4', 'num_1': '4', 'num_2': '4', 'num_3': '4', 'num_4': '4',
    'num_5': '4', 'num_6': '4', 'num_7': '4', 'num_8': '4', 'num_9': '4',
    'kp_0': '4', 'kp_1': '4', 'kp_2': '4', 'kp_3': '4', 'kp_4': '4',
    'kp_5': '4', 'kp_6': '4', 'kp_7': '4', 'kp_8': '4', 'kp_9': '4',
    'kp_enter': '4', 'kp_add': '4', 'kp_subtract': '4', 'kp_multiply': '4', 'kp_divide': '4',
    'kp_decimal': '4',
    'numpad enter': '4', 'num enter': '4', 'numpad return': '4', 'num return': '4',
    'numpad decimal': '4', 'numpad .': '4', 'num .': '4', 'num del': '4', 'numpad del': '4',
    'numpad delete': '4', 'num delete': '4',
    'numpad +': '4', 'numpad -': '4', 'numpad *': '4', 'numpad /': '4',
    'num +': '4', 'num -': '4', 'num *': '4', 'num /': '4',
}

KEYPAD_SCAN_CODES = {
    28,  # Num Enter (extended)
    53,  # Num / (extended)
    55,  # Num *
    69,  # Num Lock
    71,  # Num 7 / Home
    72,  # Num 8 / Up
    73,  # Num 9 / PgUp
    74,  # Num -
    75,  # Num 4 / Left
    76,  # Num 5 / Clear
    77,  # Num 6 / Right
    78,  # Num +
    79,  # Num 1 / End
    80,  # Num 2 / Down
    81,  # Num 3 / PgDn
    82,  # Num 0 / Ins
    83,  # Num . / Del
}


def get_key_zone(key_input: Any, is_keypad: bool = False, scan_code: int = 0) -> str:
    """Map any Windows key name, event, or character to its physical keyboard zone (1-4)."""
    if hasattr(key_input, 'scan_code'):
        scan_code = getattr(key_input, 'scan_code', scan_code) or scan_code
    if hasattr(key_input, 'is_keypad'):
        is_keypad = bool(getattr(key_input, 'is_keypad', False))

    # 1. Hardware scan code & keypad event detection (Zone 4 - Numpad)
    if is_keypad:
        return "4"
    if scan_code in (55, 69, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83):
        return "4"

    kname = getattr(key_input, 'name', str(key_input) if key_input is not None else "")
    if not kname:
        return "2"
    k = str(kname).lower().strip()

    # 2. Keypad naming prefixes/substrings
    if any(m in k for m in ("numpad", "num ", "num_", "numlock", "keypad", "kp_")):
        return "4"

    # 3. Direct dictionary mapping
    if k in KEY_TO_ZONE:
        return KEY_TO_ZONE[k]

    # 4. Positional heuristics
    if any(m in k for m in ("left", "wasd", "esc", "tab", "caps")):
        return "1"
    if any(m in k for m in ("right", "arrow", "del", "enter", "home", "end", "page", "insert", "back")):
        return "3"
    return "2"


def render_reactive_typing(
    zone_typing_times: Dict[str, float],
    zones_config: Dict[str, Any],
    now: float = 0.0,
    decay_duration: float = 0.60
) -> Dict[str, Tuple[int, int, int]]:
    """
    Render true per-zone reactive keystroke luminescence.
    Struck zone bursts with intense, ultra-bright electric luminescence of its configured color,
    sustains peak brilliance, then decays smoothly.
    Idle zones rest at a gentle, dimmed ambient glow.
    Strict zone isolation ensures ONLY the struck zone illuminates without bleeding to neighbors.
    """
    if now <= 0.0:
        now = time.time()
    
    result = {}
    for zid in ("1", "2", "3", "4"):
        dt_direct = now - zone_typing_times.get(zid, 0.0)
        
        # Punchy burst curve: 80ms sustain at peak brightness followed by smooth ease-out decay
        if 0.0 <= dt_direct < decay_duration:
            if dt_direct <= 0.08:
                direct_pulse = 1.0
            else:
                progress = (dt_direct - 0.08) / (decay_duration - 0.08)
                direct_pulse = max(0.0, (1.0 - progress) ** 0.85)
        else:
            direct_pulse = 0.0
        
        base_rgb = tuple(zones_config.get(zid, (56, 189, 248)))
        # Normalize/boost base color to full 255 dynamic range for maximum vibrance
        max_c = max(base_rgb) if base_rgb else 0
        if max_c > 0:
            scale = 255.0 / max_c
            vivid_rgb = tuple(min(255, int(round(c * scale))) for c in base_rgb)
        else:
            vivid_rgb = (255, 255, 255)
        
        # Idle ambient is clearly visible and pleasant (~35% base color, guaranteed vivid visibility)
        amb_r = max(int(base_rgb[0] * 0.35), int(vivid_rgb[0] * 0.28))
        amb_g = max(int(base_rgb[1] * 0.35), int(vivid_rgb[1] * 0.28))
        amb_b = max(int(base_rgb[2] * 0.35), int(vivid_rgb[2] * 0.28))
        
        # Peak flash reaches full electric brightness (up to 255) with vivid saturation
        flash_r = min(255, int(vivid_rgb[0] * 0.85 + 255 * 0.25))
        flash_g = min(255, int(vivid_rgb[1] * 0.85 + 255 * 0.25))
        flash_b = min(255, int(vivid_rgb[2] * 0.85 + 255 * 0.25))
        
        r = int(amb_r + (flash_r - amb_r) * direct_pulse)
        g = int(amb_g + (flash_g - amb_g) * direct_pulse)
        b = int(amb_b + (flash_b - amb_b) * direct_pulse)
        result[zid] = (r, g, b)
        
    return result


def render_wave_sweep(step: float, direction: str) -> Dict[str, Tuple[int, int, int]]:
    """Render a bright leading crest with a coloured, smoothly fading wake."""
    travel = (step * 0.065) % 6.5 - 1.5
    if "Right to Left" in direction:
        travel = 3.0 - travel
    base_hue = (step * 0.004) % 1.0
    colors = {}
    for i, zid in enumerate(("1", "2", "3", "4")):
        signed_distance = i - travel
        distance = abs(signed_distance)
        crest = math.exp(-3.2 * distance * distance)
        wake_side = signed_distance if "Right to Left" in direction else -signed_distance
        wake = math.exp(-0.9 * max(0.0, wake_side)) if wake_side > 0.0 else 0.0
        value = min(1.0, 0.055 + 0.94 * crest + 0.34 * wake)
        hue = (base_hue + i * 0.055 - signed_distance * 0.018) % 1.0
        saturation = max(0.25, 1.0 - crest * 0.70)
        colors[zid] = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(hue, saturation, value))
    return colors


def render_audio_visualizer(
    levels,
    beat: float,
    step: float,
    base_zones: Optional[Dict[str, Tuple[int, int, int]]] = None
) -> Dict[str, Tuple[int, int, int]]:
    """
    Map bass-to-treble energy to four vivid zones with a dynamic white beat flash.
    Maintains a solid visible baseline (minimum 35% brightness) so keyboard never goes dark.
    Smoothly blends with user's base signature when music is paused / silent.
    """
    values = list(levels or ())[:4]
    values += [0.0] * (4 - len(values))
    colors = {}
    tot_energy = sum(values)

    # 4 distinct, vivid acoustic frequency zones:
    # Zone 1 (WASD): Electric Cyan (0.55) - Bass / Kick
    # Zone 2 (Alpha): Royal Violet (0.76) - Low-Mid
    # Zone 3 (Arrows): Neon Magenta (0.91) - High-Mid
    # Zone 4 (Numpad): Amber Gold (0.11) - Treble
    base_hues = [0.55, 0.76, 0.91, 0.11]

    for i, zid in enumerate(("1", "2", "3", "4")):
        level = max(0.0, min(1.0, float(values[i])))
        hue = (base_hues[i] + step * 0.001) % 1.0
        # Dynamic brightness scaling: minimum 38% baseline up to 100%
        value = 0.38 + 0.62 * (level ** 0.60)

        # Beat flash: transients drive saturation down towards brilliant white and boost value
        beat_val = max(0.0, min(1.0, float(beat)))
        saturation = max(0.18, 1.0 - beat_val * 0.78)
        if beat_val > 0.25:
            value = min(1.0, value + beat_val * 0.25)

        c_rgb = tuple(int(round(c * 255)) for c in colorsys.hsv_to_rgb(hue, saturation, value))

        # When audio is silent (< 0.04 total energy), gracefully blend with user's base zone colors
        if base_zones and zid in base_zones and tot_energy < 0.04:
            blend = max(0.0, tot_energy / 0.04)
            base = tuple(base_zones[zid])
            c_rgb = (
                int(round(base[0] * (1.0 - blend) + c_rgb[0] * blend)),
                int(round(base[1] * (1.0 - blend) + c_rgb[1] * blend)),
                int(round(base[2] * (1.0 - blend) + c_rgb[2] * blend))
            )
        colors[zid] = c_rgb
    return colors



def normalize_animation_direction(value) -> str:
    """Migrate legacy four-way choices to the two directions the keyboard supports."""
    if value in ANIMATION_DIRECTIONS:
        return value
    return LEGACY_ANIMATION_DIRECTIONS.get(value, ANIMATION_DIRECTIONS[0])


def validate_lighting_preset(data):
    """Validate an entire imported profile before changing live state."""
    if not isinstance(data, dict):
        raise ValueError("A preset must be a JSON object.")
    zones = data.get("zones")
    if not isinstance(zones, dict) or set(zones) != {"1", "2", "3", "4"}:
        raise ValueError("A preset must contain all four keyboard zones.")
    for rgb in zones.values():
        if not isinstance(rgb, (list, tuple)) or len(rgb) != 3 or any(
                type(channel) is not int or not 0 <= channel <= 255 for channel in rgb):
            raise ValueError("Zone colors require three integers between 0 and 255.")
    brightness = data.get("brightness", 100)
    if type(brightness) is not int or not 0 <= brightness <= 100:
        raise ValueError("Brightness must be an integer between 0 and 100.")
    effect = data.get("effect_mode", "Solid")
    if effect not in {"Solid", "Aurora", "AllAurora", "Wave", "RandomMorph", "BreathingPulse", "ColorShift", "ScreenSync", "ReactiveTyping", "AudioSync", "RainbowPrism", "BlazingFire", *CUSTOM_MOTION_EFFECTS}:
        raise ValueError("Unsupported lighting effect.")
    power = data.get("power_mode", "Balanced")
    if power not in {"Quiet", "Balanced", "Beast"}:
        raise ValueError("Unsupported power profile.")
    speed = data.get("animation_speed", "Normal")
    raw_direction = data.get("animation_direction", ANIMATION_DIRECTIONS[0])
    if raw_direction not in ANIMATION_DIRECTIONS and raw_direction not in LEGACY_ANIMATION_DIRECTIONS:
        raise ValueError("Unsupported animation direction.")
    direction = normalize_animation_direction(raw_direction)
    if speed not in {"Slow", "Normal", "Fast", "Turbo"}:
        raise ValueError("Unsupported animation speed.")
    return dict(zones={k: list(v) for k, v in zones.items()}, brightness=brightness,
                effect_mode=effect, power_mode=power, animation_speed=speed,
                animation_direction=direction)


ZONE_THEMES = {
    # Cool / Tech
    "🌌 Twilight Glow":  {"1": (0, 180, 255),  "2": (155, 0, 255),  "3": (0, 180, 255),  "4": (155, 0, 255)},
    "💜 Cyberpunk":      {"1": (0, 255, 255),  "2": (255, 0, 255),  "3": (0, 255, 255),  "4": (255, 0, 255)},
    "🌊 Ocean Surge":    {"1": (0, 100, 255),  "2": (0, 200, 255),  "3": (0, 255, 220),  "4": (0, 180, 255)},
    "🌙 Midnight":      {"1": (60, 0, 180),   "2": (0, 60, 200),   "3": (0, 120, 255),  "4": (100, 0, 255)},
    "❄️ Frostbite":      {"1": (0, 255, 255),  "2": (0, 180, 255),   "3": (0, 120, 255),  "4": (0, 255, 200)},
    # Warm / Energetic
    "🔥 Inferno":        {"1": (255, 0, 0),    "2": (255, 80, 0),   "3": (255, 140, 0),  "4": (255, 200, 0)},
    "🍂 Autumn Sunset":  {"1": (255, 61, 0),   "2": (255, 180, 0),  "3": (255, 0, 128),  "4": (0, 200, 255)},
    "☕ Warm Cafe":      {"1": (255, 180, 0),  "2": (255, 98, 0),   "3": (255, 180, 0),  "4": (255, 61, 0)},
    "🌋 Volcano Core":   {"1": (255, 0, 0),    "2": (255, 20, 0),   "3": (200, 0, 0),    "4": (150, 0, 0)},
    "🌸 Cherry Blossom":{"1": (255, 100, 150), "2": (255, 50, 100), "3": (255, 0, 150),  "4": (200, 0, 100)},
    # High Contrast / Gaming
    "⚡ Lightning":      {"1": (255, 230, 0),  "2": (200, 255, 0),  "3": (255, 230, 0),  "4": (0, 200, 255)},
    "🎮 Gaming RGB":    {"1": (255, 0, 0),    "2": (0, 255, 0),    "3": (0, 0, 255),    "4": (255, 0, 255)},
    "☢️ Biohazard":     {"1": (140, 255, 0),  "2": (0, 255, 0),    "3": (140, 255, 0),  "4": (50, 255, 0)},
    "🕹️ Arcade Retro":  {"1": (255, 0, 128),  "2": (0, 255, 255),  "3": (255, 255, 0),  "4": (255, 0, 0)},
    "🤖 Mecha Core":    {"1": (255, 150, 0),  "2": (0, 255, 255),  "3": (0, 255, 150),  "4": (255, 150, 0)},
    # Vibrant & Lush
    "🌲 Nordic Forest":  {"1": (0, 255, 127),  "2": (0, 200, 255),  "3": (0, 255, 127),  "4": (0, 180, 255)},
    "🌺 Neon Garden":   {"1": (0, 255, 80),   "2": (170, 255, 0),  "3": (255, 0, 128),  "4": (255, 0, 200)},
    "🍭 Candy Pop":     {"1": (255, 0, 128),  "2": (255, 180, 0),  "3": (0, 255, 200),  "4": (180, 0, 255)},
    "🍇 Grapevine":     {"1": (140, 0, 255),  "2": (200, 0, 255),  "3": (100, 0, 255),  "4": (80, 0, 200)},
    "🍹 Tropical":      {"1": (255, 0, 50),   "2": (255, 100, 0),  "3": (255, 200, 0),  "4": (0, 255, 100)},
}

ZONE_LABELS = {
    "1": "Z1: WASD",
    "2": "Z2: Center",
    "3": "Z3: Right",
    "4": "Z4: Numpad"
}

KNOWN_GAME_TITLES = {
    # Installed games on this PC
    "gta5.exe": "Grand Theft Auto V",
    "playgtav.exe": "Grand Theft Auto V",
    "run_gtav.exe": "Grand Theft Auto V",
    "gta5_be.exe": "Grand Theft Auto V",
    "rdr2.exe": "Red Dead Redemption 2",
    "run_rdr2.exe": "Red Dead Redemption 2",
    "farcry6.exe": "Far Cry 6",
    "acblackflag.exe": "Assassin's Creed IV Black Flag",
    "gta_sa.exe": "Grand Theft Auto: San Andreas",
    # Popular games
    "witcher3.exe": "The Witcher 3: Wild Hunt",
    "cyberpunk2077.exe": "Cyberpunk 2077",
    "eldenring.exe": "Elden Ring",
    "cs2.exe": "Counter-Strike 2",
    "csgo.exe": "Counter-Strike: Global Offensive",
    "valorant.exe": "Valorant",
    "fortniteclient-win64-shipping.exe": "Fortnite",
    "apex.exe": "Apex Legends",
    "r5apex.exe": "Apex Legends",
    "overwatch.exe": "Overwatch 2",
    "cod.exe": "Call of Duty",
    "b1-win64-shipping.exe": "Black Myth: Wukong",
    "forzahorizon5.exe": "Forza Horizon 5",
    "forzahorizon4.exe": "Forza Horizon 4",
    "godofwar.exe": "God of War",
    "spiderman.exe": "Marvel's Spider-Man Remastered",
    "milesmorales.exe": "Marvel's Spider-Man: Miles Morales",
    "ghostoftsushima.exe": "Ghost of Tsushima",
    "horizonzerodawn.exe": "Horizon Zero Dawn",
    "starfield.exe": "Starfield",
    "bg3.exe": "Baldur's Gate 3",
    "bg3_dx11.exe": "Baldur's Gate 3",
    "pubg.exe": "PUBG: Battlegrounds",
    "tslgame.exe": "PUBG: Battlegrounds",
    "helldivers2.exe": "Helldivers 2",
    "genshinimpact.exe": "Genshin Impact",
    "starrail.exe": "Honkai: Star Rail",
    "wutheringwaves.exe": "Wuthering Waves",
    "minecraft.exe": "Minecraft",
    "javaw.exe": "Minecraft (Java Edition)",
    "robloxplayerbeta.exe": "Roblox",
    # Creative apps
    "blender.exe": "Blender",
    "premiere.exe": "Adobe Premiere Pro",
    "afterfx.exe": "Adobe After Effects",
    "obs64.exe": "OBS Studio",
    "unrealeditor.exe": "Unreal Engine Editor",
    "unity.exe": "Unity Editor",
}

KNOWN_GAME_PROCESSES = set(KNOWN_GAME_TITLES.keys())

IGNORE_GAME_EXES = {
    "unins000.exe", "uninstall.exe", "crashreporter.exe", "crash_report.exe",
    "dxsetup.exe", "vcredist_x64.exe", "vcredist_x86.exe", "easyanticheat.exe",
    "easyanticheat_eos.exe", "battleye.exe", "beservice_x64.exe", "aria2c.exe",
    "gtavlanguageselect.exe", "epicgameslauncher.exe", "steam.exe", "steamservice.exe",
    "steamwebhelper.exe", "riotclientservices.exe", "origin.exe", "eadesktop.exe",
    "battle.net.exe", "gog_galaxy.exe", "discord.exe", "chrome.exe", "brave.exe", "msedge.exe"
}

GAME_PATH_KEYWORDS = [
    r"\installed games",
    r"\games",
    r"\steamapps\common",
    r"\epic games",
    r"\xboxgames",
    r"\riot games",
    r"\ubisoft",
    r"\ea games",
    r"\origin games",
    r"\battle.net",
    r"\gog galaxy\games"
]

DEFAULT_CONFIG = {
    "gpu_gaming_alert": True,
    "theme": "Dark",
    "always_on": True,
    "brightness": 100,
    "effect_mode": "Solid",          # Solid, Aurora, Wave, RandomMorph, BreathingPulse, ColorShift, ScreenSync
    "animation_speed": "Normal",     # Slow, Normal, Fast, Turbo
    "animation_direction": ANIMATION_DIRECTIONS[0],
    "screen_sync_mode": "Spatial",            # Spatial (4-Zone) vs Unified (Full Keyboard)
    "current_theme": "",
    "current_color": [56, 189, 248],
    "zones": {
        "1": [56, 189, 248],
        "2": [167, 139, 250],
        "3": [56, 189, 248],
        "4": [167, 139, 250]
    },
    "mecha_bar_enabled": True,
    "mecha_bar_sync": True,
    "mecha_bar_color": [167, 139, 250],
    "power_mode": "Balanced",
    "cooler_boost": False,
    # The bundled OEM WMI interface exposes battery telemetry but no verified
    # charge-threshold setter. Keep this off until a model-specific command is known.
    "battery_limit_80": False,
    "auto_switch_on_ac": True,
    "automation_paused": False,
    "manual_override_minutes": 30,
    "manual_mode_until": 0.0,
    "last_page": "lighting",
    "lighting_section": "Effects",
    "last_notified_update_version": "",
    "usb_charge_off": True,
    "win_key_lock": False,
    "software_fn_lock": False,
    "emergency_battery_saver": True,
    "color_temp_kelvin": 6500,
    "autostart": True,
    "close_to_tray": True,
    "preset_include_power": False,
    "ai_governor": True,
    "ai_circadian": False,
    "ai_game_detector": True,
    "bz_mode": 1,
    "bz_color1": [56, 189, 248],
    "bz_color2": [167, 139, 250],
    "bz_speed": 3,
    "bz_brightness": 100,
    "bz_turn_off_on_battery": False,
    "bz_night_schedule_enabled": False,
    "bz_night_start": "23:00",
    "bz_night_end": "07:00",
    "bz_fps_limit": 20,
    "bz_audio_sensitivity": 1.0,
    "bz_audio_decay": 0.85,
    "bz_temp_source": "CPU",
    "bz_custom_presets": {},
    "recent_colors": ["#FF0032", "#38BDF8", "#A78BFA", "#22C55E", "#F59E0B", "#EC4899", "#06B6D4", "#8C00FF"],
    "audio_gain_multiplier": 1.5,
    "user_presets": {}
}

def kelvin_to_rgb(kelvin: float) -> Tuple[int, int, int]:
    """Convert color temperature in Kelvin (1800K - 10000K) to (R, G, B) tuple."""
    temp = max(1000, min(40000, float(kelvin))) / 100.0
    # Calculate Red
    if temp <= 66:
        r = 255.0
    else:
        r = temp - 60
        r = 329.698727446 * (r ** -0.1332047592)
        r = max(0.0, min(255.0, r))
    # Calculate Green
    if temp <= 66:
        g = temp
        g = 99.4708025861 * math.log(max(1.0, g)) - 161.1195681661
        g = max(0.0, min(255.0, g))
    else:
        g = temp - 60
        g = 288.1221695283 * (g ** -0.0755148492)
        g = max(0.0, min(255.0, g))
    # Calculate Blue
    if temp >= 66:
        b = 255.0
    elif temp <= 19:
        b = 0.0
    else:
        b = temp - 10
        b = 138.5177312231 * math.log(max(1.0, b)) - 305.0447927307
        b = max(0.0, min(255.0, b))
    return int(round(r)), int(round(g)), int(round(b))


def vivid_rgb(rgb) -> Tuple[int, int, int]:
    """Force chromatic colors to full saturation while preserving light output."""
    r, g, b = (max(0, min(255, int(v))) for v in rgb)
    if max(r, g, b) == 0 or max(r, g, b) == min(r, g, b):
        return r, g, b
    hue, _sat, value = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    return tuple(int(round(v * 255)) for v in colorsys.hsv_to_rgb(hue, 1.0, value))


BACKZONE_MODE_NAMES = dict(backzone_ui.BACKZONE_MODE_NAMES)
# Preserve legacy test key aliases
BACKZONE_MODE_NAMES[101] = "Spectrum Flow"
BACKZONE_MODE_NAMES[102] = "Dual Neon Fade"


def render_backzone_effect(mode: int, phase: float, color1, color2, brightness: int, **kwargs):
    """Render one deterministic frame for a software-driven rear effect."""
    return backzone_ui.render_backzone_effect_v2(mode, phase, color1, color2, brightness, **kwargs)

# ---------------------------------------------------------------------------
# Software Fn-Lock Engine (Media Keys Mapper)
# ---------------------------------------------------------------------------
class SoftwareFnLock:
    _enabled = False
    _f3_tap_callback = None
    _f3_hold_callback = None
    _hooks = []

    _f3_lock = threading.Lock()
    _f3_pressed = False
    _f3_press_time = 0.0
    _f3_is_hold = False

    @classmethod
    def set_callbacks(cls, on_tap, on_hold=None):
        cls._f3_tap_callback = on_tap
        cls._f3_hold_callback = on_hold

    @classmethod
    def set_callback(cls, callback):
        cls._f3_tap_callback = callback

    @classmethod
    def set_enabled(cls, enabled: bool):
        cls._enabled = enabled
        for h in cls._hooks:
            try:
                keyboard.unhook(h)
            except Exception:
                pass
        cls._hooks.clear()

        with cls._f3_lock:
            cls._f3_pressed = False
            cls._f3_is_hold = False

        if enabled:
            try:
                cls._hooks.append(keyboard.on_press_key('f1', cls._on_f1, suppress=True))
                cls._hooks.append(keyboard.on_press_key('f2', cls._on_f2, suppress=True))
                cls._hooks.append(keyboard.hook_key('f3', cls._on_f3_event, suppress=True))
            except Exception as e:
                print(f"FnLock Hook Error: {e}")

    @classmethod
    def _change_brightness(cls, step: int):
        try:
            import pythoncom
            pythoncom.CoInitialize()
            try:
                w = wmi.WMI(namespace='wmi')
                monitors = w.WmiMonitorBrightness()
                if not monitors:
                    return
                cur = monitors[0].CurrentBrightness
                new_b = max(0, min(100, cur + step))
                methods = w.WmiMonitorBrightnessMethods()
                if methods:
                    methods[0].WmiSetBrightness(Timeout=0, Brightness=new_b)
            finally:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass
        except Exception:
            pass

    @classmethod
    def _on_f1(cls, e):
        # Fire and forget in a separate thread to not block the keyboard hook
        threading.Thread(target=cls._change_brightness, args=(-10,), daemon=True).start()
        return False

    @classmethod
    def _on_f2(cls, e):
        threading.Thread(target=cls._change_brightness, args=(10,), daemon=True).start()
        return False

    @classmethod
    def _on_f3_event(cls, e):
        ev_type = getattr(e, 'event_type', '')
        if ev_type == 'down':
            with cls._f3_lock:
                if cls._f3_pressed:
                    return False
                cls._f3_pressed = True
                cls._f3_press_time = time.time()
                cls._f3_is_hold = False

            def _f3_hold_worker():
                # Initial hold threshold: 450ms
                time.sleep(0.45)
                with cls._f3_lock:
                    if not cls._f3_pressed:
                        return
                    cls._f3_is_hold = True

                # Hold trigger: cycle effect mode exactly once per hold gesture
                if cls._f3_hold_callback:
                    try:
                        cls._f3_hold_callback()
                    except Exception:
                        pass

            threading.Thread(target=_f3_hold_worker, daemon=True).start()

        elif ev_type == 'up':
            was_tap = False
            with cls._f3_lock:
                if cls._f3_pressed:
                    if not cls._f3_is_hold:
                        was_tap = True
                    cls._f3_pressed = False
                    cls._f3_is_hold = False

            if was_tap and cls._f3_tap_callback:
                try:
                    cls._f3_tap_callback()
                except Exception:
                    pass

        return False

# ---------------------------------------------------------------------------
# Serial Controller Engine (BackZone)
# ---------------------------------------------------------------------------
class SerialEngine:
    """Thread-safe low-level Serial communication for the Rear BackZone LED."""
    _lock = threading.Lock()
    _last_error = ""
    _last_port = None
    _serial = None
    _ec_power_state = None
    _last_power_refresh = 0.0
    _retry_after = 0.0

    @classmethod
    def get_last_error(cls) -> str:
        return cls._last_error

    @classmethod
    def get_port_info(cls) -> Tuple[Optional[str], bool, str]:
        return cls._last_port, (cls._serial is not None and getattr(cls._serial, "is_open", False)), cls._last_error

    @classmethod
    def test_hardware(cls) -> bool:
        """Flash cycle to test connection."""
        for col in ((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)):
            if not cls.send_backzone_rgb(1, col[0], col[1], col[2], 1, 80):
                return False
            time.sleep(0.3)
        return True

    @classmethod
    def _discover_backzone_port(cls) -> Optional[str]:
        """Locate the internal UART used by the OEM instead of assuming COM1."""
        override = os.environ.get("INFINIX_BACKZONE_COM_PORT", "").strip()
        if override:
            return override.upper()
        if cls._last_port:
            return cls._last_port

        # Match the OEM query for ACPI\PNP0501\SERIALIOUART1 and extract its
        # current Windows COM assignment from a name such as "... (COM4)".
        detected = None
        try:
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()
            try:
                locator = win32com.client.Dispatch("WbemScripting.SWbemLocator")
                services = locator.ConnectServer(".", "root\\cimv2")
                query = r"SELECT Name, PNPDeviceID FROM Win32_PNPEntity WHERE PNPDeviceID='ACPI\PNP0501\SERIALIOUART1'"
                for obj in services.ExecQuery(query):
                    match = re.search(r"\((COM\d+)\)", str(getattr(obj, "Name", "")), re.IGNORECASE)
                    if match:
                        detected = match.group(1).upper()
                        break
                del services
                del locator
            finally:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass
        except Exception:
            pass
        if detected:
            return detected

        # Some firmware exposes the same identifier through SetupAPI instead.
        try:
            from serial.tools import list_ports
            for port in list_ports.comports():
                identity = " ".join(str(v or "") for v in (
                    port.device, port.name, port.description, port.hwid
                )).upper()
                if "SERIALIOUART1" in identity or "PNP0501" in identity:
                    return str(port.device)
            # Fallback to COM1 if standard PNP serial port exists
            for port in list_ports.comports():
                if str(port.device).upper() == "COM1":
                    return "COM1"
        except Exception:
            pass
        return None

    @classmethod
    def _get_or_open_port(cls):
        if cls._serial is not None and getattr(cls._serial, "is_open", False):
            return cls._serial
        port = cls._discover_backzone_port()
        if not port:
            raise RuntimeError("Rear-light UART was not found (expected ACPI PNP0501/SERIALIOUART1)")
        cls._serial = serial.Serial(
            port=port, baudrate=115200, bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
            timeout=0.25, write_timeout=0.5,
        )
        cls._last_port = port
        return cls._serial

    @classmethod
    def send_backzone_rgb(cls, effect: int, r1: int, g1: int, b1: int, speed: int, bright: int, r2: int = 0, g2: int = 0, b2: int = 0, bright2: int = 0):
        with cls._lock:
            if time.monotonic() < cls._retry_after:
                return False
            try:
                # 1. Ensure EC RAM power switch is turned ON for the BackZone hardware
                is_on = (effect != 15)
                if cls._ec_power_state is not is_on:
                    if not HardwareEngine.set_ec_backlight_power(is_on):
                        cls._last_error = HardwareEngine.get_last_error()
                        cls._retry_after = time.monotonic() + 1.0
                        return False
                    cls._ec_power_state = is_on
                    cls._last_power_refresh = time.monotonic()

                cr1 = max(0, min(255, int(round(r1))))
                cg1 = max(0, min(255, int(round(g1))))
                cb1 = max(0, min(255, int(round(b1))))
                cr2 = max(0, min(255, int(round(r2))))
                cg2 = max(0, min(255, int(round(g2))))
                cb2 = max(0, min(255, int(round(b2))))

                # 2. Build exact OEM 17-byte PARAMS struct
                buf = bytearray(17)
                buf[0] = 0x34  # h1 (52)
                buf[1] = 0x0E  # h2 (14)
                buf[2] = effect & 0xFF  # EffectCMD: 1=Always, 2=Breath, 3=MusicRythm, 4=MusicJump, 5=GameLoop, 6=GameCover, 15=Off
                buf[3] = cr1 & 0xFF     # r1
                buf[4] = 0              # r2 (reserved)
                buf[5] = cg1 & 0xFF     # g1
                buf[6] = 0              # g2 (reserved)
                buf[7] = cb1 & 0xFF     # b1
                buf[8] = 0              # b2 (reserved)
                buf[9] = max(1, min(9, int(speed))) & 0xFF  # Spd
                
                # Brightness level: OEM formula is int(bright * 0.44)
                l1 = int(max(0, min(100, bright)) * 0.44)
                buf[10] = l1            # l1
                buf[11] = 0             # l2 (reserved)
                
                # Dual color / Game & Audio modes
                if effect in (3, 4, 5, 6):
                    buf[12] = cr2  # fd1 (Color2 Red)
                    buf[13] = cg2  # fd2 (Color2 Green)
                    buf[14] = cb2  # fd3 (Color2 Blue)
                    l2 = int(max(0, min(100, bright2)) * 0.44) if bright2 > 0 else l1
                    buf[15] = l2         # fd4 (Color2 Brightness)
                else:
                    buf[12] = 0
                    buf[13] = 0
                    buf[14] = 0
                    buf[15] = 0
                
                buf[16] = 0             # checkSum field in PARAMS struct
                
                # The OEM keeps this UART open. Reusing it avoids DTR/RTS
                # resets and dropped frames during rapid UI changes.
                ser = cls._get_or_open_port()
                written = ser.write(bytes(buf))
                ser.flush()
                if written != len(buf):
                    raise IOError(f"UART wrote {written} of {len(buf)} bytes")
                cls._last_error = ""
                cls._retry_after = 0.0
                return True
            except Exception as e:
                cls._last_error = f"Rear-light serial update failed: {e}"
                cls._retry_after = time.monotonic() + 1.0
                cls._close_port()
                cls._last_port = None
                cls._ec_power_state = None
                return False

    @classmethod
    def reconnect(cls):
        with cls._lock:
            cls._close_port()
            cls._last_port = None
            cls._ec_power_state = None
            cls._retry_after = 0.0

    @classmethod
    def _close_port(cls):
        if cls._serial is not None:
            try:
                cls._serial.close()
            except Exception:
                pass
        cls._serial = None


# ---------------------------------------------------------------------------
# Hardware Controller Engine (Low-level USB HID Communication)
# ---------------------------------------------------------------------------
class HardwareEngine:
    """Thread-safe low-level USB HID communication for Infinix GT Laptop."""
    _lock = threading.Lock()
    _dev = None
    _watchdog_device = None
    _needs_mode_restore = False
    _last_path = None
    _last_error = ""

    @classmethod
    def get_last_error(cls) -> str:
        return cls._last_error

    @staticmethod
    def _get_acpi_method_provider():
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        locator = win32com.client.Dispatch("WbemScripting.SWbemLocator")
        try:
            locator.Security_.Privileges.AddAsString("SeSecurityPrivilege", True)
        except Exception:
            pass
        services = locator.ConnectServer(".", "root\\wmi")
        for obj in services.ExecQuery("SELECT * FROM ACPIMethod"):
            return obj
        raise RuntimeError("OEM ACPIMethod WMI provider is unavailable")

    @staticmethod
    def _exec_acpi_buffer(acpi_obj, method_name: str, buf):
        in_params = acpi_obj.Methods_(method_name).InParameters.SpawnInstance_()
        in_params.Properties_("IData").Value = list(buf)
        return acpi_obj.ExecMethod_(method_name, in_params)

    @classmethod
    def _io_write(cls, acpi_obj, address: int, value: int):
        buf = [0] * 24
        buf[0:4] = [66, 89, 68, 76]  # "BYDL"
        buf[4:6] = [0x00, 0x03]       # EC port 0x300
        buf[12] = 1
        buf[13] = 1
        buf[14] = 8
        buf[15] = address & 0xFF
        buf[16] = value & 0xFF
        return cls._exec_acpi_buffer(acpi_obj, "MemIO", buf)

    @classmethod
    def _io_read(cls, acpi_obj, address: int) -> int:
        buf = [0] * 24
        buf[0:4] = [66, 89, 68, 76]
        buf[4:6] = [0x00, 0x03]
        buf[12] = 1
        buf[13] = 0
        buf[14] = 8
        buf[15] = address & 0xFF
        out_params = cls._exec_acpi_buffer(acpi_obj, "MemIO", buf)
        odata = out_params.Properties_("OData").Value
        # OEM providers may return a scalar register value or a full packet.
        # Never substitute zero for malformed data before a read-modify-write.
        if isinstance(odata, int):
            return odata & 0xFF
        if isinstance(odata, (tuple, list, bytes, bytearray)) and len(odata) > 16:
            return int(odata[16]) & 0xFF
        raise RuntimeError(f"Unexpected MemIO response: {type(odata).__name__}")

    ALLOWED_EC_RAM_ADDRESSES = {0x40, 0x41, 0x4C, 0x4D, 0x4E, 0x5E, 0xC0}

    @classmethod
    def _ec_write_ram(cls, acpi_obj, address: int, value: int):
        # Strict device safety: reject any writes outside known safe OEM registers
        if address not in cls.ALLOWED_EC_RAM_ADDRESSES:
            cls._last_error = f"EC write blocked: address 0x{address:02X} is not whitelisted"
            return False
        # Clamp value to valid 8-bit range
        val = max(0, min(255, int(value)))
        # Exact sequence used by BYDWmi2.WmiServer.ECWriteRamCMD.
        cls._io_write(acpi_obj, 148, 0)
        cls._io_write(acpi_obj, 145, 0)
        cls._io_write(acpi_obj, 146, 0)
        cls._io_write(acpi_obj, 146, 1)
        cls._io_write(acpi_obj, 144, 0)
        cls._io_write(acpi_obj, 145, address)
        cls._io_write(acpi_obj, 160, val)
        cls._io_write(acpi_obj, 147, 161)
        return True

    @classmethod
    def _ec_read_ram(cls, acpi_obj, address: int) -> int:
        cls._io_write(acpi_obj, 148, 0)
        cls._io_write(acpi_obj, 146, 1)
        cls._io_write(acpi_obj, 144, 0)
        cls._io_write(acpi_obj, 145, address)
        cls._io_write(acpi_obj, 147, 160)
        return cls._io_read(acpi_obj, 160)

    @classmethod
    def _verify_ec_value(cls, acpi_obj, address: int, expected: int, mask: int = 0xFF) -> int:
        """Read a writable EC register back with a short firmware-settle window."""
        actual = None
        for attempt in range(3):
            actual = cls._ec_read_ram(acpi_obj, address)
            if actual & mask == expected & mask:
                return actual
            if attempt < 2:
                time.sleep(0.04)
        raise RuntimeError(
            f"EC verification failed at 0x{address:02X}: "
            f"expected 0x{expected & mask:02X}, read 0x{actual & mask:02X}")

    @classmethod
    def _smi(cls, acpi_obj, command: int, operation: int, value):
        # Exact 24-byte BYDWmi2.WmiServer.SMI layout.
        buf = [0] * 24
        buf[0:4] = [66, 89, 68, 76]
        buf[4:8] = [
            command & 0xFF,
            (command >> 8) & 0xFF,
            (command >> 16) & 0xFF,
            (command >> 24) & 0xFF,
        ]
        buf[12] = operation & 0xFF
        buf[13] = 0
        buf[16] = int(bool(value)) & 0xFF
        return cls._exec_acpi_buffer(acpi_obj, "SMI", buf)

    @classmethod
    def set_ec_backlight_power(cls, enable: bool = True):
        """Controls hardware power to the Rear BackZone LED via EC RAM at address 94 (0x5E)."""
        try:
            acpi_obj = cls._get_acpi_method_provider()
            cur_val = cls._ec_read_ram(acpi_obj, 94)
            l1 = cur_val & 1
            lps = cur_val & 128
            new_val = (0 | l1 | lps) if enable else (2 | l1 | lps)
            if new_val != cur_val and not cls._ec_write_ram(acpi_obj, 94, new_val):
                return False
            cls._last_error = ""
            return True
        except Exception as e:
            cls._last_error = f"EC backlight power update failed: {e}"
            return False

    @classmethod
    def set_performance_mode(cls, mode: str) -> bool:
        """Apply the OEM performance profile through EC RAM address 0x40."""
        values = {"Quiet": 0, "Balanced": 1, "Beast": 2}
        try:
            acpi_obj = cls._get_acpi_method_provider()
            expected = values.get(mode, 1)
            if not cls._ec_write_ram(acpi_obj, 0x40, expected):
                return False
            cls._verify_ec_value(acpi_obj, 0x40, expected)
            cls._last_error = ""
            return True
        except Exception as e:
            cls._last_error = f"Performance profile update failed: {e}"
            return False

    @classmethod
    def get_performance_mode(cls) -> Optional[str]:
        """Read the active OEM thermal profile from its verified EC register."""
        try:
            value = cls._ec_read_ram(cls._get_acpi_method_provider(), 0x40)
            mode = {0: "Quiet", 1: "Balanced", 2: "Beast"}.get(value)
            if mode is None:
                raise RuntimeError(f"unsupported performance value {value}")
            cls._last_error = ""
            return mode
        except Exception as exc:
            cls._last_error = f"Performance profile read failed: {exc}"
            return None

    @classmethod
    def set_full_fan_mode(cls, enable: bool, mode: str = "Balanced") -> bool:
        """Apply the verified OEM full-fan EC sequence."""
        fan_limits = {
            "Quiet": (73, 96),
            "Balanced": (104, 140),
            "Beast": (144, 183),
        }
        try:
            acpi_obj = cls._get_acpi_method_provider()
            expected = 1 if enable else 0
            if not cls._ec_write_ram(acpi_obj, 0x41, expected):
                return False
            cls._verify_ec_value(acpi_obj, 0x41, expected)
            if enable:
                cpu_limit, gpu_limit = fan_limits.get(mode, fan_limits["Balanced"])
                cls._ec_write_ram(acpi_obj, 0x4C, cpu_limit)
                cls._ec_write_ram(acpi_obj, 0x4D, gpu_limit)
            cls._last_error = ""
            return True
        except Exception as e:
            cls._last_error = f"Full-fan update failed: {e}"
            return False

    @classmethod
    def get_full_fan_mode(cls) -> Optional[bool]:
        try:
            value = cls._ec_read_ram(cls._get_acpi_method_provider(), 0x41)
            cls._last_error = ""
            return bool(value & 1)
        except Exception as exc:
            cls._last_error = f"Full-fan state read failed: {exc}"
            return None

    @classmethod
    def set_usb_sleep_charging(cls, enable: bool) -> bool:
        """Apply the OEM USB-off charging EC value and SMI notification."""
        try:
            acpi_obj = cls._get_acpi_method_provider()
            expected = 2 if enable else 0
            if not cls._ec_write_ram(acpi_obj, 0x4E, expected):
                return False
            cls._verify_ec_value(acpi_obj, 0x4E, expected)
            cls._smi(acpi_obj, 3, 1, enable)
            cls._last_error = ""
            return True
        except Exception as e:
            cls._last_error = f"USB sleep-charging update failed: {e}"
            return False

    @classmethod
    def get_usb_sleep_charging(cls) -> Optional[bool]:
        try:
            value = cls._ec_read_ram(cls._get_acpi_method_provider(), 0x4E)
            cls._last_error = ""
            return value == 2
        except Exception as exc:
            cls._last_error = f"USB sleep-charging state read failed: {exc}"
            return None

    GPU_MODE_VALUES = {"dGPU only": 1, "Hybrid": 2, "iGPU only": 3}

    @classmethod
    def get_gpu_mode(cls) -> Optional[str]:
        """Read the verified OEM graphics mode register (EC RAM 0xC0)."""
        try:
            acpi_obj = cls._get_acpi_method_provider()
            value = cls._ec_read_ram(acpi_obj, 0xC0)
            mode = {value: name for name, value in cls.GPU_MODE_VALUES.items()}.get(value)
            if mode is None:
                raise RuntimeError(f"unsupported GPU mode value {value}")
            cls._last_error = ""
            return mode
        except Exception as e:
            cls._last_error = f"GPU mode read failed: {e}"
            return None

    @classmethod
    def set_gpu_mode(cls, mode: str) -> bool:
        """Set dGPU-only, Hybrid, or iGPU-only using the OEM 0xC0 register."""
        if mode not in cls.GPU_MODE_VALUES:
            cls._last_error = f"Unknown GPU mode: {mode}"
            return False
        try:
            acpi_obj = cls._get_acpi_method_provider()
            ok = cls._ec_write_ram(acpi_obj, 0xC0, cls.GPU_MODE_VALUES[mode])
            if not ok:
                return False
            cls._verify_ec_value(acpi_obj, 0xC0, cls.GPU_MODE_VALUES[mode])
            cls._last_error = ""
            return True
        except Exception as e:
            cls._last_error = f"GPU mode update failed: {e}"
            return False

    @staticmethod
    def get_gpu_3d_usage() -> Optional[float]:
        """Read Windows GPU Engine performance counters or NVML; return None if unavailable."""
        try:
            import ctypes
            nvml = ctypes.CDLL("nvml.dll")
            if nvml.nvmlInit_v2() == 0:
                try:
                    dev = ctypes.c_void_p()
                    if nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(dev)) == 0:
                        class _NvmlUtil(ctypes.Structure):
                            _fields_ = [("gpu", ctypes.c_uint), ("mem", ctypes.c_uint)]
                        u = _NvmlUtil()
                        if nvml.nvmlDeviceGetUtilizationRates(dev, ctypes.byref(u)) == 0:
                            return float(u.gpu)
                finally:
                    try:
                        nvml.nvmlShutdown()
                    except Exception:
                        pass
        except Exception:
            pass

        try:
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()
            try:
                locator = win32com.client.Dispatch("WbemScripting.SWbemLocator")
                services = locator.ConnectServer(".", r"root\cimv2")
                query = (
                    "SELECT Name, UtilizationPercentage FROM "
                    "Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine"
                )
                total = 0.0
                found = False
                for engine in services.ExecQuery(query):
                    name = str(getattr(engine, "Name", ""))
                    if "engtype_3d" not in name.lower():
                        continue
                    total += float(getattr(engine, "UtilizationPercentage", 0) or 0)
                    found = True
                return min(100.0, max(0.0, total)) if found else None
            finally:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass
        except Exception:
            return None

    @staticmethod
    def get_temperature_readings():
        """Use real published sensor readings; missing sensors stay unavailable."""
        readings = {"CPU": None, "GPU": None}
        import pythoncom
        import win32com.client
        import gc
        pythoncom.CoInitialize()
        try:
            locator = win32com.client.Dispatch("WbemScripting.SWbemLocator")
            for namespace in (r"root\LibreHardwareMonitor", r"root\OpenHardwareMonitor"):
                try:
                    services = locator.ConnectServer(".", namespace)
                    sensors = services.ExecQuery("SELECT Identifier, Value FROM Sensor")
                    for sensor in sensors:
                        identity = str(sensor.Properties_("Identifier").Value or "").lower()
                        kind = "CPU" if "cpu" in identity else "GPU" if "gpu" in identity else None
                        value = sensor.Properties_("Value").Value
                        if kind and value is not None and 0 <= float(value) <= 125:
                            readings[kind] = max(readings[kind] or 0, float(value))
                    del sensor, sensors, services
                    if any(value is not None for value in readings.values()):
                        break
                except Exception:
                    continue

            # Fallback 1: Windows ACPI / EC Thermal Zone perf counters for CPU
            if readings["CPU"] is None:
                try:
                    services = locator.ConnectServer(".", r"root\cimv2")
                    tzs = services.ExecQuery("SELECT Name, Temperature FROM Win32_PerfFormattedData_Counters_ThermalZoneInformation")
                    for tz in tzs:
                        name = str(tz.Properties_("Name").Value or "").upper()
                        temp_k = tz.Properties_("Temperature").Value
                        if temp_k and float(temp_k) > 200:
                            temp_c = float(temp_k) - 273.15
                            if 15.0 <= temp_c <= 115.0:
                                if "EC0" in name or "TZRZ" in name or readings["CPU"] is None:
                                    readings["CPU"] = round(temp_c, 1)
                    del tz, tzs, services
                except Exception:
                    pass

            del locator

            # Fallback 2: NVML / NVIDIA Driver for GPU
            if readings["GPU"] is None:
                try:
                    import ctypes
                    nvml = ctypes.CDLL("nvml.dll")
                    if nvml.nvmlInit_v2() == 0:
                        try:
                            dev = ctypes.c_void_p()
                            if nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(dev)) == 0:
                                gpu_t = ctypes.c_uint()
                                if nvml.nvmlDeviceGetTemperature(dev, 0, ctypes.byref(gpu_t)) == 0:
                                    val = float(gpu_t.value)
                                    if 15.0 <= val <= 115.0:
                                        readings["GPU"] = val
                        finally:
                            try:
                                nvml.nvmlShutdown()
                            except Exception:
                                pass
                except Exception:
                    pass
        finally:
            gc.collect()
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass
        return readings

    _last_open_failure = 0.0

    @classmethod
    def _get_or_open_device(cls):
        """Maintains a persistent, high-performance HID handle for 40-50 FPS animations."""
        if cls._dev is not None:
            return cls._dev
        now = time.time()
        # Rate-limit USB enumeration retries on failure to protect bus stability
        if now - cls._last_open_failure < 1.0:
            return None
        try:
            for d in hid.enumerate():
                if d.get('vendor_id') == 0x340E and d.get('product_id') == 0x8002:
                    path = d.get('path')
                    if path and b'mi_01' in path.lower():
                        dev = hid.device()
                        dev.open_path(path)
                        cls._dev = dev
                        cls._needs_mode_restore = True
                        cls._last_path = path
                        cls._last_error = ""
                        cls._last_open_failure = 0.0
                        return cls._dev
            cls._last_error = "Keyboard RGB controller 340E:8002 (MI_01) was not found"
            cls._last_open_failure = now
        except Exception as e:
            cls._last_error = f"Could not open keyboard RGB controller: {e}"
            cls._last_open_failure = now
            cls._dev = None
        return None

    @classmethod
    def _close_device(cls):
        cls._watchdog_device = None
        cls._needs_mode_restore = False
        if cls._dev:
            try:
                cls._dev.close()
            except Exception:
                pass
            cls._dev = None

    @staticmethod
    def _scale_brightness(val: int) -> int:
        """Scales brightness percentage (0-100) to full hardware register range (0-255).
        OEM ControlCenter scales Light.L * 2.55 so 100% maps to 255 (0xFF)."""
        if val is None or val <= 0:
            return 0
        if val > 100:
            return min(255, int(val))
        return min(255, max(0, int(round(val * 2.55))))

    @classmethod
    def send_global_rgb(cls, r: int, g: int, b: int, brightness: int = 100):
        with cls._lock:
            dev = cls._get_or_open_device()
            if not dev:
                return False
            try:
                cr = max(0, min(255, int(round(r))))
                cg = max(0, min(255, int(round(g))))
                cb = max(0, min(255, int(round(b))))
                buf = [0x00] * 64
                buf[0] = 0x06
                buf[1] = 0x11
                buf[2] = 0x04
                buf[7] = cr
                buf[8] = cg
                buf[9] = cb
                buf[10] = cls._scale_brightness(brightness)
                buf[63] = sum(buf[1:63]) & 0xFF
                cls._write_hid(dev, buf)
                cls._needs_mode_restore = False
                cls._last_error = ""
                return True
            except Exception as e:
                cls._last_error = f"Global RGB write failed: {e}"
                cls._close_device()
                return False

    _last_conflict_kill = 0.0

    @classmethod
    def kill_conflicting_oem_control_center(cls, force: bool = False):
        """Silently closes conflicting OEM processes and duplicate toolkit instances so they cannot reset lighting."""
        now = time.time()
        if not force and (now - cls._last_conflict_kill < 45.0):
            return
        cls._last_conflict_kill = now
        conflict_names = {
            "controlcenter.exe", 
            "infinixbacklightkeepalive.exe", 
            "bydcentral.core.exe",
            "bydcontrolcenter.exe",
            "lightconfig.exe",
            "infinixgttoolkit.exe",
            "infinixgttoolkit-updated.exe",
        }
        my_pid = os.getpid()
        parent_pid = os.getppid() if hasattr(os, 'getppid') else -1
        try:
            for proc in psutil.process_iter(['name', 'pid']):
                try:
                    pname = proc.info.get('name')
                    pid = proc.info.get('pid')
                    if not pname or pid in (my_pid, parent_pid):
                        continue
                    plower = pname.lower()
                    if plower in conflict_names:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                        try:
                            for wp in wmi.WMI().Win32_Process(ProcessId=pid):
                                wp.Terminate()
                        except Exception:
                            pass
                except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
                    pass
        except Exception:
            pass

        # Also purge legacy keepalive registry autostart entry if present
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(key, "InfinixBacklightKeepAlive")
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
        except Exception:
            pass

        # Disable conflicting OEM scheduled task if present
        try:
            subprocess.run(
                ["schtasks.exe", "/change", "/tn", "ControlCenter", "/disable"],
                capture_output=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                timeout=2
            )
        except Exception:
            pass

    @classmethod
    def send_4zone_rgb(cls, zones: Dict[str, Tuple[int, int, int]], brightness: int = 100, set_mode_static: bool = False):
        with cls._lock:
            dev = cls._get_or_open_device()
            if not dev:
                return False
            try:
                hw_bright = cls._scale_brightness(brightness)
                # If entering static mode, lock EC into 0x11 Static Mode so it cannot revert to defaults
                if set_mode_static or (cls._needs_mode_restore and brightness > 0):
                    z1 = zones.get("1", (56, 189, 248))
                    buf_mode = [0x00] * 64
                    buf_mode[0] = 0x06
                    buf_mode[1] = 0x11
                    buf_mode[2] = 0x04
                    buf_mode[7] = max(0, min(255, int(round(z1[0]))))
                    buf_mode[8] = max(0, min(255, int(round(z1[1]))))
                    buf_mode[9] = max(0, min(255, int(round(z1[2]))))
                    buf_mode[10] = hw_bright
                    buf_mode[63] = sum(buf_mode[1:63]) & 0xFF
                    cls._write_hid(dev, buf_mode)

                # Individual 4-Zone Packets (0x60, 0x64, 0x70, 0x74) for multi-zone hardware support
                cmd_map = {"1": 0x60, "2": 0x64, "3": 0x70, "4": 0x74}
                for zid, cmd in cmd_map.items():
                    rgb = zones.get(zid, (56, 189, 248))
                    cr = max(0, min(255, int(round(rgb[0]))))
                    cg = max(0, min(255, int(round(rgb[1]))))
                    cb = max(0, min(255, int(round(rgb[2]))))
                    buf = [0x00] * 64
                    buf[0] = 0x06
                    buf[1] = cmd
                    buf[2] = 0x04
                    buf[7] = cr
                    buf[8] = cg
                    buf[9] = cb
                    buf[10] = hw_bright
                    buf[63] = sum(buf[1:63]) & 0xFF
                    cls._write_hid(dev, buf)
                cls._needs_mode_restore = False
                cls._last_error = ""
                return True
            except Exception as e:
                cls._last_error = f"Four-zone RGB write failed: {e}"
                cls._close_device()
                return False

    @classmethod
    def send_hardware_mode(cls, mode_cmd: int, r: int = 56, g: int = 189, b: int = 248, brightness: int = 100):
        """Sends hardware-native animation mode (0x12 Breath, 0x13 Spectrum, 0x14 Rainbow, 0x15 Flow, 0x16 Wave)."""
        with cls._lock:
            dev = cls._get_or_open_device()
            if not dev:
                return False
            try:
                cr = max(0, min(255, int(round(r))))
                cg = max(0, min(255, int(round(g))))
                cb = max(0, min(255, int(round(b))))
                buf = [0x00] * 64
                buf[0] = 0x06
                buf[1] = int(mode_cmd) & 0xFF
                buf[2] = 0x04
                buf[7] = cr
                buf[8] = cg
                buf[9] = cb
                buf[10] = cls._scale_brightness(brightness)
                buf[63] = sum(buf[1:63]) & 0xFF
                cls._write_hid(dev, buf)
                cls._needs_mode_restore = False
                cls._last_error = ""
                return True
            except Exception as e:
                cls._last_error = f"Hardware animation write failed: {e}"
                cls._close_device()
                return False

    @classmethod
    def send_disable_auto_close(cls):
        """Latch timeout-disable once per HID connection, not on every heartbeat.

        Reissuing 0x19 can disturb the lighting controller's PWM state.
        Closing the handle (including suspend/failure) invalidates this latch.
        """
        with cls._lock:
            dev = cls._get_or_open_device()
            if not dev:
                return False
            if cls._watchdog_device is dev:
                return True
            try:
                buf = [0x00] * 64
                buf[0] = 0x06
                buf[1] = 0x19
                buf[2] = 0x04
                buf[63] = sum(buf[1:63]) & 0xFF
                cls._write_hid(dev, buf)
                cls._watchdog_device = dev
                cls._last_error = ""
                return True
            except Exception as e:
                cls._last_error = f"Backlight watchdog write failed: {e}"
                cls._close_device()
                return False

    @classmethod
    def _write_hid(cls, dev, buf):
        written = dev.write(bytes(buf))
        if written != len(buf):
            raise IOError(f"HID wrote {written} of {len(buf)} bytes")

    @classmethod
    def send_mecha_bar(cls, r: int, g: int, b: int, enabled: bool = True):
        # Forward to physical rear chassis bar on UART
        try:
            if enabled:
                SerialEngine.send_backzone_rgb(1, r, g, b, 1, 80)
            else:
                SerialEngine.send_backzone_rgb(15, 0, 0, 0, 1, 0)
        except Exception:
            pass

        with cls._lock:
            dev = cls._get_or_open_device()
            if not dev:
                return False
            try:
                buf = [0x00] * 64
                buf[0] = 0x06
                buf[1] = 0x34
                buf[2] = 0x0E
                buf[7] = int(r) & 0xFF if enabled else 0
                buf[8] = int(g) & 0xFF if enabled else 0
                buf[9] = int(b) & 0xFF if enabled else 0
                buf[10] = 255 if enabled else 0
                buf[63] = sum(buf[1:63]) & 0xFF
                cls._write_hid(dev, buf)
                cls._last_error = ""
                return True
            except Exception as e:
                cls._last_error = f"Mecha Bar write failed: {e}"
                cls._close_device()
                return False

    @staticmethod
    def get_display_brightness() -> Optional[int]:
        """Read the current internal-display brightness without changing it."""
        try:
            import pythoncom
            pythoncom.CoInitialize()
            try:
                monitors = wmi.WMI(namespace="wmi").WmiMonitorBrightness()
                if monitors:
                    return max(0, min(100, int(monitors[0].CurrentBrightness)))
            finally:
                pythoncom.CoUninitialize()
        except Exception:
            pass
        return None

    @staticmethod
    def set_display_brightness(brightness: int) -> bool:
        """Restore the internal-display brightness after a power-plan switch."""
        try:
            import pythoncom
            pythoncom.CoInitialize()
            try:
                methods = wmi.WMI(namespace="wmi").WmiMonitorBrightnessMethods()
                if not methods:
                    return False
                methods[0].WmiSetBrightness(
                    Timeout=0, Brightness=max(0, min(100, int(brightness))))
                return True
            finally:
                pythoncom.CoUninitialize()
        except Exception:
            return False

    @classmethod
    def set_windows_power_plan(cls, mode: str):
        """Switch the Windows plan while preserving the user's display brightness."""
        guid_map = {
            "Quiet": "a1841308-3541-4fab-bc81-f71556f20b4a",     # Power Saver
            "Balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",  # Balanced
            "Beast": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"      # High Performance
        }
        guid = guid_map.get(mode, guid_map["Balanced"])
        display_brightness = cls.get_display_brightness()
        try:
            result = subprocess.run(
                ["powercfg.exe", "/setactive", guid],
                capture_output=True,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                timeout=5,
            )
            ok = result.returncode == 0
            if ok and display_brightness is not None:
                cls.set_display_brightness(display_brightness)
            return ok
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Windows Key Lock Engine (WH_KEYBOARD_LL)
# ---------------------------------------------------------------------------
class WindowsKeyLockEngine:
    """Low-level Windows keyboard hook suppressing Win-Key during games."""
    _hook = None
    _active = False
    _thread = None
    _thread_id = None
    _hook_proc = None

    @classmethod
    def set_lock(cls, enable: bool):
        cls._active = enable
        if enable and cls._hook is None:
            cls._thread = threading.Thread(target=cls._run_hook, daemon=True)
            cls._thread.start()
        elif not enable:
            hook = cls._hook
            cls._hook = None
            if hook:
                try:
                    ctypes.windll.user32.UnhookWindowsHookEx(hook)
                except Exception:
                    pass
            if cls._thread_id:
                try:
                    ctypes.windll.user32.PostThreadMessageW(cls._thread_id, 0x0012, 0, 0)  # WM_QUIT
                except Exception:
                    pass

    @classmethod
    def _run_hook(cls):
        user32 = ctypes.windll.user32
        cls._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        WH_KEYBOARD_LL = 13
        VK_LWIN = 0x5B
        VK_RWIN = 0x5C

        HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, ctypes.c_size_t, ctypes.c_void_p)

        def low_level_keyboard_handler(nCode, wParam, lParam):
            if nCode >= 0 and cls._active:
                vk = ctypes.cast(lParam, ctypes.POINTER(ctypes.c_ulong))[0]
                if vk in (VK_LWIN, VK_RWIN):
                    return 1  # Suppress key event
            return user32.CallNextHookEx(cls._hook, nCode, wParam, lParam)

        cls._hook_proc = HOOKPROC(low_level_keyboard_handler)
        cls._hook = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            cls._hook_proc,
            ctypes.windll.kernel32.GetModuleHandleW(None),
            0
        )

        if not cls._active:
            if cls._hook:
                user32.UnhookWindowsHookEx(cls._hook)
                cls._hook = None
            cls._thread_id = None
            return

        msg = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            if cls._hook:
                user32.UnhookWindowsHookEx(cls._hook)
            cls._hook = None
            cls._thread_id = None
            cls._thread = None


# ---------------------------------------------------------------------------
# Windows Power Event Listener (WM_POWERBROADCAST for Sleep / Resume)
# ---------------------------------------------------------------------------
class PowerEventListener:
    """Listens for Windows power broadcast events to safely release and restore
    HID and Serial handles across Sleep, Hibernate, and Modern Standby."""
    WM_POWERBROADCAST = 0x0218
    PBT_APMSUSPEND = 0x0004
    PBT_APMRESUMEAUTOMATIC = 0x0012
    PBT_APMRESUMESUSPEND = 0x0007

    def __init__(self, on_suspend_callback=None, on_resume_callback=None, on_restore_callback=None):
        self.on_suspend = on_suspend_callback
        self.on_resume = on_resume_callback
        self.on_restore = on_restore_callback
        self.running = False
        self.hwnd = None
        self.thread = None
        self.restore_msg = 0

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="PowerEventListener")
        self.thread.start()

    def _run_loop(self):
        try:
            import win32gui
            import win32con
        except Exception:
            return

        try:
            self.restore_msg = win32gui.RegisterWindowMessage("InfinixGTToolkit_RestoreWindow")
        except Exception:
            self.restore_msg = 0

        def wndproc(hwnd, msg, wparam, lparam):
            if self.restore_msg and msg == self.restore_msg:
                if self.on_restore:
                    try:
                        self.on_restore()
                    except Exception:
                        pass
                return 1
            if msg == self.WM_POWERBROADCAST:
                if wparam == self.PBT_APMSUSPEND:
                    if self.on_suspend:
                        try:
                            self.on_suspend()
                        except Exception:
                            pass
                    return 1
                elif wparam in (self.PBT_APMRESUMEAUTOMATIC, self.PBT_APMRESUMESUSPEND):
                    if self.on_resume:
                        try:
                            self.on_resume()
                        except Exception:
                            pass
                    return 1
            return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = wndproc
        wc.lpszClassName = f"InfinixPowerNotifier_{os.getpid()}_{id(self)}"
        atom = None
        try:
            wc.hInstance = win32gui.GetModuleHandle(None)
            atom = win32gui.RegisterClass(wc)
            self.hwnd = win32gui.CreateWindow(
                atom, "InfinixPowerListenerWindow", 0, 0, 0, 0, 0, 0, 0, wc.hInstance, None
            )
        except Exception:
            return

        try:
            while self.running:
                win32gui.PumpWaitingMessages()
                time.sleep(0.2)
        finally:
            if self.hwnd:
                try:
                    win32gui.DestroyWindow(self.hwnd)
                except Exception:
                    pass
                self.hwnd = None
            if atom is not None:
                try:
                    win32gui.UnregisterClass(atom, wc.hInstance)
                except Exception:
                    pass

    def stop(self):
        self.running = False


# ---------------------------------------------------------------------------
# Main GUI Application (Sidebar + Soft Eye-Friendly Aesthetic)
# ---------------------------------------------------------------------------
class InfinixGTToolkitApp:
    SerialEngine = SerialEngine
    HardwareEngine = HardwareEngine

    def __init__(self):
        # Enforce single-instance mutex and restore existing window if already running
        self._mutex = None
        WINDOW_TITLE = "Infinix GT Toolkit"
        try:
            MUTEX_NAME = "Local\\InfinixGTToolkit_SingleInstance_Mutex_v4"
            self._mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
            if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
                # Signal running instance to unhide and restore its window even if minimized to tray
                restore_msg = ctypes.windll.user32.RegisterWindowMessageW("InfinixGTToolkit_RestoreWindow")
                if restore_msg:
                    ctypes.windll.user32.PostMessageW(0xFFFF, restore_msg, 0, 0)
                hwnd = ctypes.windll.user32.FindWindowW(None, WINDOW_TITLE)
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                sys.exit(0)
        except SystemExit:
            raise
        except Exception:
            pass

        # Check command-line flags for background autostart
        self.is_minimized = any(arg in sys.argv for arg in ("--minimized", "--bg", "-m", "--tray", "--silent"))

        self.config = self._load_config()
        self._update_service = GitHubUpdateService(UPDATE_REPOSITORY, APP_VERSION)
        self.available_update = None
        self._update_check_in_progress = False
        self._lighting_history = LightingHistory(self.config)
        self._ui_thread_id = threading.get_ident()
        self._ui_mailbox = UiMailbox()
        self._config_writer = ConfigWriter(CONFIG_FILE, on_error=lambda error: self._ui_dispatch(
            self._set_hardware_status, False, "Settings save", error))
        self._suspended = False
        self._session_locked = False
        self._rear_test_active = False
        self._power_events = {"suspend": 0, "resume": 0, "last": "No sleep event this session"}

        # Dynamic State Variables (initialized early for immediate hardware activation)
        self.running = True
        self.heartbeat_active = self.config.get("always_on", True)
        self.effect_mode = self.config.get("effect_mode", "Solid")
        self.anim_speed = self.config.get("animation_speed", "Normal")
        self.anim_direction = normalize_animation_direction(self.config.get("animation_direction"))
        self.config["animation_direction"] = self.anim_direction
        self.screen_sync_mode = self.config.get("screen_sync_mode", "Spatial")
        self.current_theme = self.config.get("current_theme", "")
        self.current_color = list(self.config.get("current_color", [56, 189, 248]))
        self.zones = {k: list(v) for k, v in self.config.get("zones", DEFAULT_CONFIG["zones"]).items()}
        self.brightness = self.config.get("brightness", 100)
        self.audio_gain_multiplier = float(self.config.get("audio_gain_multiplier", 1.5))
        self.audio_device_name = "Detecting Audio Device..."
        self.audio_volume = 0.0
        self.audio_levels = [0.0] * 4
        self.audio_beat = 0.0


        # INSTANT HARDWARE LIGHTING (Sub-20ms latency on boot/login)
        # Turn on keyboard RGB instantly so the user does not wait for CTk GUI creation
        self._apply_fast_initial_lighting()

        self.theme = self.config.get("theme", "Dark")
        self.theme_colors = THEME
        ctk.set_appearance_mode(self.theme)
        ctk.set_default_color_theme("blue")
        ctk.ThemeManager.theme["CTkFont"]["family"] = "Segoe UI"
        studio_ui.configure_controls(THEME)

        self.root = ctk.CTk()
        # Hide before styling or constructing widgets so an autostart launch
        # never flashes the dashboard on the desktop.
        if self.is_minimized:
            self.root.withdraw()
        self.root.configure(fg_color=THEME["root_bg"])
        self._drain_job = self.root.after(40, self._drain_ui_mailbox)
        self.root.bind("<Destroy>", self._on_root_destroyed, add="+")
        self._hardware_commands = HardwareCommandController(self._ui_dispatch)

        # Intercept background Tkinter callback errors to prevent GUI crashes
        def handle_tk_exception(exc, val, tb):
            if "application has been destroyed" in str(val) or "invalid command name" in str(val):
                return
            log_crash_exception(exc, val, tb, context="Tkinter Callback")

        self.root.report_callback_exception = handle_tk_exception

        self.root.title("Infinix GT Toolkit")
        self.root.geometry(studio_ui.initial_window_geometry(
            self.root.winfo_screenwidth(), self.root.winfo_screenheight(), self.root._get_window_scaling()))
        self.root.minsize(1100, 760)
        self._titlebar_job = self.root.after(100, lambda: studio_ui.style_titlebar(self.root, self._tc("sidebar_bg")) if hasattr(self, 'root') and self.root and self.root.winfo_exists() else None)
        if self.is_minimized:
            self.root.withdraw()

        # Set Window and Taskbar Icon
        if os.path.exists(ICON_PATH):
            try:
                self.root.iconbitmap(default=ICON_PATH)
            except Exception:
                try:
                    self.root.iconbitmap(ICON_PATH)
                except Exception:
                    pass
            try:
                from PIL import ImageTk
                with Image.open(ICON_PATH) as _ico_img:
                    self._app_icon_photo = ImageTk.PhotoImage(_ico_img.copy())
                self.root.iconphoto(True, self._app_icon_photo)
            except Exception:
                pass

        self.bz_mode = backzone_ui.available_rear_mode(self.config.get("bz_mode", 1))
        self.config["bz_mode"] = self.bz_mode
        self.bz_color1 = list(vivid_rgb(self.config.get("bz_color1", [56, 189, 248])))
        self.bz_color2 = list(vivid_rgb(self.config.get("bz_color2", [167, 139, 250])))
        self.bz_speed = self.config.get("bz_speed", 3)
        self.bz_brightness = self.config.get("bz_brightness", 100)
        self.cpu_temp_val = None
        self.gpu_temp_val = None
        self.battery_val = 100
        self.on_ac_val = True
        self._cached_bat_health = None
        self._cached_bat_health_pct = self.config.get("cached_bat_health_pct", None)
        self.recent_colors = list(self.config.get("recent_colors", [
            "#FF0032", "#38BDF8", "#A78BFA", "#22C55E", "#F59E0B", "#EC4899", "#06B6D4", "#8C00FF"
        ]))
        
        self.selected_zone = "1"  # Current zone being tuned via RGB sliders
        self.last_ac_state = None
        self.active_page = "lighting"
        self.automation_history: List[str] = []

        # Animation & Debounce State
        self._anim_step_reset = False
        self._last_effect_change_time = time.time()
        self.bright_quick_btns = {}

        # Reactive Typing & Color Temp State
        self._typing_pulse = 0.0
        self._last_typing_time = 0.0
        self.color_temp_kelvin = self.config.get("color_temp_kelvin", 6500)
        self.emergency_saver_active = self.config.get("emergency_battery_saver", True)
        self.hud_window = None

        # Telemetry Rolling History & Delta Metrics
        self.cpu_history: List[float] = [0.0] * 60
        self.gpu_history: List[float] = [0.0] * 60
        self.ram_history: List[float] = [0.0] * 60
        self.last_disk_io = None
        self.last_net_io = None
        self.last_io_time = time.time()
        self.current_read_mbs = 0.0
        self.current_write_mbs = 0.0
        self.current_down_kbs = 0.0
        self.current_up_kbs = 0.0
        self.current_gpu_usage = 0.0
        self.ai_last_action = "Monitoring workload"
        self._last_hardware_error_message = ""
        self._last_hardware_error_time = 0.0
        self._hardware_failures = {}

        # Register Reactive Keyboard Hook
        self._reactive_hook = None
        self._zone_typing_times = {"1": 0.0, "2": 0.0, "3": 0.0, "4": 0.0}
        def _on_key_event(e):
            if self.effect_mode == "ReactiveTyping" and getattr(self, 'brightness', 100) > 0 and self.always_on_var.get():
                kname = str(getattr(e, 'name', '')).lower().strip()
                if kname in ('f1', 'f2', 'f3', 'fn'):
                    return
                zid = get_key_zone(e)
                now = time.time()
                self._zone_typing_times[zid] = now
                self._last_typing_time = now
        try:
            self._reactive_hook = keyboard.on_press(_on_key_event)
        except Exception:
            pass

        # Silence conflicting OEM ControlCenter process to prevent it from resetting lighting
        HardwareEngine.kill_conflicting_oem_control_center()

        # Construct Layout
        self._build_sidebar()
        self._build_content_area()

        # Switch to Initial Page
        initial_page = self.config.get("last_page", "lighting")
        if initial_page not in self.pages:
            initial_page = "lighting"
        self._select_nav(initial_page)

        # Apply initial settings to hardware
        self._apply_lighting_hardware()
        self._apply_backzone_hardware()
        initial_mode = self.config.get("power_mode", "Balanced")
        # Performance modes are hardware-only.  Do not activate a Windows power
        # plan here: Windows plans can own the display-brightness policy.
        InfinixGTToolkitApp._submit_hardware_command(
            self, "startup-performance",
            lambda: HardwareEngine.set_performance_mode(initial_mode),
            lambda result: self._finish_startup_command(result, "Performance mode"))
        if self.config.get("cooler_boost", False):
            InfinixGTToolkitApp._submit_hardware_command(
                self, "startup-cooling",
                lambda: HardwareEngine.set_full_fan_mode(True, initial_mode),
                lambda result: self._finish_startup_command(result, "Extreme Cooler Boost"))
        startup_usb = bool(self.config.get("usb_charge_off", True))
        InfinixGTToolkitApp._submit_hardware_command(
            self, "startup-usb",
            lambda: HardwareEngine.set_usb_sleep_charging(startup_usb),
            lambda result: self._finish_startup_command(result, "USB sleep charging"))
        if self.config.get("win_key_lock", False):
            WindowsKeyLockEngine.set_lock(True)
        SoftwareFnLock.set_callbacks(self._cycle_kb_brightness, self._cycle_effect_mode)
        if self.config.get("software_fn_lock", False):
            SoftwareFnLock.set_enabled(True)

        # Start Background Workers
        self._start_heartbeat_worker()
        self._start_effects_worker()
        self._start_backzone_effects_worker()
        self._start_audio_visualizer_worker()
        self._start_telemetry_worker()
        self._start_ai_governor_worker()
        self._start_ai_game_detector_worker()
        self._init_tray_icon()
        self._start_update_check()
        self.root.after(150, self._about_refresh_live)

        # Listen for system sleep and wake transitions to prevent handle corruption
        self.power_listener = None
        self._start_power_listener()

        # Handle Window Protocol
        self.root.protocol("WM_DELETE_WINDOW", self._on_close_requested)

        # Synchronize Windows autostart on boot with user configuration
        if self.config.get("autostart", True):
            self._start_startup_sync()

        # If launched on boot or in background, silently realize Win32 HWND
        if getattr(self, 'is_minimized', False):
            self.root.withdraw()
            self.root.update_idletasks()

    def _start_startup_sync(self):
        """Task Scheduler maintenance must not freeze the first interactive window."""
        def sync():
            import pythoncom
            pythoncom.CoInitialize()
            try:
                if self.running:
                    self._manage_startup_shortcut(True)
            finally:
                pythoncom.CoUninitialize()
        threading.Thread(target=sync, name="StartupSync", daemon=True).start()

    def _start_update_check(self, manual: bool = False):
        """Check GitHub Releases in the background; never delay app startup."""
        if self._update_check_in_progress:
            return
        self._update_check_in_progress = True
        if hasattr(self, "update_btn"):
            self.update_btn.configure(text="Checking…", state="disabled")

        def check():
            try:
                update, error = self._update_service.check(), ""
            except Exception as exc:
                update, error = None, str(exc)
            self._ui_dispatch(self._finish_update_check, update, error, manual)

        threading.Thread(target=check, name="UpdateCheck", daemon=True).start()

    def _finish_update_check(self, update, error: str, manual: bool):
        self._update_check_in_progress = False
        if error:
            if hasattr(self, "update_btn"):
                self.update_btn.configure(text="Check updates", state="normal")
            if manual:
                messagebox.showwarning("Update check", error, parent=self.root)
            return
        if update is None:
            if hasattr(self, "update_btn"):
                self.update_btn.configure(text="Up to date", state="normal")
                self.root.after(2500, lambda: self.update_btn.configure(text="Check updates"))
            if manual:
                messagebox.showinfo("Infinix GT Toolkit", "You already have the latest version.", parent=self.root)
            return

        self.available_update = update
        if hasattr(self, "update_btn"):
            self.update_btn.configure(
                text=f"Update v{update.version}", state="normal",
                text_color=THEME["accent_green"], command=self._download_available_update)
        if self.config.get("last_notified_update_version") != update.version:
            self.config["last_notified_update_version"] = update.version
            self._save_config()
            messagebox.showinfo(
                "Update available",
                f"Infinix GT Toolkit v{update.version} is ready.\n\n"
                "Use the Update button at the top to download, verify, install, and restart from the app.",
                parent=self.root)

    def _download_available_update(self):
        update = self.available_update
        if update is None:
            self._start_update_check(manual=True)
            return
        if not getattr(sys, "frozen", False):
            messagebox.showinfo(
                "Update available",
                f"v{update.version} is available at:\n{update.release_url}\n\n"
                "The in-app installer runs from the packaged Windows application.",
                parent=self.root)
            return
        if not messagebox.askyesno(
            "Install update",
            f"Download and install v{update.version} now?\n\n"
            "The file will be verified before replacing the current app. The app will restart.",
            parent=self.root):
            return
        if hasattr(self, "update_btn"):
            self.update_btn.configure(text="Downloading…", state="disabled")

        def download():
            try:
                update_dir = os.path.join(CONFIG_DIR, "Updates")
                destination = os.path.join(update_dir, f"InfinixGTToolkit-v{update.version}.exe")
                path = self._update_service.download_verified(update, destination)
                error = ""
            except Exception as exc:
                path, error = "", str(exc)
            self._ui_dispatch(self._finish_update_download, update, path, error)

        threading.Thread(target=download, name="UpdateDownload", daemon=True).start()

    def _finish_update_download(self, update, path: str, error: str):
        if error:
            if hasattr(self, "update_btn"):
                self.update_btn.configure(text=f"Update v{update.version}", state="normal")
            messagebox.showerror("Update failed", error, parent=self.root)
            return
        try:
            self._update_service.install_after_exit(sys.executable, path, update.version)
        except Exception as exc:
            if hasattr(self, "update_btn"):
                self.update_btn.configure(text=f"Update v{update.version}", state="normal")
            messagebox.showerror("Update failed", str(exc), parent=self.root)
            return
        self._quit_app()

    def _start_power_listener(self):
        """Initializes power broadcast listener in background for sleep/resume transitions."""
        try:
            self.power_listener = PowerEventListener(
                on_suspend_callback=self._on_power_suspend,
                on_resume_callback=self._on_power_resume,
                on_restore_callback=lambda: self._ui_dispatch(self._do_show_window)
            )
            self.power_listener.start()
        except Exception:
            self.power_listener = None

    def _on_power_suspend(self):
        """Safely release low-level hardware handles before Windows suspends USB power."""
        self._suspended = True
        self._power_events["suspend"] += 1
        self._power_events["last"] = "Suspended " + datetime.datetime.now().strftime("%H:%M:%S")
        try:
            with HardwareEngine._lock:
                HardwareEngine._close_device()
        except Exception:
            pass
        try:
            with SerialEngine._lock:
                SerialEngine._close_port()
                SerialEngine._ec_power_state = None
        except Exception:
            pass

    def _on_power_resume(self):
        """Re-assert keepalive and restore active lighting after waking from sleep."""
        self._power_events["resume"] += 1
        self._power_events["last"] = "Resumed " + datetime.datetime.now().strftime("%H:%M:%S")
        def rearm():
            time.sleep(1.5)
            if not self.running:
                return
            self._suspended = False
            try:
                HardwareEngine.kill_conflicting_oem_control_center(force=True)
                HardwareEngine.send_disable_auto_close()
                self._apply_fast_initial_lighting()
                self._ui_dispatch(self._apply_backzone_hardware)
            except Exception:
                pass
        t = threading.Thread(target=rearm, daemon=True)
        t.start()

    # -----------------------------------------------------------------------
    # Configuration & Theme Management
    # -----------------------------------------------------------------------
    def _load_config(self) -> dict:
        """Loads configuration with automatic corruption recovery and backup fallback."""
        os.makedirs(CONFIG_DIR, exist_ok=True)
        bak_file = CONFIG_FILE + ".bak"

        def _try_parse(path: str) -> Optional[dict]:
            if not os.path.exists(path):
                return None
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    if isinstance(cfg, dict):
                        res = copy.deepcopy(DEFAULT_CONFIG)
                        for k, v in cfg.items():
                            if k == "zones" and isinstance(v, dict):
                                res["zones"].update(v)
                            else:
                                res[k] = v
                        return res
            except Exception:
                return None
            return None

        # First attempt primary config file
        loaded = _try_parse(CONFIG_FILE)
        if loaded is not None:
            return loaded

        # Fallback to backup config if primary is corrupted or empty
        loaded_bak = _try_parse(bak_file)
        if loaded_bak is not None:
            try:
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(loaded_bak, f, indent=2)
            except Exception:
                pass
            return loaded_bak

        return copy.deepcopy(DEFAULT_CONFIG)

    def _save_config(self):
        """Persist the latest snapshot without blocking slider or animation events."""
        if hasattr(self, "_lighting_history"):
            self._lighting_history.record(self.config)
            self._refresh_history_buttons()
        self._config_writer.submit(self.config)

    def _refresh_history_buttons(self):
        history = self._lighting_history
        for name, enabled in (("lighting_undo", history.index > 0),
                              ("lighting_redo", history.index < len(history.states)-1)):
            if hasattr(self, name):
                getattr(self, name).configure(state="normal" if enabled else "disabled")

    def _move_lighting_history(self, delta):
        state = self._lighting_history.move(delta)
        if state is not None:
            self._restore_lighting_state(state)
        self._refresh_history_buttons()

    def _restore_lighting_state(self, state):
        """Restore lighting without touching performance, rear-light rules or presets."""
        self.config.update(copy.deepcopy(state))
        self.zones = copy.deepcopy(state["zones"])
        self.brightness = state["brightness"]
        self.effect_mode = state["effect_mode"]
        self.anim_speed = state["animation_speed"]
        self.anim_direction = normalize_animation_direction(state["animation_direction"])
        self.current_color = list(state.get("current_color", self.zones["1"]))
        self.current_theme = state.get("current_theme", "")
        self.config.update(current_color=self.current_color, current_theme=self.current_theme)
        self.screen_sync_mode = state.get("screen_sync_mode", self.screen_sync_mode)
        self.heartbeat_active = self.config.get("always_on", True)
        self.always_on_var.set(self.heartbeat_active)
        self.bright_slider.set(self.brightness)
        self.bright_lbl.configure(text=f"{self.brightness}%")
        self._refresh_brightness_buttons()
        self.effect_var.set(self.effect_mode)
        self.speed_var.set(self.anim_speed)
        self.direction_var.set(self.anim_direction)
        if hasattr(self, "screen_sync_var"):
            self.screen_sync_var.set("🌈 4-Zone Spatial (Per-Zone)" if self.screen_sync_mode == "Spatial" else "💡 Single Unified (Full Keyboard)")
        self._anim_step_reset = True
        self._update_theme_buttons_ui()
        self._update_fx_status_ui()
        self._update_zone_buttons_ui()
        self._save_config()
        self._apply_lighting_hardware()

    def _tc(self, key: str) -> str:
        """Theme-aware color resolver returning the appropriate Light or Dark hex code."""
        val = THEME.get(key, ("#0F172A", "#F8FAFC"))
        if isinstance(val, tuple):
            return val[0] if ctk.get_appearance_mode() == "Light" else val[1]
        return val

    def _set_hardware_status(self, ok: bool, context: str = "", error: str = "",
                             show_dialog: bool = False, retry=None):
        """Expose hardware failures in the header and optionally in a user dialog."""
        if not hasattr(self, "top_engine_pill"):
            return
        if ok:
            if context:
                self._hardware_failures.pop(context, None)
            if self._hardware_failures:
                failed_context, failed_detail = next(iter(self._hardware_failures.items()))
                short_detail = failed_detail if len(failed_detail) <= 48 else failed_detail[:45] + "..."
                self.top_engine_pill.configure(
                    text=f"Attention needed · {len(self._hardware_failures)}",
                    text_color=THEME["accent_rose"],
                )
                return
            self._last_hardware_error_message = ""
            self._last_hardware_retry = None
            if hasattr(self, "retry_hardware_btn"):
                self.retry_hardware_btn.configure(state="disabled", text="Retry last command")
                self.retry_hardware_btn.pack_forget()
            text = "Keyboard stays on" if self.heartbeat_active else "Keyboard keepalive off"
            color = THEME["accent_blue"] if self.heartbeat_active else THEME["text_secondary"]
            self.top_engine_pill.configure(text=text, text_color=color)
            return

        detail = error or "The device did not accept the command"
        failure_key = context or "Hardware"
        self._hardware_failures[failure_key] = detail
        if retry is not None:
            self._last_hardware_retry = retry
            if hasattr(self, "retry_hardware_btn"):
                self.retry_hardware_btn.configure(state="normal", text=f"Retry {context}")
                if not self.retry_hardware_btn.winfo_manager():
                    self.retry_hardware_btn.pack(side="right", padx=(0, 8))
        self._last_hardware_error_message = f"{context}: {detail}" if context else detail
        short_detail = detail if len(detail) <= 48 else detail[:45] + "..."
        self.top_engine_pill.configure(
            text=f"Attention needed · {len(self._hardware_failures)}",
            text_color=THEME["accent_rose"],
        )
        now = time.time()
        if show_dialog and now - self._last_hardware_error_time > 2.0:
            self._last_hardware_error_time = now
            messagebox.showerror(f"{context} failed", detail)

    def _retry_last_hardware_command(self):
        retry = getattr(self, "_last_hardware_retry", None)
        if retry is None:
            return
        if hasattr(self, "retry_hardware_btn"):
            self.retry_hardware_btn.configure(state="disabled", text="Retrying…")
        retry()

    def _show_hardware_details(self):
        """Run read-only device checks away from Tk before showing diagnostics."""
        if hasattr(self, "top_engine_pill"):
            self.top_engine_pill.configure(text="Running device checks…", text_color=THEME["accent_blue"])
        accepted = InfinixGTToolkitApp._submit_hardware_command(self,
            "diagnostics", self._collect_reliability_checks,
            self._finish_hardware_details, retries=0)
        if not accepted and hasattr(self, "top_engine_pill"):
            self.top_engine_pill.configure(text="Device checks already running", text_color=THEME["accent_amber"])

    def _collect_reliability_checks(self):
        checks = []
        configured_mode = self.config.get("power_mode", "Balanced")
        actual_mode = HardwareEngine.get_performance_mode()
        if actual_mode is None:
            checks.append(("Performance read-back", "fail", HardwareEngine.get_last_error()))
        elif actual_mode == configured_mode:
            checks.append(("Performance read-back", "pass", actual_mode))
        else:
            checks.append(("Performance read-back", "warn",
                           f"Hardware {actual_mode}; app expects {configured_mode}"))

        fan = HardwareEngine.get_full_fan_mode()
        if fan is None:
            checks.append(("Cooling read-back", "fail", HardwareEngine.get_last_error()))
        else:
            expected = bool(self.config.get("cooler_boost", False))
            state = "pass" if fan == expected else "warn"
            checks.append(("Cooling read-back", state, "Maximum" if fan else "Automatic"))

        usb = HardwareEngine.get_usb_sleep_charging()
        if usb is None:
            checks.append(("USB charging read-back", "fail", HardwareEngine.get_last_error()))
        else:
            expected = bool(self.config.get("usb_charge_off", True))
            state = "pass" if usb == expected else "warn"
            checks.append(("USB charging read-back", state, "Enabled" if usb else "Disabled"))

        gpu = HardwareEngine.get_gpu_mode()
        if gpu is None:
            checks.append(("GPU routing", "fail", HardwareEngine.get_last_error()))
        else:
            configured_gpu = self.config.get("gpu_mode", gpu)
            state = "pass" if gpu == configured_gpu else "warn"
            detail = gpu if state == "pass" else f"Current {gpu}; restart pending for {configured_gpu}"
            checks.append(("GPU routing", state, detail))

        port, connected, detail = SerialEngine.get_port_info()
        checks.append(("Rear-light controller", "pass" if connected else "warn",
                       port if connected and port else detail or "Not connected"))
        battery = psutil.sensors_battery()
        checks.append(("Battery telemetry", "pass" if battery else "warn",
                       f"{battery.percent:.0f}%" if battery else "Unavailable"))
        display = HardwareEngine.get_display_brightness()
        checks.append(("Display brightness", "pass" if display is not None else "warn",
                       f"Read-only at {display}% · performance modes do not modify it"
                       if display is not None else "Read-only policy active; sensor unavailable"))
        checks.append(("Settings durability", "fail" if self._config_writer.last_error else "pass",
                       self._config_writer.last_error or "Primary file + automatic backup"))
        listener_running = bool(getattr(getattr(self, "power_listener", None), "running", False))
        events = getattr(self, "_power_events", {"suspend": 0, "resume": 0, "last": "No events"})
        checks.append(("Sleep / wake recovery", "pass" if listener_running else "warn",
                       f"Listener {'active' if listener_running else 'inactive'} · "
                       f"{events['suspend']} suspend / {events['resume']} resume · {events['last']}"))
        return checks

    def _finish_hardware_details(self, result):
        self._set_hardware_status(True)
        mode = self.config.get("power_mode", "Balanced")
        mode = "Gaming" if mode == "Beast" else mode
        summary = (
            f"Infinix GT Toolkit v{APP_VERSION} · {BUILD_CHANNEL}\n"
            f"Build date: {BUILD_DATE}\n"
            f"Performance: {mode}\n"
            f"Automation: {self._automation_status_text()}\n"
            f"Settings: {CONFIG_FILE}\n"
            f"Crash log: {CRASH_LOG_FILE}"
        )
        failures = "\n\n".join(
            f"{name}\n{detail}" for name, detail in self._hardware_failures.items())
        if failures:
            summary += f"\n\nReported command failures\n{failures}"
        else:
            summary += "\n\nNo command failures currently reported."
        if result.ok and result.value:
            summary += "\n\nRead-only reliability checks\n" + format_reliability_report(result.value)
        elif not result.ok:
            summary += f"\n\nReliability checks could not finish\n{result.error}"
        summary += (
            "\n\nCommand success means the device accepted the request; "
            "verified EC controls are read back after writes. Physical keyboard "
            "lighting cannot be read back from this controller."
        )
        messagebox.showinfo("GT Control Center · Diagnostics", summary)

    def _toggle_theme(self):
        new_theme = "Light" if self.theme == "Dark" else "Dark"
        self._set_theme(new_theme)

    def _set_theme(self, theme_name: str):
        self.theme = theme_name
        self.config["theme"] = self.theme
        self._save_config()
        ctk.set_appearance_mode(self.theme)
        studio_ui.style_titlebar(self.root, self._tc("sidebar_bg"))

        # Update Theme Switcher text
        if self.theme == "Dark":
            self.theme_btn.configure(text="Light theme")
        else:
            self.theme_btn.configure(text="Dark theme")

        # Refresh zone keycap buttons, dynamic fx badge, canvas bg & nav
        if hasattr(self, 'kb_canvas'):
            try:
                self.kb_canvas.configure(bg=self._tc("card_bg"))
            except Exception:
                pass
        self._update_fx_status_ui()
        self._update_zone_buttons_ui()
        self._select_nav(self.active_page)

    def _tray_toggle_theme(self):
        self._ui_dispatch(self._toggle_theme)

    # -----------------------------------------------------------------------
    # Left Sidebar Navigation (Modern High-Visibility)
    # -----------------------------------------------------------------------
    def _build_sidebar(self):
        self.sidebar_shell = neon_ui.Frame(
            self.root, width=310, corner_radius=22,
            fg_color=THEME["sidebar_bg"], border_width=1,
            border_color=THEME["accent_blue"])
        self.sidebar_shell.pack(side="left", fill="y", padx=(14, 10), pady=14)
        self.sidebar_shell.pack_propagate(False)
        self.sidebar = ctk.CTkScrollableFrame(self.sidebar_shell, fg_color="transparent", width=286)
        self.sidebar.pack(fill="both", expand=True, padx=4, pady=10)

        # Brand Header
        brand_box = neon_ui.Frame(self.sidebar, fg_color="transparent")
        brand_box.pack(fill="x", padx=10, pady=(8, 4))

        brand_row = neon_ui.Frame(brand_box, fg_color="transparent")
        brand_row.pack(anchor="w")

        bolt_lbl = ctk.CTkLabel(brand_row, text="ϟ", width=28,
                               font=ctk.CTkFont(size=29, weight="bold"),
                               text_color=THEME["accent_blue"])
        bolt_lbl.pack(side="left", padx=(0, 7))

        title_lbl = ctk.CTkLabel(brand_row, text="Infinix GT Toolkit", font=ctk.CTkFont(size=16, weight="bold"), text_color=THEME["text_primary"])
        title_lbl.pack(side="left")

        ctk.CTkLabel(
            brand_row, text=f"v{APP_VERSION}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=THEME["accent_blue"],
            fg_color=THEME["pill_bg"], corner_radius=7,
            padx=7, pady=2
        ).pack(side="left", padx=(7, 0), pady=(2, 0))

        sub_lbl = ctk.CTkLabel(brand_box, text="  CONTROL CENTER", image=neon_ui.icon('settings',size=20), compound="left", height=40, corner_radius=12, fg_color=THEME["card_sub_bg"], font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_secondary"])
        sub_lbl.pack(fill="x", pady=(14, 5))

        sep = neon_ui.Frame(self.sidebar, height=1, fg_color=THEME["sidebar_border"])
        sep.pack(fill="x", padx=14, pady=(0, 2))

        # Nav Buttons Container
        self.nav_buttons = {}
        nav_items = [
            ("lighting", "💡    01   Lighting studio"),
            ("backzone", "◉    02   Rear light bar"),
            ("performance", "ϟ    03   Power & performance"),
            ("telemetry", "▣    04   System monitor"),
            ("presets", "⚙    05   Profiles & settings"),
            ("about", "ⓘ    06   About device")
        ]

        for index, (key, title) in enumerate(nav_items):
            if index in (0, 2, 4):
                group = {0: "PERSONALIZE", 2: "SYSTEM", 4: "WORKSPACE"}[index]
                ctk.CTkLabel(self.sidebar, text=group, height=16,
                             font=ctk.CTkFont(size=11, weight="bold"),
                             text_color=THEME["text_secondary"]).pack(anchor="w", padx=22, pady=(7, 4))
            btn = neon_ui.Button(
                self.sidebar, text=title.split('    ', 1)[-1], image=neon_ui.icon(key, '#C5DFFF', 21),
                anchor="w", height=46, corner_radius=13,
                fg_color=THEME["button_bg"], text_color=THEME["nav_idle_text"],
                hover_color=THEME["nav_hover"], font=ctk.CTkFont(size=14),
                command=lambda k=key: self._select_nav(k)
            )
            btn.pack(fill="x", padx=8, pady=4)
            btn._nav_chevron = True
            self.nav_buttons[key] = btn
            self.root.bind(f"<Alt-Key-{index + 1}>", lambda event, k=key: self._select_nav(k))

        ctk.CTkLabel(self.sidebar, text="Alt + 1–6    Switch workspace", font=ctk.CTkFont(size=11),
                     text_color=THEME["text_secondary"]).pack(anchor="w", padx=22, pady=(12, 0))

        # Bottom Mini Status Chip
        side_footer = neon_ui.Frame(self.sidebar, fg_color=THEME["card_sub_bg"], corner_radius=14, border_width=1, border_color=THEME["card_border"])
        side_footer.pack(side="bottom", fill="x", padx=5, pady=8)

        # Live Status Chip & Suggested Action
        self.side_status_badge = ctk.CTkLabel(
            side_footer, text="System monitor",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#4ADE80", anchor="w"
        )
        self.side_status_badge.pack(fill="x", padx=14, pady=(12, 1))

        self.side_action_lbl = ctk.CTkLabel(
            side_footer, text="Cool & quiet · Balanced performance",
            font=ctk.CTkFont(size=10),
            text_color=THEME["text_muted"], anchor="w",
            wraplength=172, justify="left"
        )
        self.side_action_lbl.pack(fill="x", padx=14, pady=(0, 8))
        self.side_action_lbl.bind("<Configure>", lambda e: self.side_action_lbl.configure(wraplength=max(100, e.width-4)))

        side_div = neon_ui.Frame(side_footer, height=1, fg_color=THEME["card_sub_border"])
        side_div.pack(fill="x", padx=10, pady=(0, 4))

        def metric_card(icon_name, color):
            row = neon_ui.Frame(side_footer, fg_color=THEME["card_bg"], corner_radius=12,
                                border_width=1, border_color=THEME["card_border"])
            row.pack(fill="x", padx=8, pady=4)
            ctk.CTkLabel(row, text="", image=neon_ui.icon(icon_name, color, 24), width=32).pack(side="left", padx=(8, 2), pady=10)
            body = neon_ui.Frame(row, fg_color="transparent")
            body.pack(side="left", fill="both", expand=True, padx=(0, 4), pady=5)
            return body

        cpu_card = metric_card('cpu', '#69CDFA')
        self.side_cpu_lbl = ctk.CTkLabel(
            cpu_card, text="CPU: --%",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=THEME["accent_blue"]
        )
        self.side_cpu_lbl.pack(anchor="w", padx=12, pady=1)
        self.side_cpu_bar = ctk.CTkProgressBar(cpu_card, height=6, progress_color=THEME["accent_blue"], fg_color=THEME["progress_bg"])
        self.side_cpu_bar.pack(fill="x", padx=14, pady=(2, 7)); self.side_cpu_bar.set(0)

        gpu_card = metric_card('gpu', '#30D9C4')
        self.side_gpu_lbl = ctk.CTkLabel(
            gpu_card, text="GPU: --%",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=THEME["accent_cyan"]
        )
        self.side_gpu_lbl.pack(anchor="w", padx=12, pady=1)
        self.side_gpu_bar = ctk.CTkProgressBar(gpu_card, height=6, progress_color=THEME["accent_cyan"], fg_color=THEME["progress_bg"])
        self.side_gpu_bar.pack(fill="x", padx=14, pady=(2, 7)); self.side_gpu_bar.set(0)

        ram_card = metric_card('ram', '#A78BFA')
        self.side_ram_lbl = ctk.CTkLabel(
            ram_card, text="RAM: --%",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=THEME["accent_purple"]
        )
        self.side_ram_lbl.pack(anchor="w", padx=12, pady=1)
        self.side_ram_bar = ctk.CTkProgressBar(ram_card, height=6, progress_color=THEME["accent_purple"], fg_color=THEME["progress_bg"])
        self.side_ram_bar.pack(fill="x", padx=14, pady=(2, 7)); self.side_ram_bar.set(0)

        init_bat_txt = "⚡ Battery: --%"
        init_hp = self.config.get("cached_bat_health_pct", None)
        if init_hp is not None and init_hp > 0:
            h_val = f"{init_hp:.1f}%" if (init_hp % 1 != 0) else f"{int(init_hp)}%"
            init_bat_txt += f" • Health: {h_val}"
        battery_card = metric_card('battery', '#39E86B')
        self.side_bat_lbl = ctk.CTkLabel(
            battery_card, text=init_bat_txt,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=THEME["accent_green"],
            cursor="hand2"
        )
        self.side_bat_lbl.pack(anchor="w", padx=(10, 4), pady=(1, 1))
        self.side_bat_lbl.bind("<Button-1>", lambda event: self._about_refresh_live(silent=False))
        self.side_bat_bar = ctk.CTkProgressBar(battery_card, height=6, progress_color="#39E86B", fg_color=THEME["progress_bg"])
        self.side_bat_bar.pack(fill="x", padx=14, pady=(2, 14)); self.side_bat_bar.set(0)

        # Persistent device visual: it belongs to the sidebar, so page navigation
        # never removes or redraws it.
        sidebar_asset_root = getattr(sys, "_MEIPASS", APP_DIR)
        sidebar_laptop_path = os.path.join(sidebar_asset_root, "assets", "gtbook_sidebar.webp")
        if not os.path.exists(sidebar_laptop_path):
            sidebar_laptop_path = os.path.join(ASSET_DIR, "gtbook_sidebar.webp")
        try:
            sidebar_laptop = Image.open(sidebar_laptop_path).convert("RGBA")
            visible_bounds = sidebar_laptop.getbbox()
            if visible_bounds:
                sidebar_laptop = sidebar_laptop.crop(visible_bounds)
            self.sidebar_laptop_image = ctk.CTkImage(
                light_image=sidebar_laptop, dark_image=sidebar_laptop, size=(210, 126)
            )
            device_banner = neon_ui.Frame(self.sidebar, fg_color=THEME["card_bg"],
                corner_radius=16, border_width=1, border_color=THEME["card_border"])
            device_banner.pack(side="bottom", fill="x", padx=6, pady=(10, 5))
            ctk.CTkLabel(device_banner, text="INFINIX GTBOOK", anchor="w",
                font=ctk.CTkFont(size=14, weight="bold"), text_color=THEME["text_primary"]).pack(fill="x", padx=12, pady=(10,0))
            self.sidebar_laptop_label = ctk.CTkLabel(
                device_banner, text="", image=self.sidebar_laptop_image,
                fg_color="transparent"
            )
            self.sidebar_laptop_label.pack(side="bottom", pady=(0, 4))
        except Exception:
            self.sidebar_laptop_image = None

    def _select_nav(self, key: str):
        key = {"gaming": "performance", "battery": "performance"}.get(key, key)
        if key not in self.pages:
            key = "lighting"
        self.active_page = key
        self.config["last_page"] = key
        self._save_config()
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(
                    fg_color=THEME["nav_active_bg"],
                    text_color=THEME["nav_active_text"],
                    border_width=1.5,
                    border_color=THEME["nav_active_border"],
                    hover_color=THEME["nav_active_bg"]
                )
            else:
                btn.configure(
                    fg_color=THEME["button_bg"],
                    text_color=THEME["nav_idle_text"],
                    border_width=0,
                    hover_color=THEME["nav_hover"]
                )

        for k, page in self.pages.items():
            if k == key:
                page.pack(fill="both", expand=True)
                if hasattr(page, '_parent_canvas'):
                    self.root.after_idle(lambda p=page: p._parent_canvas.yview_moveto(0) if p.winfo_exists() else None)
            else:
                page.pack_forget()

        titles = {
            "lighting": ("🎨 Lighting Matrix", "Custom 4-Zone RGB, precision sliders, circadian adaptation & backlight fix"),
            "backzone": ("🚥 Rear Back Zone", "Animated RGB loop, dual-colors, and music visualizer for the rear chassis"),
            "performance": ("⚡ Performance & AI Governor", "Hardware thermal curves, autonomous AI scaling, and extreme cooler boost"),
            "telemetry": ("📊 System Telemetry Dashboard", "Real-time CPU, GPU, RAM, Disk I/O, Network, and battery infrastructure"),
            "gaming": ("🎮 Gaming Tools & Scenarios", "Windows Key Lock, game sensor, and 1-Click Game/Office profiles"),
            "battery": ("🔋 Battery Health & Power", "Smart 80% charge limiter, emergency saver, USB sleep charging, and AC automations"),
            "presets": ("💾 Presets & Sharing", "User profile library, import/export, hardware diagnostics, and toolkit preferences"),
            "about": ("💻 About Device & Toolkit", "Battery health, system boot time & hardware specifications")
        }
        titles.update({
            "lighting": ("Lighting  Studio", "Your keyboard. Your signature."),
            "backzone": ("Rear light bar", "Chassis lighting · Effects and dual-color control"),
            "performance": ("Power & performance", "One place for speed, gaming and battery life"),
            "telemetry": ("System monitor", "Live resource and battery readings"),
            "gaming": ("Gaming tools", "Focus controls and one-click scenarios"),
            "battery": ("Power & battery", "Power automation and supported charging controls"),
            "presets": ("Profiles & settings", "Save your setup · Import and export profiles"),
            "about": ("About device & toolkit", "Live battery health, system boot time & hardware specifications")
        })
        t, st = titles.get(key, ("Dashboard", ""))
        split_titles = {"lighting": ("Lighting", " Studio"), "backzone": ("Rear light", " bar"),
                        "performance": ("Power &", " performance"), "telemetry": ("System", " monitor"),
                        "presets": ("Profiles &", " settings"), "about": ("About device &", " toolkit")}
        leading, trailing = split_titles.get(key, (t, ""))
        self.page_title_lbl.configure(text=leading, text_color=THEME["text_primary"])
        self.page_title_suffix.configure(text=trailing)
        self.page_icon.configure(image=neon_ui.icon(key, size=32))
        self.page_sub_lbl.configure(text=st)

    # -----------------------------------------------------------------------
    # Content Area & Top Header
    # -----------------------------------------------------------------------
    def _build_content_area(self):
        self.main_container = neon_ui.Frame(self.root, fg_color=THEME["root_bg"], corner_radius=0)
        self.main_container.pack(side="right", fill="both", expand=True, padx=(0, 12), pady=(10, 0))

        # Top Header Bar
        top_bar = neon_ui.Frame(self.main_container, height=68, fg_color=THEME["topbar_bg"], corner_radius=0)
        top_bar.pack(fill="x", side="top")
        top_bar.pack_propagate(False)

        # Header Titles
        self.page_icon = title_icon = ctk.CTkLabel(top_bar, text="", image=neon_ui.icon('lighting',size=32), width=58, height=54,
                                  corner_radius=13, fg_color=THEME["pill_bg"],
                                  text_color=THEME["accent_blue"],
                                  font=ctk.CTkFont(size=31, weight="bold"))
        title_icon.pack(side="left", padx=(5, 14), pady=8)
        tbox = neon_ui.Frame(top_bar, fg_color="transparent")
        tbox.pack(side="left", pady=8)

        title_row = neon_ui.Frame(tbox, fg_color="transparent")
        title_row.pack(anchor="w")
        self.page_title_lbl = ctk.CTkLabel(title_row, text="Lighting", font=ctk.CTkFont(size=28, weight="bold"), text_color=THEME["accent_blue"])
        self.page_title_lbl.pack(side="left")
        self.page_title_suffix = ctk.CTkLabel(title_row, text=" Studio", font=ctk.CTkFont(size=28, weight="bold"), text_color=THEME["accent_purple"])
        self.page_title_suffix.pack(side="left")

        self.page_sub_lbl = ctk.CTkLabel(tbox, text="Hardware control center", font=ctk.CTkFont(size=13), text_color=THEME["text_secondary"])
        self.page_sub_lbl.pack(anchor="w")

        # Right Action Badges, HUD & Theme Toggle
        status_bar = neon_ui.Frame(self.main_container, fg_color=THEME["root_bg"], corner_radius=0, height=42)
        status_bar.pack(fill="x", side="top", padx=(4, 0), pady=(2, 0))
        ctk.CTkLabel(status_bar, text="▦   DEVICE STATUS", height=39,
                     fg_color=THEME["pill_bg"], corner_radius=18, padx=14,
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=THEME["text_secondary"]).pack(side="left", padx=(0, 7))
        rbox = neon_ui.Frame(top_bar, fg_color="transparent")
        rbox.pack(side="right", padx=18, pady=10)

        self.update_btn = neon_ui.Button(
            rbox, text="Check for updates", image=neon_ui.icon('refresh', '#C5DFFF', 18), width=160, height=42, corner_radius=13,
            fg_color=THEME["pill_bg"], hover_color=THEME["button_hover"],
            text_color=THEME["text_secondary"], border_width=1.5,
            border_color=THEME["pill_border"], font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self._start_update_check(manual=True))
        self.update_btn.pack(side="left", padx=6)

        # Mini HUD Floating Widget Button
        self.hud_btn = neon_ui.Button(
            rbox, text="Mini monitor", image=neon_ui.icon('bars', '#B477FF', 19),
            width=130, height=42, corner_radius=13,
            fg_color=THEME["pill_bg"],
            hover_color=THEME["button_hover"],
            text_color=THEME["accent_purple"],
            border_width=1.5,
            border_color=THEME["pill_border"],
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._toggle_mini_overlay
        )
        self.hud_btn.pack(side="left", padx=6)

        # Theme Toggle Button (☀️ White Mode / 🌙 Dark Mode)
        theme_btn_text = "Light theme" if self.theme == "Dark" else "Dark theme"
        self.theme_btn = neon_ui.Button(
            rbox, text=theme_btn_text, image=neon_ui.icon('sun', '#FFCD32', 21),
            width=138, height=42, corner_radius=13,
            fg_color=THEME["pill_bg"],
            hover_color=THEME["button_hover"],
            text_color=THEME["text_primary"],
            border_width=1.5,
            border_color=THEME["pill_border"],
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._toggle_theme
        )
        self.theme_btn.pack(side="left", padx=6)

        self.top_bat_pill = ctk.CTkLabel(
            status_bar, text="ϟ   Detecting power...",
            fg_color=THEME["pill_bg"], corner_radius=18,
            padx=15, pady=8,
            font=ctk.CTkFont(size=14, weight="bold"), text_color=THEME["accent_green"]
        )
        self.top_bat_pill.pack(side="left", padx=5)

        self.top_engine_pill = ctk.CTkLabel(
            status_bar, text="⌨   Keyboard stays on",
            fg_color=THEME["pill_bg"], corner_radius=18,
            padx=15, pady=8,
            font=ctk.CTkFont(size=14, weight="bold"), text_color=THEME["accent_blue"]
        )
        self.top_engine_pill.pack(side="left", padx=5)
        neon_ui.Button(status_bar, text="View diagnostics    →", width=160, height=39,
                      fg_color=THEME["button_bg"], hover_color=THEME["button_hover"],
                      text_color=THEME["text_secondary"], corner_radius=13,
                      command=self._show_hardware_details).pack(side="right")
        self.retry_hardware_btn = neon_ui.Button(
            status_bar, text="Retry last command", width=145, height=28,
            state="disabled", fg_color=THEME["button_bg"],
            hover_color=THEME["button_hover"], text_color=THEME["accent_amber"],
            command=self._retry_last_hardware_command)

        # Build Page Views
        self.pages = {}
        self.pages["lighting"] = self._create_lighting_page()
        self.pages["backzone"] = self._create_backzone_page()
        self.pages["performance"] = self._create_performance_page()
        self.pages["telemetry"] = self._create_telemetry_page()
        self.pages["presets"] = self._create_presets_page()
        self.pages["about"] = self._create_about_page()
        self.root.after_idle(lambda: studio_ui.block_slider_mousewheel(self.root))

    # -----------------------------------------------------------------------
    # PAGE 1: Lighting Matrix & Precision RGB
    # -----------------------------------------------------------------------
    def _create_lighting_page(self):
        scroll = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")

        # 1. Interactive 4-Zone GT device visualization
        card_zones = neon_ui.Frame(scroll, fg_color=THEME["card_bg"], corner_radius=14, border_width=1, border_color=THEME["card_border"])
        card_zones.pack(fill="x", padx=4, pady=(8, 7))

        z_hdr = neon_ui.Frame(card_zones, fg_color="transparent")
        z_hdr.pack(fill="x", padx=18, pady=(10, 2))
        ctk.CTkLabel(z_hdr, text="⌨", width=38,
                     font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=THEME["accent_blue"]).pack(side="left", padx=(0, 8))
        title_stack = neon_ui.Frame(z_hdr, fg_color="transparent")
        title_stack.pack(side="left")
        ctk.CTkLabel(title_stack, text="Your keyboard", font=ctk.CTkFont(size=18, weight="bold"), text_color=THEME["text_primary"]).pack(anchor="w")
        ctk.CTkLabel(title_stack, text="Select a zone on the keyboard or use the shortcuts below.", font=ctk.CTkFont(size=12), text_color=THEME["text_secondary"]).pack(anchor="w")
        
        self.zone_selected_pill = ctk.CTkLabel(
            z_hdr, text=f"Selected: Zone 1 (WASD Gaming)  •  {self._rgb_to_hex(self.zones.get('1', (56, 189, 248)))}   ●",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=self._tc("accent_blue")
        )
        self.zone_selected_pill.pack(side="right")

        # Top Zone Pill Selectors
        z_pills_row = neon_ui.Frame(card_zones, fg_color="transparent")
        z_pills_row.pack(fill="x", padx=18, pady=(2, 6))
        
        self.zone_pill_buttons = {}
        for zid in ["1", "2", "3", "4"]:
            ztitle = ZONE_LABELS.get(zid, f"Zone {zid}")
            z_hex = self._rgb_to_hex(self.zones.get(zid, (56, 189, 248)))
            z_pill = neon_ui.Button(
                z_pills_row, text=f"{ztitle}  [{z_hex}]",
                height=42, corner_radius=10,
                fg_color=THEME["nav_active_bg"] if zid == "1" else THEME["button_bg"],
                hover_color=THEME["button_hover"],
                text_color=THEME["button_text"],
                border_width=2 if zid == "1" else 1,
                border_color=THEME["accent_blue"] if zid == "1" else THEME["card_border"],
                font=ctk.CTkFont(size=12, weight="bold"),
                command=lambda z=zid: self._on_zone_clicked(z)
            )
            z_pill.pack(side="left", padx=5, fill="x", expand=True)
            self.zone_pill_buttons[zid] = z_pill

        import tkinter as tk
        self.kb_canvas = tk.Canvas(
            card_zones, width=710, height=292,
            bg=self._tc("card_bg"), highlightthickness=0
        )
        self.kb_canvas.pack(fill="x", padx=18, pady=(4, 0))
        self.kb_canvas.bind("<Configure>", lambda event: studio_ui.draw_keyboard(self))
        studio_ui.draw_keyboard(self)
        history_row = neon_ui.Frame(card_zones, fg_color="transparent")
        history_row.pack(fill="x", padx=18, pady=(0, 7))
        ctk.CTkLabel(history_row, text="✣  Experiment freely – undo lighting changes this session.",
                     fg_color=THEME["button_bg"], corner_radius=9, padx=12, pady=6,
                     text_color=THEME["text_secondary"], font=ctk.CTkFont(size=11)).pack(side="left")
        self.lighting_redo = neon_ui.Button(history_row, text="Redo", width=65, height=28,
                                          command=lambda: self._move_lighting_history(1))
        self.lighting_redo.pack(side="right", padx=(6, 0))
        self.lighting_undo = neon_ui.Button(history_row, text="Undo", width=65, height=28,
                                          command=lambda: self._move_lighting_history(-1))
        self.lighting_undo.pack(side="right")
        self._refresh_history_buttons()
        ctk.CTkLabel(card_zones, text="LIVE 4-ZONE PREVIEW    ·    Click the illuminated keyboard areas to edit",
                     font=ctk.CTkFont(size=11), text_color=THEME["text_muted"]).place(relx=.52, rely=.948, anchor="center")

        card_signature = neon_ui.Frame(scroll, fg_color=THEME["card_bg"], corner_radius=16,
                                      border_width=1, border_color=THEME["card_border"])
        card_signature.pack(fill="x", padx=16, pady=6)
        # Curated Theme Combos with Live 4-Color Swatch Previews
        combo_label_row = neon_ui.Frame(card_signature, fg_color="transparent")
        combo_label_row.pack(fill="x", padx=16, pady=(14, 8))
        ctk.CTkLabel(combo_label_row, text="SIGNATURE PALETTES   /   One click. Four coordinated colors.", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_secondary"]).pack(side="left")

        # Function to generate 4-color palette swatch CTkImage
        self.theme_swatches = {}
        def _make_theme_swatch(czones):
            img = Image.new("RGBA", (32, 10), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            sw = 8
            for idx, zk in enumerate(["1", "2", "3", "4"]):
                rgb = czones.get(zk, (56, 189, 248))
                draw.rectangle([idx * sw, 0, (idx + 1) * sw - 1, 9], fill=(*rgb, 255))
            return ctk.CTkImage(light_image=img, dark_image=img, size=(28, 8))

        self.theme_buttons = {}
        palette_rows = []
        zone_theme_items = list(ZONE_THEMES.items())
        items_per_row = 4
        for i in range(0, len(zone_theme_items), items_per_row):
            pady_val = (2, 14) if i + items_per_row >= len(zone_theme_items) else (2, 2)
            combo_row = neon_ui.Frame(card_signature, fg_color="transparent")
            combo_row.pack(fill="x", padx=16, pady=pady_val)
            if i >= items_per_row:
                combo_row.pack_forget()
                palette_rows.append(combo_row)
            for cname, czones in zone_theme_items[i:i + items_per_row]:
                swatch_img = _make_theme_swatch(czones)
                self.theme_swatches[cname] = swatch_img
                is_active = (getattr(self, 'current_theme', '') == cname and self.effect_mode == "Solid")
                cbtn = neon_ui.Button(
                    combo_row, text=f" {cname}", height=30,
                    image=swatch_img, compound="left",
                    fg_color=THEME["button_hover"] if is_active else THEME["button_bg"],
                    hover_color=THEME["button_hover"],
                    text_color=THEME["button_text"],
                    border_width=2 if is_active else 1,
                    border_color=THEME["accent_green"] if is_active else THEME["card_border"],
                    corner_radius=8, font=ctk.CTkFont(size=12, weight="bold"),
                    command=lambda n=cname, z=czones: self._apply_zone_combo(n, z)
                )
                cbtn.pack(side="left", padx=2, fill="x", expand=True)
                self.theme_buttons[cname] = cbtn

        def toggle_palettes():
            expanded = palette_toggle.cget("text") == "Show all 20 palettes"
            for row in palette_rows:
                if expanded:
                    row.pack(fill="x", padx=16, pady=2, before=palette_toggle)
                else:
                    row.pack_forget()
            palette_toggle.configure(text="Show fewer palettes" if expanded else "Show all 20 palettes")
        palette_toggle = neon_ui.Button(card_signature, text="Show all 20 palettes", height=28,
                                      fg_color="transparent", text_color=THEME["accent_blue"],
                                      hover_color=THEME["button_hover"], command=toggle_palettes)
        palette_toggle.pack(anchor="w", padx=16, pady=(4, 12))

        # 2. Dynamic Animations & Audio Sync - "Motion & effects" (DIRECTLY NEXT TO "Your RGB signature")
        card_fx = neon_ui.Frame(scroll, fg_color=THEME["card_bg"], corner_radius=14, border_width=1, border_color=THEME["card_border"])
        card_fx.pack(fill="x", padx=16, pady=6)

        fx_hdr = neon_ui.Frame(card_fx, fg_color="transparent")
        fx_hdr.pack(fill="x", padx=18, pady=(12, 6))
        ctk.CTkLabel(fx_hdr, text="ϟ", font=ctk.CTkFont(size=25, weight="bold"), text_color=THEME["accent_blue"]).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(fx_hdr, text="Motion & effects", font=ctk.CTkFont(size=17, weight="bold"), text_color=THEME["text_primary"]).pack(side="left")
        
        fx_badge_box = neon_ui.Frame(fx_hdr, fg_color="transparent")
        fx_badge_box.pack(side="right")

        self.stop_fx_btn = neon_ui.Button(
            fx_badge_box, text="⏹ Stop Animation", width=125, height=26,
            fg_color=THEME["button_bg"], hover_color=THEME["button_hover"],
            text_color=THEME["accent_rose"], border_width=1, border_color=THEME["card_border"],
            corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"),
            command=self._stop_animation
        )
        if self.effect_mode != "Solid":
            self.stop_fx_btn.pack(side="left", padx=(0, 8))

        self.fx_status_badge = ctk.CTkLabel(
            fx_badge_box, 
            text="⚪ STATIC (Themes / Manual)" if self.effect_mode == "Solid" else f"🟢 RUNNING: {self.effect_mode}",
            font=ctk.CTkFont(size=13, weight="bold"), 
            text_color=self._tc("text_muted") if self.effect_mode == "Solid" else self._tc("accent_blue")
        )
        self.fx_status_badge.pack(side="left")

        self.effect_var = ctk.StringVar(value=self.effect_mode)
        effects = [
            ("🌈 Solid Calm", "Solid"), 
            ("🌌 Aurora Borealis", "Aurora"),
            ("↔️ Bidirectional flow", "AllAurora"),
            ("🌈 Rainbow Prism", "RainbowPrism"),
            ("🔥 Blazing Fire", "BlazingFire"),
            ("🌊 Wave Sweep", "Wave"),
            ("🎲 Random Morph", "RandomMorph"),
            ("🫁 Breathing Pulse", "BreathingPulse"),
            ("🎨 Color Shift", "ColorShift"),
            ("🎬 Screen Sync", "ScreenSync"),
            ("⚡ Reactive Typing", "ReactiveTyping"),
            ("🎵 Audio Visualizer", "AudioSync"),
            ("🧲 Magnetic Slingshot", "MagneticSlingshot"),
            ("🧬 Chromatic Relay", "ChromaticRelay"),
            ("⏳ Time Fracture", "TimeFracture"),
            ("🪐 Orbital Eclipse", "OrbitalEclipse"),
        ]
        
        descriptions = {
            "Solid": "One steady signature", "Aurora": "Soft ribbons of color",
            "AllAurora": "Flow in both directions", "RainbowPrism": "The full color spectrum",
            "BlazingFire": "Warm, flickering tones", "Wave": "A sweep across your keys",
            "RandomMorph": "Unexpected color blends", "BreathingPulse": "A gentle rise and fall",
            "ColorShift": "Smooth color transitions", "ScreenSync": "Match what is on screen",
            "ReactiveTyping": "Respond to each keystroke", "AudioSync": "Move with your music",
            "MagneticSlingshot": "Collide, swap, and release", "ChromaticRelay": "Pass colour zone to zone",
            "TimeFracture": "Freeze, rewind, fast-forward", "OrbitalEclipse": "Moving shadow and bright rim",
        }
        effect_grid = neon_ui.Frame(card_fx, fg_color="transparent")
        effect_grid.pack(fill="x", padx=12, pady=(0, 6))
        effect_grid.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="effects")
        self.effect_tiles = {}
        for index, (title, mode) in enumerate(effects):
            tile = neon_ui.Frame(effect_grid, fg_color=THEME["card_sub_bg"],
                                corner_radius=10, border_width=1, border_color=THEME["card_border"])
            tile.grid(row=index // 4, column=index % 4, sticky="ew", padx=4, pady=4)
            rb = ctk.CTkRadioButton(tile, text=title, value=mode,
                                    variable=self.effect_var, command=self._on_effect_changed,
                                    radiobutton_width=18, radiobutton_height=18,
                                    fg_color=THEME["accent_blue"], hover_color=THEME["accent_blue"],
                                    text_color=THEME["text_primary"], font=ctk.CTkFont(size=14))
            rb.pack(anchor="w", padx=12, pady=(10, 0))
            caption = ctk.CTkLabel(tile, text=descriptions[mode], height=22,
                                  text_color=THEME["text_secondary"], font=ctk.CTkFont(size=12))
            caption.pack(anchor="w", padx=38, pady=(0, 7))
            def choose(event=None, value=mode):
                self.effect_var.set(value)
                self._on_effect_changed()
            tile.bind("<Button-1>", choose)
            caption.bind("<Button-1>", choose)
            self.effect_tiles[mode] = tile

        # Speed & Direction Row
        self.fx_ctrl_row = neon_ui.Frame(card_fx, fg_color="transparent")
        self.fx_ctrl_row.pack(fill="x", padx=16, pady=(4, 14))

        ctk.CTkLabel(self.fx_ctrl_row, text="Speed:", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_secondary"]).pack(side="left", padx=(0, 6))
        self.speed_var = ctk.StringVar(value=self.anim_speed)
        self.speed_seg = neon_ui.SegmentedButton(
            self.fx_ctrl_row, values=["Slow", "Normal", "Fast", "Turbo"],
            variable=self.speed_var, command=lambda v: self._on_speed_changed(),
            selected_color=THEME["accent_blue"],
            selected_hover_color=THEME["accent_purple"]
        )
        self.speed_seg.pack(side="left", padx=(0, 16))

        self.dir_lbl = ctk.CTkLabel(self.fx_ctrl_row, text="Direction / Flow:", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_secondary"])
        self.dir_lbl.pack(side="left", padx=(0, 6))
        self.direction_var = ctk.StringVar(value=self.anim_direction)
        self.dir_seg = ctk.CTkOptionMenu(
            self.fx_ctrl_row, values=list(ANIMATION_DIRECTIONS),
            variable=self.direction_var, command=lambda v: self._on_direction_changed(),
            fg_color=THEME["button_bg"], button_color=THEME["button_hover"],
            text_color=THEME["text_primary"], width=170
        )
        self.dir_seg.pack(side="left", padx=0)
        if self.effect_mode not in DIRECTIONAL_EFFECTS:
            self.dir_seg.configure(state="disabled")
        if self.effect_mode not in SPEED_CONTROLLED_EFFECTS:
            self.speed_seg.configure(state="disabled")

        # Screen Sync Mode Row (Spatial 4-Zone vs Single Unified Color)
        self.sync_mode_row = neon_ui.Frame(card_fx, fg_color="transparent")
        if self.effect_mode == "ScreenSync":
            self.sync_mode_row.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(self.sync_mode_row, text="🎬 Screen Sync Mode:", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_secondary"]).pack(side="left", padx=(0, 10))
        cur_sync_label = "🌈 4-Zone Spatial (Per-Zone)" if getattr(self, 'screen_sync_mode', 'Spatial') == 'Spatial' else "💡 Single Unified (Full Keyboard)"
        self.screen_sync_var = ctk.StringVar(value=cur_sync_label)
        self.sync_seg = neon_ui.SegmentedButton(
            self.sync_mode_row, values=["🌈 4-Zone Spatial (Per-Zone)", "💡 Single Unified (Full Keyboard)"],
            variable=self.screen_sync_var, command=lambda v: self._on_screen_sync_mode_changed(),
            selected_color=THEME["accent_green"],
            selected_hover_color=THEME["accent_blue"]
        )
        self.sync_seg.pack(side="left", padx=0)

        # Real-Time 4-Band Graphical Audio Equalizer & VU-Meter (Appears when AudioSync is active)
        self.audio_viz_frame = neon_ui.Frame(card_fx, fg_color="#0A0F1D", corner_radius=12, border_width=1.5, border_color="#1E293B")
        if self.effect_mode == "AudioSync":
            self.audio_viz_frame.pack(fill="x", padx=16, pady=(2, 12))

        eq_top = neon_ui.Frame(self.audio_viz_frame, fg_color="transparent")
        eq_top.pack(fill="x", padx=12, pady=(10, 4))

        self.audio_dev_lbl = ctk.CTkLabel(
            eq_top, 
            text=f"🎧 Audio Source: {getattr(self, 'audio_device_name', 'Detecting Output...')} • AGC Auto-Boost ON",
            font=ctk.CTkFont(size=13, weight="bold"), 
            text_color=THEME["accent_blue"]
        )
        self.audio_dev_lbl.pack(side="left")

        self.audio_beat_badge = ctk.CTkLabel(
            eq_top, text="⚡ BEAT PULSE",
            fg_color="#1E293B", text_color=THEME["text_muted"],
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=8, padx=8, pady=2
        )
        self.audio_beat_badge.pack(side="right")

        gain_row = neon_ui.Frame(self.audio_viz_frame, fg_color="transparent")
        gain_row.pack(fill="x", padx=12, pady=(2, 6))

        ctk.CTkLabel(gain_row, text="Mic/Headphone Gain Boost:", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_secondary"]).pack(side="left", padx=(0, 6))
        self.audio_gain_slider = neon_ui.Slider(
            gain_row, from_=0.5, to=3.0, number_of_steps=25, width=140,
            command=self._on_audio_gain_changed,
            progress_color=THEME["accent_blue"], fg_color=THEME["progress_bg"], button_color=THEME["accent_blue"]
        )
        self.audio_gain_slider.set(getattr(self, "audio_gain_multiplier", 1.5))
        self.audio_gain_slider.pack(side="left", padx=(0, 8))

        self.audio_gain_lbl = ctk.CTkLabel(
            gain_row, 
            text=f"{self.audio_gain_slider.get():.1f}x (Auto-Compensated)", 
            font=ctk.CTkFont(size=12, weight="bold"), 
            text_color=THEME["accent_blue"]
        )
        self.audio_gain_lbl.pack(side="left")

        ctk.CTkLabel(
            gain_row, 
            text="• Adaptive Auto-Gain for Headphones & Low Laptop Volume", 
            font=ctk.CTkFont(size=12), 
            text_color=THEME["text_muted"]
        ).pack(side="right")

        self.audio_eq_canvas = tk.Canvas(
            self.audio_viz_frame, height=115, bg="#070B14", highlightthickness=1, highlightbackground="#1E293B"
        )
        self.audio_eq_canvas.pack(fill="x", padx=12, pady=(2, 10))
        self._init_audio_eq_canvas_items()


        # 5. Compact Zone Color Studio Card
        card_precision = neon_ui.Frame(scroll, fg_color=THEME["card_bg"], corner_radius=16, border_width=1, border_color=THEME["card_border"])
        card_precision.pack(fill="x", padx=16, pady=6)

        p_hdr = neon_ui.Frame(card_precision, fg_color="transparent")
        p_hdr.pack(fill="x", padx=16, pady=(12, 2))

        ctk.CTkLabel(
            p_hdr, text="Zone color",
            font=ctk.CTkFont(size=15, weight="bold"), text_color=THEME["text_primary"]
        ).pack(side="left")

        zone_names_init = {"1": "WASD Gaming", "2": "Center Alpha", "3": "Right / Arrows", "4": "Full Numpad"}
        self.slider_target_lbl = ctk.CTkLabel(
            card_precision,
            text=f"Zone {self.selected_zone} · {zone_names_init.get(self.selected_zone, 'WASD Gaming')}",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["accent_blue"]
        )
        self.slider_target_lbl.pack(anchor="w", padx=16, pady=(0, 6))

        # Main Color Control Row
        cur_rgb = self.zones.get(self.selected_zone, [56, 189, 248])
        self.picked_rgb = list(cur_rgb)
        cur_hex = self._rgb_to_hex(cur_rgb)

        picker_row = neon_ui.Frame(card_precision, fg_color="transparent")
        picker_row.pack(fill="x", padx=16, pady=(2, 6))

        # 48x38 rounded swatch
        swatch_outer = neon_ui.Frame(picker_row, fg_color=THEME["card_border"], corner_radius=8, width=54, height=38, cursor="hand2")
        swatch_outer.pack(side="left", padx=(0, 10))
        swatch_outer.pack_propagate(False)
        self.color_swatch = tk.Frame(swatch_outer, bg=cur_hex, width=48, height=32, cursor="hand2")
        self.color_swatch.place(relx=0.5, rely=0.5, anchor="center")
        self.color_swatch.bind("<Button-1>", lambda e: self._open_color_picker())
        swatch_outer.bind("<Button-1>", lambda e: self._open_color_picker())

        # Hex text display & entry
        self.hex_display_lbl = ctk.CTkLabel(
            picker_row, text=cur_hex, font=ctk.CTkFont(size=15, weight="bold"),
            text_color=THEME["text_primary"]
        )
        self.hex_display_lbl.pack(side="left", padx=(0, 10))

        self.hex_entry = ctk.CTkEntry(picker_row, width=80, height=28, font=ctk.CTkFont(size=13))
        self.hex_entry.insert(0, cur_hex)
        self.hex_entry.pack(side="left", padx=(0, 8))
        self.hex_entry.bind("<Return>", lambda e: self._on_hex_applied())

        # Primary Edit Color button
        edit_btn = neon_ui.Button(
            picker_row, text="🎨 Edit Color", width=105, height=30,
            fg_color=THEME["accent_blue"], hover_color=THEME["button_hover"],
            text_color=("#FFFFFF", "#0C1824"), corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"),
            command=self._open_color_picker
        )
        edit_btn.pack(side="left", padx=(0, 6))

        # Copy Hex button
        copy_btn = neon_ui.Button(
            picker_row, text="📋 Copy", width=65, height=30,
            fg_color=THEME["button_bg"], hover_color=THEME["button_hover"],
            text_color=THEME["text_secondary"], corner_radius=8, font=ctk.CTkFont(size=13),
            command=self._copy_current_hex
        )
        copy_btn.pack(side="left", padx=(0, 6))

        # Apply to All Zones button
        apply_all_btn = neon_ui.Button(
            picker_row, text="⬛ Apply to All Zones", width=155, height=30,
            fg_color=THEME["button_bg"], hover_color=THEME["button_hover"],
            text_color=THEME["accent_blue"], border_width=1.5, border_color=THEME["accent_blue"],
            corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"),
            command=self._apply_picked_color_to_all_zones
        )
        apply_all_btn.pack(side="right")

        group_row = neon_ui.Frame(card_precision, fg_color="transparent")
        group_row.pack(fill="x", padx=16, pady=(6, 4))
        self.zone_group_vars = {}
        for zid in ("1", "2", "3", "4"):
            var = tk.BooleanVar(value=zid == self.selected_zone)
            self.zone_group_vars[zid] = var
            ctk.CTkCheckBox(group_row, text=f"Zone {zid}", variable=var, width=75,
                            checkbox_width=16, checkbox_height=16).pack(side="left", padx=(0, 8))
        neon_ui.Button(group_row, text="Apply to checked", width=130, height=28,
                       command=self._apply_color_to_checked_zones).pack(side="right")

        # Row 2: Recent Colors row
        recent_box = neon_ui.Frame(card_precision, fg_color="transparent")
        recent_box.pack(fill="x", padx=16, pady=(4, 8))
        ctk.CTkLabel(
            recent_box, text="Recent:", font=ctk.CTkFont(size=13, weight="bold"),
            text_color=THEME["text_secondary"]
        ).pack(side="left", padx=(0, 8))

        self.recent_swatches_container = neon_ui.Frame(recent_box, fg_color="transparent")
        self.recent_swatches_container.pack(side="left")
        self.recent_swatches_frame = self.recent_swatches_container
        self.btn_edit_color = edit_btn
        self.btn_copy_hex = copy_btn
        self.btn_apply_all = apply_all_btn
        self.zone_hex_label = self.hex_display_lbl
        self._refresh_recent_swatches()

        # Row 3: Separated White Temperature (Kelvin) Subsection
        kelvin_card = neon_ui.Frame(card_precision, fg_color=THEME.get("card_sub_bg", "#13161C"), corner_radius=10)
        kelvin_card.pack(fill="x", padx=16, pady=(4, 12))

        k_top = neon_ui.Frame(kelvin_card, fg_color="transparent")
        k_top.pack(fill="x", padx=12, pady=(8, 2))
        ctk.CTkLabel(
            k_top, text="White temperature · Warm to cool",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["accent_amber"]
        ).pack(side="left")

        self.kelvin_lbl = ctk.CTkLabel(
            k_top, text=f"{getattr(self, 'color_temp_kelvin', 6500)}K",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["accent_amber"]
        )
        self.kelvin_lbl.pack(side="right")

        k_controls = neon_ui.Frame(kelvin_card, fg_color="transparent")
        k_controls.pack(fill="x", padx=12, pady=(2, 10))

        self.kelvin_slider = neon_ui.Slider(
            k_controls, from_=2000, to=6500, number_of_steps=45,
            command=self._on_kelvin_slider_changed, progress_color=THEME["accent_amber"],
            button_color=THEME["accent_amber"], fg_color=THEME["progress_bg"]
        )
        self.kelvin_slider.set(getattr(self, 'color_temp_kelvin', 6500))
        self.kelvin_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))

        neon_ui.Button(
            k_controls, text="Apply Temp", width=95, height=28,
            fg_color=THEME["button_bg"], hover_color=THEME["button_hover"],
            text_color=THEME["accent_amber"], border_width=1, border_color=THEME["card_border"],
            corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"),
            command=self._apply_kelvin_temperature
        ).pack(side="right")

        # 6. Vivid Neon Color Presets Grid (16 colors in 4 rows of 4)
        card_pal = neon_ui.Frame(scroll, fg_color=THEME["card_bg"], corner_radius=16, border_width=1, border_color=THEME["card_border"])
        card_pal.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(card_pal, text="Color library · Applies to all four zones", font=ctk.CTkFont(size=15, weight="bold"), text_color=THEME["text_primary"]).pack(anchor="w", padx=16, pady=(12, 6))

        for row_start in range(0, 16, 4):
            row_frame = neon_ui.Frame(card_pal, fg_color="transparent")
            row_frame.pack(fill="x", padx=16, pady=2)
            for name, hex_col, rgb in SOFT_COLOR_PRESETS[row_start:row_start + 4]:
                b = neon_ui.Button(
                    row_frame, text=name,
                    fg_color=THEME["card_sub_bg"], hover_color=THEME["button_hover"],
                    text_color=THEME["text_primary"], border_width=1, border_color=THEME["card_border"],
                    image=self._color_chip(hex_col), compound="left",
                    corner_radius=8, height=38, font=ctk.CTkFont(size=13, weight="bold"),
                    command=lambda c=rgb: self._apply_global_color(c)
                )
                b.pack(side="left", fill="x", expand=True, padx=3)

        neon_ui.Frame(card_pal, fg_color="transparent", height=6).pack()  # bottom spacer

        # Brightness Card
        card_bright = neon_ui.Frame(scroll, fg_color=THEME["card_bg"], corner_radius=14, border_width=1, border_color=THEME["card_border"])
        card_bright.pack(fill="x", padx=4, pady=7)

        b_hdr = neon_ui.Frame(card_bright, fg_color="transparent")
        b_hdr.pack(fill="x", padx=18, pady=(12, 6))

        ctk.CTkLabel(b_hdr, text="☼", width=38,
                     font=ctk.CTkFont(size=29),
                     text_color=THEME["accent_blue"]).pack(side="left", padx=(0, 9))

        title_group = neon_ui.Frame(b_hdr, fg_color="transparent")
        title_group.pack(side="left")
        ctk.CTkLabel(title_group, text="Keyboard brightness", font=ctk.CTkFont(size=15, weight="bold"), text_color=THEME["text_primary"]).pack(anchor="w")
        ctk.CTkLabel(title_group, text="Keyboard lighting only · Display brightness stays unchanged",
                     font=ctk.CTkFont(size=12), text_color=THEME["text_secondary"]).pack(anchor="w")
        self.bright_lbl = ctk.CTkLabel(b_hdr, text=f"{self.brightness}%", font=ctk.CTkFont(size=15, weight="bold"), text_color=THEME["accent_blue"])
        self.bright_lbl.pack(side="right")

        b_ctrl = neon_ui.Frame(card_bright, fg_color="transparent")
        b_ctrl.pack(fill="x", padx=72, pady=(0, 14))

        self.bright_slider = neon_ui.Slider(
            b_ctrl, from_=10, to=100, number_of_steps=90,
            command=self._on_brightness_changed, progress_color=THEME["accent_blue"],
            button_color=THEME["accent_blue"], fg_color=THEME["progress_bg"]
        )
        self.bright_slider.set(self.brightness)
        self.bright_slider.pack(side="left", fill="x", expand=True, padx=(0, 12))

        self.bright_quick_btns = {}
        for pct in [25, 50, 75, 100]:
            is_active = (self.brightness == pct)
            btn = neon_ui.Button(
                b_ctrl, text=f"{pct}%", width=48, height=28,
                fg_color=THEME["button_hover"] if is_active else THEME["button_bg"], 
                hover_color=THEME["button_hover"],
                text_color=THEME["accent_blue"] if is_active else THEME["button_text"], 
                border_width=2 if is_active else 1, 
                border_color=THEME["accent_blue"] if is_active else THEME["card_border"],
                corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"),
                command=lambda p=pct: self._set_brightness_pct(p)
            )
            btn.pack(side="left", padx=3)
            self.bright_quick_btns[pct] = btn

        # Anti-Timeout Hero Switch Card
        card_hero = neon_ui.Frame(scroll, fg_color=THEME["card_bg"], corner_radius=16, border_width=1, border_color=THEME["card_border"])
        card_hero.pack(fill="x", padx=16, pady=6)

        hero_row = neon_ui.Frame(card_hero, fg_color="transparent")
        hero_row.pack(fill="x", padx=16, pady=(14, 4))

        self.always_on_var = ctk.BooleanVar(value=self.config.get("always_on", True))
        hero_switch = ctk.CTkSwitch(
            hero_row,
            text="Keyboard lighting · Always on",
            variable=self.always_on_var,
            command=self._on_always_on_toggled,
            font=ctk.CTkFont(size=16, weight="bold"),
            progress_color=THEME["accent_blue"],
            text_color=THEME["text_primary"]
        )
        hero_switch.pack(side="left")

        ctk.CTkLabel(
            card_hero,
            text="Keeps supported keyboards illuminated. Switch off to turn off the keyboard and mecha bar.",
            font=ctk.CTkFont(size=13), text_color=THEME["text_secondary"]
        ).pack(anchor="w", padx=16, pady=(0, 14))
        # 7. Rear Mecha Bar LED
        card_mecha = neon_ui.Frame(scroll, fg_color=THEME["card_bg"], corner_radius=16, border_width=1, border_color=THEME["card_border"])
        card_mecha.pack(fill="x", padx=16, pady=(6, 16))

        self.mecha_var = ctk.BooleanVar(value=self.config.get("mecha_bar_enabled", True))
        mecha_switch = ctk.CTkSwitch(
            card_mecha, text="🏎️ Rear Mecha Bar LED Light Strip",
            variable=self.mecha_var, command=self._on_mecha_toggled,
            font=ctk.CTkFont(size=15, weight="bold"), progress_color=THEME["accent_purple"],
            text_color=THEME["text_primary"]
        )
        mecha_switch.pack(side="left", padx=16, pady=14)

        self.mecha_sync_var = ctk.BooleanVar(value=self.config.get("mecha_bar_sync", True))
        mecha_sync_chk = ctk.CTkCheckBox(
            card_mecha, text="Sync Color with Keyboard Zone 1",
            variable=self.mecha_sync_var, command=self._on_mecha_sync_toggled,
            fg_color=THEME["accent_purple"], hover_color=THEME["accent_purple"],
            text_color=THEME["text_primary"]
        )
        mecha_sync_chk.pack(side="right", padx=16, pady=14)

        # Keep preview and brightness in view, with all detailed controls one click away.
        card_bright.pack_configure(before=card_fx)
        section_bar = neon_ui.Frame(scroll, fg_color="transparent")
        section_bar.pack(fill="x", padx=4, pady=(3, 2), before=card_fx)
        self.studio_sections = {
            "Effects": (card_fx,), "Zone color": (card_precision,),
            "Color presets": (card_signature, card_pal), "Device options": (card_hero, card_mecha),
        }
        self.studio_section_buttons = {}
        self.studio_section = self.config.get("lighting_section", "Effects")
        if self.studio_section not in self.studio_sections:
            self.studio_section = "Effects"
        for title in self.studio_sections:
            tab_icons = {"Effects": "✣", "Zone color": "◉", "Color presets": "▦", "Device options": "⚙"}
            button = neon_ui.Button(section_bar, text=f"{tab_icons[title]}    {title}", height=44, width=170,
                                  fg_color=THEME["button_bg"], text_color=THEME["text_secondary"],
                                  hover_color=THEME["button_hover"], corner_radius=11,
                                  command=lambda name=title: self._show_studio_section(name))
            button.pack(side="left", padx=(0, 8))
            self.studio_section_buttons[title] = button
        self._show_studio_section(self.studio_section)
        return scroll

    def _color_chip(self, color):
        image = Image.new("RGBA", (18, 18), (0, 0, 0, 0))
        ImageDraw.Draw(image).rounded_rectangle((1, 1, 17, 17), radius=5, fill=color)
        return ctk.CTkImage(light_image=image, dark_image=image, size=(16, 16))

    def _show_studio_section(self, name):
        if name not in self.studio_sections:
            name = "Effects"
        self.studio_section = name
        self.config["lighting_section"] = name
        self._save_config()
        for section, cards in self.studio_sections.items():
            for card in cards:
                if section == name:
                    card.pack(fill="x", padx=4, pady=(5, 12))
                else:
                    card.pack_forget()
            selected = section == name
            self.studio_section_buttons[section].configure(
                fg_color=THEME["nav_active_bg"] if selected else THEME["button_bg"],
                text_color=THEME["nav_active_text"] if selected else THEME["text_secondary"],
                border_width=1 if selected else 0, border_color=THEME["accent_blue"])

    # -----------------------------------------------------------------------
    # PAGE 1B: Rear Back Zone Lighting
    # -----------------------------------------------------------------------
    def _create_backzone_page(self):
        self.backzone_view = backzone_ui.BackZoneView(self)
        return self.backzone_view.build_page(self.main_container)

    # -----------------------------------------------------------------------
    # PAGE 2: Performance & AI Governor
    # -----------------------------------------------------------------------
    def _create_performance_page(self):
        scroll = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")

        def label(parent, text, size=14, bold=False):
            item = ctk.CTkLabel(parent, text=text, anchor="w", justify="left",
                font=ctk.CTkFont(size=size, weight="bold" if bold else "normal"),
                text_color=THEME["text_primary" if bold else "text_secondary"])
            item.pack(fill="x", padx=16, pady=(5, 7))
            item.bind("<Configure>", lambda e: item.configure(wraplength=max(180, e.width-12)))
            return item

        def card(title):
            frame = neon_ui.Frame(scroll, fg_color=THEME["card_bg"], corner_radius=14,
                border_width=1, border_color=THEME["card_border"])
            frame.pack(fill="x", padx=4, pady=6)
            heading = label(frame, title, 16, True)
            heading.configure(image=neon_ui.icon({'Performance mode':'performance','Control mode':'settings',
                               'Quick setups':'game','Automatic switching':'refresh',
                               'Cooling & keyboard':'keyboard','Charging':'battery'}.get(title,'settings'),size=28),compound='left',padx=12)
            return frame

        def section(title, hint):
            frame = card(title)
            label(frame, hint, 12)
            body = neon_ui.Frame(frame, fg_color="transparent")
            body.pack(fill="x", pady=(0, 12))
            return body

        def setting(parent, attr, key, title, description, handler, default=False):
            tiled = hasattr(parent, '_setting_count')
            row = neon_ui.Frame(parent, fg_color=THEME['card_sub_bg'] if tiled else "transparent",
                                border_width=1 if tiled else 0, border_color=THEME['card_sub_border'],corner_radius=10)
            if tiled:
                index=parent._setting_count
                parent._setting_count+=1
                row.grid(row=index//3,column=index%3,columnspan=3 if index==3 else 1,sticky='nsew',padx=5,pady=5)
            else:
                row.pack(fill="x", padx=16, pady=6)
            row.grid_columnconfigure(0, weight=1)
            text = ctk.CTkLabel(row, text=title + "\n" + description, anchor="w", justify="left",
                font=ctk.CTkFont(size=14), text_color=THEME["text_primary"])
            text.grid(row=0, column=0, sticky="ew", padx=(12 if tiled else 0, 12),pady=10 if tiled else 0)
            text.bind("<Configure>", lambda e: text.configure(wraplength=max(160, e.width-8)))
            var = ctk.BooleanVar(value=self.config.get(key, default))
            setattr(self, attr, var)
            control = ctk.CTkSwitch(row, text="", width=42, variable=var, command=handler,
                progress_color=THEME["accent_blue"])
            control.grid(row=0, column=1,padx=(0,12) if tiled else 0)
            setattr(self, attr.replace("_var", "_switch"), control)

        modes = card("Performance mode")
        label(modes, "Choose the balance you need. Display brightness is never changed by a performance mode.")
        self.mode_var = ctk.StringVar(value=self.config.get("power_mode", "Balanced"))
        current_mode_name = "Gaming" if self.mode_var.get() == "Beast" else self.mode_var.get()
        self.mode_display_var = ctk.StringVar(value=current_mode_name)
        self.mode_selector = neon_ui.SegmentedButton(
            modes, values=["Quiet", "Balanced", "Gaming"],
            variable=self.mode_display_var, command=self._on_power_mode_segmented,
            height=40, selected_color=THEME["accent_blue"],
            selected_hover_color=THEME["accent_purple"],
            unselected_color=THEME["button_bg"],
            unselected_hover_color=THEME["button_hover"])
        self.mode_selector.pack(fill="x", padx=16, pady=(4, 6))
        mode_hints = neon_ui.Frame(modes, fg_color="transparent")
        mode_hints.pack(fill="x", padx=16, pady=(0, 4))
        mode_hints.grid_columnconfigure((0, 1, 2), weight=1, uniform="mode_hints")
        for index, hint in enumerate(("Silent fans", "Everyday use", "Peak performance")):
            ctk.CTkLabel(mode_hints, text=hint, font=ctk.CTkFont(size=12),
                         text_color=THEME["text_muted"]).grid(row=0, column=index, sticky="ew")
        self.mode_apply_status = ctk.CTkLabel(
            modes, text=f"●  {current_mode_name} mode active", anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=THEME["accent_green"])
        self.mode_apply_status.pack(fill="x", padx=16, pady=(0, 12))

        # Keep manual performance choices and their automation policy together.
        divider = ctk.CTkFrame(modes, height=1, fg_color=THEME["card_border"])
        divider.pack(fill="x", padx=16, pady=(4, 12))
        control = modes
        label(control, "Control mode", 14, True)
        control_top = neon_ui.Frame(control, fg_color="transparent")
        control_top.pack(fill="x", padx=16, pady=(0, 6))
        self.automation_paused_var = ctk.BooleanVar(value=self.config.get("automation_paused", False))
        self.control_mode_var = ctk.StringVar(
            value="Manual" if self._automation_block_reason() else "Auto")
        self.control_mode_selector = neon_ui.SegmentedButton(
            control_top, values=["Auto", "Manual"], variable=self.control_mode_var,
            command=self._on_control_mode_changed, width=220, height=36, dynamic_resizing=False,
            selected_color=THEME["accent_blue"],
            selected_hover_color=THEME["accent_purple"],
            unselected_color=THEME["button_bg"],
            unselected_hover_color=THEME["button_hover"])
        self.control_mode_selector.pack(side="left")
        ctk.CTkLabel(
            control_top, text="Auto follows enabled rules · Manual keeps your choice",
            anchor="e", font=ctk.CTkFont(size=12),
            text_color=THEME["text_secondary"]).pack(side="right", fill="x", expand=True, padx=(12, 0))
        self.automation_state_lbl = ctk.CTkLabel(
            control, text=self._automation_status_text(), anchor="w",
            font=ctk.CTkFont(size=13),
            text_color=THEME["accent_amber"] if self._automation_block_reason()
                       else THEME["text_secondary"])
        self.automation_state_lbl.pack(fill="x", padx=16, pady=(0, 5))
        self.automation_event_labels = []
        event_label = ctk.CTkLabel(
            control, text="Last activity · No automatic changes yet",
            anchor="w", font=ctk.CTkFont(size=12), text_color=THEME["text_muted"])
        event_label.pack(fill="x", padx=16, pady=(0, 9))
        self.automation_event_labels.append(event_label)

        quick = card("Quick setups")
        label(quick, "Choose a setup · Changes performance and keyboard lighting together.", 12)
        grid = neon_ui.Frame(quick, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=(0, 12))
        scenarios = [
            ("Gaming", "Max speed · Win lock", self._preset_scenario_beast),
            ("Office", "Quiet · Soft white", self._preset_scenario_office),
            ("Cinema", "Quiet · Lights off", self._preset_scenario_cinema),
            ("Battery", "Quiet · 20% light", self._preset_scenario_battery)]
        for i, (title, desc, action) in enumerate(scenarios):
            grid.grid_columnconfigure(i, weight=1, uniform="setups")
            box = neon_ui.Frame(grid, fg_color=THEME["card_sub_bg"], corner_radius=12,
                               border_width=1, border_color=THEME["card_sub_border"])
            box.grid(row=0, column=i, sticky="nsew", padx=4, pady=4)
            icon_name = {"Gaming": "game", "Office": "monitor", "Cinema": "monitor", "Battery": "battery"}[title]
            ctk.CTkLabel(box, text="", image=neon_ui.icon(icon_name, size=30)).pack(pady=(16, 4))
            ctk.CTkLabel(box, text=title, font=ctk.CTkFont(size=16, weight="bold"),
                         text_color=THEME["text_primary"]).pack()
            neon_ui.Button(box, text="Apply setup  →", anchor="center", height=36,
                fg_color=THEME["button_bg"], hover_color=THEME["button_hover"],
                text_color=THEME["accent_blue"], command=action).pack(side="bottom", fill="x", padx=12, pady=(4, 12))
            detail = ctk.CTkLabel(box, text=desc, justify="center", anchor="center",
                                  font=ctk.CTkFont(size=12), text_color=THEME["text_secondary"])
            detail.pack(fill="x", padx=7, pady=(6, 9))
            detail.bind("<Configure>", lambda e, item=detail: item.configure(wraplength=max(100, e.width - 10)))

        # 3. OEM GPU routing / MUX mode
        card_gpu_mode = neon_ui.Frame(scroll, fg_color=THEME["card_bg"], corner_radius=16,
                                     border_width=1, border_color=THEME["card_border"])
        card_gpu_mode.pack(fill="x", padx=16, pady=6)
        gpu_head = neon_ui.Frame(card_gpu_mode, fg_color="transparent")
        gpu_head.pack(fill="x", padx=16, pady=(14, 5))
        ctk.CTkLabel(gpu_head, text="GPU mode", font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=THEME["text_primary"]).pack(side="left")
        self.gpu_mode_status = ctk.CTkLabel(
            gpu_head, text="Restart required after changing",
            font=ctk.CTkFont(size=12), text_color=THEME["text_muted"])
        self.gpu_mode_status.pack(side="right")

        self._active_gpu_mode = ""
        self.gpu_mode_var = ctk.StringVar(value="")
        self.gpu_mode_selector = neon_ui.SegmentedButton(
            card_gpu_mode, values=["iGPU only", "Hybrid", "dGPU only"],
            variable=self.gpu_mode_var, command=self._on_gpu_mode_changed,
            height=38, selected_color=THEME["accent_blue"],
            selected_hover_color=THEME["accent_purple"],
            unselected_color=THEME["button_bg"],
            unselected_hover_color=THEME["button_hover"])
        self.gpu_mode_selector.pack(fill="x", padx=16, pady=(4, 8))
        self.gpu_mode_selectors = [self.gpu_mode_selector]
        self.gpu_mode_status_labels = [self.gpu_mode_status]
        ctk.CTkLabel(
            card_gpu_mode,
            text="iGPU saves battery · Hybrid switches automatically · dGPU gives maximum graphics performance",
            font=ctk.CTkFont(size=13), text_color=THEME["text_secondary"]
        ).pack(anchor="w", padx=16, pady=(0, 14))

        def load_gpu_mode():
            # The EC register reports the requested next-boot mode, not
            # necessarily the adapters currently active in Windows.
            current = self._get_pnp_gpu_mode()
            self._ui_dispatch(self._sync_gpu_mode_ui, current)
        threading.Thread(target=load_gpu_mode, daemon=True).start()


        auto = card("Automatic switching")
        self.ai_status_badge = label(auto, "Workload switching enabled" if self.config.get("ai_governor", True) else "Workload switching disabled", 11)
        auto_grid=neon_ui.Frame(auto,fg_color='transparent')
        auto_grid.pack(fill='x',padx=12,pady=(0,10))
        auto_grid.grid_columnconfigure((0,1,2),weight=1,uniform='automation')
        auto=auto_grid
        auto._setting_count=0
        setting(auto, "ai_gov_var", "ai_governor", "Adapt to CPU workload",
                "Switches between Balanced and Gaming as load changes.", self._on_ai_gov_toggled, True)
        setting(auto, "ai_game_var", "ai_game_detector", "Detect games & creative apps",
                "Enables Gaming mode and locks the Windows key for detected apps.", self._on_ai_game_toggled, True)
        setting(auto, "auto_ac_var", "auto_switch_on_ac", "Adapt when charger changes",
                "Uses Quiet on battery and Gaming when AC power returns.", self._on_auto_ac_toggled, True)
        setting(auto, "emerg_saver_var", "emergency_battery_saver", "Low battery saver",
                "Below 20%: Quiet mode and 10% keyboard brightness.", self._on_emergency_saver_toggled, True)

        extras = section("Cooling & keyboard", "Fan boost, key controls and gaming alerts")
        setting(extras, "cooler_var", "cooler_boost", "Maximum fan speed",
                "Extra cooling with more fan noise.", self._on_cooler_boost_toggled)
        setting(extras, "winlock_var", "win_key_lock", "Lock Windows key",
                "Prevents accidental Start-menu presses.", self._on_winlock_toggled)
        setting(extras, "fnlock_var", "software_fn_lock", "Media keys without Fn",
                "F1/F2 adjust screen brightness; F3 controls keyboard lighting.", self._on_fnlock_toggled)
        setting(extras, "gpu_alert_var", "gpu_gaming_alert", "Gaming GPU reminder",
                "Shows a notification when a game starts in iGPU or Hybrid mode.", self._on_gpu_alert_toggled, True)

        charging = section("Charging", "USB charging and battery-limit availability")
        setting(charging, "usb_chg_var", "usb_charge_off", "USB charging while asleep or off",
                "Power connected phones and accessories through supported USB ports.", self._on_usb_charge_toggled, True)
        self.bat_limit_var = ctk.BooleanVar(value=False)
        self.config["battery_limit_80"] = False
        label(charging, "80% charge limit is unavailable on this device's OEM interface.", 11)
        return scroll

    # -----------------------------------------------------------------------
    # PAGE 3: System Telemetry (Redesigned Zero-Scroll Compact Dashboard)
    # -----------------------------------------------------------------------
    def _create_telemetry_page(self):
        scroll = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        self.telemetry_hero_image = None

        # 1. TOP LIVE HEALTH & SYSTEM STATUS HUD BANNER
        status_banner = neon_ui.Frame(scroll, fg_color=THEME["card_bg"], corner_radius=14,
                                    border_width=1, border_color=THEME["card_border"])
        status_banner.pack(fill="x", padx=4, pady=(8, 8))

        banner_inner = neon_ui.Frame(status_banner, fg_color="transparent")
        banner_inner.pack(fill="x", padx=16, pady=12)
        banner_inner.grid_columnconfigure(0, weight=1)
        banner_inner.grid_columnconfigure(1, weight=0)

        # Left Column: Live status pill + suggested action
        left_status = neon_ui.Frame(banner_inner, fg_color="transparent")
        left_status.grid(row=0, column=0, sticky="w")

        status_row = neon_ui.Frame(left_status, fg_color="transparent")
        status_row.pack(anchor="w")

        self.telemetry_status_badge = ctk.CTkLabel(
            status_row, text="🟢 LIVE: SYSTEM OPTIMAL",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=THEME["accent_green"],
            fg_color=THEME["card_sub_bg"], corner_radius=8, padx=12, pady=6
        )
        self.telemetry_status_badge.pack(side="left")

        self.telemetry_cpu_temp_pill = ctk.CTkLabel(
            status_row, text="💻 CPU: --°C",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME["accent_blue"],
            fg_color=THEME["pill_bg"], corner_radius=8, padx=10, pady=6
        )
        self.telemetry_cpu_temp_pill.pack(side="left", padx=8)

        self.telemetry_gpu_temp_pill = ctk.CTkLabel(
            status_row, text="🎮 GPU: --°C",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME["accent_green"],
            fg_color=THEME["pill_bg"], corner_radius=8, padx=10, pady=6
        )
        self.telemetry_gpu_temp_pill.pack(side="left")

        self.telemetry_action_lbl = ctk.CTkLabel(
            left_status,
            text="Cool & quiet (Balanced Mode). All systems operating within optimal thresholds.",
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_muted"], anchor="w"
        )
        self.telemetry_action_lbl.pack(anchor="w", pady=(8, 0))

        # Right Column: Model Specs & Performance / GPU Mode readouts
        right_info = neon_ui.Frame(banner_inner, fg_color="transparent")
        right_info.grid(row=0, column=1, sticky="e", padx=(12, 0))

        right_chips_row = neon_ui.Frame(right_info, fg_color="transparent")
        right_chips_row.pack(anchor="e")

        ctk.CTkLabel(right_chips_row, text="GT BOOK · GL613",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=THEME["text_primary"],
                     fg_color=THEME["card_sub_bg"], corner_radius=8,
                     padx=10, pady=6).pack(side="left", padx=(0, 6))

        current_mode = "Gaming" if self.mode_var.get() == "Beast" else self.mode_var.get()
        self.telemetry_mode_value = ctk.CTkLabel(
            right_chips_row, text=f"⚡ {current_mode}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME["accent_blue"],
            fg_color=THEME["card_sub_bg"], corner_radius=8,
            padx=10, pady=6
        )
        self.telemetry_mode_value.pack(side="left", padx=(0, 6))

        self.telemetry_gpu_mode_value = ctk.CTkLabel(
            right_chips_row, text=f"🎮 {self.gpu_mode_var.get()}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME["accent_green"],
            fg_color=THEME["card_sub_bg"], corner_radius=8,
            padx=10, pady=6
        )
        self.telemetry_gpu_mode_value.pack(side="left")

        ctk.CTkLabel(right_info, text="Intel Core i5-13420H • RTX 4050 • 16\" 120Hz IPS",
                     font=ctk.CTkFont(size=11), text_color=THEME["text_muted"], anchor="e").pack(anchor="e", pady=(8, 0))

        # 2. TELEMETRY GRID (4 RICH UNIFIED HIGH-TECH CARDS)
        grid_frame = neon_ui.Frame(scroll, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=4, pady=4)
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)

        gauge_bg = self._tc('card_bg')
        sub_border = THEME["card_sub_border"][1] if isinstance(THEME["card_sub_border"], tuple) else "#263247"

        # CARD 1: PROCESSOR (CPU) WITH CIRCULAR GAUGE & SPARKLINE
        c1 = neon_ui.Frame(grid_frame, fg_color=THEME["card_bg"], corner_radius=14,
                          border_width=1, border_color=THEME["card_border"])
        c1.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 6))

        c1_top = neon_ui.Frame(c1, fg_color="transparent")
        c1_top.pack(fill="x", padx=14, pady=(10, 4))
        ctk.CTkLabel(c1_top, text="Processor (CPU)", image=neon_ui.icon('cpu'), compound='left', padx=10, font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=THEME["text_secondary"]).pack(side="left")
        ctk.CTkLabel(c1_top, text="LIVE (1s)", fg_color=THEME["pill_bg"], text_color=THEME["accent_green"],
                     font=ctk.CTkFont(size=11, weight="bold"), corner_radius=8, padx=8, pady=2).pack(side="right")

        # 2-Column Gauge & Stats Row
        c1_body = neon_ui.Frame(c1, fg_color="transparent")
        c1_body.pack(fill="x", padx=14, pady=(2, 6))
        c1_body.grid_columnconfigure(0, weight=0)
        c1_body.grid_columnconfigure(1, weight=1)

        # Circular Gauge on the Left
        self.cpu_gauge_canvas = tk.Canvas(c1_body, width=110, height=110, bg=gauge_bg, highlightthickness=0,
                                          highlightbackground=sub_border)
        self.cpu_gauge_canvas.grid(row=0, column=0, padx=(0, 12), pady=2)

        # Right details column
        c1_details = neon_ui.Frame(c1_body, fg_color="transparent")
        c1_details.grid(row=0, column=1, sticky="nsew")

        c1_stat = neon_ui.Frame(c1_details, fg_color="transparent")
        c1_stat.pack(fill="x", pady=(2, 2))
        self.hero_cpu_lbl = ctk.CTkLabel(c1_stat, text="--%", font=ctk.CTkFont(size=26, weight="bold"),
                                         text_color=THEME["accent_blue"])
        self.hero_cpu_lbl.pack(side="left")
        self.cpu_temp_chip = ctk.CTkLabel(c1_stat, text="🌡️ CPU: --°C", font=ctk.CTkFont(size=12, weight="bold"),
                                          text_color=THEME["accent_blue"], fg_color=THEME["card_sub_bg"], corner_radius=6, padx=8, pady=2)
        self.cpu_temp_chip.pack(side="right")

        self.cpu_pct_lbl = ctk.CTkLabel(c1_details, text="13th Gen Intel Core i5-13420H (8C/12T • 12MB Cache)",
                                        font=ctk.CTkFont(size=12), text_color=THEME["text_muted"], anchor="w")
        self.cpu_pct_lbl.pack(fill="x", pady=(2, 4))

        self.cpu_bar = ctk.CTkProgressBar(c1_details, height=7, progress_color=THEME["accent_blue"],
                                          fg_color=THEME["progress_bg"])
        self.cpu_bar.set(0.0)
        self.cpu_bar.pack(fill="x", pady=(2, 2))
        self.hero_cpu_bar = self.cpu_bar

        # Sparkline Section for CPU
        spark_frame = neon_ui.Frame(c1, fg_color="transparent")
        spark_frame.pack(fill="x", padx=14, pady=(2, 10))
        ctk.CTkLabel(spark_frame, text="60-Second Real-Time Activity Sparkline:",
                     font=ctk.CTkFont(size=11, weight="bold"), text_color=THEME["text_muted"]).pack(anchor="w", pady=(0, 2))
        self.cpu_graph_canvas = tk.Canvas(spark_frame, height=76, bg="#071522", highlightthickness=1,
                                          highlightbackground=sub_border)
        self.cpu_graph_canvas.pack(fill="x", expand=True)

        # CARD 2: GRAPHICS (GPU) WITH CIRCULAR GAUGE & SPARKLINE
        c2 = neon_ui.Frame(grid_frame, fg_color=THEME["card_bg"], corner_radius=14,
                          border_width=1, border_color=THEME["card_border"])
        c2.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 6))

        c2_top = neon_ui.Frame(c2, fg_color="transparent")
        c2_top.pack(fill="x", padx=14, pady=(10, 4))
        ctk.CTkLabel(c2_top, text="Graphics Acceleration (GPU)", image=neon_ui.icon('gpu'), compound='left', padx=10, font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=THEME["text_secondary"]).pack(side="left")
        ctk.CTkLabel(c2_top, text="DirectX 12.1", fg_color=THEME["pill_bg"], text_color=THEME["accent_green"],
                     font=ctk.CTkFont(size=11, weight="bold"), corner_radius=8, padx=8, pady=2).pack(side="right")

        # 2-Column Gauge & Stats Row
        c2_body = neon_ui.Frame(c2, fg_color="transparent")
        c2_body.pack(fill="x", padx=14, pady=(2, 6))
        c2_body.grid_columnconfigure(0, weight=0)
        c2_body.grid_columnconfigure(1, weight=1)

        # Circular Gauge on the Left
        self.gpu_gauge_canvas = tk.Canvas(c2_body, width=110, height=110, bg=gauge_bg, highlightthickness=0,
                                          highlightbackground=sub_border)
        self.gpu_gauge_canvas.grid(row=0, column=0, padx=(0, 12), pady=2)

        # Right details column
        c2_details = neon_ui.Frame(c2_body, fg_color="transparent")
        c2_details.grid(row=0, column=1, sticky="nsew")

        c2_stat = neon_ui.Frame(c2_details, fg_color="transparent")
        c2_stat.pack(fill="x", pady=(2, 2))
        self.hero_gpu_lbl = ctk.CTkLabel(c2_stat, text="--%", font=ctk.CTkFont(size=26, weight="bold"),
                                         text_color=THEME["accent_green"])
        self.hero_gpu_lbl.pack(side="left")
        self.gpu_temp_chip = ctk.CTkLabel(c2_stat, text="🌡️ GPU: --°C", font=ctk.CTkFont(size=12, weight="bold"),
                                          text_color=THEME["accent_green"], fg_color=THEME["card_sub_bg"], corner_radius=6, padx=8, pady=2)
        self.gpu_temp_chip.pack(side="right")

        self.gpu_pct_lbl = ctk.CTkLabel(c2_details, text="Intel(R) UHD Graphics & NVIDIA RTX 4050",
                                        font=ctk.CTkFont(size=12), text_color=THEME["text_muted"], anchor="w")
        self.gpu_pct_lbl.pack(fill="x", pady=(2, 4))

        self.gpu_bar = ctk.CTkProgressBar(c2_details, height=7, progress_color=THEME["accent_green"],
                                          fg_color=THEME["progress_bg"])
        self.gpu_bar.set(0.0)
        self.gpu_bar.pack(fill="x", pady=(2, 2))
        self.hero_gpu_bar = self.gpu_bar

        # Sparkline Section for GPU
        gpu_spark_frame = neon_ui.Frame(c2, fg_color="transparent")
        gpu_spark_frame.pack(fill="x", padx=14, pady=(2, 10))
        ctk.CTkLabel(gpu_spark_frame, text="60-Second Real-Time GPU Activity Sparkline:",
                     font=ctk.CTkFont(size=11, weight="bold"), text_color=THEME["text_muted"]).pack(anchor="w", pady=(0, 2))
        self.gpu_graph_canvas = tk.Canvas(gpu_spark_frame, height=76, bg="#071522", highlightthickness=1,
                                          highlightbackground=sub_border)
        self.gpu_graph_canvas.pack(fill="x", expand=True)

        # CARD 3: MEMORY & STORAGE (RAM & SSD)
        c3 = neon_ui.Frame(grid_frame, fg_color=THEME["card_bg"], corner_radius=14,
                          border_width=1, border_color=THEME["card_border"])
        c3.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=(6, 0))

        c3_top = neon_ui.Frame(c3, fg_color="transparent")
        c3_top.pack(fill="x", padx=14, pady=(10, 2))
        ctk.CTkLabel(c3_top, text="Memory & Storage (RAM & SSD)", image=neon_ui.icon('ram'), compound='left', padx=10, font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=THEME["text_secondary"]).pack(side="left")
        self.hero_ram_lbl = ctk.CTkLabel(c3_top, text="--%", font=ctk.CTkFont(size=12, weight="bold"),
                                         text_color=THEME["accent_purple"])
        self.hero_ram_lbl.pack(side="right")

        # RAM Sub-Section
        memory_columns = neon_ui.Frame(c3,fg_color='transparent')
        memory_columns.pack(fill='x',padx=14,pady=(4,8))
        memory_columns.grid_columnconfigure((0,1),weight=1,uniform='memory')
        c3_ram = neon_ui.Frame(memory_columns, fg_color="transparent")
        c3_ram.grid(row=0,column=0,sticky='nsew',padx=(0,10))
        self.ram_pct_lbl = ctk.CTkLabel(c3_ram, text="RAM Usage: Detecting...",
                                        font=ctk.CTkFont(size=14, weight="bold"), text_color=THEME["accent_purple"])
        self.ram_pct_lbl.pack(fill='x')
        self.ram_pct_lbl.configure(anchor='w',justify='left',wraplength=250)
        self.ram_pct_lbl.bind('<Configure>',lambda e:self.ram_pct_lbl.configure(wraplength=max(130,e.width-4)))

        self.ram_bar = ctk.CTkProgressBar(c3_ram, height=7, progress_color=THEME["accent_purple"],
                                          fg_color=THEME["progress_bg"])
        self.ram_bar.set(0.0)
        self.ram_bar.pack(fill="x", pady=(3, 8))
        self.hero_ram_bar = self.ram_bar

        self.ram_graph_canvas=tk.Canvas(c3_ram,height=72,width=200,bg='#071522',highlightthickness=0)
        self.ram_graph_canvas.pack(fill='x')
        self._ram_chart_samples=[]
        self._disk_chart_samples=[]

        # Disk Sub-Section
        c3_disk = neon_ui.Frame(memory_columns, fg_color="transparent")
        c3_disk.grid(row=0,column=1,sticky='nsew',padx=(10,0))
        self.disk_stat_lbl = ctk.CTkLabel(c3_disk, text="Drive C: Detecting...",
                                          font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["accent_amber"])
        self.disk_stat_lbl.pack(fill='x')
        self.disk_stat_lbl.configure(anchor='w',justify='left',wraplength=250)
        self.disk_stat_lbl.bind('<Configure>',lambda e:self.disk_stat_lbl.configure(wraplength=max(130,e.width-4)))

        self.disk_bar = ctk.CTkProgressBar(c3_disk, height=7, progress_color=THEME["accent_amber"],
                                           fg_color=THEME["progress_bg"])
        self.disk_bar.set(0.0)
        self.disk_bar.pack(fill="x", pady=(3, 8))
        self.disk_graph_canvas=tk.Canvas(c3_disk,height=72,width=200,bg='#071522',highlightthickness=0)
        self.disk_graph_canvas.pack(fill='x')

        self.disk_io_lbl = ctk.CTkLabel(c3, text="Active Read: 0.0 MB/s • Active Write: 0.0 MB/s",
                                        font=ctk.CTkFont(size=12), text_color=THEME["text_muted"])
        self.disk_io_lbl.pack(anchor="w", padx=14, pady=(0, 10))

        # CARD 4: POWER & CONNECTIVITY (BATTERY & WI-FI)
        c4 = neon_ui.Frame(grid_frame, fg_color=THEME["card_bg"], corner_radius=14,
                          border_width=1, border_color=THEME["card_border"])
        c4.grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=(6, 0))

        c4_top = neon_ui.Frame(c4, fg_color="transparent")
        c4_top.pack(fill="x", padx=14, pady=(10, 2))
        ctk.CTkLabel(c4_top, text="Power & Connectivity", image=neon_ui.icon('bolt'), compound='left', padx=10, font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=THEME["text_secondary"]).pack(side="left")
        self.hero_bat_lbl = ctk.CTkLabel(c4_top, text="--%", font=ctk.CTkFont(size=12, weight="bold"),
                                         text_color=THEME["accent_green"])
        self.hero_bat_lbl.pack(side="right")

        # Battery Sub-Section
        c4_bat = neon_ui.Frame(c4, fg_color="transparent")
        c4_bat.pack(fill="x", padx=14, pady=(2, 0))
        self.bat_stat_lbl = ctk.CTkLabel(c4_bat, text="Battery Status: Detecting...",
                                         font=ctk.CTkFont(size=14, weight="bold"), text_color=THEME["accent_green"])
        self.bat_stat_lbl.pack(anchor="w")

        self.bat_bar = ctk.CTkProgressBar(c4, height=7, progress_color=THEME["accent_green"],
                                          fg_color=THEME["progress_bg"])
        self.bat_bar.set(0.0)
        self.bat_bar.pack(fill="x", padx=14, pady=(3, 4))
        self.hero_bat_bar = self.bat_bar

        # Live Battery Health & Boot Info Line inside System Monitor
        bat_detail_box = neon_ui.Frame(c4, fg_color=THEME["card_sub_bg"], corner_radius=8,
                                      border_width=1, border_color=THEME["card_sub_border"])
        bat_detail_box.pack(fill="x", padx=14, pady=(2, 6))

        bd_top = neon_ui.Frame(bat_detail_box, fg_color="transparent")
        bd_top.pack(fill="x", padx=8, pady=(4, 2))

        self.telemetry_bat_health_badge = ctk.CTkLabel(
            bd_top, text="🔋 Battery Health: Detecting…",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["accent_green"]
        )
        self.telemetry_bat_health_badge.pack(side="left")

        self.telemetry_refresh_btn = neon_ui.Button(
            bd_top, text="🔄 Refresh", width=68, height=22,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=THEME["button_bg"], hover_color=THEME["button_hover"],
            text_color=THEME["accent_blue"], corner_radius=6,
            command=self._about_refresh_live
        )
        self.telemetry_refresh_btn.pack(side="right")

        self.telemetry_bat_sub_lbl = ctk.CTkLabel(
            bat_detail_box, text="Design: 70.0 Wh • Uptime: Detecting…",
            font=ctk.CTkFont(size=12), text_color=THEME["text_muted"], anchor="w"
        )
        self.telemetry_bat_sub_lbl.pack(fill="x", padx=8, pady=(0, 4))

        # Divider
        neon_ui.Frame(c4, height=1, fg_color=THEME["card_sub_border"]).pack(fill="x", padx=14, pady=(0, 6))

        # Network Sub-Section
        c4_net = neon_ui.Frame(c4, fg_color="transparent")
        c4_net.pack(fill="x", padx=14)
        self.net_speed_lbl = ctk.CTkLabel(c4_net, text="⬇️ Download: 0.0 KB/s    ⬆️ Upload: 0.0 KB/s",
                                          font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["accent_blue"])
        self.net_speed_lbl.pack(anchor="w")

        self.net_total_lbl = ctk.CTkLabel(c4, text="Total Received: 0.0 GB • Total Sent: 0.0 GB",
                                          font=ctk.CTkFont(size=12), text_color=THEME["text_muted"])
        self.net_total_lbl.pack(anchor="w", padx=14, pady=(4, 10))

        sensors = neon_ui.Frame(scroll,fg_color=THEME['card_bg'],corner_radius=14,border_width=1,border_color=THEME['card_border'])
        sensors.pack(fill='x',padx=4,pady=(6,10))
        ctk.CTkLabel(sensors,text='Other sensors',image=neon_ui.icon('chip'),compound='left',padx=10,
                     font=ctk.CTkFont(size=15,weight='bold')).pack(anchor='w',padx=16,pady=(10,4))
        sensor_row=neon_ui.Frame(sensors,fg_color='transparent')
        sensor_row.pack(fill='x',padx=12,pady=(0,12))
        self.sensor_labels={}
        for index,(key,title) in enumerate((('CPU','CPU Temperature'),('GPU','GPU Temperature'),('SSD','SSD Temperature'),('Ambient','Ambient Temperature'),('Fan','Fan Speed'))):
            sensor_row.grid_columnconfigure(index,weight=1,uniform='sensors')
            tile=neon_ui.Frame(sensor_row,fg_color=THEME['card_sub_bg'],border_width=1,border_color=THEME['card_sub_border'],corner_radius=10)
            tile.grid(row=0,column=index,sticky='nsew',padx=4)
            ctk.CTkLabel(tile,text=title,font=ctk.CTkFont(size=11),text_color=THEME['text_secondary']).pack(anchor='w',padx=12,pady=(8,0))
            value=ctk.CTkLabel(tile,text='Not available',font=ctk.CTkFont(size=15,weight='bold'),text_color=THEME['accent_blue'])
            value.pack(anchor='w',padx=12,pady=(0,10))
            self.sensor_labels[key]=value

        return scroll

    def _update_telemetry_mode_buttons(self):
        """Refresh read-only mode state in System monitor."""
        current_mode = "Gaming" if self.mode_var.get() == "Beast" else self.mode_var.get()
        if hasattr(self, "telemetry_mode_value"):
            self.telemetry_mode_value.configure(text=f"●  {current_mode}")

    # -----------------------------------------------------------------------
    # PAGE 4: Gaming & Tools
    # -----------------------------------------------------------------------
    def _create_presets_page(self):
        scroll = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")

        # 1. Custom User Preset Manager Card
        card_preset_mgr = neon_ui.Frame(scroll, fg_color=THEME["card_bg"], corner_radius=16, border_width=1, border_color=THEME["card_border"])
        card_preset_mgr.pack(fill="x", padx=16, pady=(10, 6))

        ctk.CTkLabel(card_preset_mgr, text="Your preset library", font=ctk.CTkFont(size=20, weight="bold"), text_color=THEME["text_primary"]).pack(anchor="w", padx=20, pady=(20, 2))
        ctk.CTkLabel(card_preset_mgr, text="Save a lighting setup, then return to it with one click.", text_color=THEME["text_secondary"]).pack(anchor="w", padx=20, pady=(0, 18))

        save_row = neon_ui.Frame(card_preset_mgr, fg_color="transparent")
        save_row.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(save_row, text="Preset Name:", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_secondary"]).pack(side="left", padx=(0, 6))

        self.preset_name_entry = ctk.CTkEntry(save_row, width=220, height=40, placeholder_text="Name your setup", fg_color=THEME["entry_bg"], border_color=THEME["entry_border"], text_color=THEME["text_primary"])
        self.preset_name_entry.pack(side="left", padx=4)
        self.preset_name_entry.bind("<Return>", lambda event: self._save_user_preset())

        save_btn = neon_ui.Button(
            save_row, text="Save current setup", width=155, height=40,
            fg_color=THEME["button_bg"], hover_color=THEME["button_hover"],
            text_color=THEME["accent_blue"], border_width=1, border_color=THEME["card_border"],
            corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"),
            command=self._save_user_preset
        )
        save_btn.pack(side="left", padx=6)

        # Load Preset Dropdown
        load_row = neon_ui.Frame(card_preset_mgr, fg_color="transparent")
        load_row.pack(fill="x", padx=16, pady=(4, 8))

        ctk.CTkLabel(load_row, text="Saved Presets:", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_secondary"]).pack(side="left", padx=(0, 6))

        user_presets_list = list(self.config.get("user_presets", {}).keys()) or ["No saved presets"]
        self.preset_dropdown = ctk.CTkOptionMenu(
            load_row, values=user_presets_list, width=220, height=40,
            fg_color=THEME["entry_bg"], button_color=THEME["button_bg"], button_hover_color=THEME["button_hover"],
            text_color=THEME["text_primary"], dropdown_fg_color=THEME["card_bg"],
            dropdown_text_color=THEME["text_primary"], dropdown_hover_color=THEME["button_hover"]
        )
        self.preset_dropdown.pack(side="left", padx=4)

        load_btn = neon_ui.Button(
            load_row, text="📂 Load Preset", width=120, height=32,
            fg_color=THEME["button_bg"], hover_color=THEME["button_hover"],
            text_color=THEME["text_primary"], border_width=1, border_color=THEME["card_border"],
            corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"),
            command=self._load_user_preset
        )
        load_btn.pack(side="left", padx=6)
        rename_btn = neon_ui.Button(load_row, text="Rename", width=75, height=32,
                       command=self._rename_user_preset)
        rename_btn.pack(side="left", padx=4)
        delete_btn = neon_ui.Button(load_row, text="Delete", width=65, height=32,
                       command=self._delete_user_preset)
        delete_btn.pack(side="left", padx=4)
        self.preset_library_actions = (load_btn, rename_btn, delete_btn)
        for button in self.preset_library_actions:
            button.configure(state="normal" if self.config.get("user_presets") else "disabled")
        self.preset_power_var = tk.BooleanVar(value=self.config.get("preset_include_power", False))
        ctk.CTkCheckBox(card_preset_mgr, text="Also apply the preset's performance mode",
                        variable=self.preset_power_var,
                        command=lambda: self._set_user_preference("preset_include_power", self.preset_power_var.get())
                        ).pack(anchor="w", padx=16, pady=(4, 6))
        self.preset_status = ctk.CTkLabel(card_preset_mgr, text=("Select a preset to load it. To rename, enter a new name above." if self.config.get("user_presets") else "No presets yet. Name your current setup and save it, or import a preset below."),
                                          text_color=THEME["text_secondary"], anchor="w", wraplength=550, justify="left")
        self.preset_status.pack(fill="x", padx=16, pady=(0, 6))

        # Export / Import Shareable Presets Row
        share_row = neon_ui.Frame(card_preset_mgr, fg_color="transparent")
        share_row.pack(fill="x", padx=16, pady=(4, 14))

        exp_btn = neon_ui.Button(
            share_row, text="📤 Export Preset File", width=155, height=32,
            fg_color=THEME["button_bg"], hover_color=THEME["button_hover"],
            text_color=THEME["accent_green"], border_width=1, border_color=THEME["card_border"],
            corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"),
            command=self._export_preset_file
        )
        exp_btn.pack(side="left", padx=(0, 6))

        imp_btn = neon_ui.Button(
            share_row, text="📥 Import Preset File", width=155, height=32,
            fg_color=THEME["button_bg"], hover_color=THEME["button_hover"],
            text_color=THEME["accent_purple"], border_width=1, border_color=THEME["card_border"],
            corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"),
            command=self._import_preset_file
        )
        imp_btn.pack(side="left", padx=6)

        # 2. Windows Startup Card
        card_start = neon_ui.Frame(scroll, fg_color=THEME["card_bg"], corner_radius=16, border_width=1, border_color=THEME["card_border"])
        card_start.pack(fill="x", padx=16, pady=6)

        self.start_var = ctk.BooleanVar(value=self.config.get("autostart", True))
        start_switch = ctk.CTkSwitch(
            card_start, text="Open toolkit when I sign in",
            variable=self.start_var, command=self._on_autostart_toggled,
            font=ctk.CTkFont(size=16, weight="bold"), progress_color=THEME["accent_blue"],
            text_color=THEME["text_primary"]
        )
        start_switch.pack(anchor="w", padx=16, pady=(14, 4))

        ctk.CTkLabel(
            card_start,
            text="Starts silently in the notification area and restores your saved settings after Windows sign-in.",
            font=ctk.CTkFont(size=13), text_color=THEME["text_secondary"]
        ).pack(anchor="w", padx=16, pady=(0, 14))

        # 3. Hardware Info Card
        close_row = neon_ui.Frame(card_start, fg_color="transparent")
        close_row.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkLabel(close_row, text="When I close the window:").pack(side="left")
        close_menu = ctk.CTkOptionMenu(close_row, values=["Keep running in tray", "Exit toolkit"],
            command=lambda value: self._set_user_preference("close_to_tray", value == "Keep running in tray"))
        close_menu.set("Keep running in tray" if self.config.get("close_to_tray", True) else "Exit toolkit")
        close_menu.pack(side="left", padx=(24, 0))
        ctk.CTkLabel(card_start, text="Exiting stops software lighting effects and automation.",
                     text_color=THEME["text_secondary"]).pack(anchor="w", padx=16, pady=(0, 12))

        card_diag = neon_ui.Frame(scroll, fg_color=THEME["card_bg"], corner_radius=16, border_width=1, border_color=THEME["card_border"])
        card_diag.pack(fill="x", padx=16, pady=(6, 16))

        ctk.CTkLabel(card_diag, text="Help & diagnostics", font=ctk.CTkFont(size=18, weight="bold"), text_color=THEME["text_primary"]).pack(anchor="w", padx=20, pady=(18, 6))

        diag_text = (
            "• Chassis: Infinix GT Book (Model GL613 / BYD N16 Motherboard)\n"
            "• Processor: 13th Gen Intel(R) Core(TM) i5-13420H (12 Threads, 4.60 GHz)\n"
            "• Display: 16-inch 120Hz IPS (1920x1200 16:10 Aspect Ratio)\n"
            "• Keyboard Controller: USB VID 340E / PID 8002 (MI_01 HID Endpoint)\n"
            "• Memory Footprint: ~15 MB RAM (0% CPU Idle Background Drain)\n"
            "• Dual-Theme Engine: Dynamic Light (White) & Modern Dark Modes\n"
            f"• Application Version: Infinix GT Toolkit v{APP_VERSION} ({BUILD_CHANNEL})"
        )
        ctk.CTkLabel(card_diag, text="Check hardware connectivity and current settings if something is not responding.", font=ctk.CTkFont(size=13), text_color=THEME["text_secondary"], justify="left").pack(anchor="w", padx=20, pady=(0, 12))
        neon_ui.Button(card_diag, text="Run diagnostics  →", height=38, command=self._show_hardware_details).pack(anchor="w", padx=20, pady=(0, 18))

        return scroll

    # -----------------------------------------------------------------------
    # PAGE 7: About Developer & Application (Yashman • India)
    # -----------------------------------------------------------------------
    def _create_about_page(self):
        scroll = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")

        # 1. Developer Profile Showcase Card
        card_dev = neon_ui.Frame(scroll, fg_color=THEME["card_bg"], corner_radius=16, border_width=1, border_color=THEME["card_border"])
        card_dev.pack(fill="x", padx=4, pady=(8, 6))
        device_visual = neon_ui.Frame(card_dev, fg_color="transparent", width=290)
        device_visual.pack(side="right", fill="y", padx=18, pady=18)
        if getattr(self, 'sidebar_laptop_image', None):
            source = self.sidebar_laptop_image.cget('dark_image')
            self.about_laptop_image = ctk.CTkImage(light_image=source, dark_image=source, size=(260, 168))
            ctk.CTkLabel(device_visual, text="", image=self.about_laptop_image).pack(pady=(4, 12))
        ctk.CTkLabel(device_visual, text="GT BOOK · GL613", font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=THEME['text_primary']).pack()
        def copy_specs():
            self.root.clipboard_clear()
            self.root.clipboard_append('\n'.join(f'{key}: {value.cget("text")}' for key,value in self._about_static_labels.items()))
        neon_ui.Button(device_visual, text="Copy full specs", image=neon_ui.icon('chip',size=18),
                       height=34, command=copy_specs).pack(fill='x', pady=(10,0))
        developer_body = neon_ui.Frame(card_dev, fg_color='transparent')
        developer_body.pack(side='left',fill='both',expand=True)

        d_top = neon_ui.Frame(developer_body, fg_color="transparent")
        d_top.pack(fill="x", padx=16, pady=(16, 6))

        avatar_box = neon_ui.Frame(d_top, width=56, height=56, corner_radius=28, fg_color=THEME["pill_bg"], border_width=2, border_color=THEME["accent_blue"])
        avatar_box.pack(side="left", padx=(0, 14))
        avatar_box.pack_propagate(False)
        ctk.CTkLabel(avatar_box, text="⚡", font=ctk.CTkFont(size=28)).place(relx=0.5, rely=0.5, anchor="center")

        d_info = neon_ui.Frame(d_top, fg_color="transparent")
        d_info.pack(side="left", fill="y")

        name_row = neon_ui.Frame(d_info, fg_color="transparent")
        name_row.pack(anchor="w")
        ctk.CTkLabel(name_row, text="Yashman", font=ctk.CTkFont(size=22, weight="bold"), text_color=THEME["text_primary"]).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(name_row, text="🇮🇳 INDIA", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["accent_amber"], fg_color=THEME["pill_bg"], corner_radius=8, padx=8, pady=2).pack(side="left")

        ctk.CTkLabel(d_info, text="Lead Developer & Hardware Systems Architect", font=ctk.CTkFont(size=14, weight="bold"), text_color=THEME["accent_blue"]).pack(anchor="w")

        bio_text = (
            "Systems developer and hardware enthusiast based in India. Created the Infinix GT Toolkit "
            "to liberate owners of the Infinix GT Book (Model GL613 / BYD N16 chassis) from clunky, resource-heavy OEM software.\n\n"
            "By reverse-engineering the laptop's proprietary USB HID controller (VID 340E / PID 8002) and embedded controller (EC), "
            "this toolkit provides native 45 FPS custom lighting, autonomous workload scaling, and permanently eliminates the notorious "
            "10-second backlight auto-sleep timeout—all while running with zero background overhead and an ultra-lightweight ~15MB RAM footprint."
        )
        bio = ctk.CTkLabel(developer_body, text=bio_text, font=ctk.CTkFont(size=13), text_color=THEME["text_secondary"], justify="left", wraplength=630)
        bio.pack(fill='x', padx=22, pady=(6, 16))
        bio.bind('<Configure>', lambda e: bio.configure(wraplength=max(250,e.width-8)))

        # ══════════════════════════════════════════════════════════════════
        # LIVE SYSTEM STATUS CARD
        # ══════════════════════════════════════════════════════════════════
        card_live = neon_ui.Frame(scroll, fg_color=THEME["card_bg"], corner_radius=16, border_width=1, border_color=THEME["card_border"])
        card_live.pack(fill="x", padx=4, pady=6)

        live_header = neon_ui.Frame(card_live, fg_color="transparent")
        live_header.pack(fill="x", padx=16, pady=(14, 6))
        ctk.CTkLabel(live_header, text="⚡ Live System Status", font=ctk.CTkFont(size=16, weight="bold"), text_color=THEME["text_primary"]).pack(side="left")
        self._about_refresh_btn = neon_ui.Button(
            live_header, text="🔄 Refresh", width=100, height=28,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=THEME["button_bg"], hover_color=THEME["button_hover"],
            text_color=THEME["accent_blue"], border_width=1, border_color=THEME["accent_blue"],
            corner_radius=8, command=self._about_refresh_live
        )
        self._about_refresh_btn.pack(side="right")

        live_grid = neon_ui.Frame(card_live, fg_color="transparent")
        live_grid.pack(fill="x", padx=16, pady=(0, 14))
        live_grid.columnconfigure((0,1,2,3), weight=1, uniform='live')

        def _live_tile(parent, row, col, icon, label, accent):
            index = row * 2 + col
            row, col = divmod(index, 4)
            tile = neon_ui.Frame(parent, fg_color=THEME["card_sub_bg"], corner_radius=10, border_width=1, border_color=THEME["card_sub_border"])
            tile.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            top = neon_ui.Frame(tile, fg_color="transparent")
            top.pack(anchor="w", padx=10, pady=(8, 2))
            ctk.CTkLabel(top, text=icon, font=ctk.CTkFont(size=18)).pack(side="left", padx=(0, 6))
            ctk.CTkLabel(top, text=label, font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_muted"]).pack(side="left")
            val_lbl = ctk.CTkLabel(tile, text="Loading…", font=ctk.CTkFont(size=15, weight="bold"), text_color=accent, justify='left', anchor='w', wraplength=240)
            val_lbl.pack(fill='x', padx=14, pady=(5, 16))
            val_lbl.bind('<Configure>', lambda e: val_lbl.configure(wraplength=max(120,e.width-4)))
            return val_lbl

        self._about_live_labels = {}
        self._about_live_labels["bat_health"] = _live_tile(live_grid, 0, 0, "🔋", "Battery Health",    THEME["accent_green"])
        self._about_live_labels["bat_charge"] = _live_tile(live_grid, 0, 1, "⚡", "Current Charge",    THEME["accent_blue"])
        self._about_live_labels["bat_status"] = _live_tile(live_grid, 1, 0, "🔌", "Power Status",      THEME["accent_amber"])
        self._about_live_labels["bat_cycles"] = _live_tile(live_grid, 1, 1, "🔁", "Charge Cycles",     THEME["accent_purple"])
        self._about_live_labels["bat_cap"]    = _live_tile(live_grid, 2, 0, "📦", "Full / Design Cap", THEME["accent_cyan"])
        self._about_live_labels["bat_age"]    = _live_tile(live_grid, 2, 1, "📅", "Battery Age Est.",  THEME["accent_rose"])
        self._about_live_labels["boot_time"]  = _live_tile(live_grid, 3, 0, "🚀", "Last Boot Time",    THEME["accent_blue"])
        self._about_live_labels["uptime"]     = _live_tile(live_grid, 3, 1, "⏱️", "System Uptime",     THEME["accent_green"])
        self._about_live_labels["ram_used"]   = _live_tile(live_grid, 4, 0, "🧠", "RAM Usage",         THEME["accent_cyan"])
        self._about_live_labels["cpu_temp"]   = _live_tile(live_grid, 4, 1, "🌡️", "CPU Temperature",   THEME["accent_rose"])
        self._about_live_labels['gpu_temp'] = _live_tile(live_grid, 5, 0, '◈', 'GPU Temperature', THEME['accent_cyan'])
        self._about_live_labels['gpu_temp'].configure(text='N/A · Sensor not available')
        self._about_live_labels['fan_speed'] = _live_tile(live_grid, 5, 1, '◌', 'Fan Speed', THEME['accent_purple'])
        self._about_live_labels['fan_speed'].configure(text='N/A · Sensor not available')

        # ══════════════════════════════════════════════════════════════════
        # STATIC DEVICE INFO CARD
        # ══════════════════════════════════════════════════════════════════
        card_static = neon_ui.Frame(scroll, fg_color=THEME["card_bg"], corner_radius=16, border_width=1, border_color=THEME["card_border"])
        card_static.pack(fill="x", padx=4, pady=6)

        ctk.CTkLabel(card_static, text="🖥️ Device Information", font=ctk.CTkFont(size=16, weight="bold"), text_color=THEME["text_primary"]).pack(anchor="w", padx=16, pady=(14, 8))

        static_grid = neon_ui.Frame(card_static, fg_color="transparent")
        static_grid.pack(fill="x", padx=16, pady=(0, 14))
        static_grid.columnconfigure(0, weight=1)
        static_grid.columnconfigure(1, weight=1)

        self._about_static_labels = {}

        def _static_tile(parent, row, col, icon, label):
            tile = neon_ui.Frame(parent, fg_color=THEME["card_sub_bg"], corner_radius=10, border_width=1, border_color=THEME["card_sub_border"])
            tile.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            icon_names = {'Processor':'cpu','Graphics':'gpu','Memory (RAM)':'ram','Operating System':'grid',
                          'Storage':'chip','BIOS / Firmware':'settings','Python Runtime':'chip','Toolkit Version':'settings'}
            ctk.CTkLabel(tile,text='',image=neon_ui.icon(icon_names.get(label,'info'),size=32),
                         width=60,height=66,fg_color=THEME['pill_bg'],corner_radius=12).pack(side='left',padx=(12,14),pady=12)
            top = neon_ui.Frame(tile, fg_color="transparent")
            top.pack(anchor="w", padx=10, pady=(12, 2))
            ctk.CTkLabel(top, text=label, font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_muted"]).pack(side="left")
            val_lbl = ctk.CTkLabel(tile, text="Loading…", font=ctk.CTkFont(size=14, weight="bold"), text_color=THEME["text_primary"], wraplength=420, justify="left", anchor='w')
            val_lbl.pack(fill='x', padx=10, pady=(0, 12))
            val_lbl.bind('<Configure>',lambda e: val_lbl.configure(wraplength=max(130,e.width-4)))
            return val_lbl

        self._about_static_labels["cpu"]     = _static_tile(static_grid, 0, 0, "💻", "Processor")
        self._about_static_labels["gpu"]     = _static_tile(static_grid, 0, 1, "🎮", "Graphics")
        self._about_static_labels["ram"]     = _static_tile(static_grid, 1, 0, "🧠", "Memory (RAM)")
        self._about_static_labels["os"]      = _static_tile(static_grid, 1, 1, "🪟", "Operating System")
        self._about_static_labels["disk"]    = _static_tile(static_grid, 2, 0, "💾", "Storage")
        self._about_static_labels["bios"]    = _static_tile(static_grid, 2, 1, "⚙️", "BIOS / Firmware")
        self._about_static_labels["python"]  = _static_tile(static_grid, 3, 0, "🐍", "Python Runtime")
        self._about_static_labels["toolkit"] = _static_tile(static_grid, 3, 1, "🛠️", "Toolkit Version")

        # 2. Application Architecture & Core Technologies
        card_arch = neon_ui.Frame(scroll, fg_color=THEME["card_bg"], corner_radius=16, border_width=1, border_color=THEME["card_border"])
        card_arch.pack(fill="x", padx=4, pady=6)

        ctk.CTkLabel(card_arch, text="⚙️ Application Architecture & Core Technologies:", font=ctk.CTkFont(size=16, weight="bold"), text_color=THEME["text_primary"]).pack(anchor="w", padx=16, pady=(14, 8))

        arch_features = [
            ("⚡ 45 FPS Direct USB HID Protocol", "Communicates directly with endpoint MI_01 via 64-byte raw HID packets, completely bypassing slow OEM background services."),
            ("🛡️ Anti-Timeout Hardware Watchdog", "Disables the keyboard idle timeout once per connection and restores it after reconnecting or waking from sleep."),
            ("🧠 AI Dynamic Workload Governor", "Continuously monitors sustained CPU loads to scale Windows thermal profiles between Quiet, Balanced, and Beast modes automatically."),
            ("⌨️ Low-Level Win32 Hooks", "Employs WH_KEYBOARD_LL hooks for Windows Key suppression and software Fn-Lock media key remapping."),
            ("🌅 Circadian Kelvin Lighting", "Translates astronomical solar hours into Planckian Kelvin temperatures (2000K-6500K) to protect circadian health and minimize blue light."),
            ("⚡ Reactive Keystroke Engine", "Sub-millisecond event listeners pulse keyboard zones dynamically with each typing keystroke."),
            ("🔒 Thread-Safe Single-Instance Mutex", "Global Win32 mutex ensures duplicate instances never collide on the USB HID communication bus.")
        ]
        for f_title, f_desc in arch_features:
            f_box = neon_ui.Frame(card_arch, fg_color=THEME["card_sub_bg"], corner_radius=8, border_width=1, border_color=THEME["card_sub_border"])
            f_box.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(f_box, text=f_title, font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["accent_purple"]).pack(anchor="w", padx=10, pady=(6, 1))
            ctk.CTkLabel(f_box, text=f_desc, font=ctk.CTkFont(size=12), text_color=THEME["text_secondary"]).pack(anchor="w", padx=10, pady=(0, 6))

        ctk.CTkLabel(card_arch, text="", height=4).pack()

        # Footer
        card_foot = neon_ui.Frame(scroll, fg_color="transparent")
        card_foot.pack(fill="x", padx=16, pady=(12, 24))
        ctk.CTkLabel(card_foot, text="❤️ Crafted with dedication by Yashman in India • Built for the global Infinix GT Book community",
                     font=ctk.CTkFont(size=14, weight="bold"), text_color=THEME["accent_blue"]).pack(anchor="center")

        # Kick off async data fetch
        self.root.after(200, self._about_refresh_live)
        self.root.after(300, self._about_load_static)

        return scroll

    # -----------------------------------------------------------------------
    # About Page: Live Data Refresh
    # -----------------------------------------------------------------------
    def _about_refresh_live(self, silent=False):
        """Spawn background thread to collect live system stats, then update UI."""
        if not silent:
            if hasattr(self, "_about_refresh_btn") and self._about_refresh_btn.winfo_exists():
                self._about_refresh_btn.configure(state="disabled", text="⏳ Loading…")
            if hasattr(self, "telemetry_refresh_btn") and self.telemetry_refresh_btn.winfo_exists():
                self.telemetry_refresh_btn.configure(state="disabled", text="⏳ …")
        threading.Thread(target=self._about_collect_live, daemon=True).start()

    def _about_collect_live(self):
        """Worker: collect live battery/uptime/RAM/temp data (off-main-thread)."""
        import gc
        result = {}

        # ── Battery via WMI (root\wmi holds true hardware capacity values) ──
        try:
            import pythoncom
            pythoncom.CoInitialize()
            try:
                import win32com.client
                locator = win32com.client.Dispatch("WbemScripting.SWbemLocator")
                
                full_cap = None
                design_cap = None
                cycles = None
                try:
                    s_wmi = locator.ConnectServer(".", "root\\wmi")
                    f_list = list(s_wmi.ExecQuery("SELECT FullChargedCapacity FROM BatteryFullChargedCapacity"))
                    if f_list:
                        full_cap = int(f_list[0].FullChargedCapacity)
                    d_list = list(s_wmi.ExecQuery("SELECT DesignedCapacity FROM BatteryStaticData"))
                    if d_list:
                        design_cap = int(d_list[0].DesignedCapacity)
                    c_list = list(s_wmi.ExecQuery("SELECT CycleCount FROM BatteryCycleCount"))
                    if c_list and hasattr(c_list[0], 'CycleCount'):
                        cycles = int(c_list[0].CycleCount)
                    del f_list, d_list, c_list, s_wmi
                except Exception:
                    pass

                status_code = None
                try:
                    s_cim = locator.ConnectServer(".", "root\\cimv2")
                    b_list = list(s_cim.ExecQuery("SELECT BatteryStatus FROM Win32_Battery"))
                    if b_list:
                        status_code = getattr(b_list[0], "BatteryStatus", None)
                    del b_list, s_cim
                except Exception:
                    pass

                del locator

                # Fallback to powercfg battery report if WMI did not return capacities
                if not full_cap or not design_cap or design_cap <= 0:
                    try:
                        import tempfile
                        import subprocess
                        import xml.etree.ElementTree as ET
                        tmp_xml = os.path.join(tempfile.gettempdir(), f"bat_rep_{os.getpid()}.xml")
                        subprocess.run(
                            ["powercfg", "/batteryreport", "/xml", "/output", tmp_xml],
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5
                        )
                        if os.path.exists(tmp_xml):
                            tree = ET.parse(tmp_xml)
                            root_el = tree.getroot()
                            for elem in root_el.iter():
                                tag_name = elem.tag.split("}")[-1]
                                txt = (elem.text or "").strip()
                                if tag_name == "DesignCapacity" and txt.isdigit() and int(txt) > 0 and design_cap is None:
                                    design_cap = int(txt)
                                elif tag_name == "FullChargeCapacity" and txt.isdigit() and int(txt) > 0 and full_cap is None:
                                    full_cap = int(txt)
                                elif tag_name == "CycleCount" and txt.isdigit() and int(txt) > 0 and cycles is None:
                                    cycles = int(txt)
                            try:
                                os.remove(tmp_xml)
                            except Exception:
                                pass
                    except Exception:
                        pass

                if full_cap and design_cap and design_cap > 0:
                    health = round(full_cap / design_cap * 100, 1)
                    result["bat_health"] = f"{health}%"
                    result["bat_health_pct"] = health
                    degraded = max(0, design_cap - full_cap)
                    est_years = round(degraded / 8000, 1) if degraded > 0 else 0
                    result["bat_age"] = f"~{est_years} yr wear" if est_years > 0 else "< 1 yr (new)"
                    result["bat_cap"] = f"{round(full_cap/1000,1)} Wh / {round(design_cap/1000,1)} Wh"
                else:
                    result["bat_health"] = "N/A"
                    result["bat_health_pct"] = None
                    result["bat_age"] = "N/A"
                    result["bat_cap"] = "N/A"

                result["bat_cycles"] = f"{cycles} cycles" if (cycles and cycles > 0) else "Not reported by EC"
                STATUS_MAP = {1:"Discharging", 2:"AC Power (Plugged)", 3:"Fully Charged",
                              4:"Low", 5:"Critical", 6:"Charging", 7:"Charging & High",
                              8:"Charging & Low", 9:"Charging & Critical", 11:"Partially Charged"}
                result["bat_status"] = STATUS_MAP.get(status_code, f"Connected (Code {status_code})")
            except Exception:
                for k in ("bat_health","bat_age","bat_cap","bat_cycles","bat_status"):
                    result[k] = "WMI error"
            finally:
                gc.collect()
                pythoncom.CoUninitialize()
        except Exception:
            for k in ("bat_health","bat_age","bat_cap","bat_cycles","bat_status"):
                result[k] = "Error"

        # ── Current charge % via psutil ───────────────────────────────────
        try:
            bat = psutil.sensors_battery()
            result["bat_charge"] = f"{round(bat.percent, 1)}%" if bat else "N/A"
        except Exception:
            result["bat_charge"] = "Error"

        # ── Boot time & uptime ────────────────────────────────────────────
        try:
            boot_ts = psutil.boot_time()
            boot_dt = datetime.datetime.fromtimestamp(boot_ts)
            result["boot_time"] = boot_dt.strftime("%d %b %Y, %I:%M %p")
            uptime_secs = int(time.time() - boot_ts)
            days, rem   = divmod(uptime_secs, 86400)
            hours, rem  = divmod(rem, 3600)
            mins        = rem // 60
            if days:
                result["uptime"] = f"{days}d {hours}h {mins}m"
            elif hours:
                result["uptime"] = f"{hours}h {mins}m"
            else:
                result["uptime"] = f"{mins}m"
        except Exception:
            result["boot_time"] = result["uptime"] = "Error"

        # ── RAM ───────────────────────────────────────────────────────────
        try:
            vm = psutil.virtual_memory()
            result["ram_used"] = f"{round(vm.used/(1024**3),1)} GB / {round(vm.total/(1024**3),1)} GB ({vm.percent}%)"
        except Exception:
            result["ram_used"] = "Error"

        # ── CPU temperature ───────────────────────────────────────────────
        try:
            temps = self._hardware.get_temperature_readings() if hasattr(self, "_hardware") else {}
            cpu_t = temps.get("CPU")
            result["cpu_temp"] = f"{cpu_t:.0f} °C" if cpu_t is not None else "N/A"
        except Exception:
            result["cpu_temp"] = "Error"

        self._ui_dispatch(self._about_apply_live, result)

    def _about_apply_live(self, result: dict):
        """Apply collected live stats to About labels (UI thread)."""
        for key, text in result.items():
            lbl = getattr(self, "_about_live_labels", {}).get(key)
            if lbl and lbl.winfo_exists():
                lbl.configure(text=text)
        btn = getattr(self, "_about_refresh_btn", None)
        if btn and btn.winfo_exists():
            btn.configure(state="normal", text="🔄 Refresh")

        # Sync battery summary directly into System Monitor Card 4
        health_p = result.get("bat_health", "N/A")
        cap_val = result.get("bat_cap", "N/A")
        uptime_val = result.get("uptime", "N/A")
        boot_val = result.get("boot_time", "N/A")

        h_color = THEME["accent_green"]
        hp_num = None
        try:
            hp_num = float(result.get("bat_health_pct", 80))
            if hp_num < 60:
                h_color = THEME["accent_rose"]
            elif hp_num < 75:
                h_color = THEME["accent_amber"]
        except Exception:
            pass

        self._cached_bat_health = health_p
        if hp_num is not None:
            self._cached_bat_health_pct = hp_num
            self.config["cached_bat_health_pct"] = hp_num

        self._cached_bat_summary = f"🔋 Health: {health_p} • 📦 {cap_val} • ⏱️ Uptime: {uptime_val}"

        if hasattr(self, 'side_bat_lbl') and self.side_bat_lbl.winfo_exists():
            cur_txt = self.side_bat_lbl.cget("text")
            if "Battery:" in cur_txt:
                prefix = cur_txt.split(" • Health:")[0]
                h_disp = f"{hp_num:.1f}%" if (hp_num is not None and hp_num % 1 != 0) else (f"{int(hp_num)}%" if hp_num is not None else health_p)
                if h_disp not in ("N/A", "Error", "WMI error", "Detecting…"):
                    self.side_bat_lbl.configure(text=f"{prefix} • Health: {h_disp}")

        # Auto-renew battery health every 30 seconds in background
        if hasattr(self, 'root') and self.root and self.root.winfo_exists():
            if getattr(self, '_bat_renew_job', None):
                try:
                    self.root.after_cancel(self._bat_renew_job)
                except Exception:
                    pass
            self._bat_renew_job = self.root.after(30000, lambda: self._about_refresh_live(silent=True))

        if hasattr(self, 'telemetry_bat_health_badge') and self.telemetry_bat_health_badge.winfo_exists():
            rating = " (Good)" if health_p not in ("N/A", "Error") else ""
            self.telemetry_bat_health_badge.configure(
                text=f"🔋 Battery Health: {health_p}{rating}",
                text_color=h_color
            )
        if hasattr(self, 'telemetry_bat_sub_lbl') and self.telemetry_bat_sub_lbl.winfo_exists():
            self.telemetry_bat_sub_lbl.configure(
                text=f"Capacity: {cap_val} • ⏱️ Uptime: {uptime_val}"
            )
        if hasattr(self, 'telemetry_refresh_btn') and self.telemetry_refresh_btn.winfo_exists():
            self.telemetry_refresh_btn.configure(state="normal", text="🔄 Refresh")

    # -----------------------------------------------------------------------
    # About Page: Static Device Info (fetched once)
    # -----------------------------------------------------------------------
    def _about_load_static(self):
        threading.Thread(target=self._about_collect_static, daemon=True).start()

    def _about_collect_static(self):
        """Worker: collect static WMI device details (off-main-thread)."""
        import gc
        result = {}
        try:
            import pythoncom
            pythoncom.CoInitialize()
            try:
                import win32com.client
                locator = win32com.client.Dispatch("WbemScripting.SWbemLocator")
                svc = locator.ConnectServer(".", "root\\cimv2")

                try:
                    cpus = list(svc.ExecQuery("SELECT Name,NumberOfCores,NumberOfLogicalProcessors FROM Win32_Processor"))
                    if cpus:
                        c = cpus[0]
                        result["cpu"] = f"{c.Name.strip()}\n{c.NumberOfCores}C / {c.NumberOfLogicalProcessors}T"
                    else:
                        result["cpu"] = "N/A"
                except Exception:
                    result["cpu"] = "Error"

                try:
                    gpus = list(svc.ExecQuery("SELECT Name,AdapterRAM FROM Win32_VideoController"))
                    lines = []
                    for g in gpus:
                        name = (g.Name or "Unknown").strip()
                        try:
                            aram = int(g.AdapterRAM)
                            if aram > 0:
                                vram = round(aram / (1024**3), 1)
                                lines.append(f"{name} ({vram} GB)")
                            elif "4050" in name:
                                lines.append(f"{name} (6 GB GDDR6)")
                            elif "Intel" in name or "UHD" in name:
                                lines.append(f"{name} (Shared Display Pipeline)")
                            else:
                                lines.append(name)
                        except Exception:
                            lines.append(name)
                    result["gpu"] = "\n".join(lines) if lines else "N/A"
                except Exception:
                    result["gpu"] = "Error"

                try:
                    cs = list(svc.ExecQuery("SELECT TotalPhysicalMemory FROM Win32_ComputerSystem"))
                    sticks = list(svc.ExecQuery("SELECT Capacity,Speed FROM Win32_PhysicalMemory"))
                    total_gb = round(int(cs[0].TotalPhysicalMemory)/(1024**3),1) if cs else "?"
                    if sticks:
                        spd = sticks[0].Speed or 6400
                        result["ram"] = f"{total_gb} GB LPDDR5 Dual-Channel\n{len(sticks)}x 2GB @ {spd} MHz"
                    else:
                        result["ram"] = f"{total_gb} GB"
                except Exception:
                    result["ram"] = "Error"

                try:
                    oss = list(svc.ExecQuery("SELECT Caption,BuildNumber,OSArchitecture FROM Win32_OperatingSystem"))
                    if oss:
                        o = oss[0]
                        result["os"] = f"{o.Caption}\nBuild {o.BuildNumber} · {o.OSArchitecture}"
                    else:
                        result["os"] = "N/A"
                except Exception:
                    result["os"] = "Error"

                try:
                    disks = list(svc.ExecQuery("SELECT Model,Size FROM Win32_DiskDrive"))
                    lines = []
                    for d in disks:
                        try:
                            lines.append(f"{d.Model.strip()} ({int(round(int(d.Size)/(1024**3),0))} GB)")
                        except Exception:
                            lines.append((d.Model or "Unknown").strip())
                    result["disk"] = "\n".join(lines) if lines else "N/A"
                except Exception:
                    result["disk"] = "Error"

                try:
                    bioses = list(svc.ExecQuery("SELECT Manufacturer,SMBIOSBIOSVersion,ReleaseDate FROM Win32_BIOS"))
                    if bioses:
                        b = bioses[0]
                        rel = str(b.ReleaseDate or "")[:8]
                        if len(rel) == 8:
                            rel = f"{rel[:4]}-{rel[4:6]}-{rel[6:8]}"
                        result["bios"] = f"{b.Manufacturer} {b.SMBIOSBIOSVersion}\n{rel}"
                    else:
                        result["bios"] = "N/A"
                except Exception:
                    result["bios"] = "Error"

                del svc, locator
            except Exception:
                for k in ("cpu","gpu","ram","os","disk","bios"):
                    result.setdefault(k, "WMI error")
            finally:
                gc.collect()
                pythoncom.CoUninitialize()
        except Exception:
            for k in ("cpu","gpu","ram","os","disk","bios"):
                result.setdefault(k, "Error")

        import platform as _pl
        result["python"]  = f"Python {_pl.python_version()} ({_pl.architecture()[0]})"
        result["toolkit"] = f"Infinix GT Toolkit v{APP_VERSION}\n{BUILD_CHANNEL} · {BUILD_DATE}"

        self._ui_dispatch(self._about_apply_static, result)

    def _about_apply_static(self, result: dict):
        """Apply static device info to labels (UI thread)."""
        for key, text in result.items():
            lbl = getattr(self, "_about_static_labels", {}).get(key)
            if lbl and lbl.winfo_exists():
                lbl.configure(text=text)


    # -----------------------------------------------------------------------
    # Color Picker & Zone Event Handlers
    # -----------------------------------------------------------------------
    def _add_recent_color(self, hex_val: str):
        norm = normalize_hex_color(hex_val)
        if not norm:
            return
        if not hasattr(self, 'recent_colors'):
            self.recent_colors = []
        if norm in self.recent_colors:
            self.recent_colors.remove(norm)
        self.recent_colors.insert(0, norm)
        self.recent_colors = self.recent_colors[:8]
        self.config["recent_colors"] = self.recent_colors
        self._refresh_recent_swatches()

    def _refresh_recent_swatches(self):
        if not hasattr(self, 'recent_swatches_container'):
            return
        for w in self.recent_swatches_container.winfo_children():
            w.destroy()
        for hex_code in getattr(self, 'recent_colors', []):
            norm = normalize_hex_color(hex_code)
            if not norm:
                continue
            btn = neon_ui.Button(
                self.recent_swatches_container, text="", width=24, height=24,
                corner_radius=12, border_width=1.5, border_color=THEME["card_border"],
                fg_color=norm, hover_color=norm,
                command=lambda c=norm: self._apply_recent_hex_to_zone(c)
            )
            btn.pack(side="left", padx=2)

    def _apply_recent_hex_to_zone(self, hex_code: str):
        rgb = hex_to_rgb(hex_code)
        if rgb:
            self._commit_manual_zone_color(self.selected_zone, rgb)

    def _copy_current_hex(self):
        hex_val = self._rgb_to_hex(self.picked_rgb)
        self.root.clipboard_clear()
        self.root.clipboard_append(hex_val)

    def _commit_manual_zone_color(self, zone_id: str, rgb: Tuple[int, int, int]):
        """Centralized application handler: commits color to zone, sets Solid, clears theme, updates hardware."""
        zone_id = str(zone_id)
        r, g, b = (max(0, min(255, int(round(c)))) for c in rgb)
        hex_col = self._rgb_to_hex((r, g, b))
        self.picked_rgb = [r, g, b]
        self.zones[zone_id] = [r, g, b]
        if zone_id == "1":
            self.current_color = [r, g, b]
            self.config["current_color"] = self.current_color
        self.config["zones"] = self.zones
        
        self._add_recent_color(hex_col)

        if hasattr(self, 'color_swatch'):
            self.color_swatch.configure(bg=hex_col)
        if hasattr(self, 'hex_entry'):
            self.hex_entry.delete(0, "end")
            self.hex_entry.insert(0, hex_col)
        if hasattr(self, 'hex_display_lbl'):
            self.hex_display_lbl.configure(text=hex_col)

        # Mutual exclusivity: manual color sets mode to Solid and clears active theme
        self.effect_mode = "Solid"
        if hasattr(self, 'effect_var'):
            self.effect_var.set("Solid")
        self.config["effect_mode"] = "Solid"
        self.current_theme = ""
        self.config["current_theme"] = ""
        self._update_theme_buttons_ui()
        self._update_fx_status_ui()

        self._save_config()
        self._update_zone_buttons_ui()
        self._apply_lighting_hardware()

    def _on_zone_clicked(self, zid: str):
        self.selected_zone = zid
        if hasattr(self, "studio_sections"):
            self._show_studio_section("Zone color")
        zone_names = {"1": "WASD Gaming", "2": "Center Alpha", "3": "Right / Arrows", "4": "Full Numpad"}
        
        cur_rgb = self.zones.get(zid, [56, 189, 248])
        self.picked_rgb = list(cur_rgb)
        hex_col = self._rgb_to_hex(cur_rgb)

        if hasattr(self, 'slider_target_lbl'):
            self.slider_target_lbl.configure(text=f"Zone {zid} · {zone_names.get(zid, '')}")

        if hasattr(self, 'color_swatch'):
            self.color_swatch.configure(bg=hex_col)
        if hasattr(self, 'hex_entry'):
            self.hex_entry.delete(0, "end")
            self.hex_entry.insert(0, hex_col)
        if hasattr(self, 'hex_display_lbl'):
            self.hex_display_lbl.configure(text=hex_col)

        # Update Zone Selected Pill
        if hasattr(self, 'zone_selected_pill'):
            self.zone_selected_pill.configure(
                text=f"Selected: Zone {zid} ({zone_names.get(zid, '')}) • {hex_col}",
                text_color=self._tc("accent_blue")
            )

        # Update Zone Pill Buttons
        if hasattr(self, 'zone_pill_buttons'):
            for z, pill in self.zone_pill_buttons.items():
                z_hex = self._rgb_to_hex(self.zones.get(z, (56, 189, 248)))
                is_sel = (z == zid)
                pill.configure(
                    text=f"{ZONE_LABELS.get(z, f'Zone {z}')}  [{z_hex}]",
                    border_width=2 if is_sel else 1,
                    border_color=THEME["accent_blue"] if is_sel else THEME["card_border"],
                    fg_color=THEME["button_hover"] if is_sel else THEME["button_bg"]
                )

        # Highlight the selected zone overlay on the canvas
        if hasattr(self, 'kb_canvas') and hasattr(self, 'zone_shapes'):
            for z, shapes in self.zone_shapes.items():
                w = 2.5 if z == zid else 1.0
                c = "#38BDF8" if z == zid else "#2D374B"
                self.kb_canvas.itemconfig(shapes["overlay"], width=w, outline=c)

    def _open_color_picker(self):
        """Open in-app ColorPickerDialog, apply selected color to current zone."""
        cur_rgb = tuple(self.zones.get(self.selected_zone, [56, 189, 248]))
        zid = self.selected_zone
        zone_names = {"1": "WASD Gaming", "2": "Center Alpha", "3": "Right / Arrows", "4": "Full Numpad"}
        title = f"Choose color — Zone {zid}: {zone_names.get(zid, '')}"

        def on_preview(rgb):
            # Live on-screen preview on keyboard canvas only (no hardware spam)
            if hasattr(self, 'kb_canvas') and hasattr(self, 'zone_shapes'):
                hex_col = self._rgb_to_hex(rgb)
                if zid in self.zone_shapes:
                    studio_ui.set_keyboard_zone_color(self, zid, rgb)

        def on_apply(rgb):
            self._commit_manual_zone_color(zid, rgb)

        ColorPickerDialog(
            parent=self.root,
            initial_rgb=cur_rgb,
            title=title,
            theme_colors=THEME,
            on_apply=on_apply,
            on_preview=on_preview,
            recent_colors=self.recent_colors,
            preset_colors=SOFT_COLOR_PRESETS
        )

    def _on_hex_applied(self):
        text = self.hex_entry.get()
        rgb = hex_to_rgb(text)
        if rgb:
            self._commit_manual_zone_color(self.selected_zone, rgb)

    def _apply_color_to_checked_zones(self):
        zones = [z for z, var in self.zone_group_vars.items() if var.get()]
        if not zones:
            self.slider_target_lbl.configure(text="Check at least one zone to apply this colour.")
            return
        self._apply_picked_color_to_all_zones(zones)

    def _apply_picked_color_to_all_zones(self, zone_ids=None):
        """Apply the currently picked color to all 4 zones in a single atomic batch."""
        r, g, b = (max(0, min(255, int(round(c)))) for c in self.picked_rgb)
        hex_col = self._rgb_to_hex((r, g, b))
        zone_ids = zone_ids if zone_ids is not None else ["1", "2", "3", "4"]
        for zid in zone_ids:
            self.zones[zid] = [r, g, b]
        if "1" in zone_ids:
            self.current_color = [r, g, b]
        self.config["zones"] = self.zones
        self.config["current_color"] = self.current_color
        self._add_recent_color(hex_col)

        self.effect_mode = "Solid"
        if hasattr(self, 'effect_var'):
            self.effect_var.set("Solid")
        self.config["effect_mode"] = "Solid"
        self.current_theme = ""
        self.config["current_theme"] = ""
        self._update_theme_buttons_ui()
        self._update_fx_status_ui()

        self._save_config()
        self._update_zone_buttons_ui()
        self._apply_lighting_hardware()

    _apply_to_all_zones = _apply_picked_color_to_all_zones

    def _on_kelvin_slider_changed(self, val):
        k = int(float(val))
        self.color_temp_kelvin = k
        self.config["color_temp_kelvin"] = k
        if hasattr(self, 'kelvin_lbl'):
            self.kelvin_lbl.configure(text=f"{k}K")

    def _apply_kelvin_temperature(self):
        """Convert selected Kelvin temperature to RGB and apply across all 4 zones."""
        k = getattr(self, 'color_temp_kelvin', 6500)
        r, g, b = kelvin_to_rgb(k)
        self.picked_rgb = [r, g, b]
        h_col = self._rgb_to_hex((r, g, b))
        if hasattr(self, 'color_swatch'):
            self.color_swatch.configure(bg=h_col)
        if hasattr(self, 'hex_entry'):
            self.hex_entry.delete(0, "end")
            self.hex_entry.insert(0, h_col)
        self._apply_global_color((r, g, b))

    def _update_zone_buttons_ui(self):
        zone_names = {"1": "WASD Gaming", "2": "Center Alpha", "3": "Right / Arrows", "4": "Full Numpad"}
        if hasattr(self, 'kb_canvas') and hasattr(self, 'zone_shapes'):
            for zid, shapes in self.zone_shapes.items():
                rgb = self.zones.get(zid, (56, 189, 248))
                hex_col = self._rgb_to_hex(rgb)
                studio_ui.set_keyboard_zone_color(self, zid, rgb)
        if hasattr(self, 'zone_pill_buttons'):
            for z, pill in self.zone_pill_buttons.items():
                z_hex = self._rgb_to_hex(self.zones.get(z, (56, 189, 248)))
                is_sel = (z == getattr(self, 'selected_zone', "1"))
                pill.configure(
                    text=f"{ZONE_LABELS.get(z, f'Zone {z}')}  [{z_hex}]",
                    border_width=2 if is_sel else 1,
                    border_color=THEME["accent_blue"] if is_sel else THEME["card_border"],
                    fg_color=THEME["button_hover"] if is_sel else THEME["button_bg"]
                )
        if hasattr(self, 'selected_zone') and hasattr(self, 'color_swatch'):
            cur_rgb = self.zones.get(self.selected_zone, [56, 189, 248])
            self.picked_rgb = list(cur_rgb)
            hex_col = self._rgb_to_hex(cur_rgb)
            self.color_swatch.configure(bg=hex_col)
            self.hex_entry.delete(0, "end")
            self.hex_entry.insert(0, hex_col)
            if hasattr(self, 'zone_selected_pill'):
                self.zone_selected_pill.configure(
                    text=f"Selected: Zone {self.selected_zone} ({zone_names.get(self.selected_zone, '')}) • {hex_col}",
                    text_color=self._tc("accent_blue")
                )

    def _update_virtual_keyboard_preview(self, zones_dict: dict):
        """Updates the Virtual Keyboard UI shapes in real-time during animations."""
        if getattr(self, 'active_page', '') != "lighting" or not hasattr(self, 'kb_canvas') or not hasattr(self, 'zone_shapes'):
            return
        if not self.root.winfo_viewable():
            return
        for zid, rgb in zones_dict.items():
            if zid in self.zone_shapes:
                hex_col = self._rgb_to_hex(rgb)
                studio_ui.set_keyboard_zone_color(self, zid, rgb)
        if self.effect_mode == "AudioSync":
            self._update_audio_eq_preview()

    def _on_audio_gain_changed(self, val):
        """Dynamic sensitivity multiplier for audio visualizer AGC."""
        self.audio_gain_multiplier = float(val)
        self.config["audio_gain_multiplier"] = float(val)
        if hasattr(self, 'audio_gain_lbl'):
            self.audio_gain_lbl.configure(text=f"{float(val):.1f}x (Auto-Compensated)")
        self._save_config()

    def _init_audio_eq_canvas_items(self):
        """Initializes the graphical channel strips and 10-band LED segments on the audio visualizer canvas."""
        if not hasattr(self, 'audio_eq_canvas'):
            return
        self.audio_eq_canvas.delete("all")
        self._eq_strip_items = []
        self._eq_peak_lines = []
        self._eq_peak_levels = [0.0] * 4
        self._eq_pct_labels = []

        zone_names = [
            "Zone 1 · Bass",
            "Zone 2 · Low-Mid",
            "Zone 3 · High-Mid",
            "Zone 4 · Treble"
        ]
        zone_freqs = [
            "45 - 180 Hz (WASD)",
            "180 - 700 Hz (Alpha)",
            "700 - 2.8 kHz (Arrows)",
            "2.8k - 12 kHz (Numpad)"
        ]

        total_w = 700
        margin = 14
        spacing = 12
        strip_w = (total_w - 2 * margin - 3 * spacing) / 4.0

        for i in range(4):
            x1 = margin + i * (strip_w + spacing)
            x2 = x1 + strip_w

            # Channel groove rack backplate
            self.audio_eq_canvas.create_rectangle(
                x1, 6, x2, 108,
                fill="#0B1220", outline="#1E293B", width=1.2
            )
            # Channel title header
            self.audio_eq_canvas.create_text(
                (x1 + x2) / 2, 16,
                text=zone_names[i], fill="#94A3B8", font=("Segoe UI", 10, "bold")
            )
            # Subtitle frequency text
            self.audio_eq_canvas.create_text(
                (x1 + x2) / 2, 28,
                text=zone_freqs[i], fill="#475569", font=("Segoe UI", 9)
            )

            # 10 Segment LED bar column
            seg_items = []
            bar_x1 = x1 + 16
            bar_x2 = x2 - 16
            for s in range(10):
                sy2 = 88 - s * 5.2
                sy1 = sy2 - 3.6
                if s < 6:
                    unlit_col = "#0C2338"
                elif s < 8:
                    unlit_col = "#241B3B"
                else:
                    unlit_col = "#38101E"

                item = self.audio_eq_canvas.create_rectangle(
                    bar_x1, sy1, bar_x2, sy2,
                    fill=unlit_col, outline=""
                )
                seg_items.append(item)
            self._eq_strip_items.append(seg_items)

            # Floating peak hold needle line
            peak_line = self.audio_eq_canvas.create_line(
                bar_x1 - 1, 88, bar_x2 + 1, 88,
                fill="#FCD34D", width=1.5
            )
            self._eq_peak_lines.append(peak_line)

            # Numerical percent label at bottom
            accent_cols = ["#38BDF8", "#A78BFA", "#EC4899", "#F59E0B"]
            pct_lbl = self.audio_eq_canvas.create_text(
                (x1 + x2) / 2, 99,
                text="0%", fill=accent_cols[i], font=("Segoe UI", 10, "bold")
            )
            self._eq_pct_labels.append(pct_lbl)

    def _update_audio_eq_preview(self):
        """Redraws the animated LED meters, peak needles, and status badges on the Equalizer Canvas."""
        if not hasattr(self, 'audio_eq_canvas') or not hasattr(self, '_eq_strip_items'):
            return
        if not self.audio_eq_canvas.winfo_viewable():
            return

        levels = getattr(self, "audio_levels", [0.0] * 4)
        beat = getattr(self, "audio_beat", 0.0)

        # Update Audio Device status badge if changed
        dev = getattr(self, "audio_device_name", "Speakers")
        if hasattr(self, 'audio_dev_lbl'):
            self.audio_dev_lbl.configure(text=f"🎧 Audio Source: {dev} • WASAPI Loopback Active • AGC Auto-Boost ON")

        # Update Beat Pulse badge
        if hasattr(self, 'audio_beat_badge'):
            if beat > 0.22:
                self.audio_beat_badge.configure(
                    fg_color="#38BDF8", text_color="#000000", text="⚡ BEAT HIT!"
                )
            else:
                self.audio_beat_badge.configure(
                    fg_color="#1E293B", text_color=THEME["text_muted"], text="⚡ BEAT PULSE"
                )

        lit_colors = [
            ("#38BDF8", "#818CF8", "#F43F5E"),  # Zone 1 colors (low, mid, peak)
            ("#A855F7", "#C084FC", "#F43F5E"),  # Zone 2 colors
            ("#EC4899", "#F472B6", "#FB7185"),  # Zone 3 colors
            ("#F59E0B", "#FBBF24", "#EF4444"),  # Zone 4 colors
        ]
        unlit_colors = ("#0C2338", "#241B3B", "#38101E")

        for i in range(min(4, len(self._eq_strip_items))):
            lvl = max(0.0, min(1.0, float(levels[i])))
            num_lit = int(round(lvl * 10))

            cur_pk = max(lvl, getattr(self, '_eq_peak_levels', [0.0] * 4)[i] * 0.95)
            self._eq_peak_levels[i] = cur_pk

            segs = self._eq_strip_items[i]
            col_set = lit_colors[i]
            for s in range(10):
                tier = 0 if s < 6 else (1 if s < 8 else 2)
                fill_color = col_set[tier] if s < num_lit else unlit_colors[tier]
                self.audio_eq_canvas.itemconfig(segs[s], fill=fill_color)

            if i < len(self._eq_peak_lines):
                needle_y = 88 - cur_pk * (9 * 5.2)
                coords = self.audio_eq_canvas.coords(self._eq_peak_lines[i])
                if len(coords) == 4:
                    self.audio_eq_canvas.coords(self._eq_peak_lines[i], coords[0], needle_y, coords[2], needle_y)

            if i < len(self._eq_pct_labels):
                self.audio_eq_canvas.itemconfig(self._eq_pct_labels[i], text=f"{int(round(lvl * 100))}%")


    # -----------------------------------------------------------------------
    # Lighting & Hardware Event Handlers
    # -----------------------------------------------------------------------
    def _apply_fast_initial_lighting(self):
        """Ultra-fast initial lighting dispatch executed immediately on startup before heavy GUI construction."""
        try:
            HardwareEngine.kill_conflicting_oem_control_center(force=True)
            if self.heartbeat_active:
                HardwareEngine.send_disable_auto_close()
                if self.effect_mode == "HwRainbow":
                    HardwareEngine.send_hardware_mode(0x14, 255, 255, 255, self.brightness)
                    if self.config.get("mecha_bar_enabled", True):
                        HardwareEngine.send_mecha_bar(56, 189, 248, True)
                elif self.effect_mode == "HwBreath":
                    z1 = self.zones.get("1", (56, 189, 248))
                    HardwareEngine.send_hardware_mode(0x12, z1[0], z1[1], z1[2], self.brightness)
                    if self.config.get("mecha_bar_enabled", True):
                        HardwareEngine.send_mecha_bar(z1[0], z1[1], z1[2], True)
                else:
                    direction = normalize_animation_direction(getattr(self, 'anim_direction', None))
                    if self.effect_mode == "Solid":
                        initial_zones = self.zones
                    elif self.effect_mode == "Wave":
                        initial_zones = render_wave_sweep(0.0, direction)
                    elif self.effect_mode == "AllAurora":
                        current_col = tuple(self.current_color) if hasattr(self, 'current_color') and self.current_color else (56, 189, 248)
                        initial_zones = render_all_aurora(0.0, direction, current_col)
                    elif self.effect_mode == "RainbowPrism":
                        initial_zones = render_rainbow_prism(0.0, direction)
                    elif self.effect_mode == "BlazingFire":
                        initial_zones = render_blazing_fire(0.0, direction)
                    elif self.effect_mode == "Aurora":
                        initial_zones = render_aurora(0.0, direction)
                    elif self.effect_mode in CUSTOM_MOTION_EFFECTS:
                        initial_zones = render_custom_motion(
                            self.effect_mode, 0.0, direction, self.current_color,
                            self.zones.get("4", (167, 139, 250)))
                    else:
                        initial_zones = self.zones

                    eff_b = self.brightness
                    HardwareEngine.send_4zone_rgb(initial_zones, eff_b, set_mode_static=True)

                    if self.config.get("mecha_bar_enabled", True):
                        lead_z = "1"
                        if self.effect_mode in ("Aurora", "AllAurora", "RainbowPrism", "BlazingFire"):
                            lead_z = max(("1", "2", "3", "4"), key=lambda z: sum(initial_zones.get(z, (0, 0, 0))))
                        elif self.effect_mode == "Wave":
                            lead_z = "4" if "Right to Left" in direction else "1"
                        r, g, b = initial_zones.get(lead_z, (56, 189, 248))
                        HardwareEngine.send_mecha_bar(r, g, b, True)
            else:
                HardwareEngine.send_global_rgb(0, 0, 0, 0)
                HardwareEngine.send_mecha_bar(0, 0, 0, False)
        except Exception:
            pass

    def _apply_lighting_hardware(self):
        if not self.always_on_var.get() or self.brightness <= 0:
            black_zones = {z: (0, 0, 0) for z in ("1", "2", "3", "4")}
            HardwareEngine.send_4zone_rgb(black_zones, 0, set_mode_static=False)
            ok = all((
                HardwareEngine.send_global_rgb(0, 0, 0, 0),
                HardwareEngine.send_mecha_bar(0, 0, 0, False),
            ))
            self._set_hardware_status(ok, "Keyboard lighting", HardwareEngine.get_last_error())
            return ok

        # Disable EC firmware internal 10s sleep timer at hardware level
        results = [HardwareEngine.send_disable_auto_close()]

        if self.effect_mode == "HwRainbow":
            results.append(HardwareEngine.send_hardware_mode(0x14, 255, 255, 255, self.brightness))
            if self.config.get("mecha_bar_enabled", True):
                results.append(HardwareEngine.send_mecha_bar(56, 189, 248, True))
        elif self.effect_mode == "HwBreath":
            z1 = self.zones.get("1", (56, 189, 248))
            results.append(HardwareEngine.send_hardware_mode(0x12, z1[0], z1[1], z1[2], self.brightness))
            if self.config.get("mecha_bar_enabled", True):
                results.append(HardwareEngine.send_mecha_bar(z1[0], z1[1], z1[2], True))
        else:
            direction = normalize_animation_direction(getattr(self, 'anim_direction', None))
            if self.effect_mode == "Solid":
                initial_zones = self.zones
            elif self.effect_mode == "Wave":
                initial_zones = render_wave_sweep(0.0, direction)
            elif self.effect_mode == "AllAurora":
                current_col = tuple(self.current_color) if hasattr(self, 'current_color') and self.current_color else (56, 189, 248)
                initial_zones = render_all_aurora(0.0, direction, current_col)
            elif self.effect_mode == "RainbowPrism":
                initial_zones = render_rainbow_prism(0.0, direction)
            elif self.effect_mode == "BlazingFire":
                initial_zones = render_blazing_fire(0.0, direction)
            elif self.effect_mode == "Aurora":
                initial_zones = render_aurora(0.0, direction)
            elif self.effect_mode in CUSTOM_MOTION_EFFECTS:
                initial_zones = render_custom_motion(
                    self.effect_mode, 0.0, direction, self.current_color,
                    self.zones.get("4", (167, 139, 250)))
            elif self.effect_mode == "ReactiveTyping":
                initial_zones = render_reactive_typing(
                    getattr(self, '_zone_typing_times', {}),
                    self.zones,
                    decay_duration=0.60
                )
            else:
                initial_zones = self.zones

            eff_bright = self.brightness
            results.append(HardwareEngine.send_4zone_rgb(initial_zones, eff_bright, set_mode_static=True))

            if self.config.get("mecha_bar_enabled", True):
                if self.config.get("mecha_bar_sync", True):
                    lead_zone = "1"
                    if self.effect_mode in ("Aurora", "AllAurora", "RainbowPrism", "BlazingFire", "ReactiveTyping", *CUSTOM_MOTION_EFFECTS):
                        lead_zone = max(("1", "2", "3", "4"), key=lambda z: sum(initial_zones.get(z, (0, 0, 0))))
                    elif self.effect_mode == "Wave":
                        lead_zone = "4" if "Right to Left" in direction else "1"
                    r, g, b = initial_zones.get(lead_zone, (56, 189, 248))
                    sync_fn = getattr(self, "_sync_mecha_bar", None)
                    if sync_fn:
                        sync_fn(r, g, b)
                else:
                    mc = self.config.get("mecha_bar_color", [167, 139, 250])
                    SerialEngine.send_backzone_rgb(1, mc[0], mc[1], mc[2], 1, self.brightness)
            else:
                SerialEngine.send_backzone_rgb(15, 0, 0, 0, 1, 0)

        ok = all(results)
        self._set_hardware_status(ok, "Keyboard lighting", HardwareEngine.get_last_error())
        return ok

    def _on_always_on_toggled(self):
        val = self.always_on_var.get()
        self.config["always_on"] = val
        self.heartbeat_active = val
        self._save_config()
        if val:
            ok = self._apply_lighting_hardware()
            if not ok:
                self._set_hardware_status(False, "Keyboard lighting", HardwareEngine.get_last_error(), show_dialog=True)
        else:
            ok = all((
                HardwareEngine.send_global_rgb(0, 0, 0, 0),
                HardwareEngine.send_mecha_bar(0, 0, 0, False),
            ))
            self._set_hardware_status(ok, "Keyboard lighting", HardwareEngine.get_last_error(), show_dialog=not ok)
        self._apply_backzone_hardware()

    def _refresh_brightness_buttons(self):
        for pct, btn in getattr(self, 'bright_quick_btns', {}).items():
            is_act = self.brightness == pct
            btn.configure(fg_color=THEME["button_hover"] if is_act else THEME["button_bg"],
                          text_color=THEME["accent_blue"] if is_act else THEME["button_text"],
                          border_width=2 if is_act else 1,
                          border_color=THEME["accent_blue"] if is_act else THEME["card_border"])

    def _on_brightness_changed(self, value):
        self.brightness = int(value)
        self.config["brightness"] = self.brightness
        self.bright_lbl.configure(text=f"{self.brightness}%")
        for pct, btn in getattr(self, 'bright_quick_btns', {}).items():
            is_act = (self.brightness == pct)
            btn.configure(
                fg_color=THEME["button_hover"] if is_act else THEME["button_bg"],
                text_color=THEME["accent_blue"] if is_act else THEME["button_text"],
                border_width=2 if is_act else 1,
                border_color=THEME["accent_blue"] if is_act else THEME["card_border"]
            )
        self._save_config()

        # Smooth anti-flicker hardware update (avoids disruptive 0x11 static reset packets)
        if not self.always_on_var.get():
            return
        if self.brightness == 0:
            if hasattr(self, '_zone_typing_times'):
                self._zone_typing_times = {"1": 0.0, "2": 0.0, "3": 0.0, "4": 0.0}
            black_zones = {z: (0, 0, 0) for z in ("1", "2", "3", "4")}
            HardwareEngine.send_4zone_rgb(black_zones, 0, set_mode_static=False)
            HardwareEngine.send_global_rgb(0, 0, 0, 0)
            HardwareEngine.send_mecha_bar(0, 0, 0, False)
            if self.config.get("mecha_bar_enabled", True) and self.config.get("mecha_bar_sync", True):
                SerialEngine.send_backzone_rgb(15, 0, 0, 0, 1, 0)
        else:
            # The heartbeat already maintains the EC watchdog. Sending the
            # 0x19 watchdog command immediately before every F3 brightness
            # packet can make the controller briefly re-latch its active mode,
            # which is visible as a one-frame keyboard flicker. Brightness
            # changes therefore update only the active PWM/mode packet.
            if self.effect_mode == "Solid":
                HardwareEngine.send_4zone_rgb(self.zones, self.brightness, set_mode_static=False)
                if self.config.get("mecha_bar_enabled", True):
                    if self.config.get("mecha_bar_sync", True):
                        r, g, b = self.zones.get("1", (56, 189, 248))
                        sync_fn = getattr(self, "_sync_mecha_bar", None)
                        if sync_fn:
                            sync_fn(r, g, b)
                    else:
                        mc = self.config.get("mecha_bar_color", [167, 139, 250])
                        SerialEngine.send_backzone_rgb(1, mc[0], mc[1], mc[2], 1, self.brightness)
            elif self.effect_mode == "HwRainbow":
                HardwareEngine.send_hardware_mode(0x14, 255, 255, 255, self.brightness)
            elif self.effect_mode == "HwBreath":
                z1 = self.zones.get("1", (56, 189, 248))
                HardwareEngine.send_hardware_mode(0x12, z1[0], z1[1], z1[2], self.brightness)
        # Dynamic effects (Aurora, Wave, etc.) run in effects_loop at 40 FPS and seamlessly pick up self.brightness on the next frame with ZERO white flicker!

    def _show_effect_osd(self, mode_key: str):
        display_name = EFFECT_DISPLAY_NAMES.get(mode_key, mode_key)
        self._show_hud_osd("KEYBOARD EFFECT", f"✨  {display_name}", subtitle="Motion Dynamic", accent="#A78BFA")

    def _show_brightness_osd(self, pct: int):
        val_str = f"{pct}%" if pct > 0 else "OFF"
        icon = "🔆" if pct >= 50 else ("🔅" if pct > 0 else "🌑")
        sub = "High" if pct >= 80 else ("Medium" if pct >= 50 else ("Dim" if pct > 0 else "Disabled"))
        self._show_hud_osd("KEYBOARD BRIGHTNESS", f"{icon}  {val_str}", subtitle=sub, accent="#38BDF8" if pct > 0 else "#64748B", level=pct)

    def _show_hud_osd(self, category: str, message: str, subtitle: str = "", level: int = None, accent: str = "#38BDF8"):
        """Modern Windows 11 floating card OSD with DPI-aware dead-center alignment and progress glow."""
        try:
            # Auto-detect level if not explicitly provided
            if level is None and "BRIGHTNESS" in category.upper():
                match = re.search(r"(\d+)%", message)
                if match:
                    level = int(match.group(1))
                elif "OFF" in message.upper():
                    level = 0

            if not hasattr(self, '_osd_win') or not self._osd_win or not self._osd_win.winfo_exists():
                win = tk.Toplevel(self.root)
                win.overrideredirect(True)
                win.attributes('-topmost', True)
                try:
                    win.attributes('-alpha', 0.96)
                except Exception:
                    pass
                try:
                    win.wm_attributes("-disabled", True)
                except Exception:
                    pass
                win.configure(bg="#0B0F19")

                # Enable Windows 11 native rounded corners & drop shadow
                win.update_idletasks()
                hwnd = ctypes.windll.user32.GetParent(win.winfo_id()) or win.winfo_id()
                try:
                    dwmapi = ctypes.windll.dwmapi
                    val = ctypes.c_int(2)  # DWMWCP_ROUND
                    dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(val), ctypes.sizeof(val))
                    
                    class MARGINS(ctypes.Structure):
                        _fields_ = [('cxLeftWidth', ctypes.c_int), ('cxRightWidth', ctypes.c_int), 
                                    ('cyTopHeight', ctypes.c_int), ('cyBottomHeight', ctypes.c_int)]
                    margins = MARGINS(1, 1, 1, 1)
                    dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
                except Exception:
                    pass

                self._osd_win = win
            else:
                win = self._osd_win

            # Rebuild widgets inside OSD container for clean crisp styling
            for child in win.winfo_children():
                child.destroy()

            # Outer subtle border with glowing accent
            outer = tk.Frame(win, bg="#1E293B", padx=1, pady=1)
            outer.pack(fill="both", expand=True)

            card = tk.Frame(outer, bg="#0F172A", padx=20, pady=12)
            card.pack(fill="both", expand=True)

            # Top header row: dot + category + optional level percentage badge
            header_row = tk.Frame(card, bg="#0F172A")
            header_row.pack(fill="x", anchor="w")

            dot = tk.Label(header_row, text="●", font=("Segoe UI", 9), fg=accent, bg="#0F172A")
            dot.pack(side="left", padx=(0, 6))

            cat_lbl = tk.Label(
                header_row, text=category.upper(),
                font=("Segoe UI Semibold", 10),
                fg="#94A3B8", bg="#0F172A"
            )
            cat_lbl.pack(side="left")

            if level is not None:
                pct_txt = f"{level}%" if level > 0 else "OFF"
                pct_lbl = tk.Label(
                    header_row, text=pct_txt,
                    font=("Segoe UI Bold", 11),
                    fg=accent if level > 0 else "#64748B",
                    bg="#0F172A"
                )
                pct_lbl.pack(side="right")

            # Main content row: icon + title + subtitle
            content_row = tk.Frame(card, bg="#0F172A")
            content_row.pack(fill="x", pady=(6, 4 if level is not None else 2))

            msg_lbl = tk.Label(
                content_row, text=message,
                font=("Segoe UI", 15, "bold"),
                fg="#F8FAFC", bg="#0F172A"
            )
            msg_lbl.pack(side="left")

            if subtitle:
                sub_lbl = tk.Label(
                    content_row, text=subtitle,
                    font=("Segoe UI", 12),
                    fg="#94A3B8", bg="#0F172A"
                )
                sub_lbl.pack(side="left", padx=(8, 0), pady=(2, 0))

            # Optional Segmented Level Bar (e.g. for brightness)
            if level is not None:
                bar_frame = tk.Frame(card, bg="#0F172A", height=6)
                bar_frame.pack(fill="x", pady=(4, 2))
                steps = [20, 50, 75, 100]
                for i, step_val in enumerate(steps):
                    active = (level >= step_val) or (level > 0 and i == 0)
                    seg_bg = accent if active else "#1E293B"
                    seg = tk.Frame(bar_frame, bg=seg_bg, height=4)
                    seg.pack(side="left", fill="x", expand=True, padx=2)

            win.deiconify()
            win.lift()
            win.update_idletasks()

            # Accurate multi-monitor DPI-aware screen centering
            w = max(310, card.winfo_reqwidth() + 4)
            h = card.winfo_reqheight() + 4

            user32 = ctypes.windll.user32
            class RECT(ctypes.Structure):
                _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
            class MONITORINFO(ctypes.Structure):
                _fields_ = [('cbSize', ctypes.c_ulong), ('rcMonitor', RECT), ('rcWork', RECT), ('dwFlags', ctypes.c_ulong)]

            pt = ctypes.wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            hmon = user32.MonitorFromPoint(pt, 2)
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                screen_left = mi.rcWork.left
                screen_top = mi.rcWork.top
                screen_w = mi.rcWork.right - mi.rcWork.left
            else:
                screen_left = 0
                screen_top = 0
                screen_w = win.winfo_screenwidth()

            x = screen_left + (screen_w - w) // 2
            y = screen_top + 48

            win.geometry(f"{w}x{h}+{x}+{y}")
            try:
                hwnd = user32.GetParent(win.winfo_id()) or win.winfo_id()
                user32.SetWindowPos(hwnd, -1, x, y, w, h, 0x0040 | 0x0010)
            except Exception:
                pass

            if hasattr(self, '_osd_timer') and self._osd_timer:
                try:
                    win.after_cancel(self._osd_timer)
                except Exception:
                    pass

            def _dismiss():
                if hasattr(self, '_osd_win') and self._osd_win and self._osd_win.winfo_exists():
                    self._osd_win.destroy()
                self._osd_win = None
                self._osd_timer = None

            self._osd_timer = win.after(1200, _dismiss)
        except Exception:
            pass

    def _set_brightness_pct(self, pct: int):
        self.bright_slider.set(pct)
        self._on_brightness_changed(pct)

    def _cycle_kb_brightness(self):
        """Cycle keyboard brightness: 100% -> 50% -> 20% -> 0% (off) -> 100%."""
        cur = self.brightness
        if cur > 50:
            nxt = 50
        elif cur > 20:
            nxt = 20
        elif cur > 0:
            nxt = 0
        else:
            nxt = 100

        def _apply():
            self._set_brightness_pct(nxt)
            if hasattr(self, '_show_brightness_osd'):
                self._show_brightness_osd(nxt)

        self._ui_dispatch(_apply)

    def _cycle_effect_mode(self):
        """Cycle through Motion & Effects modes one by one upon F3 press and hold."""
        all_modes = [
            "Solid",
            "Aurora",
            "AllAurora",
            "RainbowPrism",
            "BlazingFire",
            "Wave",
            "RandomMorph",
            "BreathingPulse",
            "ColorShift",
            "ScreenSync",
            "ReactiveTyping",
            "AudioSync",
            *CUSTOM_MOTION_EFFECTS,
        ]
        cur = self.effect_mode
        try:
            cur_idx = all_modes.index(cur)
            nxt_mode = all_modes[(cur_idx + 1) % len(all_modes)]
        except ValueError:
            nxt_mode = all_modes[0]

        def _apply():
            if hasattr(self, 'effect_var'):
                self.effect_var.set(nxt_mode)
            self._on_effect_changed()
            if hasattr(self, '_show_effect_osd'):
                self._show_effect_osd(nxt_mode)

        self._ui_dispatch(_apply)

    def _stop_animation(self):
        """Immediately stops dynamic animation and smoothly returns to Solid mode."""
        self.effect_mode = "Solid"
        if hasattr(self, 'effect_var'):
            self.effect_var.set("Solid")
        self.config["effect_mode"] = "Solid"
        self._anim_step_reset = True
        self._last_effect_change_time = time.time()
        self._update_fx_status_ui()
        self._update_theme_buttons_ui()
        self._update_zone_buttons_ui()
        self._update_virtual_keyboard_preview(self.zones)
        self._save_config()
        self._apply_lighting_hardware()

    def _update_fx_status_ui(self):
        for mode, tile in getattr(self, "effect_tiles", {}).items():
            tile.configure(border_color=THEME["accent_blue"] if mode == self.effect_mode else THEME["card_border"],
                           fg_color=THEME["nav_active_bg"] if mode == self.effect_mode else THEME["card_sub_bg"])
        if not hasattr(self, 'fx_status_badge'):
            return
        is_solid = (self.effect_mode == "Solid")
        if is_solid:
            if getattr(self, 'current_theme', ''):
                self.fx_status_badge.configure(
                    text=f"🎨 STATIC: {self.current_theme}",
                    text_color=self._tc("accent_green")
                )
            else:
                self.fx_status_badge.configure(
                    text="⚪ STATIC (Custom RGB Matrix)",
                    text_color=self._tc("text_muted")
                )
            if hasattr(self, 'stop_fx_btn'):
                self.stop_fx_btn.pack_forget()
        else:
            self.fx_status_badge.configure(
                text=f"🟢 RUNNING: {self.effect_mode}",
                text_color=self._tc("accent_blue")
            )
            if hasattr(self, 'stop_fx_btn'):
                self.stop_fx_btn.pack(side="left", padx=(0, 8))

        # Only expose controls that affect the selected effect.
        if hasattr(self, 'dir_seg'):
            self.dir_seg.configure(state="normal" if self.effect_mode in DIRECTIONAL_EFFECTS else "disabled")
        if hasattr(self, 'speed_seg'):
            self.speed_seg.configure(state="normal" if self.effect_mode in SPEED_CONTROLLED_EFFECTS else "disabled")

        # Dynamic Screen Sync Mode row visibility
        if hasattr(self, 'sync_mode_row'):
            if self.effect_mode == "ScreenSync":
                self.sync_mode_row.pack(fill="x", padx=16, pady=(0, 12))
            else:
                self.sync_mode_row.pack_forget()

        # Dynamic Audio Visualizer Equalizer frame visibility
        if hasattr(self, 'audio_viz_frame'):
            if self.effect_mode == "AudioSync":
                self.audio_viz_frame.pack(fill="x", padx=16, pady=(2, 12))
            else:
                self.audio_viz_frame.pack_forget()


    def _on_effect_changed(self):
        self.effect_mode = self.effect_var.get()
        self.config["effect_mode"] = self.effect_mode
        self._anim_step_reset = True
        self._last_effect_change_time = time.time()
        if self.effect_mode != "Solid":
            # Mutual exclusivity: clear active theme
            self.current_theme = ""
            self.config["current_theme"] = ""
            self._update_theme_buttons_ui()
            # Suppress conflicting OEM process and ensure EC accept frames
            HardwareEngine.kill_conflicting_oem_control_center()
            HardwareEngine.send_disable_auto_close()
        else:
            self._update_zone_buttons_ui()
            self._update_virtual_keyboard_preview(self.zones)
        self._update_fx_status_ui()
        self._save_config()
        self._apply_lighting_hardware()

    def _on_speed_changed(self):
        self.anim_speed = self.speed_var.get()
        self.config["animation_speed"] = self.anim_speed
        self._anim_step_reset = True
        self._last_effect_change_time = time.time()
        self._save_config()
        HardwareEngine.kill_conflicting_oem_control_center()
        HardwareEngine.send_disable_auto_close()

    def _on_direction_changed(self):
        self.anim_direction = normalize_animation_direction(self.direction_var.get())
        self.direction_var.set(self.anim_direction)
        self.config["animation_direction"] = self.anim_direction
        self._anim_step_reset = True
        self._last_effect_change_time = time.time()
        self._save_config()
        HardwareEngine.kill_conflicting_oem_control_center()
        HardwareEngine.send_disable_auto_close()

    def _on_screen_sync_mode_changed(self):
        val = self.screen_sync_var.get()
        self.screen_sync_mode = "Unified" if "Unified" in val else "Spatial"
        self.config["screen_sync_mode"] = self.screen_sync_mode
        self._anim_step_reset = True
        self._last_effect_change_time = time.time()
        self._save_config()
        HardwareEngine.kill_conflicting_oem_control_center()
        HardwareEngine.send_disable_auto_close()

    def _crossfade_to_global_color(self, target_rgb: Tuple[int, int, int]):
        """Commit on the UI thread so stale fade workers cannot override a new choice."""
        self._apply_global_color(target_rgb, skip_fade=True)

    def _apply_global_color(self, rgb: Tuple[int, int, int], skip_fade: bool = False):
        if not skip_fade and self.effect_mode == "Solid":
            self._crossfade_to_global_color(rgb)
            return

        self.current_color = list(rgb)
        for zid in ["1", "2", "3", "4"]:
            self.zones[zid] = list(rgb)
        self.config["current_color"] = self.current_color
        self.config["zones"] = self.zones
        
        # Mutual exclusivity
        self.effect_mode = "Solid"
        if hasattr(self, 'effect_var'):
            self.effect_var.set("Solid")
        self.config["effect_mode"] = "Solid"
        self.current_theme = ""
        self.config["current_theme"] = ""
        self._update_theme_buttons_ui()
        self._update_fx_status_ui()

        self._save_config()
        self._update_zone_buttons_ui()
        self._on_zone_clicked(getattr(self, 'selected_zone', "1"))
        self._apply_lighting_hardware()

    def _crossfade_zone_combo(self, target_czones: dict):
        """Apply one consistent snapshot; lighting-off remains authoritative."""
        self.zones = {z: list(target_czones.get(z, self.zones[z])) for z in ("1", "2", "3", "4")}
        self.config["zones"] = self.zones
        self._save_config()
        self._update_zone_buttons_ui()
        self._on_zone_clicked(self.selected_zone)
        self._apply_lighting_hardware()

    def _update_theme_buttons_ui(self):
        if not hasattr(self, 'theme_buttons'):
            return
        for tname, btn in self.theme_buttons.items():
            if getattr(self, 'current_theme', '') == tname and self.effect_mode == "Solid":
                btn.configure(border_width=2, border_color=THEME["accent_green"], fg_color=THEME["button_hover"])
            else:
                btn.configure(border_width=1, border_color=THEME["card_border"], fg_color=THEME["button_bg"])

    def _apply_zone_combo(self, theme_name: str, czones: dict):
        """Apply a curated zone theme with strict mutual exclusivity (stops animations)."""
        self.current_theme = theme_name
        self.effect_mode = "Solid"
        if hasattr(self, 'effect_var'):
            self.effect_var.set("Solid")
        self.config["effect_mode"] = "Solid"
        self.config["current_theme"] = theme_name
        self._update_theme_buttons_ui()
        self._update_fx_status_ui()
        self._crossfade_zone_combo(czones)



    def _on_mecha_toggled(self):
        val = self.mecha_var.get()
        self.config["mecha_bar_enabled"] = val
        self._save_config()
        self._apply_lighting_hardware()
        if hasattr(self, 'backzone_view'):
            self.backzone_view.master_switch_var.set(val)
        self._apply_backzone_hardware()

    def _on_mecha_sync_toggled(self):
        val = self.mecha_sync_var.get()
        self.config["mecha_bar_sync"] = val
        self._save_config()
        self._apply_lighting_hardware()
        if hasattr(self, 'backzone_view'):
            self.backzone_view.sync_var.set(val)
        self._apply_backzone_hardware()

    # -----------------------------------------------------------------------
    # Rear Back Zone Hardware Handlers
    # -----------------------------------------------------------------------
    def _rear_temperature(self):
        return getattr(self, "gpu_temp_val" if self.config.get("bz_temp_source") == "GPU" else "cpu_temp_val", None)

    def _backzone_allowed(self):
        """One policy shared by buttons, animation workers, and the visual preview."""
        if not self.config.get("mecha_bar_enabled", True) or not self.config.get("always_on", True):
            return False
        if getattr(self, "_suspended", False) or getattr(self, "_session_locked", False):
            return False
        if not getattr(self, "on_ac_val", True):
            if self.config.get("bz_turn_off_on_battery", False) or getattr(self, "battery_val", 100) <= 8:
                return False
        if self.config.get("bz_night_schedule_enabled", False):
            hour = time.localtime().tm_hour
            if hour >= 23 or hour < 7:
                return False
        return True

    _last_mecha_bar_sync_time = 0.0
    _last_mecha_bar_sync_rgb = None

    def _sync_mecha_bar(self, r: int, g: int, b: int):
        """Synchronize the rear mecha light bar to keyboard lighting via SerialEngine."""
        if not self.config.get("mecha_bar_enabled", True):
            return
        if not self.config.get("mecha_bar_sync", True):
            return
        if not self._backzone_allowed():
            return
        now = time.monotonic()
        target_rgb = (max(0, min(255, int(round(r)))), max(0, min(255, int(round(g)))), max(0, min(255, int(round(b)))))
        # Throttle to max 25 FPS (40ms) and skip identical frames unless 0.5s elapsed
        if target_rgb == self._last_mecha_bar_sync_rgb and (now - self._last_mecha_bar_sync_time < 0.5):
            return
        if (now - self._last_mecha_bar_sync_time) < 0.040:
            return
        self._last_mecha_bar_sync_time = now
        self._last_mecha_bar_sync_rgb = target_rgb
        bright = getattr(self, "brightness", 80)
        if bright <= 0:
            SerialEngine.send_backzone_rgb(15, 0, 0, 0, 1, 0)
            return
        SerialEngine.send_backzone_rgb(1, target_rgb[0], target_rgb[1], target_rgb[2], 1, bright)

    def _apply_backzone_hardware(self):
        self.bz_mode = backzone_ui.available_rear_mode(self.bz_mode)
        if hasattr(self, "config"):
            self.config["bz_mode"] = self.bz_mode
        try:
            r1, g1, b1 = self.bz_color1
            r2, g2, b2 = self.bz_color2
            bright = self.bz_brightness
            if not self._backzone_allowed() or self.bz_mode == 15:
                ok = SerialEngine.send_backzone_rgb(
                    effect=15,
                    r1=0, g1=0, b1=0,
                    speed=1,
                    bright=0,
                    r2=0, g2=0, b2=0,
                    bright2=0
                )
            elif self.bz_mode >= 100:
                audio_vol = getattr(self, "audio_volume", 0.0)
                audio_levels = getattr(self, "audio_levels", [0.0]*4)
                audio_beat = getattr(self, "audio_beat", 0.0)
                rgb, frame_brightness = render_backzone_effect(
                    self.bz_mode, 0.0, self.bz_color1, self.bz_color2, bright,
                    audio_volume=audio_vol, audio_levels=audio_levels, audio_beat=audio_beat,
                    temp_celsius=self._rear_temperature(),
                    bat_pct=getattr(self, "battery_val", 100),
                    on_ac=getattr(self, "on_ac_val", True)
                )
                ok = SerialEngine.send_backzone_rgb(
                    effect=1, r1=rgb[0], g1=rgb[1], b1=rgb[2],
                    speed=self.bz_speed, bright=frame_brightness
                )
            else:
                ok = SerialEngine.send_backzone_rgb(
                    effect=self.bz_mode,
                    r1=r1, g1=g1, b1=b1,
                    speed=self.bz_speed,
                    bright=bright,
                    r2=r2, g2=g2, b2=b2,
                    bright2=bright
                )
            self._ui_dispatch(self._set_hardware_status, ok, "Rear Back Zone", SerialEngine.get_last_error())
            return ok
        except Exception as e:
            self._ui_dispatch(self._set_hardware_status, False, "Rear Back Zone", str(e))
            return False

    def _on_bz_mode_changed(self, value):
        mode_map = {name: mode for mode, name in BACKZONE_MODE_NAMES.items()}
        self.bz_mode = backzone_ui.available_rear_mode(mode_map.get(value, 1))
        self.config["bz_mode"] = self.bz_mode
        self._save_config()
        self._apply_backzone_hardware()

    def _open_bz_color_picker(self, color_idx: int):
        init_color = tuple(self.bz_color1 if color_idx == 1 else self.bz_color2)
        title = f"Choose {'primary' if color_idx == 1 else 'secondary'} Rear Bar color"

        def on_apply(rgb):
            cr = max(0, min(255, int(round(rgb[0]))))
            cg = max(0, min(255, int(round(rgb[1]))))
            cb = max(0, min(255, int(round(rgb[2]))))
            chosen_rgb = [cr, cg, cb]
            hex_val = self._rgb_to_hex(chosen_rgb)
            if color_idx == 1:
                self.bz_color1 = chosen_rgb
                self.config["bz_color1"] = self.bz_color1
                if hasattr(self, 'bz_c1_swatch'):
                    self.bz_c1_swatch.configure(bg=hex_val)
            else:
                self.bz_color2 = chosen_rgb
                self.config["bz_color2"] = self.bz_color2
                if hasattr(self, 'bz_c2_swatch'):
                    self.bz_c2_swatch.configure(bg=hex_val)
            self._add_recent_color(hex_val)
            self._save_config()
            self._apply_backzone_hardware()

        ColorPickerDialog(
            parent=self.root,
            initial_rgb=init_color,
            title=title,
            theme_colors=THEME,
            on_apply=on_apply,
            recent_colors=self.recent_colors,
            preset_colors=SOFT_COLOR_PRESETS
        )

    def _on_bz_speed_changed(self, value):
        self.bz_speed = int(value)
        self.config["bz_speed"] = self.bz_speed
        if hasattr(self, 'bz_speed_lbl'):
            self.bz_speed_lbl.configure(text=str(self.bz_speed))
        self._save_config()
        self._apply_backzone_hardware()

    def _on_bz_brightness_changed(self, value):
        self.bz_brightness = int(value)
        self.config["bz_brightness"] = self.bz_brightness
        if hasattr(self, 'bz_bright_lbl'):
            self.bz_bright_lbl.configure(text=f"{self.bz_brightness}%")
        self._save_config()
        self._apply_backzone_hardware()

    # -----------------------------------------------------------------------
    # Performance & AI Governor Handlers
    # -----------------------------------------------------------------------
    def _set_mode_apply_status(self, text: str, color=None):
        if hasattr(self, "mode_apply_status"):
            self.mode_apply_status.configure(text=text, text_color=color or THEME["text_secondary"])

    def _record_automation_event(self, reason: str, mode: Optional[str] = None):
        display_mode = "Gaming" if mode == "Beast" else mode
        timestamp = datetime.datetime.now().strftime("%H:%M")
        suffix = f" → {display_mode}" if display_mode else ""
        self.automation_history.insert(0, f"{timestamp}  {reason}{suffix}")
        del self.automation_history[3:]
        for index, label in enumerate(getattr(self, "automation_event_labels", [])):
            label.configure(text=self.automation_history[index] if index < len(self.automation_history) else "")

    def _automation_is_paused(self) -> bool:
        return bool(self.config.get("automation_paused", False))

    def _manual_override_until(self) -> float:
        return AutomationPolicy.manual_until(self.config)

    def _automation_block_reason(self) -> str:
        return AutomationPolicy.block_reason(self.config)

    def _automation_status_text(self) -> str:
        return AutomationPolicy.status_text(self.config)

    def _refresh_automation_status(self):
        blocked = bool(self._automation_block_reason())
        if hasattr(self, "control_mode_var"):
            self.control_mode_var.set("Manual" if blocked else "Auto")
        if hasattr(self, "automation_state_lbl"):
            self.automation_state_lbl.configure(
                text=self._automation_status_text(),
                text_color=THEME["accent_amber"] if blocked else THEME["text_secondary"])

    def _automatic_mode_change_blocked(self, force: bool = False) -> bool:
        return False if force else bool(self._automation_block_reason())

    def _protect_manual_mode(self):
        minutes = AutomationPolicy.protect_manual(self.config)
        self._refresh_automation_status()
        return minutes

    def _resume_automatic_control(self):
        AutomationPolicy.resume(self.config)
        if hasattr(self, "automation_paused_var"):
            self.automation_paused_var.set(False)
        self._save_config()
        self._refresh_automation_status()
        self._record_automation_event("Automatic control resumed")

    def _on_control_mode_changed(self, selected: str):
        if selected == "Auto":
            self._resume_automatic_control()
            return
        self.config["automation_paused"] = True
        self.config["manual_mode_until"] = 0.0
        if hasattr(self, "automation_paused_var"):
            self.automation_paused_var.set(True)
        self._save_config()
        self._refresh_automation_status()
        self._record_automation_event("Manual control enabled")

    def _on_automation_pause_toggled(self):
        paused = bool(self.automation_paused_var.get())
        self.config["automation_paused"] = paused
        self._save_config()
        self._refresh_automation_status()
        self._record_automation_event("Automation paused" if paused else "Automation resumed")

    def _on_power_mode_segmented(self, selected: str):
        self.mode_var.set("Beast" if selected == "Gaming" else selected)
        self._on_mode_selected("Manual selection")

    def _submit_hardware_command(self, key, operation, callback, retries=1):
        """Use the serialized worker in the app, with a synchronous test fallback."""
        controller = getattr(self, "_hardware_commands", None)
        if controller is not None:
            return controller.submit(
                key, operation, callback, retries=retries,
                error_provider=HardwareEngine.get_last_error)
        try:
            value = operation()
            result = CommandResult(
                key, bool(value), value,
                "" if value else HardwareEngine.get_last_error(), 1)
        except Exception as exc:
            result = CommandResult(key, False, None, str(exc), 1)
        callback(result)
        return True

    def _finish_startup_command(self, result, context):
        self._set_hardware_status(result.ok, context, result.error)

    def _on_mode_selected(self, source: str = "Manual selection", automatic: bool = False):
        mode = self.mode_var.get()
        previous_mode = self.config.get("power_mode", "Balanced")
        display_mode = "Gaming" if mode == "Beast" else mode
        self._set_mode_apply_status(f"◌  Applying {display_mode} mode…", THEME["accent_blue"])
        if hasattr(self, "mode_selector"):
            self.mode_selector.configure(state="disabled")
        accepted = InfinixGTToolkitApp._submit_hardware_command(self,
            "performance-mode",
            lambda: HardwareEngine.set_performance_mode(mode),
            lambda result: InfinixGTToolkitApp._finish_performance_mode(self,
                result, mode, previous_mode, source, automatic),
        )
        if not accepted:
            previous_display = "Gaming" if previous_mode == "Beast" else previous_mode
            self.mode_var.set(previous_mode)
            if hasattr(self, "mode_display_var"):
                self.mode_display_var.set(previous_display)
            self._set_mode_apply_status("◌  A mode change is already running", THEME["accent_amber"])

    def _finish_performance_mode(self, result, mode, previous_mode, source, automatic):
        if hasattr(self, "mode_selector"):
            self.mode_selector.configure(state="normal")
        display_mode = "Gaming" if mode == "Beast" else mode
        if result.ok:
            self.config["power_mode"] = mode
            if hasattr(self, "mode_display_var"):
                self.mode_display_var.set(display_mode)
            if automatic:
                self._record_automation_event(source, mode)
            else:
                minutes = self._protect_manual_mode()
                self._record_automation_event(f"Manual control for {minutes} min", mode)
            self._save_config()
            self._set_mode_apply_status(f"●  {display_mode} mode active", THEME["accent_green"])
        else:
            self.mode_var.set(previous_mode)
            previous_display = "Gaming" if previous_mode == "Beast" else previous_mode
            if hasattr(self, "mode_display_var"):
                self.mode_display_var.set(previous_display)
            self._set_mode_apply_status(
                f"!  Could not apply {display_mode} · {previous_display} remains active",
                THEME["accent_rose"])
        self._set_hardware_status(
            result.ok,
            "Performance mode",
            result.error,
            show_dialog=not result.ok,
            retry=None if result.ok else lambda: self._retry_performance_mode(mode, source, automatic),
        )
        if hasattr(self, "_update_telemetry_mode_buttons"):
            self._update_telemetry_mode_buttons()

    def _retry_performance_mode(self, mode, source, automatic):
        self.mode_var.set(mode)
        if hasattr(self, "mode_display_var"):
            self.mode_display_var.set("Gaming" if mode == "Beast" else mode)
        self._on_mode_selected(source, automatic)

    def _sync_gpu_mode_ui(self, mode: str):
        if not hasattr(self, "gpu_mode_var"):
            return
        if mode not in HardwareEngine.GPU_MODE_VALUES:
            self._active_gpu_mode = ""
            self.gpu_mode_var.set("")
            for status in getattr(self, "gpu_mode_status_labels", []):
                status.configure(text="Active mode unavailable", text_color=THEME["text_muted"])
            return
        self._active_gpu_mode = mode
        self.gpu_mode_var.set(mode)
        self.config["gpu_mode"] = mode
        if hasattr(self, "telemetry_gpu_mode_value"):
            self.telemetry_gpu_mode_value.configure(text=f"●  {mode}")
        for status in getattr(self, "gpu_mode_status_labels", []):
            pending = self.config.get("gpu_mode_pending")
            if pending and pending != mode:
                status.configure(text=f"Active: {mode} · {pending} pending restart", text_color=THEME["accent_amber"])
            else:
                self.config.pop("gpu_mode_pending", None)
                status.configure(text=f"Current: {mode}", text_color=THEME["accent_green"])

    def _on_gpu_mode_changed(self, selected: str):
        previous = getattr(self, "_active_gpu_mode", "")
        self.gpu_mode_var.set(previous)
        if selected == previous and not self.config.get("gpu_mode_pending"):
            return
        for selector in getattr(self, "gpu_mode_selectors", [self.gpu_mode_selector]):
            selector.configure(state="disabled")
        for status in getattr(self, "gpu_mode_status_labels", [self.gpu_mode_status]):
            status.configure(text="Applying…", text_color=THEME["accent_blue"])

        accepted = InfinixGTToolkitApp._submit_hardware_command(self,
            "gpu-mode", lambda: HardwareEngine.set_gpu_mode(selected),
            lambda result: self._finish_gpu_mode_change(result, selected, previous))
        if not accepted:
            self.gpu_mode_var.set(previous)
            for selector in getattr(self, "gpu_mode_selectors", [self.gpu_mode_selector]):
                selector.configure(state="normal")

    def _finish_gpu_mode_change(self, result, selected: str, previous: str):
        for selector in getattr(self, "gpu_mode_selectors", [self.gpu_mode_selector]):
            selector.configure(state="normal")
        if result.ok:
            self.gpu_mode_var.set(previous)
            self.config["gpu_mode_pending"] = selected
            self._save_config()
            for status in getattr(self, "gpu_mode_status_labels", [self.gpu_mode_status]):
                status.configure(
                    text=f"Active: {previous or 'Unknown'} · {selected} pending restart",
                    text_color=THEME["accent_amber"])
            self._set_hardware_status(True, "GPU mode")
            if hasattr(self, "telemetry_gpu_mode_value"):
                self.telemetry_gpu_mode_value.configure(text=f"●  {previous or 'Unknown'}")
            self._prompt_gpu_restart(selected)
        else:
            self.gpu_mode_var.set(previous)
            for status in getattr(self, "gpu_mode_status_labels", [self.gpu_mode_status]):
                status.configure(text="Change failed", text_color=THEME["accent_rose"])
            self._set_hardware_status(
                False, "GPU mode", result.error, show_dialog=True,
                retry=lambda: self._on_gpu_mode_changed(selected))

    def _prompt_gpu_restart(self, selected: str):
        """Offer an explicit restart after a successful hardware MUX change."""
        restart_now = messagebox.askyesno(
            "Restart required",
            f"GPU mode changed to {selected}.\n\n"
            "Windows must restart before the new graphics mode becomes active.\n\n"
            "Restart Windows now?",
            icon="warning",
            parent=self.root,
        )
        if not restart_now:
            return
        try:
            subprocess.Popen(
                ["shutdown.exe", "/r", "/t", "0"],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception as exc:
            messagebox.showerror(
                "Restart failed",
                f"Windows could not be restarted automatically.\n\n{exc}",
                parent=self.root)

    def _on_cooler_boost_toggled(self):
        val = self.cooler_var.get()
        if hasattr(self, "cooler_switch"):
            self.cooler_switch.configure(state="disabled")
        accepted = InfinixGTToolkitApp._submit_hardware_command(self,
            "cooler-boost",
            lambda: HardwareEngine.set_full_fan_mode(val, self.mode_var.get()),
            lambda result: self._finish_cooler_boost(result, val))
        if not accepted:
            self.cooler_var.set(not val)
            if hasattr(self, "cooler_switch"):
                self.cooler_switch.configure(state="normal")

    def _finish_cooler_boost(self, result, val):
        if hasattr(self, "cooler_switch"):
            self.cooler_switch.configure(state="normal")
        if result.ok:
            self.config["cooler_boost"] = val
            self._save_config()
            self._set_hardware_status(True, "Extreme Cooler Boost")
        else:
            self.cooler_var.set(not val)
            self._set_hardware_status(
                False, "Extreme Cooler Boost", result.error, show_dialog=True,
                retry=lambda: self._retry_cooler_boost(val))

    def _retry_cooler_boost(self, val):
        self.cooler_var.set(val)
        self._on_cooler_boost_toggled()

    def _on_winlock_toggled(self):
        val = self.winlock_var.get()
        self.config["win_key_lock"] = val
        self._save_config()
        WindowsKeyLockEngine.set_lock(val)

    def _on_fnlock_toggled(self):
        val = self.fnlock_var.get()
        self.config["software_fn_lock"] = val
        self._save_config()
        SoftwareFnLock.set_enabled(val)

    def _on_ai_gov_toggled(self):
        val = self.ai_gov_var.get()
        self.config["ai_governor"] = val
        self._save_config()
        if val:
            self.ai_status_badge.configure(text="Active (Watching Load)", text_color=THEME["accent_blue"], fg_color=THEME["pill_bg"])
        else:
            self.ai_status_badge.configure(text="Disabled", text_color=THEME["text_secondary"], fg_color=THEME["pill_bg"])

    def _on_ai_game_toggled(self):
        val = self.ai_game_var.get()
        self.config["ai_game_detector"] = val
        self._save_config()

    def _on_gpu_alert_toggled(self):
        val = self.gpu_alert_var.get()
        self.config["gpu_gaming_alert"] = val
        self._save_config()

    def _on_battery_limit_toggled(self):
        # Intentionally unavailable: no verified setter exists in BYDWmi2/ControlCenter.
        self.bat_limit_var.set(False)
        self.config["battery_limit_80"] = False
        self._save_config()
        messagebox.showwarning(
            "Battery limit unavailable",
            "This model's supplied OEM interface exposes battery telemetry but no verified charge-threshold command. No EC value was changed.",
        )

    def _on_auto_ac_toggled(self):
        val = self.auto_ac_var.get()
        self.config["auto_switch_on_ac"] = val
        self._save_config()

    def _on_usb_charge_toggled(self):
        val = self.usb_chg_var.get()
        if hasattr(self, "usb_chg_switch"):
            self.usb_chg_switch.configure(state="disabled")
        accepted = InfinixGTToolkitApp._submit_hardware_command(self,
            "usb-sleep-charging",
            lambda: HardwareEngine.set_usb_sleep_charging(val),
            lambda result: self._finish_usb_charge(result, val))
        if not accepted:
            self.usb_chg_var.set(not val)
            if hasattr(self, "usb_chg_switch"):
                self.usb_chg_switch.configure(state="normal")

    def _finish_usb_charge(self, result, val):
        if hasattr(self, "usb_chg_switch"):
            self.usb_chg_switch.configure(state="normal")
        if result.ok:
            self.config["usb_charge_off"] = val
            self._save_config()
            self._set_hardware_status(True, "USB sleep charging")
        else:
            self.usb_chg_var.set(not val)
            self._set_hardware_status(
                False, "USB sleep charging", result.error, show_dialog=True,
                retry=lambda: self._retry_usb_charge(val))

    def _retry_usb_charge(self, val):
        self.usb_chg_var.set(val)
        self._on_usb_charge_toggled()

    # -----------------------------------------------------------------------
    # User Custom Presets Library
    # -----------------------------------------------------------------------
    def _set_user_preference(self, key, value):
        self.config[key] = value
        self._save_config()

    def _preset_feedback(self, text):
        self.preset_status.configure(text=text)
        for button in getattr(self, "preset_library_actions", ()):
            button.configure(state="normal" if self.config.get("user_presets") else "disabled")

    def _rename_user_preset(self):
        old_name = self.preset_dropdown.get()
        new_name = self.preset_name_entry.get().strip()
        presets = self.config.get("user_presets", {})
        if old_name not in presets:
            self._preset_feedback("Select a saved preset first.")
            return
        if not new_name or len(new_name) > 60:
            self._preset_feedback("Enter a new name (1–60 characters) in Preset Name.")
            return
        if new_name in presets and new_name != old_name:
            self._preset_feedback("That name already exists. Choose a different name.")
            return
        if new_name != old_name:
            presets[new_name] = presets.pop(old_name)
            self._save_config()
            self.preset_dropdown.configure(values=list(presets))
            self.preset_dropdown.set(new_name)
        self._preset_feedback(f"Renamed to {new_name}.")

    def _delete_user_preset(self):
        name = self.preset_dropdown.get()
        presets = self.config.get("user_presets", {})
        if name not in presets:
            self._preset_feedback("Select a saved preset first.")
            return
        if not messagebox.askyesno("Delete preset?", f"Remove '{name}' from your library? Current lighting stays as it is."):
            return
        del presets[name]
        self._save_config()
        names = list(presets) or ["No saved presets"]
        self.preset_dropdown.configure(values=names)
        self.preset_dropdown.set(names[0])
        self._preset_feedback(f"Deleted {name}.")

    def _save_user_preset(self):
        name = self.preset_name_entry.get().strip()
        if not name or len(name) > 60:
            self._preset_feedback("Enter a preset name (1–60 characters).")
            return
        presets = self.config.get("user_presets", {})
        if name in presets and not messagebox.askyesno("Replace preset?", f"Replace existing preset '{name}'?"):
            return
        presets[name] = {
            "zones": {k: list(v) for k, v in self.zones.items()},
            "brightness": self.brightness,
            "effect_mode": self.effect_mode,
            "animation_speed": self.anim_speed,
            "animation_direction": self.anim_direction,
            "power_mode": self.mode_var.get()
        }
        self.config["user_presets"] = presets
        self._save_config()
        self.preset_dropdown.configure(values=list(presets.keys()))
        self.preset_dropdown.set(name)
        self._preset_feedback(f"Saved {name}.")

    def _load_user_preset(self):
        name = self.preset_dropdown.get()
        presets = self.config.get("user_presets", {})
        if name in presets:
            try:
                p = validate_lighting_preset(presets[name])
            except ValueError as exc:
                messagebox.showerror("Invalid preset", str(exc))
                return
            self.zones = {k: list(v) for k, v in p.get("zones", self.zones).items()}
            self.config["zones"] = self.zones
            self.current_color = list(self.zones["1"])
            self.config["current_color"] = self.current_color
            self.brightness = p.get("brightness", 100)
            self.config["brightness"] = self.brightness
            self.bright_slider.set(self.brightness)
            self.bright_lbl.configure(text=f"{self.brightness}%")
            self._refresh_brightness_buttons()
            if self.config.get("preset_include_power", False):
                self.mode_var.set(p.get("power_mode", "Balanced"))
                self._on_mode_selected()
            self.effect_mode = p.get("effect_mode", self.effect_mode)
            self.effect_var.set(self.effect_mode)
            self.config["effect_mode"] = self.effect_mode
            self.current_theme = ""
            self.config["current_theme"] = ""
            self.anim_speed = p["animation_speed"]
            self.anim_direction = normalize_animation_direction(p["animation_direction"])
            self.speed_var.set(self.anim_speed)
            self.direction_var.set(self.anim_direction)
            self.config["animation_speed"] = self.anim_speed
            self.config["animation_direction"] = self.anim_direction
            self._update_fx_status_ui()
            self._save_config()
            self._update_zone_buttons_ui()
            self._update_theme_buttons_ui()
            self._anim_step_reset = True
            self._apply_lighting_hardware()
            self._preset_feedback(f"Loaded {name}. Lighting changes can be undone in Lighting studio.")

    def _on_emergency_saver_toggled(self):
        val = self.emerg_saver_var.get()
        self.config["emergency_battery_saver"] = val
        self.emergency_saver_active = val
        self._save_config()

    def _export_preset_file(self):
        """Exports currently loaded preset or zones to a shareable .igtkpreset JSON file."""
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            title="Export Infinix GT Preset",
            defaultextension=".igtkpreset",
            filetypes=[("Infinix GT Preset (*.igtkpreset)", "*.igtkpreset"), ("JSON Files (*.json)", "*.json")]
        )
        if not file_path:
            return
        p_name = self.preset_name_entry.get().strip() or "Custom Setup"
        data = {
            "version": "4.2",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "preset_name": p_name,
            "zones": self.zones,
            "brightness": self.brightness,
            "effect_mode": self.effect_mode,
            "animation_speed": self.anim_speed,
            "animation_direction": self.anim_direction,
            "power_mode": self.mode_var.get()
        }
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Preset Exported", f"Successfully exported preset to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not save preset file: {e}")

    def _import_preset_file(self):
        """Imports a .igtkpreset file into the user's custom presets library."""
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Import Infinix GT Preset",
            filetypes=[("Infinix GT Preset (*.igtkpreset)", "*.igtkpreset"), ("JSON Files (*.json)", "*.json")]
        )
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            validated = validate_lighting_preset(data)
            name = data.get("preset_name", os.path.splitext(os.path.basename(file_path))[0])
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Preset name must be non-empty text.")
            presets = self.config.get("user_presets", {})
            if name in presets and not messagebox.askyesno("Replace preset?", f"Replace existing preset '{name}'?"):
                return
            presets[name] = validated
            self.config["user_presets"] = presets
            self._save_config()
            self.preset_dropdown.configure(values=list(presets.keys()))
            self.preset_dropdown.set(name)
            self._preset_feedback(f"Imported {name}. Click Load Preset to apply it.")
        except Exception as e:
            messagebox.showerror("Import Failed", f"Could not parse preset file: {e}")

    def _toggle_mini_overlay(self):
        """Toggles the sleek, floating always-on-top desktop HUD."""
        if getattr(self, 'hud_window', None) is not None and self.hud_window.winfo_exists():
            self.hud_window.destroy()
            self.hud_window = None
            if hasattr(self, 'hud_btn'):
                self.hud_btn.configure(fg_color=THEME["pill_bg"], text_color=THEME["accent_purple"])
            return

        self.hud_window = ctk.CTkToplevel(self.root)
        self.hud_window.title("Infinix GT HUD")
        self.hud_window.geometry("280x120+40+40")
        self.hud_window.overrideredirect(True)
        self.hud_window.attributes("-topmost", True)
        self.hud_window.attributes("-alpha", 0.94)

        def _start_move(e):
            self.hud_window._x = e.x
            self.hud_window._y = e.y
        def _on_motion(e):
            deltax = e.x - self.hud_window._x
            deltay = e.y - self.hud_window._y
            x = self.hud_window.winfo_x() + deltax
            y = self.hud_window.winfo_y() + deltay
            self.hud_window.geometry(f"+{x}+{y}")

        hud_frame = neon_ui.Frame(self.hud_window, fg_color="#0F172A", corner_radius=12, border_width=1.5, border_color="#38BDF8")
        hud_frame.pack(fill="both", expand=True)
        hud_frame.bind("<Button-1>", _start_move)
        hud_frame.bind("<B1-Motion>", _on_motion)

        h_top = neon_ui.Frame(hud_frame, fg_color="transparent")
        h_top.pack(fill="x", padx=10, pady=(6, 2))
        h_top.bind("<Button-1>", _start_move)
        h_top.bind("<B1-Motion>", _on_motion)

        h_title = ctk.CTkLabel(h_top, text="⚡ GT BOOK HUD", font=ctk.CTkFont(size=13, weight="bold"), text_color="#38BDF8")
        h_title.pack(side="left")
        h_title.bind("<Button-1>", _start_move)
        h_title.bind("<B1-Motion>", _on_motion)

        exp_btn = neon_ui.Button(
            h_top, text="↗️ Full", width=48, height=20, corner_radius=6,
            fg_color="#1E293B", hover_color="#334155", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._restore_from_hud
        )
        exp_btn.pack(side="right")

        self.hud_cpu_lbl = ctk.CTkLabel(hud_frame, text="💻 CPU: --%  |  🧠 RAM: --%", font=ctk.CTkFont(size=13, weight="bold"), text_color="#F8FAFC")
        self.hud_cpu_lbl.pack(anchor="w", padx=12, pady=1)

        self.hud_bat_lbl = ctk.CTkLabel(hud_frame, text="🔋 Battery: --%  |  ⚡ Plan: Balanced", font=ctk.CTkFont(size=13, weight="bold"), text_color="#4ADE80")
        self.hud_bat_lbl.pack(anchor="w", padx=12, pady=1)

        self.hud_fx_lbl = ctk.CTkLabel(hud_frame, text=f"✨ FX: {self.effect_mode}", font=ctk.CTkFont(size=12), text_color="#94A3B8")
        self.hud_fx_lbl.pack(anchor="w", padx=12, pady=(0, 6))

        if hasattr(self, 'hud_btn'):
            self.hud_btn.configure(fg_color="#38BDF8", text_color="#0F172A")

    def _restore_from_hud(self):
        if getattr(self, 'hud_window', None):
            self.hud_window.destroy()
            self.hud_window = None
            if hasattr(self, 'hud_btn'):
                self.hud_btn.configure(fg_color=THEME["pill_bg"], text_color=THEME["accent_purple"])
        self.root.deiconify()
        self.root.lift()

    def _draw_cpu_sparkline(self):
        if not hasattr(self, 'cpu_graph_canvas') or not self.cpu_graph_canvas.winfo_exists():
            return
        if not self.root.winfo_viewable():
            return
        w = self.cpu_graph_canvas.winfo_width()
        h = self.cpu_graph_canvas.winfo_height()
        if w < 20 or h < 10:
            return
        self.cpu_graph_canvas.delete("all")
        # Grid lines
        for y_ratio in [0.25, 0.5, 0.75]:
            gy = int(h * y_ratio)
            self.cpu_graph_canvas.create_line(0, gy, w, gy, fill="#1E293B", dash=(2, 4))
        
        n = len(self.cpu_history)
        if n < 2:
            return
        pts = []
        for i, val in enumerate(self.cpu_history):
            x = (i / (n - 1)) * w
            y = h - (max(0.0, min(100.0, val)) / 100.0 * (h - 6)) - 3
            pts.append((x, y))
        
        poly_pts = [(0, h)] + pts + [(w, h)]
        flat_poly = [coord for pt in poly_pts for coord in pt]
        self.cpu_graph_canvas.create_polygon(flat_poly, fill="#0E3858", outline="")
        
        flat_line = [coord for pt in pts for coord in pt]
        self.cpu_graph_canvas.create_line(flat_line, fill="#38BDF8", width=2, smooth=True)
        
        last_x, last_y = pts[-1]
        self.cpu_graph_canvas.create_oval(last_x - 3, last_y - 3, last_x + 3, last_y + 3, fill="#38BDF8", outline="#FFFFFF")

    def _draw_gpu_sparkline(self):
        if not hasattr(self, 'gpu_graph_canvas') or not self.gpu_graph_canvas.winfo_exists():
            return
        if not self.root.winfo_viewable():
            return
        w = self.gpu_graph_canvas.winfo_width()
        h = self.gpu_graph_canvas.winfo_height()
        if w < 20 or h < 10:
            return
        self.gpu_graph_canvas.delete("all")
        # Grid lines
        for y_ratio in [0.25, 0.5, 0.75]:
            gy = int(h * y_ratio)
            self.gpu_graph_canvas.create_line(0, gy, w, gy, fill="#1E293B", dash=(2, 4))
        
        n = len(getattr(self, 'gpu_history', []))
        if n < 2:
            return
        pts = []
        for i, val in enumerate(self.gpu_history):
            x = (i / (n - 1)) * w
            y = h - (max(0.0, min(100.0, val)) / 100.0 * (h - 6)) - 3
            pts.append((x, y))
        
        poly_pts = [(0, h)] + pts + [(w, h)]
        flat_poly = [coord for pt in poly_pts for coord in pt]
        self.gpu_graph_canvas.create_polygon(flat_poly, fill="#06382E", outline="")
        
        flat_line = [coord for pt in pts for coord in pt]
        self.gpu_graph_canvas.create_line(flat_line, fill="#10B981", width=2, smooth=True)
        
        last_x, last_y = pts[-1]
        self.gpu_graph_canvas.create_oval(last_x - 3, last_y - 3, last_x + 3, last_y + 3, fill="#10B981", outline="#FFFFFF")

    def _draw_donut_gauge(self, canvas, pct, temp_str, color, label="LOAD"):
        if not canvas or not canvas.winfo_exists():
            return
        if not self.root.winfo_viewable():
            return
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 30 or h < 30:
            w, h = 110, 110
        canvas.delete("all")
        cx, cy = w // 2, h // 2
        r = min(cx, cy) - 10
        lw = 8

        # Background track (dark slate)
        canvas.create_arc(cx - r, cy - r, cx + r, cy + r,
                          start=225, extent=-270,
                          style="arc", width=lw, outline="#1E293B")

        # Active value arc
        val = max(0.0, min(100.0, pct)) if pct is not None else 0.0
        val_extent = -270.0 * (val / 100.0)
        if abs(val_extent) > 0.5:
            canvas.create_arc(cx - r, cy - r, cx + r, cy + r,
                              start=225, extent=val_extent,
                              style="arc", width=lw, outline=color)

        # Center typography
        pct_text = f"{pct:.0f}%" if pct is not None else "--%"
        canvas.create_text(cx, cy - 10, text=pct_text, fill="#FFFFFF",
                           font=("Segoe UI", 16, "bold"))
        canvas.create_text(cx, cy + 10, text=temp_str, fill=color,
                           font=("Segoe UI", 11, "bold"))
        canvas.create_text(cx, cy + 25, text=label, fill="#64748B",
                           font=("Segoe UI", 8, "bold"))

    # -----------------------------------------------------------------------
    # 1-Click Scenario Presets
    # -----------------------------------------------------------------------
    def _preset_scenario_beast(self):
        self.mode_var.set("Beast")
        self._on_mode_selected()
        self.winlock_var.set(True)
        self._on_winlock_toggled()
        self.always_on_var.set(True)
        self._on_always_on_toggled()
        self._set_brightness_pct(100)
        if "🌌 Twilight Glow" in ZONE_THEMES:
            self._apply_zone_combo("🌌 Twilight Glow", ZONE_THEMES["🌌 Twilight Glow"])
        elif "🔥 Inferno" in ZONE_THEMES:
            self._apply_zone_combo("🔥 Inferno", ZONE_THEMES["🔥 Inferno"])

    def _preset_scenario_office(self):
        self.mode_var.set("Quiet")
        self._on_mode_selected()
        self.winlock_var.set(False)
        self._on_winlock_toggled()
        self.always_on_var.set(True)
        self._on_always_on_toggled()
        self._set_brightness_pct(30)
        self._apply_global_color((255, 255, 255))
        self.mecha_var.set(False)
        self._on_mecha_toggled()

    def _preset_scenario_cinema(self):
        self.mode_var.set("Quiet")
        self._on_mode_selected()
        self.always_on_var.set(False)
        self._on_always_on_toggled()
        self.mecha_var.set(False)
        self._on_mecha_toggled()

    def _preset_scenario_battery(self):
        self.mode_var.set("Quiet")
        self._on_mode_selected()
        self.auto_ac_var.set(True)
        self._on_auto_ac_toggled()
        self._set_brightness_pct(20)

    # -----------------------------------------------------------------------
    # Windows Startup Shortcut
    # -----------------------------------------------------------------------
    def _on_autostart_toggled(self):
        val = self.start_var.get()
        if self._manage_startup_shortcut(val):
            self.config["autostart"] = val
            self._save_config()
        else:
            self.start_var.set(not val)

    def _manage_startup_shortcut(self, enable: bool):
        """Register elevated scheduled task and Windows Run key for instant logon startup and Task Manager integration."""
        cmd_target = startup_command_target()

        task_name = "InfinixGTToolkit"
        run_key_name = "InfinixGTToolkit"

        # 1. Keep startup single-sourced through the elevated scheduled task.
        # A parallel HKCU Run entry races the task at logon and can launch a
        # stale executable from another folder, so always remove it.
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(key, run_key_name)
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
        except Exception:
            pass

        # 2. Manage clean shortcut in Start Menu Startup folder
        if not enable and os.path.exists(SHORTCUT_PATH):
            try:
                os.remove(SHORTCUT_PATH)
            except OSError:
                pass

        # 3. Manage elevated Windows Scheduled Task for silent, instant boot without UAC prompt
        if enable:
            args = [
                "schtasks.exe", "/Create", "/TN", task_name, "/TR", cmd_target,
                "/SC", "ONLOGON", "/RL", "HIGHEST", "/F",
            ]
            try:
                subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    timeout=10,
                )
            except Exception:
                pass

            # Tune Scheduled Task settings: Priority 4 (Normal), allow on battery, don't stop on battery
            ps_script = (
                f"$t = Get-ScheduledTask -TaskName '{task_name}' -ErrorAction SilentlyContinue; "
                "if ($t) { "
                "$t.Settings.DisallowStartIfOnBatteries = $false; "
                "$t.Settings.StopIfGoingOnBatteries = $false; "
                "$t.Settings.Priority = 4; "
                "$t.Settings.StartWhenAvailable = $true; "
                "$t.Settings.ExecutionTimeLimit = 'PT0S'; "
                "Set-ScheduledTask -InputObject $t -ErrorAction SilentlyContinue "
                "}"
            )
            try:
                subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                    capture_output=True,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    timeout=8
                )
            except Exception:
                pass
            return True
        else:
            try:
                res = subprocess.run(
                    ["schtasks.exe", "/Delete", "/TN", task_name, "/F"],
                    capture_output=True,
                    text=True,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    timeout=5,
                )
                return res.returncode == 0 or "cannot find" in (res.stderr or "").lower()
            except Exception as e:
                self._set_hardware_status(False, "Windows startup", str(e), show_dialog=True)
                return False

    # -----------------------------------------------------------------------
    # Background Workers
    # -----------------------------------------------------------------------
    def _keyboard_heartbeat_tick(self):
        """Refresh colors without restarting PWM or a firmware animation."""
        if (not self.running or not self.heartbeat_active or self._suspended
                or self.brightness <= 0):
            return
        if not HardwareEngine.send_disable_auto_close():
            return
        if self.effect_mode == "Solid":
            HardwareEngine.send_4zone_rgb(dict(self.zones), self.brightness, set_mode_static=False)
        elif HardwareEngine._needs_mode_restore:
            if self.effect_mode == "HwRainbow":
                HardwareEngine.send_hardware_mode(0x14, 255, 255, 255, self.brightness)
            elif self.effect_mode == "HwBreath":
                rgb = self.zones.get("1", (56, 189, 248))
                HardwareEngine.send_hardware_mode(0x12, *rgb, self.brightness)

    def _start_heartbeat_worker(self):
        """Keep the keyboard awake and prevent EC hardware watchdog from reverting to factory defaults."""
        def heartbeat_loop():
            time.sleep(1.0)
            while self.running:
                if self.heartbeat_active and not self._suspended:
                    try:
                        HardwareEngine.kill_conflicting_oem_control_center()
                        self._keyboard_heartbeat_tick()
                    except Exception:
                        pass
                for _ in range(25):
                    if not self.running:
                        break
                    time.sleep(0.1)

        t = threading.Thread(target=heartbeat_loop, daemon=True)
        t.start()

    def _start_effects_worker(self):
        """Renders dynamic, high frame-rate (40-50 FPS) RGB animations."""
        speed_mult = {"Slow": 0.5, "Normal": 1.0, "Fast": 2.5, "Turbo": 5.0}

        def effects_loop():
            step = 0.0
            morph_t = 0.0
            current_hues = [random.random() for _ in range(4)]
            target_hues = [(h + 0.25 + 0.5 * random.random()) % 1.0 for h in current_hues]
            
            # Spatial Screen Sync State (Exponential Lerp at 30 FPS)
            last_screen_sync = 0.0
            screen_targets = {z: (0, 180, 255) for z in ["1", "2", "3", "4"]}
            screen_current = {z: [0.0, 180.0, 255.0] for z in ["1", "2", "3", "4"]}
            sct_inst = None
            frame_count = 0
            reported_hardware_error = ""
            last_effect_mode = None

            while self.running:
                # When turned off or brightness is 0, sleep and do not send any HID animation packets
                if getattr(self, 'brightness', 100) <= 0 or not self.heartbeat_active:
                    time.sleep(0.05)
                    continue
                if self.heartbeat_active and not self._suspended and self.effect_mode not in ("Solid", "HwRainbow", "HwBreath"):
                    try:
                        frame_count += 1
                        force_static = False

                        # Mode switch detection -> assert static mode lock 0x11
                        if self.effect_mode != last_effect_mode:
                            last_effect_mode = self.effect_mode
                            force_static = True

                        # Immediate step reset on speed or direction changes
                        if getattr(self, '_anim_step_reset', False):
                            step = 0.0
                            morph_t = 0.0
                            self._anim_step_reset = False

                        mult = speed_mult.get(self.anim_speed, 1.0)
                        direction = normalize_animation_direction(getattr(self, 'anim_direction', None))

                        if self.effect_mode in CUSTOM_MOTION_EFFECTS:
                            motion_zones = render_custom_motion(
                                self.effect_mode, step, direction, self.current_color,
                                self.zones.get("4", (167, 139, 250)))
                            HardwareEngine.send_4zone_rgb(
                                motion_zones, self.brightness, set_mode_static=force_static)
                            if self.config.get("mecha_bar_enabled", True):
                                lead_zone = max(motion_zones, key=lambda z: sum(motion_zones[z]))
                                self._sync_mecha_bar(*motion_zones[lead_zone])
                            self._ui_dispatch(self._update_virtual_keyboard_preview, motion_zones)

                        elif self.effect_mode == "Aurora":
                            aurora_zones = render_aurora(step, direction)
                            HardwareEngine.send_4zone_rgb(aurora_zones, self.brightness, set_mode_static=force_static)
                            if self.config.get("mecha_bar_enabled", True):
                                lead_zone = max(("1", "2", "3", "4"), key=lambda z: sum(aurora_zones[z]))
                                mr, mg, mb = aurora_zones[lead_zone]
                                self._sync_mecha_bar(mr, mg, mb)
                            self._ui_dispatch(self._update_virtual_keyboard_preview, aurora_zones)

                        elif self.effect_mode == "AllAurora":
                            current_col = tuple(self.current_color) if hasattr(self, 'current_color') and self.current_color else (56, 189, 248)
                            aurora_zones = render_all_aurora(step, direction, current_col)
                            HardwareEngine.send_4zone_rgb(aurora_zones, self.brightness, set_mode_static=force_static)
                            if self.config.get("mecha_bar_enabled", True):
                                lead_zone = max(("1", "2", "3", "4"), key=lambda z: sum(aurora_zones[z]))
                                mr, mg, mb = aurora_zones[lead_zone]
                                self._sync_mecha_bar(mr, mg, mb)
                            self._ui_dispatch(self._update_virtual_keyboard_preview, aurora_zones)

                        elif self.effect_mode == "RainbowPrism":
                            prism_zones = render_rainbow_prism(step, direction)
                            HardwareEngine.send_4zone_rgb(prism_zones, self.brightness, set_mode_static=force_static)
                            if self.config.get("mecha_bar_enabled", True):
                                lead_zone = max(("1", "2", "3", "4"), key=lambda z: sum(prism_zones[z]))
                                mr, mg, mb = prism_zones[lead_zone]
                                self._sync_mecha_bar(mr, mg, mb)
                            self._ui_dispatch(self._update_virtual_keyboard_preview, prism_zones)

                        elif self.effect_mode == "BlazingFire":
                            fire_zones = render_blazing_fire(step, direction)
                            HardwareEngine.send_4zone_rgb(fire_zones, self.brightness, set_mode_static=force_static)
                            if self.config.get("mecha_bar_enabled", True):
                                lead_zone = max(("1", "2", "3", "4"), key=lambda z: sum(fire_zones[z]))
                                mr, mg, mb = fire_zones[lead_zone]
                                self._sync_mecha_bar(mr, mg, mb)
                            self._ui_dispatch(self._update_virtual_keyboard_preview, fire_zones)

                        elif self.effect_mode == "Wave":
                            wave_zones = render_wave_sweep(step, direction)
                            if self.config.get("mecha_bar_enabled", True):
                                lead_zone = "4" if "Right to Left" in direction else "1"
                                mr, mg, mb = wave_zones[lead_zone]
                                self._sync_mecha_bar(mr, mg, mb)

                            HardwareEngine.send_4zone_rgb(wave_zones, self.brightness, set_mode_static=force_static)
                            self._ui_dispatch(self._update_virtual_keyboard_preview, wave_zones)

                        elif self.effect_mode == "RandomMorph":
                            # Continuous smooth morph between random 100% saturated neon colors
                            morph_t += 0.015 * mult
                            if morph_t >= 1.0:
                                morph_t = 0.0
                                current_hues = list(target_hues)
                                target_hues = [(h + 0.25 + 0.5 * random.random()) % 1.0 for h in current_hues]
                            
                            ease = (1.0 - math.cos(morph_t * math.pi)) / 2.0
                            morph_zones = {}
                            for i, zid in enumerate(["1", "2", "3", "4"]):
                                diff = (target_hues[i] - current_hues[i] + 0.5) % 1.0 - 0.5
                                h = (current_hues[i] + diff * ease) % 1.0
                                r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(h, 1.0, 1.0)]
                                morph_zones[zid] = (r, g, b)
                            
                            HardwareEngine.send_4zone_rgb(morph_zones, self.brightness, set_mode_static=force_static)
                            if self.config.get("mecha_bar_enabled", True):
                                mr, mg, mb = morph_zones["1"]
                                self._sync_mecha_bar(mr, mg, mb)
                            self._ui_dispatch(self._update_virtual_keyboard_preview, morph_zones)

                        elif self.effect_mode == "BreathingPulse":
                            cur_bright_pct = (math.sin(step * 0.05) + 1.0) / 2.0
                            dyn_bright = int((0.15 + 0.85 * cur_bright_pct) * self.brightness)
                            HardwareEngine.send_4zone_rgb(self.zones, dyn_bright, set_mode_static=force_static)
                            if self.config.get("mecha_bar_enabled", True):
                                mr, mg, mb = self.zones.get("1", (56, 189, 248))
                                self._sync_mecha_bar(mr, mg, mb)
                            b_factor = dyn_bright / 100.0
                            preview_zones = {z: (int(r*b_factor), int(g*b_factor), int(b*b_factor)) for z, (r,g,b) in self.zones.items()}
                            self._ui_dispatch(self._update_virtual_keyboard_preview, preview_zones)

                        elif self.effect_mode == "ColorShift":
                            hue_dir = -1.0 if "Right to Left" in direction else 1.0
                            hue = (step * 0.003 * hue_dir) % 1.0
                            r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(hue, 1.0, 1.0)]
                            shift_zones = {z: (r, g, b) for z in ["1", "2", "3", "4"]}
                            HardwareEngine.send_4zone_rgb(shift_zones, self.brightness, set_mode_static=force_static)
                            if self.config.get("mecha_bar_enabled", True):
                                self._sync_mecha_bar(r, g, b)
                            self._ui_dispatch(self._update_virtual_keyboard_preview, shift_zones)

                        elif self.effect_mode == "ScreenSync":
                            # Multi-zone 4-column spatial OR Single unified full-keyboard screen sync
                            sync_mode = getattr(self, 'screen_sync_mode', "Spatial")
                            now = time.time()
                            if now - last_screen_sync > 0.05:
                                last_screen_sync = now
                                try:
                                    if sct_inst is None:
                                        sct_inst = mss.MSS() if hasattr(mss, 'MSS') else mss.mss()
                                    mon = sct_inst.monitors[1] if len(sct_inst.monitors) > 1 else sct_inst.monitors[0]
                                    mw, mh = mon["width"], mon["height"]

                                    top_offset = int(mh * 0.04)
                                    left_offset = int(mw * 0.02)
                                    capture_w = max(10, int(mw * 0.96))
                                    capture_h = max(10, int(mh * 0.92))

                                    bbox = {
                                        "top": mon["top"] + top_offset,
                                        "left": mon["left"] + left_offset,
                                        "width": capture_w,
                                        "height": capture_h
                                    }
                                    grab_img = sct_inst.grab(bbox)
                                    pil_img = Image.frombytes("RGB", grab_img.size, grab_img.rgb)

                                    if sync_mode == "Unified":
                                        small = pil_img.resize((1, 1), Image.Resampling.BOX)
                                        sr, sg, sb = small.getpixel((0, 0))
                                        target_rgb = process_screen_pixel(sr, sg, sb)
                                        for zid in ["1", "2", "3", "4"]:
                                            screen_targets[zid] = target_rgb
                                    else:
                                        small = pil_img.resize((4, 1), Image.Resampling.BOX)
                                        for i, zid in enumerate(["1", "2", "3", "4"]):
                                            sr, sg, sb = small.getpixel((i, 0))
                                            screen_targets[zid] = process_screen_pixel(sr, sg, sb)
                                except Exception:
                                    sct_inst = None
                                    try:
                                        from PIL import ImageGrab
                                        grab_fallback = ImageGrab.grab()
                                        if sync_mode == "Unified":
                                            small = grab_fallback.resize((1, 1), Image.Resampling.BOX)
                                            sr, sg, sb = small.getpixel((0, 0))[:3]
                                            target_rgb = process_screen_pixel(sr, sg, sb)
                                            for zid in ["1", "2", "3", "4"]:
                                                screen_targets[zid] = target_rgb
                                        else:
                                            small = grab_fallback.resize((4, 1), Image.Resampling.BOX)
                                            for i, zid in enumerate(["1", "2", "3", "4"]):
                                                sr, sg, sb = small.getpixel((i, 0))[:3]
                                                screen_targets[zid] = process_screen_pixel(sr, sg, sb)
                                    except Exception:
                                        pass

                            # Smooth exponential lerp (30-40 FPS)
                            sync_zones = {}
                            for zid in ["1", "2", "3", "4"]:
                                tr, tg, tb = screen_targets[zid]
                                cr, cg, cb = screen_current[zid]
                                cr += (tr - cr) * 0.35
                                cg += (tg - cg) * 0.35
                                cb += (tb - cb) * 0.35
                                screen_current[zid] = [cr, cg, cb]
                                sync_zones[zid] = (int(cr), int(cg), int(cb))

                            HardwareEngine.send_4zone_rgb(sync_zones, self.brightness, set_mode_static=force_static)
                            if self.config.get("mecha_bar_enabled", True):
                                mr = int(sum(c[0] for c in sync_zones.values()) / 4)
                                mg = int(sum(c[1] for c in sync_zones.values()) / 4)
                                mb = int(sum(c[2] for c in sync_zones.values()) / 4)
                                self._sync_mecha_bar(mr, mg, mb)
                            self._ui_dispatch(self._update_virtual_keyboard_preview, sync_zones)

                        elif self.effect_mode == "ReactiveTyping":
                            # Dynamic Per-Zone Reactive Keystroke Luminescence
                            now = time.time()
                            reactive_zones = render_reactive_typing(
                                getattr(self, '_zone_typing_times', {}),
                                self.zones,
                                now=now,
                                decay_duration=0.60
                            )
                            HardwareEngine.send_4zone_rgb(reactive_zones, self.brightness, set_mode_static=force_static)
                            if self.config.get("mecha_bar_enabled", True):
                                hottest_zid = max(
                                    ("1", "2", "3", "4"),
                                    key=lambda z: sum(reactive_zones[z])
                                )
                                mr, mg, mb = reactive_zones[hottest_zid]
                                self._sync_mecha_bar(mr, mg, mb)
                            self._ui_dispatch(self._update_virtual_keyboard_preview, reactive_zones)

                        elif self.effect_mode == "AudioSync":
                            audio_zones = render_audio_visualizer(
                                getattr(self, "audio_levels", (0.0,) * 4),
                                getattr(self, "audio_beat", 0.0),
                                step,
                                base_zones=self.zones,
                            )
                            HardwareEngine.send_4zone_rgb(audio_zones, self.brightness, set_mode_static=force_static)
                            if self.config.get("mecha_bar_enabled", True):
                                hottest = max(audio_zones, key=lambda z: sum(audio_zones[z]))
                                hz = audio_zones[hottest]
                                self._sync_mecha_bar(hz[0], hz[1], hz[2])
                            self._ui_dispatch(self._update_virtual_keyboard_preview, audio_zones)

                        hardware_error = HardwareEngine.get_last_error()
                        if hardware_error and hardware_error != reported_hardware_error:
                            reported_hardware_error = hardware_error
                            self._ui_dispatch(
                                self._set_hardware_status,
                                False,
                                "Keyboard lighting",
                                hardware_error,
                            )
                        elif not hardware_error and reported_hardware_error:
                            reported_hardware_error = ""
                            self._ui_dispatch(self._set_hardware_status, True, "Keyboard lighting")

                        step += mult
                        time.sleep(0.025)
                    except Exception:
                        time.sleep(0.04)
                else:
                    time.sleep(0.25)

        t = threading.Thread(target=effects_loop, daemon=True)
        t.start()

    def _start_backzone_effects_worker(self):
        """Drive custom rear effects with intelligent rules, rate limiting, and telemetry."""
        def effect_loop():
            phase = 0.0
            last_mode = None
            reported_error = ""
            last_lock_check = 0.0
            while self.running:
                mode = backzone_ui.available_rear_mode(getattr(self, "bz_mode", 1))
                self.bz_mode = mode
                if self._suspended or self._rear_test_active:
                    time.sleep(0.2)
                    continue
                if time.monotonic() - last_lock_check >= 1.0:
                    last_lock_check = time.monotonic()
                    try:
                        user32 = ctypes.windll.user32
                        user32.OpenInputDesktop.restype = ctypes.c_void_p
                        user32.CloseDesktop.argtypes = [ctypes.c_void_p]
                        desk = user32.OpenInputDesktop(0, False, 0x0100)
                        self._session_locked = not bool(desk)
                        if desk:
                            user32.CloseDesktop(desk)
                    except Exception:
                        pass
                enabled = self._backzone_allowed()

                if not enabled or mode == 15:
                    if last_mode != 15:
                        if SerialEngine.send_backzone_rgb(15, 0, 0, 0, 1, 0):
                            last_mode = 15
                    time.sleep(0.3)
                    continue

                if mode >= 100:
                    if mode != last_mode:
                        phase = 0.0
                        last_mode = mode
                    speed = max(1, min(9, int(getattr(self, "bz_speed", 3))))
                    
                    audio_vol = getattr(self, "audio_volume", 0.0)
                    audio_levels = getattr(self, "audio_levels", [0.0]*4)
                    audio_beat = getattr(self, "audio_beat", 0.0)

                    rgb, frame_brightness = render_backzone_effect(
                        mode, phase, self.bz_color1, self.bz_color2, self.bz_brightness,
                        audio_volume=audio_vol, audio_levels=audio_levels, audio_beat=audio_beat,
                        temp_celsius=self._rear_temperature(),
                        bat_pct=getattr(self, "battery_val", 100),
                        on_ac=getattr(self, "on_ac_val", True),
                        audio_sensitivity=self.config.get("bz_audio_sensitivity", 1.0),
                        audio_decay=self.config.get("bz_audio_decay", 0.85),
                    )
                    ok = SerialEngine.send_backzone_rgb(
                        effect=1, r1=rgb[0], g1=rgb[1], b1=rgb[2],
                        speed=speed, bright=frame_brightness
                    )
                    error = SerialEngine.get_last_error()
                    if not ok and error != reported_error:
                        reported_error = error
                        self._ui_dispatch(self._set_hardware_status, False, "Rear Back Zone", error)
                    elif ok and reported_error:
                        reported_error = ""
                        self._ui_dispatch(self._set_hardware_status, True, "Rear Back Zone")
                    phase = (phase + (0.005 + speed * 0.003)) % 1.0
                    
                    fps = max(10, min(30, int(self.config.get("bz_fps_limit", 20))))
                    time.sleep(1.0 / fps)
                else:
                    # Firmware effects must be restored after a power rule releases them.
                    # Do not resend each frame: that restarts autonomous motion.
                    # Include controls so changes and failed writes are retried.
                    native_state = (mode, tuple(self.bz_color1), tuple(self.bz_color2),
                                    self.bz_speed, self.bz_brightness)
                    if last_mode != native_state and self._apply_backzone_hardware():
                        last_mode = native_state
                    time.sleep(0.20)

        threading.Thread(target=effect_loop, daemon=True).start()


    def _needs_audio(self):
        return (
            not getattr(self, "_suspended", False) and (
                (self.heartbeat_active and self.effect_mode == "AudioSync") or
                (self._backzone_allowed() and self.bz_mode in (110, 111))
            )
        )

    def _start_audio_visualizer_worker(self):
        self.audio_volume = 0.0
        self.audio_levels = [0.0] * 4
        self.audio_beat = 0.0
        if not hasattr(self, 'audio_device_name'):
            self.audio_device_name = "Detecting Audio Output..."

        def find_loopback():
            speaker = None
            try:
                speaker = sc.default_speaker()
            except Exception:
                try:
                    speakers = sc.all_speakers()
                    if speakers:
                        speaker = speakers[0]
                except Exception:
                    pass

            mic = None
            if speaker:
                # 1. Direct lookup with include_loopback=True
                try:
                    mic = sc.get_microphone(id=speaker.id, include_loopback=True)
                except Exception:
                    pass

                # 2. Match by ID or Name from all loopback microphones
                if not mic:
                    try:
                        microphones = sc.all_microphones(include_loopback=True)
                        speaker_id = str(getattr(speaker, "id", "")).lower()
                        speaker_name = str(getattr(speaker, "name", "")).lower()
                        for device in microphones:
                            if not getattr(device, "isloopback", False):
                                continue
                            device_id = str(getattr(device, "id", "")).lower()
                            device_name = str(getattr(device, "name", "")).lower()
                            if speaker_id and (speaker_id in device_id or device_id in speaker_id):
                                mic = device
                                break
                            if speaker_name and (speaker_name in device_name or device_name in speaker_name):
                                mic = device
                                break
                    except Exception:
                        pass

            # 3. Fallback: Any loopback microphone
            if not mic:
                try:
                    for m in sc.all_microphones(include_loopback=True):
                        if getattr(m, "isloopback", False):
                            mic = m
                            break
                except Exception:
                    pass

            # 4. Final fallback: default microphone
            if not mic:
                try:
                    mic = sc.default_microphone()
                except Exception:
                    pass

            return speaker, mic

        def audio_loop():
            sample_rate = 48000
            bands = ((45, 180), (180, 700), (700, 2800), (2800, 12000))
            agc_peak = np.full(4, 5.0e-5, dtype=float)
            noise_floor = np.full(4, 1.0e-8, dtype=float)
            bass_average = 0.0
            device_check_counter = 0

            while self.running:
                try:
                    if not self._needs_audio():
                        self.audio_levels = [0.0] * 4
                        self.audio_beat = self.audio_volume = 0.0
                        time.sleep(0.25)
                        continue
                    speaker, mic = find_loopback()
                    if not mic:
                        time.sleep(1.0)
                        continue

                    current_sp_id = str(getattr(speaker, "id", "")) if speaker else ""
                    dev_name = getattr(speaker, "name", "Audio Output") if speaker else "Default Audio"
                    self.audio_device_name = dev_name

                    with mic.recorder(samplerate=sample_rate, channels=2) as rec:
                        while self.running:
                            device_check_counter += 1
                            if device_check_counter >= 35:
                                device_check_counter = 0
                                try:
                                    cur_sp = sc.default_speaker()
                                    if str(getattr(cur_sp, "id", "")) != current_sp_id:
                                        # Audio endpoint switched (e.g. headphones plugged/unplugged)
                                        break
                                except Exception:
                                    pass

                            if not self._needs_audio():
                                break  # Close the recorder while audio effects are inactive.

                            data = rec.record(numframes=1024)
                            mono = np.asarray(data, dtype=np.float32)
                            if mono.ndim > 1:
                                mono = np.mean(mono, axis=1)
                            if mono.size == 0:
                                continue

                            mono -= float(np.mean(mono))
                            rms = float(np.sqrt(np.mean(mono * mono)))

                            # Digital silence gating
                            if rms < 1.0e-7:
                                self.audio_levels = [lvl * 0.72 for lvl in self.audio_levels]
                                self.audio_beat *= 0.55
                                self.audio_volume = 0.0
                                continue

                            windowed = mono * np.hanning(mono.size)
                            spectrum = np.abs(np.fft.rfft(windowed)) / max(1, mono.size)
                            freqs = np.fft.rfftfreq(mono.size, 1.0 / sample_rate)
                            raw = np.array([
                                float(np.sqrt(np.mean(spectrum[(freqs >= lo) & (freqs < hi)] ** 2)))
                                for lo, hi in bands
                            ])

                            # Adaptive noise floor tracking
                            noise_floor = np.minimum(noise_floor * 1.002, np.maximum(raw * 0.55, 1.0e-8))
                            adjusted = np.maximum(0.0, raw - noise_floor)

                            # Adaptive peak: fast attack, smooth decay (enables high sensitivity on quiet headphones / low volume)
                            agc_peak = np.maximum(adjusted, agc_peak * 0.978)
                            agc_peak = np.maximum(agc_peak, 1.0e-6)

                            gain_mult = max(0.5, min(3.0, float(getattr(self, "audio_gain_multiplier", 1.5))))
                            ratio = (adjusted / agc_peak) * gain_mult
                            normalized = np.clip(ratio ** 0.65, 0.0, 1.0)

                            old = np.asarray(self.audio_levels, dtype=float)
                            smoothed = np.where(
                                normalized > old,
                                old * 0.20 + normalized * 0.80,   # Fast attack
                                old * 0.76 + normalized * 0.24    # Smooth decay
                            )
                            bass = float(normalized[0])
                            bass_average = bass_average * 0.90 + bass * 0.10
                            beat = max(0.0, min(1.0, (bass - bass_average - 0.08) * 4.8))

                            self.audio_levels = smoothed.tolist()
                            self.audio_beat = max(beat, self.audio_beat * 0.70)
                            self.audio_volume = max(rms, self.audio_volume * 0.75)
                except Exception:
                    self.audio_levels = [0.0] * 4
                    self.audio_beat = 0.0
                    time.sleep(0.50)

        t = threading.Thread(target=audio_loop, daemon=True)
        t.start()

    def _start_telemetry_worker(self):
        """Periodically polls CPU, GPU, RAM, Disk I/O, Network, and Battery stats and updates GUI safely."""
        def telem_loop():
            next_temperature_read = 0.0
            while self.running:
                try:
                    cpu_p = psutil.cpu_percent(interval=1.0)
                    vmem = psutil.virtual_memory()
                    ram_p = vmem.percent
                    ram_used_gb = vmem.used / (1024 ** 3)
                    ram_total_gb = vmem.total / (1024 ** 3)

                    battery = psutil.sensors_battery()
                    bat_pct = battery.percent if battery else 100
                    on_ac = battery.power_plugged if battery else True
                    self.battery_val = bat_pct
                    self.on_ac_val = on_ac

                    # Delta Disk I/O calculation
                    now = time.time()
                    dt = max(0.1, now - getattr(self, 'last_io_time', now))
                    self.last_io_time = now

                    dio = psutil.disk_io_counters()
                    if dio and getattr(self, 'last_disk_io', None):
                        self.current_read_mbs = max(0.0, (dio.read_bytes - self.last_disk_io.read_bytes) / (1024 * 1024 * dt))
                        self.current_write_mbs = max(0.0, (dio.write_bytes - self.last_disk_io.write_bytes) / (1024 * 1024 * dt))
                    self.last_disk_io = dio

                    # Delta Network bandwidth calculation
                    nio = psutil.net_io_counters()
                    if nio and getattr(self, 'last_net_io', None):
                        self.current_down_kbs = max(0.0, (nio.bytes_recv - self.last_net_io.bytes_recv) / (1024 * dt))
                        self.current_up_kbs = max(0.0, (nio.bytes_sent - self.last_net_io.bytes_sent) / (1024 * dt))
                    self.last_net_io = nio
                    net_recv_gb = (nio.bytes_recv / (1024 ** 3)) if nio else 0.0
                    net_sent_gb = (nio.bytes_sent / (1024 ** 3)) if nio else 0.0

                    # Disk C: Storage Usage
                    try:
                        du = psutil.disk_usage("C:\\")
                        disk_used_gb = du.used / (1024 ** 3)
                        disk_total_gb = du.total / (1024 ** 3)
                        disk_pct = du.percent
                    except Exception:
                        disk_used_gb, disk_total_gb, disk_pct = 0.0, 0.0, 0.0

                    # Real Windows GPU Engine counter. None means the counter is
                    # unavailable; never manufacture a value from CPU activity.
                    gpu_p = HardwareEngine.get_gpu_3d_usage()

                    if time.monotonic() >= next_temperature_read:
                        readings = HardwareEngine.get_temperature_readings()
                        self.cpu_temp_val = readings["CPU"]
                        self.gpu_temp_val = readings["GPU"]
                        next_temperature_read = time.monotonic() + (5.0 if any(v is not None for v in readings.values()) else 30.0)
                    # Track CPU & GPU history for 60s sparkline graphs & AI Governor
                    self.cpu_history.append(cpu_p)
                    if len(self.cpu_history) > 60:
                        self.cpu_history.pop(0)

                    gpu_hist_val = gpu_p if gpu_p is not None else 0.0
                    self.gpu_history.append(gpu_hist_val)
                    if len(self.gpu_history) > 60:
                        self.gpu_history.pop(0)

                    # Critical Battery Protection (<8% charge): cut heavy rear LED draw and clamp brightness
                    if not on_ac and bat_pct <= 8:
                        if self.config.get("mecha_bar_enabled", True):
                            try:
                                HardwareEngine.send_mecha_bar(0, 0, 0, False)
                            except Exception:
                                pass
                        if self.brightness > 15:
                            self._ui_dispatch(self._set_brightness_pct, 10)
                        if self.config.get("power_mode") != "Quiet":
                            self._ui_dispatch(self._ai_set_mode, "Quiet", "Critical battery below 8%", True)

                    # Low Battery Emergency Saver (<20%)
                    elif not on_ac and bat_pct <= 20 and self.config.get("emergency_battery_saver", True):
                        if self.brightness > 15:
                            self._ui_dispatch(self._set_brightness_pct, 10)
                        if self.config.get("power_mode") != "Quiet":
                            self._ui_dispatch(self._ai_set_mode, "Quiet", "Low battery below 20%")

                    if self.config.get("auto_switch_on_ac", True) and self.last_ac_state is not None:
                        if on_ac != self.last_ac_state:
                            if on_ac:
                                self._ui_dispatch(self._on_ac_connected)
                            else:
                                self._ui_dispatch(self._on_battery_disconnected)
                    self.last_ac_state = on_ac

                    self._ui_dispatch(
                        self._update_telemetry_ui,
                        cpu_p, ram_p, ram_used_gb, ram_total_gb, bat_pct, on_ac,
                        gpu_p, disk_used_gb, disk_total_gb, disk_pct,
                        self.current_read_mbs, self.current_write_mbs,
                        self.current_down_kbs, self.current_up_kbs,
                        net_recv_gb, net_sent_gb
                    )
                except Exception:
                    pass
                time.sleep(1.0)

        t = threading.Thread(target=telem_loop, daemon=True)
        t.start()

    def _compute_live_system_status(self, cpu_p, cpu_temp, gpu_p, gpu_temp, bat_pct, on_ac):
        cur_mode = self.mode_var.get() if hasattr(self, "mode_var") else "Balanced"
        bat_pct = int(bat_pct) if bat_pct is not None else 100
        cpu_p = float(cpu_p) if cpu_p is not None else 0.0
        if not on_ac and bat_pct <= 15:
            return ("🔴 LIVE: CRITICAL BATTERY", THEME["accent_rose"],
                    f"Battery at {bat_pct}%! Plug in charger immediately.")
        max_temp = max(t for t in (cpu_temp, gpu_temp) if t is not None) if any(t is not None for t in (cpu_temp, gpu_temp)) else None
        if max_temp is not None and max_temp >= 85:
            action = "Beast Mode active." if cur_mode == "Beast" else "Suggested: Switch to Beast Mode / Boost Fan."
            return ("🔥 LIVE: HIGH HEAT", THEME["accent_rose"],
                    f"Temps peaking at {max_temp:.0f}°C. {action}")
        gpu_active = (gpu_p is not None and gpu_p >= 40) or (gpu_temp is not None and gpu_temp >= 70)
        cpu_heavy = cpu_p >= 75
        if gpu_active or cpu_heavy:
            if cur_mode != "Beast":
                return ("🎮 LIVE: HEAVY LOAD", THEME["accent_cyan"],
                        "Heavy workload active. Suggested: Beast Mode for peak FPS.")
            return ("🚀 LIVE: BEAST PERFORMANCE", THEME["accent_cyan"],
                    "High workload. Full performance profile unlocked.")
        if not on_ac and bat_pct <= 30:
            if cur_mode != "Quiet":
                return ("🟡 LIVE: LOW BATTERY", THEME["accent_amber"],
                        f"Battery {bat_pct}%. Suggested: Switch to Quiet Mode.")
            return ("🔋 LIVE: ECO SAVER", THEME["accent_amber"],
                    f"Quiet Mode saving power on battery ({bat_pct}%).")
        if not on_ac:
            if cur_mode == "Beast":
                return ("🔋 LIVE: ON BATTERY", THEME["accent_amber"],
                        "Beast draws high power. Suggested: Balanced Mode.")
            return ("🔋 LIVE: ON BATTERY", THEME["accent_green"],
                    f"Operating on battery ({bat_pct}%). Normal endurance.")
        if max_temp is not None and max_temp >= 72:
            return ("⚡ LIVE: ACTIVE WORKLOAD", THEME["accent_blue"],
                    f"Temps at {max_temp:.0f}°C. Airflow maintaining stability.")
        return ("🟢 LIVE: SYSTEM OPTIMAL", THEME["accent_green"],
                f"Cool & quiet ({cur_mode} Mode). All systems normal.")

    def _update_telemetry_ui(self, cpu_p, ram_p, ram_used_gb, ram_total_gb, bat_pct, on_ac,
                            gpu_p=0.0, disk_used_gb=0.0, disk_total_gb=0.0, disk_pct=0.0,
                            read_mbs=0.0, write_mbs=0.0, down_kbs=0.0, up_kbs=0.0,
                            net_recv_gb=0.0, net_sent_gb=0.0):
        try:
            self._refresh_automation_status()
            status_text, status_color, action_text = self._compute_live_system_status(
                cpu_p, self.cpu_temp_val, gpu_p, self.gpu_temp_val, bat_pct, on_ac
            )

            cpu_color = THEME["accent_rose"] if cpu_p > 90 else THEME["accent_amber"] if cpu_p > 70 else THEME["accent_blue"]
            cpu_temp_display = f"{self.cpu_temp_val:.0f}°C" if self.cpu_temp_val is not None else "Normal"
            gpu_temp_display = f"{self.gpu_temp_val:.0f}°C" if self.gpu_temp_val is not None else ("Active" if gpu_p else "Standby")

            # Update Top HUD Banner inside System Monitor
            if hasattr(self, 'telemetry_status_badge'):
                self.telemetry_status_badge.configure(text=status_text, text_color=status_color)
            if hasattr(self, 'telemetry_action_lbl'):
                self.telemetry_action_lbl.configure(text=action_text)
            if hasattr(self, 'telemetry_cpu_temp_pill'):
                self.telemetry_cpu_temp_pill.configure(text=f"💻 CPU: {cpu_temp_display}", text_color=cpu_color)
            if hasattr(self, 'telemetry_gpu_temp_pill'):
                gpu_pill_color = THEME["accent_rose"] if (self.gpu_temp_val and self.gpu_temp_val >= 80) else THEME["accent_green"]
                self.telemetry_gpu_temp_pill.configure(text=f"🎮 GPU: {gpu_temp_display}", text_color=gpu_pill_color)

            if hasattr(self, 'hero_cpu_lbl'):
                self.hero_cpu_lbl.configure(text=f"{cpu_p:.1f}%", text_color=cpu_color)
            if hasattr(self, 'cpu_pct_lbl'):
                self.cpu_pct_lbl.configure(text="13th Gen Intel Core i5-13420H (8C/12T • 12MB Cache)")
            if hasattr(self, 'cpu_temp_chip'):
                self.cpu_temp_chip.configure(text=f"🌡️ CPU: {cpu_temp_display}", text_color=cpu_color)
            if hasattr(self, 'cpu_bar'):
                self.cpu_bar.set(cpu_p / 100.0)
                self.cpu_bar.configure(progress_color=cpu_color)
            if hasattr(self, 'hero_cpu_bar') and self.hero_cpu_bar != self.cpu_bar:
                self.hero_cpu_bar.set(cpu_p / 100.0)
                self.hero_cpu_bar.configure(progress_color=cpu_color)

            # Draw CPU Circular Gauge & 60-Second Real-Time Sparkline
            if hasattr(self, 'cpu_gauge_canvas'):
                self._draw_donut_gauge(self.cpu_gauge_canvas, cpu_p, cpu_temp_display, cpu_color, "CPU LOAD")
            self._draw_cpu_sparkline()

            if hasattr(self, 'ram_pct_lbl'):
                self.ram_pct_lbl.configure(text=f"RAM Usage: {ram_used_gb:.1f} GB / {ram_total_gb:.1f} GB ({ram_p:.1f}%)")
            if hasattr(self, 'ram_bar'):
                self.ram_bar.set(ram_p / 100.0)

            # GPU Telemetry
            if gpu_p is None:
                if hasattr(self, 'gpu_pct_lbl'):
                    self.gpu_pct_lbl.configure(text="GPU 3D Engine Load: Standby", text_color=THEME["text_muted"])
                if hasattr(self, 'gpu_bar'):
                    self.gpu_bar.set(0.0)
                if hasattr(self, 'hero_gpu_lbl'):
                    self.hero_gpu_lbl.configure(text="Standby", text_color=THEME["text_muted"])
                if hasattr(self, 'hero_gpu_bar') and self.hero_gpu_bar != self.gpu_bar:
                    self.hero_gpu_bar.set(0.0)
                if hasattr(self, 'gpu_temp_chip'):
                    self.gpu_temp_chip.configure(text=f"🌡️ GPU: {gpu_temp_display}", text_color=THEME["text_muted"])
                if hasattr(self, 'gpu_gauge_canvas'):
                    self._draw_donut_gauge(self.gpu_gauge_canvas, 0.0, gpu_temp_display, THEME["text_muted"], "GPU LOAD")
            else:
                gpu_color = THEME["accent_rose"] if gpu_p > 85 else THEME["accent_amber"] if gpu_p > 60 else THEME["accent_green"]
                if hasattr(self, 'hero_gpu_lbl'):
                    self.hero_gpu_lbl.configure(text=f"{gpu_p:.1f}%", text_color=gpu_color)
                if hasattr(self, 'gpu_pct_lbl'):
                    self.gpu_pct_lbl.configure(text="Intel UHD Graphics & NVIDIA RTX 4050")
                if hasattr(self, 'gpu_temp_chip'):
                    self.gpu_temp_chip.configure(text=f"🌡️ GPU: {gpu_temp_display}", text_color=gpu_color)
                if hasattr(self, 'gpu_bar'):
                    self.gpu_bar.set(gpu_p / 100.0)
                    self.gpu_bar.configure(progress_color=gpu_color)
                if hasattr(self, 'hero_gpu_bar') and self.hero_gpu_bar != self.gpu_bar:
                    self.hero_gpu_bar.set(gpu_p / 100.0)
                    self.hero_gpu_bar.configure(progress_color=gpu_color)
                if hasattr(self, 'gpu_gauge_canvas'):
                    self._draw_donut_gauge(self.gpu_gauge_canvas, gpu_p, gpu_temp_display, gpu_color, "GPU LOAD")

            # Draw GPU 60-Second Real-Time Sparkline
            self._draw_gpu_sparkline()

            if hasattr(self, 'hero_ram_lbl'):
                self.hero_ram_lbl.configure(text=f"{ram_p:.0f}%")
                self.hero_ram_bar.set(ram_p / 100.0)

            # Storage & Disk I/O
            if hasattr(self, 'disk_stat_lbl'):
                self.disk_stat_lbl.configure(text=f"Drive C: {disk_used_gb:.1f} GB Used / {disk_total_gb:.1f} GB Total ({disk_pct:.1f}%)")
            if hasattr(self, '_ram_chart_samples'):
                self._ram_chart_samples=(self._ram_chart_samples+[ram_p])[-60:]
                self._disk_chart_samples=(self._disk_chart_samples+[disk_pct])[-60:]
                neon_ui.sparkline(self.ram_graph_canvas,self._ram_chart_samples,'#AC6AFF')
                neon_ui.sparkline(self.disk_graph_canvas,self._disk_chart_samples,'#FFC331')
            for key, value in (('CPU', self.cpu_temp_val), ('GPU', self.gpu_temp_val)):
                sensor=getattr(self,'sensor_labels',{}).get(key)
                if sensor:
                    sensor.configure(text=f'{value:.0f}°C' if value is not None else 'Not available')
                about=getattr(self,'_about_live_labels',{}).get(key.lower()+'_temp')
                if about:
                    about.configure(text=f'{value:.0f}°C' if value is not None else 'N/A · Sensor not available')
            if hasattr(self, 'disk_bar'):
                self.disk_bar.set(disk_pct / 100.0)
            if hasattr(self, 'disk_io_lbl'):
                self.disk_io_lbl.configure(text=f"Active Read: {read_mbs:.1f} MB/s • Active Write: {write_mbs:.1f} MB/s")

            # Network Telemetry
            if hasattr(self, 'net_speed_lbl'):
                down_txt = f"{down_kbs/1024.0:.1f} MB/s" if down_kbs >= 1024.0 else f"{down_kbs:.1f} KB/s"
                up_txt = f"{up_kbs/1024.0:.1f} MB/s" if up_kbs >= 1024.0 else f"{up_kbs:.1f} KB/s"
                self.net_speed_lbl.configure(text=f"⬇️ Download: {down_txt}    ⬆️ Upload: {up_txt}")
            if hasattr(self, 'net_total_lbl'):
                self.net_total_lbl.configure(text=f"Total Received: {net_recv_gb:.2f} GB • Total Sent: {net_sent_gb:.2f} GB")

            bat_color = THEME["accent_green"]
            if not on_ac:
                bat_color = THEME["accent_rose"] if bat_pct < 15 else THEME["accent_amber"] if bat_pct < 30 else THEME["accent_green"]

            ac_text = f"⚡ AC: {bat_pct}%" if on_ac else f"🔋 Battery: {bat_pct}%"
            if hasattr(self, 'top_bat_pill'):
                self.top_bat_pill.configure(
                    text=ac_text,
                    text_color=THEME["accent_green"] if on_ac else bat_color
                )

            charge_desc = "AC Power Adapter Connected • Fast Charging" if on_ac else "Operating on Lithium-Ion Battery Power"
            if hasattr(self, 'bat_stat_lbl'):
                self.bat_stat_lbl.configure(text=f"{charge_desc} ({bat_pct}%)", text_color=bat_color)
            if hasattr(self, 'bat_bar'):
                self.bat_bar.set(bat_pct / 100.0)
                self.bat_bar.configure(progress_color=bat_color)
            if hasattr(self, 'hero_bat_lbl'):
                self.hero_bat_lbl.configure(text=f"{bat_pct}%", text_color=bat_color)
                self.hero_bat_bar.set(bat_pct / 100.0)
                self.hero_bat_bar.configure(progress_color=bat_color)
            if hasattr(self, 'telemetry_bat_sub_lbl') and self.telemetry_bat_sub_lbl.winfo_exists():
                try:
                    boot_ts = psutil.boot_time()
                    uptime_mins = int((time.time() - boot_ts) / 60)
                    hrs, mins = divmod(uptime_mins, 60)
                    days, hrs = divmod(hrs, 24)
                    up_str = f"{days}d {hrs}h {mins}m" if days else f"{hrs}h {mins}m"
                    cap_info = getattr(self, '_cached_cap_info', "57.0 Wh / 70.0 Wh")
                    self.telemetry_bat_sub_lbl.configure(text=f"Capacity: {cap_info} • ⏱️ Uptime: {up_str}")
                except Exception:
                    pass

            # Sidebar Mini-Badges & Live Status
            status_text, status_color, action_text = self._compute_live_system_status(
                cpu_p, self.cpu_temp_val, gpu_p, self.gpu_temp_val, bat_pct, on_ac
            )
            if hasattr(self, 'side_status_badge'):
                self.side_status_badge.configure(text="●  System monitor", text_color=status_color)
            if hasattr(self, 'side_action_lbl'):
                self.side_action_lbl.configure(text=action_text)

            if hasattr(self, 'side_cpu_lbl'):
                cpu_temp_str = f" • {self.cpu_temp_val:.0f}°C" if self.cpu_temp_val is not None else ""
                self.side_cpu_lbl.configure(text=f"💻 CPU: {cpu_p:.0f}%{cpu_temp_str}", text_color=cpu_color)
                self.side_cpu_bar.set(max(0.0, min(1.0, cpu_p / 100.0)))
                self.side_cpu_bar.configure(progress_color=cpu_color)
            if hasattr(self, 'side_gpu_lbl'):
                gpu_p_val = gpu_p if gpu_p is not None else 0.0
                gpu_temp_str = f" • {self.gpu_temp_val:.0f}°C" if self.gpu_temp_val is not None else ""
                gpu_color = THEME["accent_rose"] if (self.gpu_temp_val and self.gpu_temp_val >= 80) or gpu_p_val >= 85 else THEME["accent_amber"] if (self.gpu_temp_val and self.gpu_temp_val >= 70) or gpu_p_val >= 60 else THEME["accent_cyan"]
                if gpu_p is not None or self.gpu_temp_val is not None:
                    self.side_gpu_lbl.configure(text=f"🎮 GPU: {gpu_p_val:.0f}%{gpu_temp_str}", text_color=gpu_color)
                else:
                    self.side_gpu_lbl.configure(text="🎮 GPU: Standby", text_color=THEME["text_muted"])
                self.side_gpu_bar.set(max(0.0, min(1.0, gpu_p_val / 100.0)))
                self.side_gpu_bar.configure(progress_color=gpu_color)
            if hasattr(self, 'side_ram_lbl'):
                self.side_ram_lbl.configure(text=f"🧠 RAM: {ram_p:.0f}%")
                self.side_ram_bar.set(max(0.0, min(1.0, ram_p / 100.0)))
            if hasattr(self, 'side_bat_lbl'):
                bat_icon = "⚡" if on_ac else "🔋"
                bat_txt = f"{bat_icon} Battery: {bat_pct}%"
                bat_hp = getattr(self, '_cached_bat_health_pct', None)
                if bat_hp is not None and bat_hp > 0:
                    h_val = f"{bat_hp:.1f}%" if (bat_hp % 1 != 0) else f"{int(bat_hp)}%"
                    bat_txt += f" • Health: {h_val}"
                elif getattr(self, '_cached_bat_health', None) and self._cached_bat_health not in ("N/A", "Error", "WMI error", "Detecting…"):
                    bat_txt += f" • Health: {self._cached_bat_health}"
                self.side_bat_lbl.configure(text=bat_txt, text_color=bat_color)
                self.side_bat_bar.set(max(0.0, min(1.0, bat_pct / 100.0)))
                self.side_bat_bar.configure(progress_color=bat_color)

            # Mini HUD Floating Widget Update
            if getattr(self, 'hud_window', None) is not None and self.hud_window.winfo_exists():
                if hasattr(self, 'hud_cpu_lbl'):
                    self.hud_cpu_lbl.configure(text=f"💻 CPU: {cpu_p:.0f}%  |  🧠 RAM: {ram_p:.0f}%", text_color=cpu_color)
                if hasattr(self, 'hud_bat_lbl'):
                    plan_mode = getattr(self, 'mode_var', None)
                    p_text = plan_mode.get() if plan_mode else "Balanced"
                    self.hud_bat_lbl.configure(text=f"⚡ Battery: {bat_pct}%  |  🚀 Plan: {p_text}", text_color=bat_color)
                if hasattr(self, 'hud_fx_lbl'):
                    self.hud_fx_lbl.configure(text=f"✨ FX: {self.effect_mode}")
        except Exception:
            pass

    def _on_ac_connected(self):
        self._about_refresh_live(silent=True)
        if (not self.config.get("auto_switch_on_ac", True)
                or self._automatic_mode_change_blocked()):
            return
        self.mode_var.set("Beast")
        self._on_mode_selected("Charger connected", automatic=True)

    def _on_battery_disconnected(self):
        self._about_refresh_live(silent=True)
        if (not self.config.get("auto_switch_on_ac", True)
                or self._automatic_mode_change_blocked()):
            return
        self.mode_var.set("Quiet")
        self._on_mode_selected("Running on battery", automatic=True)

    # -----------------------------------------------------------------------
    # AI Background Workers (Governor & Game Sensor)
    # -----------------------------------------------------------------------
    def _start_ai_governor_worker(self):
        """Autonomous governor scaling thermal profiles based on sustained workload."""
        def governor_loop():
            while self.running:
                if (self.config.get("ai_governor", True)
                        and not self._automatic_mode_change_blocked()
                        and len(self.cpu_history) >= 5):
                    avg_cpu = sum(self.cpu_history[-5:]) / 5.0
                    cur_mode = self.config.get("power_mode", "Balanced")
                    if avg_cpu > 65.0 and cur_mode != "Beast":
                        self._ui_dispatch(self._ai_set_mode, "Beast", f"Load high ({avg_cpu:.0f}%) -> Boosted to Beast")
                    elif avg_cpu < 25.0 and cur_mode == "Beast" and len(self.cpu_history) >= 10:
                        avg_10 = sum(self.cpu_history[-10:]) / 10.0
                        if avg_10 < 25.0:
                            self._ui_dispatch(self._ai_set_mode, "Balanced", f"Idle ({avg_10:.0f}%) -> Scaled to Balanced")
                time.sleep(3.0)

        t = threading.Thread(target=governor_loop, daemon=True)
        t.start()

    def _ai_set_mode(self, mode: str, reason: str, force: bool = False):
        if self._automatic_mode_change_blocked(force=force):
            return
        if mode != "Quiet" and not getattr(self, "on_ac_val", True):
            battery = getattr(self, "battery_val", 100)
            if battery <= 8 or (battery <= 20 and self.config.get("emergency_battery_saver", True)):
                return
        self.mode_var.set(mode)
        self._on_mode_selected(reason, automatic=True)
        self.ai_status_badge.configure(text=f"Auto: {mode} ({reason})", text_color=THEME["accent_blue"])

    def _get_pnp_gpu_mode(self) -> str:
        """Detect GPU mode via Windows PnP/WMI (non-elevated fallback)."""
        try:
            import win32com.client
            import pythoncom
            pythoncom.CoInitialize()
            wmi = win32com.client.Dispatch("WbemScripting.SWbemLocator").ConnectServer(".", "root\\cimv2")
            items = wmi.ExecQuery("SELECT Name, Status, ConfigManagerErrorCode, Present FROM Win32_PnPEntity WHERE PNPClass = 'Display'")
            has_igpu_active = False
            has_dgpu_active = False
            for item in items:
                name = (item.Name or "").lower()
                is_present = getattr(item, "Present", False)
                err_code = getattr(item, "ConfigManagerErrorCode", -1)
                status = getattr(item, "Status", "")
                is_active = (is_present is True) and (err_code == 0) and (status == "OK")
                if "intel" in name or "amd" in name or "radeon" in name:
                    if is_active:
                        has_igpu_active = True
                elif "nvidia" in name or "geforce" in name or "rtx" in name or "gtx" in name:
                    if is_active:
                        has_dgpu_active = True

            if has_igpu_active and not has_dgpu_active:
                return "iGPU only"
            elif has_igpu_active and has_dgpu_active:
                return "Hybrid"
            elif has_dgpu_active and not has_igpu_active:
                return "dGPU only"
        except Exception:
            pass
        return "Unknown"

    def _show_windows_toast(self, title: str, message: str):
        """Display a native Windows Toast notification in bottom-right corner."""
        clean_title = title.replace('"', '`"').replace("'", "''")
        clean_message = message.replace('"', '`"').replace("'", "''")
        ps_script = f"""
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
        $template = @"
        <toast duration="short">
            <visual>
                <binding template="ToastGeneric">
                    <text>{clean_title}</text>
                    <text>{clean_message}</text>
                </binding>
            </visual>
            <audio src="ms-winsoundevent:Notification.Default" />
        </toast>
"@
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($template)
        $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
        $appId = '{{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}}\\WindowsPowerShell\\v1.0\\powershell.exe'
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)
        """
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        creationflags = 0x08000000  # CREATE_NO_WINDOW
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                startupinfo=startupinfo,
                creationflags=creationflags,
                capture_output=True,
                timeout=8
            )
        except Exception:
            pass

    def _check_and_notify_gpu_mode(self, game_name: str = "Game"):
        """Checks GPU mode upon game launch and alerts user if on iGPU or Hybrid via native Windows Toast."""
        mode = HardwareEngine.get_gpu_mode()
        if not mode or mode == "Unknown":
            mode = self._get_pnp_gpu_mode()
        if not mode:
            return

        mode_lower = mode.lower()
        # Silent on dGPU mode
        if "dgpu" in mode_lower:
            return

        if "igpu" in mode_lower:
            # iGPU: Remind and advise dGPU only (never recommend Hybrid)
            title = "⚠️ GPU Warning: Running on iGPU!"
            msg = f"{game_name} launched while on Integrated Graphics (iGPU). For smooth FPS and full performance, please switch your laptop to dGPU mode!"
            self._show_windows_toast(title, msg)
        elif "hybrid" in mode_lower:
            # Hybrid: Remind and suggest dGPU for peak performance
            title = "ℹ️ GPU Notice: Hybrid Mode Active"
            msg = f"{game_name} launched in Hybrid mode. Switch to dGPU mode to bypass the iGPU bottleneck and get peak FPS & lower latency!"
            self._show_windows_toast(title, msg)

    def _start_ai_game_detector_worker(self):
        """Detects launched games and creative apps to automatically engage Beast mode & Win-Lock."""
        def game_sensor_loop():
            was_in_game = False
            while self.running:
                if (self.config.get("ai_game_detector", True)
                        and not self._automatic_mode_change_blocked()):
                    in_game = False
                    detected_title = "Game"
                    for p in psutil.process_iter(['name', 'exe']):
                        try:
                            pname = (p.info.get('name') or "").lower()
                            if not pname or pname in IGNORE_GAME_EXES:
                                continue
                            if pname in KNOWN_GAME_TITLES:
                                in_game = True
                                detected_title = KNOWN_GAME_TITLES[pname]
                                break
                            pexe = (p.info.get('exe') or "").lower()
                            if pexe and any(kw in pexe for kw in GAME_PATH_KEYWORDS):
                                in_game = True
                                parent_folder = os.path.basename(os.path.dirname(p.info.get('exe') or ""))
                                detected_title = parent_folder if parent_folder.lower() not in {"bin", "binaries", "x64", "win64", "retail", "content", "shipping"} else os.path.splitext(pname)[0]
                                break
                        except Exception:
                            pass

                    if in_game and not was_in_game:
                        was_in_game = True
                        game_name = detected_title
                        self._ui_dispatch(lambda: self._on_game_launched(game_name))
                    elif not in_game and was_in_game:
                        was_in_game = False
                        self._ui_dispatch(self._on_game_closed)
                time.sleep(3.0)

        t = threading.Thread(target=game_sensor_loop, daemon=True)
        t.start()

    def _on_game_launched(self, game_name: str = "Game"):
        if self._automatic_mode_change_blocked():
            return
        self._pre_game_winlock = self.winlock_var.get()
        self.mode_var.set("Beast")
        self._on_mode_selected(f"Game detected: {game_name}", automatic=True)
        self.winlock_var.set(True)
        self._on_winlock_toggled()
        self.always_on_var.set(True)
        self._on_always_on_toggled()
        self._pre_game_bz_mode = getattr(self, "bz_mode", 1)
        if getattr(self, "bz_mode", 1) == 114:
            self._apply_backzone_hardware()
        if self.config.get("gpu_gaming_alert", True):
            threading.Thread(target=self._check_and_notify_gpu_mode, args=(game_name,), daemon=True).start()

    def _on_game_closed(self):
        if hasattr(self, "_pre_game_winlock"):
            self.winlock_var.set(self._pre_game_winlock)
            self._on_winlock_toggled()
        if hasattr(self, "_pre_game_bz_mode"):
            self.bz_mode = self._pre_game_bz_mode
            self._apply_backzone_hardware()

    # -----------------------------------------------------------------------
    # System Tray Integration
    # -----------------------------------------------------------------------
    def _init_tray_icon(self):
        try:
            if os.path.exists(ICON_PATH):
                img = Image.open(ICON_PATH)
            else:
                img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                draw.polygon([(32, 4), (58, 18), (58, 46), (32, 60), (6, 46), (6, 18)], fill="#0E1015", outline="#38BDF8", width=3)
                draw.polygon([(34, 14), (20, 34), (32, 34), (28, 50), (44, 28), (32, 28)], fill="#38BDF8")
        except Exception:
            img = Image.new("RGBA", (64, 64), color=(56, 189, 248, 255))

        menu = pystray.Menu(
            pystray.MenuItem("Open Dashboard", self._show_window, default=True),
            pystray.MenuItem("Toggle White / Dark Mode", self._tray_toggle_theme),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Toggle Always-On Backlight", self._tray_toggle_backlight),
            pystray.MenuItem("Performance Mode", pystray.Menu(
                pystray.MenuItem("🌿 Quiet Mode", lambda: self._tray_set_mode("Quiet")),
                pystray.MenuItem("⚖️ Balanced Mode", lambda: self._tray_set_mode("Balanced")),
                pystray.MenuItem("🚀 Beast Mode", lambda: self._tray_set_mode("Beast"))
            )),
            pystray.MenuItem("Quick Scenarios", pystray.Menu(
                pystray.MenuItem("🎮 Esports Beast", lambda: self._ui_dispatch(self._preset_scenario_beast)),
                pystray.MenuItem("💼 Stealth Office", lambda: self._ui_dispatch(self._preset_scenario_office)),
                pystray.MenuItem("🎬 Cinema Mode", lambda: self._ui_dispatch(self._preset_scenario_cinema))
            )),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit Toolkit", self._quit_app)
        )
        self.tray_icon = pystray.Icon("InfinixGTToolkit", img, "Infinix GT Toolkit", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _show_window(self):
        self._ui_dispatch(self._do_show_window)

    def _do_show_window(self):
        self.root.deiconify()
        self.root.state("normal")
        self.root.attributes("-topmost", True)
        self.root.lift()
        self.root.focus_force()
        self.root.after(100, lambda: self.root.attributes("-topmost", False))

    def _on_close_requested(self):
        if self.config.get("close_to_tray", True):
            self.root.withdraw()
        else:
            self._quit_app()

    def _tray_toggle_backlight(self):
        def toggle():
            self.always_on_var.set(not self.always_on_var.get())
            self._on_always_on_toggled()
        self._ui_dispatch(toggle)

    def _tray_set_mode(self, mode: str):
        def set_mode():
            self.mode_var.set(mode)
            self._on_mode_selected()
        self._ui_dispatch(set_mode)

    def _quit_app(self):
        if threading.get_ident() != self._ui_thread_id:
            self._ui_dispatch(self._quit_app)
            return
        if not self.running:
            return
        self._save_config()
        if not self._config_writer.close():
            messagebox.showerror("Settings save failed", self._config_writer.last_error or "Settings are still being saved. Please retry Exit.")
            return
        if hasattr(self, "_hardware_commands"):
            self._hardware_commands.close()
        self.running = False
        self._ui_mailbox.close()
        if hasattr(self, "backzone_view"):
            self.backzone_view.close()
        if hasattr(self, 'power_listener') and self.power_listener:
            try:
                self.power_listener.stop()
            except Exception:
                pass
        WindowsKeyLockEngine.set_lock(False)
        try:
            SoftwareFnLock.set_enabled(False)
        except Exception:
            pass
        if hasattr(self, '_reactive_hook') and self._reactive_hook:
            try:
                keyboard.unhook(self._reactive_hook)
            except Exception:
                pass
        try:
            self.tray_icon.stop()
        except Exception:
            pass
        try:
            HardwareEngine._close_device()
        except Exception:
            pass
        try:
            SerialEngine._close_port()
        except Exception:
            pass
        try:
            if hasattr(self, 'root') and self.root and self.root.winfo_exists():
                for job in self.root.tk.call("after", "info"):
                    self.root.after_cancel(job)
                self.root.destroy()
        except Exception:
            pass

    def _ui_dispatch(self, fn, *args, **kwargs):
        """Do not call Tcl/Tk from device, audio, hook, or tray worker threads."""
        if not getattr(self, 'running', True):
            return
        if threading.get_ident() == self._ui_thread_id:
            self._safe_execute(fn, *args, **kwargs)
            return
        name = getattr(fn, "__name__", "")
        key = name if name in ("_update_virtual_keyboard_preview", "_update_telemetry_ui") else None
        if name == "_update_virtual_keyboard_preview" and self.active_page != "lighting":
            return
        self._ui_mailbox.post(fn, args, kwargs, key=key)

    def _on_root_destroyed(self, event=None):
        if event is None or event.widget == getattr(self, "root", None):
            self.running = False
            for job_name in ("_drain_job", "_titlebar_job", "_anim_job", "_preview_job", "_debounce_job"):
                job = getattr(self, job_name, None)
                if job:
                    try:
                        self.root.after_cancel(job)
                    except Exception:
                        pass
                    setattr(self, job_name, None)
            if hasattr(self, "backzone_view"):
                try:
                    self.backzone_view.close()
                except Exception:
                    pass

    def _drain_ui_mailbox(self):
        if not self.running:
            return
        try:
            if not hasattr(self, 'root') or not self.root or not self.root.winfo_exists():
                return
            for fn, args, kwargs in self._ui_mailbox.take():
                self._safe_execute(fn, *args, **kwargs)
            if self.running and hasattr(self, 'root') and self.root and self.root.winfo_exists():
                self._drain_job = self.root.after(40, self._drain_ui_mailbox)
        except Exception:
            pass

    def _safe_execute(self, fn, *args, **kwargs):
        if not getattr(self, 'running', True):
            return
        try:
            if hasattr(self, 'root') and self.root and self.root.winfo_exists():
                fn(*args, **kwargs)
        except Exception:
            log_crash_exception(*sys.exc_info(), context="UI callback")

    # -----------------------------------------------------------------------
    # Utilities
    # -----------------------------------------------------------------------
    @staticmethod
    def _rgb_to_hex(rgb) -> str:
        return f"#{int(rgb[0]):02X}{int(rgb[1]):02X}{int(rgb[2]):02X}"


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def request_admin_elevation():
    if not is_admin():
        try:
            if getattr(sys, 'frozen', False):
                executable = sys.executable
                params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
            else:
                executable = sys.executable
                params = f'"{os.path.abspath(__file__)}" ' + " ".join([f'"{arg}"' for arg in sys.argv[1:]])
            
            # ShellExecuteW with 'runas' requests UAC elevation
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, None, 1)
            if ret > 32:
                sys.exit(0)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    request_admin_elevation()
    app = InfinixGTToolkitApp()
    app.root.mainloop()


"""
Infinix GT Toolkit - Color Studio & Modern Color Picker Component
================================================================
A professional, theme-aware custom color picker dialog (ColorPickerDialog)
and pure color science/validation utilities for CustomTkinter.

Features:
- Pure color conversions: Hex, RGB (0-255), HSV (0-359, 0-100, 0-100)
- Relative luminance calculation for WCAG contrast text selection
- 256x256 Saturation/Value spectrum with PIL generation and hue-based caching
- Dual-ring high-contrast crosshair cursor (black outer, white inner)
- Keyboard arrow navigation (1-step and 10-step with Shift)
- Horizontal rainbow hue slider (0-360 deg)
- Bidirectional synchronized inputs with re-entrancy protection
- Previous vs New color comparison swatches
- Recent colors row (8 unique items, newest first)
- Preset palette with selection rings and tooltips
- Clean modal window with Escape/Enter handling and proper transient lifecycle
"""

import math
import colorsys
import tkinter as tk
from tkinter import messagebox
from typing import Dict, Tuple, List, Optional, Callable, Any
import customtkinter as ctk
from PIL import Image, ImageTk


# ---------------------------------------------------------------------------
# Pure Color Conversion and Validation Helpers
# ---------------------------------------------------------------------------

def normalize_hex_color(value: str) -> Optional[str]:
    """Normalize a user-entered hex string to standard uppercase #RRGGBB."""
    if not value or not isinstance(value, str):
        return None
    cleaned = value.strip().lstrip("#")
    if len(cleaned) == 3:
        # Shorthand hex #RGB -> #RRGGBB
        if all(c in "0123456789abcdefABCDEF" for c in cleaned):
            return f"#{cleaned[0]*2}{cleaned[1]*2}{cleaned[2]*2}".upper()
    elif len(cleaned) == 6:
        if all(c in "0123456789abcdefABCDEF" for c in cleaned):
            return f"#{cleaned}".upper()
    return None


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """Convert RGB 0-255 tuple to uppercase #RRGGBB."""
    r, g, b = (max(0, min(255, int(round(v)))) for v in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def hex_to_rgb(value: str) -> Optional[Tuple[int, int, int]]:
    """Convert hex string (with or without #) to (R, G, B) tuple in 0-255."""
    norm = normalize_hex_color(value)
    if not norm:
        return None
    hex_str = norm.lstrip("#")
    try:
        return (int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))
    except ValueError:
        return None


def rgb_to_hsv_display(rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Convert RGB (0-255) to integer display HSV: H in [0, 359], S in [0, 100], V in [0, 100]."""
    r, g, b = (max(0, min(255, int(v))) / 255.0 for v in rgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h_deg = int(round(h * 360.0)) % 360
    s_pct = int(round(s * 100.0))
    v_pct = int(round(v * 100.0))
    return h_deg, max(0, min(100, s_pct)), max(0, min(100, v_pct))


def hsv_display_to_rgb(h: int, s: int, v: int) -> Tuple[int, int, int]:
    """Convert display HSV integers (H: 0-359, S: 0-100, V: 0-100) to RGB (0-255)."""
    h_norm = (int(h) % 360) / 360.0
    s_norm = max(0.0, min(100.0, float(s))) / 100.0
    v_norm = max(0.0, min(100.0, float(v))) / 100.0
    r, g, b = colorsys.hsv_to_rgb(h_norm, s_norm, v_norm)
    return (int(round(r * 255.0)), int(round(g * 255.0)), int(round(b * 255.0)))


def best_text_color(rgb: Tuple[int, int, int]) -> str:
    """
    Calculate WCAG relative luminance to choose readable foreground text color:
    Returns '#000000' for bright backgrounds and '#FFFFFF' for dark backgrounds.
    """
    channels = []
    for c in rgb:
        norm = max(0, min(255, int(c))) / 255.0
        if norm <= 0.03928:
            channels.append(norm / 12.92)
        else:
            channels.append(((norm + 0.055) / 1.055) ** 2.4)
    lum = 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
    return "#000000" if lum > 0.45 else "#FFFFFF"


def validate_rgb_channels(r: Any, g: Any, b: Any) -> bool:
    """Verify that R, G, B are valid integers within [0, 255]."""
    try:
        ri, gi, bi = int(r), int(g), int(b)
        return (0 <= ri <= 255) and (0 <= gi <= 255) and (0 <= bi <= 255)
    except (ValueError, TypeError):
        return False


def validate_hsv_channels(h: Any, s: Any, v: Any) -> bool:
    """Verify that H is in [0, 359], and S and V are in [0, 100]."""
    try:
        hi, si, vi = int(h), int(s), int(v)
        return (0 <= hi <= 359) and (0 <= si <= 100) and (0 <= vi <= 100)
    except (ValueError, TypeError):
        return False


def add_recent_color(recent_list: List[str], hex_code: str, max_items: int = 8) -> List[str]:
    """Add a hex color to the front of recent list, deduplicating and capping at max_items."""
    norm = normalize_hex_color(hex_code)
    if not norm:
        return recent_list
    if norm in recent_list:
        recent_list.remove(norm)
    recent_list.insert(0, norm)
    while len(recent_list) > max_items:
        recent_list.pop()
    return recent_list



# ---------------------------------------------------------------------------
# Saturation / Value Spectrum & Hue Slider Component
# ---------------------------------------------------------------------------

class SpectrumCanvas(tk.Canvas):
    """
    Interactive 256x256 Saturation / Value Spectrum Canvas.
    Horizontal axis: Saturation (0% to 100%)
    Vertical axis: Value / Brightness (100% at top to 0% at bottom)
    Caches the generated PIL image by integer hue to ensure lag-free dragging.
    """

    def __init__(self, parent, size: int = 256, on_change: Optional[Callable[[int, int], None]] = None, **kwargs):
        super().__init__(parent, width=size, height=size, highlightthickness=1, bd=0, relief="solid", **kwargs)
        self.size = size
        self.on_change = on_change
        
        self.current_hue = 0
        self.current_sat = 100
        self.current_val = 100
        
        # Image cache: integer hue -> PhotoImage
        self._cache: Dict[int, ImageTk.PhotoImage] = {}
        self._photo_ref: Optional[ImageTk.PhotoImage] = None
        
        # Bind pointer events
        self.bind("<Button-1>", self._on_pointer_event)
        self.bind("<B1-Motion>", self._on_pointer_event)
        
        # Bind keyboard arrows for accessibility
        self.bind("<FocusIn>", lambda e: self.configure(highlightbackground="#38BDF8", highlightcolor="#38BDF8"))
        self.bind("<FocusOut>", lambda e: self.configure(highlightbackground="#282B33", highlightcolor="#282B33"))
        self.bind("<Left>", lambda e: self._on_key_move(-1, 0, e))
        self.bind("<Right>", lambda e: self._on_key_move(1, 0, e))
        self.bind("<Up>", lambda e: self._on_key_move(0, 1, e))
        self.bind("<Down>", lambda e: self._on_key_move(0, -1, e))

    def _generate_spectrum_image(self, hue: int) -> ImageTk.PhotoImage:
        """Generate a 256x256 RGB image for the given hue."""
        h_norm = (hue % 360) / 360.0
        size = self.size
        # Fast bytearray buffer construction
        buf = bytearray(size * size * 3)
        idx = 0
        for y in range(size):
            v = (size - 1 - y) / float(size - 1)
            for x in range(size):
                s = x / float(size - 1)
                r, g, b = colorsys.hsv_to_rgb(h_norm, s, v)
                buf[idx] = int(round(r * 255.0))
                buf[idx + 1] = int(round(g * 255.0))
                buf[idx + 2] = int(round(b * 255.0))
                idx += 3
        img = Image.frombytes("RGB", (size, size), bytes(buf))
        photo = ImageTk.PhotoImage(img)
        return photo

    def set_sv(self, sat: int, val: int, redraw: bool = True):
        """Update current saturation and value."""
        self.current_sat = max(0, min(100, int(round(sat))))
        self.current_val = max(0, min(100, int(round(val))))
        if redraw:
            self._redraw_handle()

    def set_hue(self, hue: int, redraw: bool = True):
        """Update the base hue and reload the cached spectrum."""
        hue = int(round(hue)) % 360
        if hue != self.current_hue or self._photo_ref is None:
            self.current_hue = hue
            if hue not in self._cache:
                self._cache[hue] = self._generate_spectrum_image(hue)
            self._photo_ref = self._cache[hue]
        if redraw:
            self._redraw_all()

    def _redraw_all(self):
        self.delete("all")
        if self._photo_ref:
            self.create_image(0, 0, anchor="nw", image=self._photo_ref)
        self._redraw_handle()

    def _redraw_handle(self):
        """Draw the high-contrast dual-ring handle at the current (S, V) position."""
        self.delete("cursor_handle")
        
        # Calculate pixel coordinates from S [0, 100] and V [0, 100]
        x = (self.current_sat / 100.0) * (self.size - 1)
        y = ((100.0 - self.current_val) / 100.0) * (self.size - 1)
        
        # Outer ring: Black (radius 7, width 2)
        self.create_oval(
            x - 7, y - 7, x + 7, y + 7,
            outline="#000000", width=2, tags="cursor_handle"
        )
        # Inner ring: White (radius 5, width 2)
        self.create_oval(
            x - 5, y - 5, x + 5, y + 5,
            outline="#FFFFFF", width=2, tags="cursor_handle"
        )

    def _on_pointer_event(self, event):
        self.focus_set()
        # Clamp event coordinates to canvas bounds
        x = max(0, min(self.size - 1, event.x))
        y = max(0, min(self.size - 1, event.y))
        
        sat = int(round((x / float(self.size - 1)) * 100.0))
        val = int(round(((self.size - 1 - y) / float(self.size - 1)) * 100.0))
        
        self.set_sv(sat, val, redraw=True)
        if self.on_change:
            self.on_change(self.current_sat, self.current_val)

    def _on_key_move(self, dx: int, dy: int, event):
        step = 10 if (event.state & 0x0001) else 1  # Shift modifier
        new_sat = max(0, min(100, self.current_sat + dx * step))
        new_val = max(0, min(100, self.current_val + dy * step))
        self.set_sv(new_sat, new_val, redraw=True)
        if self.on_change:
            self.on_change(self.current_sat, self.current_val)
        return "break"


class HueSliderCanvas(tk.Canvas):
    """
    Horizontal rainbow gradient slider canvas displaying hues 0° to 360°.
    """

    def __init__(self, parent, width: int = 256, height: int = 22, on_change: Optional[Callable[[int], None]] = None, **kwargs):
        super().__init__(parent, width=width, height=height, highlightthickness=1, bd=0, relief="solid", **kwargs)
        self.w = width
        self.h = height
        self.on_change = on_change
        self.current_hue = 0

        # Generate rainbow gradient image
        buf = bytearray(width * height * 3)
        idx = 0
        for y in range(height):
            for x in range(width):
                h = x / float(width - 1)
                r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
                buf[idx] = int(round(r * 255.0))
                buf[idx + 1] = int(round(g * 255.0))
                buf[idx + 2] = int(round(b * 255.0))
                idx += 3
        self._bg_img = ImageTk.PhotoImage(Image.frombytes("RGB", (width, height), bytes(buf)))
        
        self.configure(takefocus=True, highlightbackground="#282B33", highlightcolor="#38BDF8")
        self.bind("<Button-1>", self._on_pointer)
        self.bind("<B1-Motion>", self._on_pointer)
        self.bind("<FocusIn>", lambda e: self.configure(highlightbackground="#38BDF8", highlightcolor="#38BDF8"))
        self.bind("<FocusOut>", lambda e: self.configure(highlightbackground="#282B33", highlightcolor="#282B33"))
        self.bind("<Left>", lambda e: self._on_key_move(-1, e))
        self.bind("<Right>", lambda e: self._on_key_move(1, e))
        self._redraw()

    def _on_key_move(self, dx: int, event):
        step = 10 if (event.state & 0x0001) else 1
        new_hue = (self.current_hue + dx * step) % 360
        self.set_hue(new_hue, redraw=True)
        if self.on_change:
            self.on_change(self.current_hue)
        return "break"

    def set_hue(self, hue: int, redraw: bool = True):
        self.current_hue = max(0, min(359, int(round(hue))))
        if redraw:
            self._redraw()

    def _redraw(self):
        self.delete("all")
        self.create_image(0, 0, anchor="nw", image=self._bg_img)
        
        # Draw high-contrast handle marker
        x = (self.current_hue / 359.0) * (self.w - 1)
        self.create_rectangle(x - 3, 0, x + 3, self.h, fill="#FFFFFF", outline="#000000", width=1.5)

    def _on_pointer(self, event):
        x = max(0, min(self.w - 1, event.x))
        hue = int(round((x / float(self.w - 1)) * 359.0))
        self.set_hue(hue, redraw=True)
        if self.on_change:
            self.on_change(self.current_hue)


# ---------------------------------------------------------------------------
# Modal ColorPickerDialog Component
# ---------------------------------------------------------------------------

PRESET_PALETTE: List[Tuple[str, str, Tuple[int, int, int]]] = [
    ("🔴 Red", "#FF0000", (255, 0, 0)),
    ("🌹 Rose", "#FF0032", (255, 0, 50)),
    ("🟠 Orange", "#FF3C00", (255, 60, 0)),
    ("🌟 Amber", "#FFB400", (255, 180, 0)),
    ("🌸 Pink", "#FF0078", (255, 0, 120)),
    ("🔮 Magenta", "#FF00FF", (255, 0, 255)),
    ("💜 Purple", "#8C00FF", (140, 0, 255)),
    ("🌌 Indigo", "#5000FF", (80, 0, 255)),
    ("⚡ Blue", "#0000FF", (0, 0, 255)),
    ("🌤️ Sky", "#00A0FF", (0, 160, 255)),
    ("🔵 Cyan", "#00FFFF", (0, 255, 255)),
    ("🌿 Mint", "#00FF64", (0, 255, 100)),
    ("🟢 Green", "#00FF00", (0, 255, 0)),
    ("☢️ Lime", "#8CFF00", (140, 255, 0)),
    ("❄️ White", "#FFFFFF", (255, 255, 255)),
    ("🌑 Black", "#000000", (0, 0, 0)),
]

DARK_THEME_TOKENS: Dict[str, str] = {
    "bg": "#0E1015",
    "card_bg": "#181A20",
    "card_border": "#282B33",
    "text_primary": "#FFFFFF",
    "text_secondary": "#94A3B8",
    "accent_blue": "#38BDF8",
    "button_bg": "#222630",
    "button_hover": "#2D3748",
    "entry_bg": "#13161C",
    "entry_border": "#282B33",
    "accent_rose": "#F43F5E",
    "accent_green": "#22C55E",
}

LIGHT_THEME_TOKENS: Dict[str, str] = {
    "bg": "#F1F5F9",
    "card_bg": "#FFFFFF",
    "card_border": "#CBD5E1",
    "text_primary": "#0F172A",
    "text_secondary": "#64748B",
    "accent_blue": "#0284C7",
    "button_bg": "#E2E8F0",
    "button_hover": "#CBD5E1",
    "entry_bg": "#F8FAFC",
    "entry_border": "#CBD5E1",
    "accent_rose": "#E11D48",
    "accent_green": "#16A34A",
}


class ColorPickerDialog(ctk.CTkToplevel):
    """
    Modern, theme-aware in-app Color Studio Dialog.
    Centered over parent, modal, resizable, with synchronized Hex/RGB/HSV,
    previous vs new swatches, recent colors, and neon presets.
    """

    def __init__(
        self,
        parent,
        initial_rgb: Tuple[int, int, int] = (56, 189, 248),
        title: str = "Choose Color",
        theme_colors: Optional[Any] = None,
        on_apply: Optional[Callable[[Tuple[int, int, int]], None]] = None,
        on_preview: Optional[Callable[[Tuple[int, int, int]], None]] = None,
        recent_colors: Optional[List[str]] = None,
        preset_colors: Optional[List[Tuple[str, str, Tuple[int, int, int]]]] = None,
    ):
        super().__init__(parent)
        self.parent = parent
        self.title(title)
        
        if isinstance(theme_colors, str):
            if theme_colors.lower() == "light":
                self.theme = dict(LIGHT_THEME_TOKENS)
            else:
                self.theme = dict(DARK_THEME_TOKENS)
        elif isinstance(theme_colors, dict):
            self.theme = dict(theme_colors)
        else:
            mode = ctk.get_appearance_mode()
            if mode.lower() == "light":
                self.theme = dict(LIGHT_THEME_TOKENS)
            else:
                self.theme = dict(DARK_THEME_TOKENS)

        
        self.on_apply = on_apply
        self.on_preview = on_preview
        self.recent_colors = recent_colors or ["#FF0032", "#38BDF8", "#A78BFA", "#22C55E", "#F59E0B", "#EC4899", "#06B6D4", "#8C00FF"]
        self.preset_colors = preset_colors or list(PRESET_PALETTE)
        
        # Color state
        self.original_rgb = tuple(int(c) for c in initial_rgb)
        self.working_rgb = tuple(int(c) for c in initial_rgb)
        self.result: Optional[Tuple[int, int, int]] = None
        self._syncing = False
        
        # Configure window lifecycle
        self.configure(fg_color=self.theme.get("bg", "#0E1015"))
        self.minsize(720, 500)
        self.geometry("740x530")
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
        # Key bindings
        self.bind("<Escape>", lambda e: self._on_cancel())
        self.bind("<Return>", lambda e: self._on_enter_pressed())

        # Center window over parent
        self._center_window()

        # Build UI layout
        self._build_ui()

        # Initialize color values
        self._update_all_from_rgb(self.working_rgb, trigger_preview=False)

    def _center_window(self):
        self.update_idletasks()
        try:
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
            px = self.parent.winfo_rootx()
            py = self.parent.winfo_rooty()
            w, h = 740, 530
            x = max(10, px + (pw - w) // 2)
            y = max(10, py + (ph - h) // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            self.geometry("740x530")

    def _build_ui(self):
        # Outer container frame
        main_box = ctk.CTkFrame(self, fg_color="transparent")
        main_box.pack(fill="both", expand=True, padx=16, pady=16)

        # 2-Column Grid
        main_box.grid_columnconfigure(0, weight=0)  # Left column (Spectrum fixed width)
        main_box.grid_columnconfigure(1, weight=1)  # Right column (Controls expandable)
        main_box.grid_rowconfigure(0, weight=1)

        # ===================================================================
        # LEFT COLUMN: Saturation/Value Spectrum + Rainbow Hue Slider
        # ===================================================================
        left_card = ctk.CTkFrame(
            main_box, fg_color=self.theme.get("card_bg", "#181A20"),
            corner_radius=14, border_width=1.5,
            border_color=self.theme.get("card_border", "#282B33")
        )
        left_card.grid(row=0, column=0, padx=(0, 10), sticky="nsew")

        ctk.CTkLabel(
            left_card, text="Saturation & Brightness",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.theme.get("text_primary", "#FFFFFF")
        ).pack(anchor="w", padx=16, pady=(12, 6))

        # Spectrum Canvas (256x256)
        self.spectrum = SpectrumCanvas(
            left_card, size=256,
            on_change=self._on_spectrum_changed,
            bg="#000000"
        )
        self.spectrum.pack(padx=16, pady=(0, 10))

        # Hue Slider Label
        ctk.CTkLabel(
            left_card, text="Hue Spectrum (0° – 360°)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.theme.get("text_secondary", "#94A3B8")
        ).pack(anchor="w", padx=16, pady=(2, 4))

        # Hue Slider Canvas (256x22)
        self.hue_slider = HueSliderCanvas(
            left_card, width=256, height=22,
            on_change=self._on_hue_slider_changed,
            bg="#000000"
        )
        self.hue_slider.pack(padx=16, pady=(0, 14))

        # Accessibility Hint
        ctk.CTkLabel(
            left_card, text="💡 Tip: Click & drag spectrum or use Arrow keys (Shift=10x)",
            font=ctk.CTkFont(size=11),
            text_color=self.theme.get("text_secondary", "#94A3B8")
        ).pack(anchor="w", padx=16, pady=(0, 10))

        # ===================================================================
        # RIGHT COLUMN: Comparison Swatches, Inputs, History, Actions
        # ===================================================================
        right_card = ctk.CTkFrame(
            main_box, fg_color=self.theme.get("card_bg", "#181A20"),
            corner_radius=14, border_width=1.5,
            border_color=self.theme.get("card_border", "#282B33")
        )
        right_card.grid(row=0, column=1, padx=(10, 0), sticky="nsew")

        # --- 1. Comparison Swatches (Previous vs New) ---
        cmp_frame = ctk.CTkFrame(right_card, fg_color="transparent")
        cmp_frame.pack(fill="x", padx=16, pady=(12, 10))

        # Previous Color Box
        prev_box = ctk.CTkFrame(cmp_frame, fg_color="transparent")
        prev_box.pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkLabel(
            prev_box, text="Previous",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.theme.get("text_secondary", "#94A3B8")
        ).pack(anchor="w", pady=(0, 4))
        
        self.prev_swatch_label = ctk.CTkLabel(
            prev_box, text=rgb_to_hex(self.original_rgb),
            height=42, corner_radius=8,
            fg_color=rgb_to_hex(self.original_rgb),
            text_color=best_text_color(self.original_rgb),
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.prev_swatch_label.pack(fill="x")

        # New Color Box
        new_box = ctk.CTkFrame(cmp_frame, fg_color="transparent")
        new_box.pack(side="left", expand=True, fill="x", padx=(6, 0))
        ctk.CTkLabel(
            new_box, text="New (Current)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.theme.get("accent_blue", "#38BDF8")
        ).pack(anchor="w", pady=(0, 4))

        self.new_swatch_label = ctk.CTkLabel(
            new_box, text=rgb_to_hex(self.working_rgb),
            height=42, corner_radius=8,
            fg_color=rgb_to_hex(self.working_rgb),
            text_color=best_text_color(self.working_rgb),
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.new_swatch_label.pack(fill="x")

        # --- 2. Color Input Matrix (HEX, RGB, HSV) ---
        inputs_frame = ctk.CTkFrame(right_card, fg_color="transparent")
        inputs_frame.pack(fill="x", padx=16, pady=4)

        # Hex Row
        hex_row = ctk.CTkFrame(inputs_frame, fg_color="transparent")
        hex_row.pack(fill="x", pady=2)
        ctk.CTkLabel(
            hex_row, text="HEX:", width=45, anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.theme.get("text_primary", "#FFFFFF")
        ).pack(side="left")

        self.hex_var = ctk.StringVar(value=rgb_to_hex(self.working_rgb))
        self.hex_entry = ctk.CTkEntry(
            hex_row, textvariable=self.hex_var, width=110, height=28,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.hex_entry.pack(side="left", padx=(0, 6))
        self.hex_var.trace_add("write", self._on_hex_input_changed)

        ctk.CTkButton(
            hex_row, text="Copy", width=55, height=26,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=self.theme.get("button_bg", "#222630"),
            hover_color=self.theme.get("accent_blue", "#38BDF8"),
            command=self._copy_hex
        ).pack(side="left")

        self.hex_error_lbl = ctk.CTkLabel(
            hex_row, text="", font=ctk.CTkFont(size=12),
            text_color=self.theme.get("accent_rose", "#F43F5E")
        )
        self.hex_error_lbl.pack(side="left", padx=8)

        # RGB Row
        rgb_row = ctk.CTkFrame(inputs_frame, fg_color="transparent")
        rgb_row.pack(fill="x", pady=3)
        ctk.CTkLabel(
            rgb_row, text="RGB:", width=45, anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.theme.get("text_primary", "#FFFFFF")
        ).pack(side="left")

        self.r_var = ctk.StringVar(value=str(self.working_rgb[0]))
        self.g_var = ctk.StringVar(value=str(self.working_rgb[1]))
        self.b_var = ctk.StringVar(value=str(self.working_rgb[2]))

        for val_var, lbl_txt in ((self.r_var, "R"), (self.g_var, "G"), (self.b_var, "B")):
            ctk.CTkLabel(rgb_row, text=lbl_txt, font=ctk.CTkFont(size=12, weight="bold"), text_color=self.theme.get("text_secondary", "#94A3B8")).pack(side="left", padx=(2, 2))
            entry = ctk.CTkEntry(rgb_row, textvariable=val_var, width=54, height=26, font=ctk.CTkFont(size=13))
            entry.pack(side="left", padx=(0, 6))
            val_var.trace_add("write", self._on_rgb_input_changed)

        # HSV Row
        hsv_row = ctk.CTkFrame(inputs_frame, fg_color="transparent")
        hsv_row.pack(fill="x", pady=3)
        ctk.CTkLabel(
            hsv_row, text="HSV:", width=45, anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.theme.get("text_primary", "#FFFFFF")
        ).pack(side="left")

        h_init, s_init, v_init = rgb_to_hsv_display(self.working_rgb)
        self.h_var = ctk.StringVar(value=str(h_init))
        self.s_var = ctk.StringVar(value=str(s_init))
        self.v_var = ctk.StringVar(value=str(v_init))

        for val_var, lbl_txt in ((self.h_var, "H°"), (self.s_var, "S%"), (self.v_var, "V%")):
            ctk.CTkLabel(hsv_row, text=lbl_txt, font=ctk.CTkFont(size=12, weight="bold"), text_color=self.theme.get("text_secondary", "#94A3B8")).pack(side="left", padx=(2, 2))
            entry = ctk.CTkEntry(hsv_row, textvariable=val_var, width=54, height=26, font=ctk.CTkFont(size=13))
            entry.pack(side="left", padx=(0, 6))
            val_var.trace_add("write", self._on_hsv_input_changed)

        # --- 3. Recent Colors Row ---
        ctk.CTkLabel(
            right_card, text="Recent Colors",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.theme.get("text_secondary", "#94A3B8")
        ).pack(anchor="w", padx=16, pady=(8, 4))

        self.recent_row = ctk.CTkFrame(right_card, fg_color="transparent")
        self.recent_row.pack(fill="x", padx=16, pady=(0, 4))
        self._populate_recent_swatches()

        # --- 4. Preset Palette Row ---
        ctk.CTkLabel(
            right_card, text="Vivid Presets",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.theme.get("text_secondary", "#94A3B8")
        ).pack(anchor="w", padx=16, pady=(6, 4))

        self.presets_frame = ctk.CTkFrame(right_card, fg_color="transparent")
        self.presets_frame.pack(fill="x", padx=16, pady=(0, 8))
        self._populate_preset_swatches()

        # --- 5. Action Buttons (Cancel / Apply Color) ---
        btn_bar = ctk.CTkFrame(right_card, fg_color="transparent")
        btn_bar.pack(fill="x", padx=16, pady=(10, 14), side="bottom")

        self.cancel_btn = ctk.CTkButton(
            btn_bar, text="Cancel", width=100, height=32,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=self.theme.get("button_bg", "#222630"),
            hover_color=self.theme.get("button_hover", "#2D3748"),
            text_color=self.theme.get("text_primary", "#FFFFFF"),
            command=self._on_cancel
        )
        self.cancel_btn.pack(side="right", padx=(6, 0))

        self.apply_btn = ctk.CTkButton(
            btn_bar, text="Apply Color", width=120, height=32,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=self.theme.get("accent_blue", "#38BDF8"),
            hover_color=self.theme.get("button_hover", "#2D3748"),
            text_color="#000000",
            command=self._on_apply
        )
        self.apply_btn.pack(side="right")

    # -----------------------------------------------------------------------
    # Swatches and Palettes
    # -----------------------------------------------------------------------
    def _populate_recent_swatches(self):
        for w in self.recent_row.winfo_children():
            w.destroy()
        
        # Take up to 8 unique recent colors
        seen = set()
        unique_recents = []
        for c in self.recent_colors:
            norm = normalize_hex_color(c)
            if norm and norm not in seen:
                seen.add(norm)
                unique_recents.append(norm)
            if len(unique_recents) >= 8:
                break

        for hex_code in unique_recents:
            rgb = hex_to_rgb(hex_code)
            if not rgb:
                continue
            btn = ctk.CTkButton(
                self.recent_row, text="", width=26, height=26,
                corner_radius=13, border_width=1.5,
                border_color=self.theme.get("card_border", "#282B33"),
                fg_color=hex_code, hover_color=hex_code,
                command=lambda c=rgb: self._load_swatch_color(c)
            )
            btn.pack(side="left", padx=3)

    def _populate_preset_swatches(self):
        for w in self.presets_frame.winfo_children():
            w.destroy()

        # Display 16 vivid preset colors in 2 rows of 8
        row1 = ctk.CTkFrame(self.presets_frame, fg_color="transparent")
        row1.pack(fill="x", pady=2)
        row2 = ctk.CTkFrame(self.presets_frame, fg_color="transparent")
        row2.pack(fill="x", pady=2)

        for i, (name, hex_code, rgb) in enumerate(self.preset_colors[:16]):
            target_row = row1 if i < 8 else row2
            btn = ctk.CTkButton(
                target_row, text="", width=26, height=22,
                corner_radius=6, border_width=1.5,
                border_color=self.theme.get("card_border", "#282B33"),
                fg_color=hex_code, hover_color=hex_code,
                command=lambda c=rgb: self._load_swatch_color(c)
            )
            btn.pack(side="left", padx=3)

    def _load_swatch_color(self, rgb: Tuple[int, int, int]):
        self._update_all_from_rgb(rgb)

    def _copy_hex(self):
        norm = normalize_hex_color(self.hex_var.get())
        if norm:
            self.clipboard_clear()
            self.clipboard_append(norm)
            self.hex_error_lbl.configure(text="Copied!", text_color=self.theme.get("accent_green", "#22C55E"))
            self.after(1500, lambda: self.hex_error_lbl.configure(text=""))

    # -----------------------------------------------------------------------
    # Bidirectional Synchronization Core
    # -----------------------------------------------------------------------
    def _update_all_from_rgb(self, rgb: Tuple[int, int, int], trigger_preview: bool = True):
        if self._syncing:
            return
        self._syncing = True
        try:
            self.working_rgb = tuple(int(round(c)) for c in rgb)
            hex_val = rgb_to_hex(self.working_rgb)
            h, s, v = rgb_to_hsv_display(self.working_rgb)

            # Update spectrum & slider
            self.spectrum.set_hue(h, redraw=False)
            self.spectrum.set_sv(s, v, redraw=False)
            self.spectrum._redraw_all()
            self.hue_slider.set_hue(h, redraw=True)

            # Update previews
            self.new_swatch_label.configure(
                text=hex_val,
                fg_color=hex_val,
                text_color=best_text_color(self.working_rgb)
            )

            # Update numeric input fields
            self.hex_var.set(hex_val)
            self.r_var.set(str(self.working_rgb[0]))
            self.g_var.set(str(self.working_rgb[1]))
            self.b_var.set(str(self.working_rgb[2]))
            self.h_var.set(str(h))
            self.s_var.set(str(s))
            self.v_var.set(str(v))

            self._set_valid(True)

            if trigger_preview and self.on_preview:
                self.on_preview(self.working_rgb)
        finally:
            self._syncing = False

    def _on_spectrum_changed(self, sat: int, val: int):
        if self._syncing:
            return
        h = self.hue_slider.current_hue
        rgb = hsv_display_to_rgb(h, sat, val)
        self._update_all_from_rgb(rgb)

    def _on_hue_slider_changed(self, hue: int):
        if self._syncing:
            return
        s = self.spectrum.current_sat
        v = self.spectrum.current_val
        rgb = hsv_display_to_rgb(hue, s, v)
        self._update_all_from_rgb(rgb)

    def _on_hex_input_changed(self, *args):
        if self._syncing:
            return
        text = self.hex_var.get()
        rgb = hex_to_rgb(text)
        if rgb:
            self._set_valid(True)
            self._update_all_from_rgb(rgb)
        else:
            self._set_valid(False, "Invalid hex code")

    def _on_rgb_input_changed(self, *args):
        if self._syncing:
            return
        r_str, g_str, b_str = self.r_var.get(), self.g_var.get(), self.b_var.get()
        if validate_rgb_channels(r_str, g_str, b_str):
            self._set_valid(True)
            rgb = (int(r_str), int(g_str), int(b_str))
            self._update_all_from_rgb(rgb)
        else:
            self._set_valid(False, "RGB channels must be 0–255")

    def _on_hsv_input_changed(self, *args):
        if self._syncing:
            return
        h_str, s_str, v_str = self.h_var.get(), self.s_var.get(), self.v_var.get()
        if validate_hsv_channels(h_str, s_str, v_str):
            self._set_valid(True)
            rgb = hsv_display_to_rgb(int(h_str), int(s_str), int(v_str))
            self._update_all_from_rgb(rgb)
        else:
            self._set_valid(False, "HSV ranges: H:0–359, S/V:0–100")

    def _set_valid(self, is_valid: bool, msg: str = ""):
        if is_valid:
            self.hex_error_lbl.configure(text="")
            self.hex_entry.configure(border_color=self.theme.get("entry_border", "#282B33"))
            self.apply_btn.configure(state="normal", fg_color=self.theme.get("accent_blue", "#38BDF8"))
        else:
            self.hex_error_lbl.configure(text=f"⚠️ {msg}", text_color=self.theme.get("accent_rose", "#F43F5E"))
            self.hex_entry.configure(border_color=self.theme.get("accent_rose", "#F43F5E"))
            self.apply_btn.configure(state="disabled", fg_color="#334155")

    # -----------------------------------------------------------------------
    # Commit / Cancel Handling
    # -----------------------------------------------------------------------
    def _on_enter_pressed(self):
        if self.apply_btn.cget("state") != "disabled":
            self._on_apply()

    def _on_apply(self):
        self.result = self.working_rgb
        # Add to recent colors list
        hex_code = rgb_to_hex(self.working_rgb)
        if hex_code in self.recent_colors:
            self.recent_colors.remove(hex_code)
        self.recent_colors.insert(0, hex_code)
        if len(self.recent_colors) > 8:
            self.recent_colors = self.recent_colors[:8]

        if self.on_apply:
            self.on_apply(self.working_rgb)

        self.grab_release()
        self.destroy()

    def destroy(self):
        try:
            self.grab_release()
        except Exception:
            pass
        super().destroy()

    def _on_cancel(self):
        # Restore original on-screen preview if preview was active
        if self.on_preview:
            self.on_preview(self.original_rgb)
        self.result = None
        self.destroy()


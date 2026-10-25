"""Game Automation & In-Game Floating HUD Engine for Infinix GT Book.

Features:
1. Per-game hardware profile management (Power Mode, Fan Curve, Refresh Rate, Win-Lock).
2. Autonomous process monitoring with pre-game state capture and 100% clean post-game reversion.
3. In-Game Floating HUD Telemetry Overlay (transparent, topmost, non-activating, click-through).
4. Global hotkey toggling (Ctrl + Shift + O) without stealing game focus.
"""

import os
import sys
import time
import logging
import threading
import ctypes
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger("InfinixGameAutomation")


@dataclass
class GameProfile:
    exe_name: str                         # e.g. "cyberpunk2077.exe"
    display_name: str                     # e.g. "Cyberpunk 2077"
    power_mode: str = "Beast"             # "Beast", "Balanced", "Quiet", "No Change"
    fan_profile: str = "Aggressive"       # "Aggressive", "Balanced", "Quiet", "Full Speed", "Auto (OEM)", "No Change"
    target_refresh_rate: int = 120        # 120, 60, or 0 (No Change)
    winlock: bool = True                  # True to lock Windows key
    auto_hud: bool = True                 # Automatically show HUD overlay on game launch

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "GameProfile":
        return cls(
            exe_name=str(data.get("exe_name", "")).lower().strip(),
            display_name=str(data.get("display_name", "Game")).strip(),
            power_mode=str(data.get("power_mode", "Beast")),
            fan_profile=str(data.get("fan_profile", "Aggressive")),
            target_refresh_rate=int(data.get("target_refresh_rate", 120)),
            winlock=bool(data.get("winlock", True)),
            auto_hud=bool(data.get("auto_hud", True)),
        )


# Default built-in popular game definitions
DEFAULT_KNOWN_GAMES: Dict[str, str] = {
    # Installed games & popular Infinix GT titles
    "gta5.exe": "Grand Theft Auto V",
    "playgtav.exe": "Grand Theft Auto V",
    "run_gtav.exe": "Grand Theft Auto V",
    "gta5_be.exe": "Grand Theft Auto V",
    "rdr2.exe": "Red Dead Redemption 2",
    "run_rdr2.exe": "Red Dead Redemption 2",
    "farcry6.exe": "Far Cry 6",
    "acblackflag.exe": "Assassin's Creed IV Black Flag",
    "gta_sa.exe": "Grand Theft Auto: San Andreas",
    "witcher3.exe": "The Witcher 3: Wild Hunt",
    "cyberpunk2077.exe": "Cyberpunk 2077",
    "eldenring.exe": "Elden Ring",
    "cs2.exe": "Counter-Strike 2",
    "csgo.exe": "Counter-Strike: Global Offensive",
    "valorant.exe": "Valorant",
    "valorant-win64-shipping.exe": "Valorant",
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
    "hogwartslegacy.exe": "Hogwarts Legacy",
    "starfield.exe": "Starfield",
    "pubg.exe": "PUBG: BATTLEGROUNDS",
    "tslgame.exe": "PUBG: BATTLEGROUNDS",
    "dota2.exe": "Dota 2",
    "leagueclientux.exe": "League of Legends",
}

IGNORE_GAME_EXES = {
    "explorer.exe", "cmd.exe", "powershell.exe", "taskmgr.exe", "python.exe",
    "infinixgttoolkit.exe", "steam.exe", "epicgameslauncher.exe", "discord.exe",
    "chrome.exe", "msedge.exe", "firefox.exe", "spotify.exe", "riotclientservices.exe"
}

GAME_PATH_KEYWORDS = ("steamapps", "epic games", "riot games", "ubisoft game launcher", "ea games", "xboxgames", "gog galaxy")


class GameAutomationGovernor:
    """Manages active game detection, per-game hardware profile switching, and state reversion."""

    def __init__(self, custom_profiles: Optional[List[dict]] = None):
        self._profiles: Dict[str, GameProfile] = {}
        self._active_game: Optional[GameProfile] = None
        self._pre_game_state: Optional[dict] = None
        self._lock = threading.Lock()

        # Initialize with default popular titles
        for exe, title in DEFAULT_KNOWN_GAMES.items():
            self._profiles[exe.lower()] = GameProfile(
                exe_name=exe.lower(),
                display_name=title,
                power_mode="Beast",
                fan_profile="Aggressive",
                target_refresh_rate=120,
                winlock=True,
                auto_hud=True
            )

        # Merge custom user profiles
        if custom_profiles:
            self.load_custom_profiles(custom_profiles)

    def load_custom_profiles(self, profile_list: List[dict]):
        with self._lock:
            for item in profile_list:
                try:
                    prof = GameProfile.from_dict(item)
                    if prof.exe_name:
                        self._profiles[prof.exe_name] = prof
                except Exception as e:
                    logger.debug(f"Failed to load profile {item}: {e}")

    def get_all_profiles(self) -> List[GameProfile]:
        with self._lock:
            return list(self._profiles.values())

    def get_profile(self, exe_name: str) -> Optional[GameProfile]:
        with self._lock:
            return self._profiles.get(exe_name.lower())

    def set_profile(self, profile: GameProfile):
        with self._lock:
            self._profiles[profile.exe_name.lower()] = profile

    def delete_profile(self, exe_name: str) -> bool:
        with self._lock:
            key = exe_name.lower()
            if key in self._profiles:
                del self._profiles[key]
                return True
            return False

    @property
    def active_game(self) -> Optional[GameProfile]:
        with self._lock:
            return self._active_game

    @property
    def is_in_game(self) -> bool:
        with self._lock:
            return self._active_game is not None

    def capture_pre_game_state(self, current_power_mode: str, current_fan_mode: str,
                               current_refresh_rate: int, winlock_active: bool,
                               bz_mode: int = 1) -> dict:
        """Saves a complete snapshot of hardware state before game activation."""
        snapshot = {
            "power_mode": current_power_mode,
            "fan_mode": current_fan_mode,
            "refresh_rate": current_refresh_rate,
            "winlock": winlock_active,
            "bz_mode": bz_mode,
            "timestamp": time.time(),
        }
        with self._lock:
            self._pre_game_state = snapshot
        return snapshot

    def scan_for_game(self, process_names: List[str]) -> Optional[GameProfile]:
        """Scans a list of active process names and returns matching GameProfile if any."""
        with self._lock:
            for p in process_names:
                pl = p.lower().strip()
                if not pl or pl in IGNORE_GAME_EXES:
                    continue
                if pl in self._profiles:
                    return self._profiles[pl]
        return None

    def evaluate_game_transition(
        self,
        active_processes: List[str],
        current_system_state: dict
    ) -> Tuple[Optional[str], Optional[dict]]:
        """Evaluates whether system has entered or exited a game session.

        Returns:
            ("LAUNCH", {profile, actions, pre_game_state})
            ("EXIT", {previous_game, restore_state})
            (None, None) if no state change occurred.
        """
        detected_profile = self.scan_for_game(active_processes)

        with self._lock:
            # Case 1: Game Launch detected
            if detected_profile is not None and self._active_game is None:
                self._active_game = detected_profile
                self._pre_game_state = {
                    "power_mode": current_system_state.get("power_mode", "Balanced"),
                    "fan_mode": current_system_state.get("fan_mode", "auto"),
                    "refresh_rate": current_system_state.get("refresh_rate", 120),
                    "winlock": current_system_state.get("winlock", False),
                    "bz_mode": current_system_state.get("bz_mode", 1),
                }
                return ("LAUNCH", {
                    "profile": detected_profile,
                    "target_power_mode": detected_profile.power_mode,
                    "target_fan_mode": detected_profile.fan_profile,
                    "target_refresh_rate": detected_profile.target_refresh_rate,
                    "winlock": detected_profile.winlock,
                    "auto_hud": detected_profile.auto_hud,
                    "pre_game_state": self._pre_game_state,
                })

            # Case 2: Game Exit detected
            elif detected_profile is None and self._active_game is not None:
                prev_game = self._active_game
                restore = self._pre_game_state or {
                    "power_mode": "Balanced",
                    "fan_mode": "auto",
                    "refresh_rate": 120,
                    "winlock": False,
                    "bz_mode": 1,
                }
                self._active_game = None
                self._pre_game_state = None
                return ("EXIT", {
                    "previous_game": prev_game,
                    "restore_state": restore,
                })

        return (None, None)


class InGameHUDOverlay:
    """Semi-transparent, non-activating, click-through in-game telemetry HUD.

    Floating stats bar:
    [🎮 GT HUD]  💻 CPU: 65°C 42% | 🎮 GPU: 68°C 85% | 🌪️ Fan: 4,200 RPM | ⚡ BEAST 120Hz | 🔋 85% (+45W)
    """

    def __init__(self, master=None, hotkey: str = "ctrl+shift+o"):
        self.master = master
        self.window = None
        self.is_visible = False
        self.hotkey = hotkey
        self._hotkey_hook = None
        self._click_through = True
        self._lock = threading.Lock()

        # Labels
        self.lbl_cpu = None
        self.lbl_gpu = None
        self.lbl_fan = None
        self.lbl_mode = None
        self.lbl_power = None
        self.card_frame = None

        self._register_global_hotkey()

    def _register_global_hotkey(self):
        """Registers global Windows hotkey without blocking the Tkinter event loop."""
        try:
            import keyboard
            if self.hotkey:
                keyboard.add_hotkey(self.hotkey, self.toggle_visibility, suppress=False)
                logger.info(f"Registered global HUD hotkey: {self.hotkey}")
        except Exception as e:
            logger.debug(f"Global hotkey hook not registered: {e}")

    def toggle_visibility(self):
        """Thread-safe toggle entry point."""
        if self.master is None:
            return
        try:
            self.master.after(0, self._toggle_impl)
        except Exception:
            pass

    def _toggle_impl(self):
        if self.is_visible:
            self.hide()
        else:
            self.show()

    def show(self):
        """Displays and lifts the HUD overlay."""
        if self.master is None:
            return
        if threading.current_thread() is threading.main_thread():
            self._show_impl()
        else:
            try:
                self.master.after(0, self._show_impl)
            except Exception:
                pass

    def _show_impl(self):
        if self.window is None or not self.window.winfo_exists():
            self._create_window()

        self._position_window()
        self.window.deiconify()
        self.window.lift()
        self.is_visible = True

    def hide(self):
        """Hides the HUD overlay."""
        if self.master is None:
            return
        if threading.current_thread() is threading.main_thread():
            self._hide_impl()
        else:
            try:
                self.master.after(0, self._hide_impl)
            except Exception:
                pass

    def _hide_impl(self):
        if self.window and self.window.winfo_exists():
            self.window.withdraw()
        self.is_visible = False

    def _create_window(self):
        import tkinter as tk

        self.window = tk.Toplevel(self.master)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-alpha", 0.90)
        self.window.configure(bg="#0B132B")

        # Win32 non-activating and click-through extended styles
        self._apply_win32_styles()

        # Build sleek horizontal HUD bar
        self.card_frame = tk.Frame(
            self.window, bg="#0B132B",
            highlightthickness=1, highlightbackground="#38BDF8",
            padx=12, pady=6
        )
        self.card_frame.pack(fill="both", expand=True)

        badge_lbl = tk.Label(
            self.card_frame, text="🎮 GT HUD",
            font=("Segoe UI", 10, "bold"), fg="#38BDF8", bg="#0B132B"
        )
        badge_lbl.pack(side="left", padx=(0, 10))

        sep1 = tk.Label(self.card_frame, text="|", font=("Segoe UI", 10), fg="#334155", bg="#0B132B")
        sep1.pack(side="left", padx=5)

        self.lbl_cpu = tk.Label(
            self.card_frame, text="💻 CPU: --°C --%",
            font=("Consolas", 10, "bold"), fg="#60A5FA", bg="#0B132B"
        )
        self.lbl_cpu.pack(side="left", padx=5)

        sep2 = tk.Label(self.card_frame, text="|", font=("Segoe UI", 10), fg="#334155", bg="#0B132B")
        sep2.pack(side="left", padx=5)

        self.lbl_gpu = tk.Label(
            self.card_frame, text="🎮 GPU: --°C --%",
            font=("Consolas", 10, "bold"), fg="#34D399", bg="#0B132B"
        )
        self.lbl_gpu.pack(side="left", padx=5)

        sep3 = tk.Label(self.card_frame, text="|", font=("Segoe UI", 10), fg="#334155", bg="#0B132B")
        sep3.pack(side="left", padx=5)

        self.lbl_fan = tk.Label(
            self.card_frame, text="🌪️ Fan: -- RPM",
            font=("Consolas", 10), fg="#E2E8F0", bg="#0B132B"
        )
        self.lbl_fan.pack(side="left", padx=5)

        sep4 = tk.Label(self.card_frame, text="|", font=("Segoe UI", 10), fg="#334155", bg="#0B132B")
        sep4.pack(side="left", padx=5)

        self.lbl_mode = tk.Label(
            self.card_frame, text="⚡ BEAST 120Hz",
            font=("Consolas", 10, "bold"), fg="#F59E0B", bg="#0B132B"
        )
        self.lbl_mode.pack(side="left", padx=5)

        sep5 = tk.Label(self.card_frame, text="|", font=("Segoe UI", 10), fg="#334155", bg="#0B132B")
        sep5.pack(side="left", padx=5)

        self.lbl_power = tk.Label(
            self.card_frame, text="🔋 --% (--W)",
            font=("Consolas", 10), fg="#94A3B8", bg="#0B132B"
        )
        self.lbl_power.pack(side="left", padx=5)

    def _apply_win32_styles(self):
        """Applies WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW, and optionally WS_EX_TRANSPARENT."""
        try:
            hwnd = ctypes.windll.user32.GetParent(self.window.winfo_id()) or self.window.winfo_id()
            user32 = ctypes.windll.user32
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_NOACTIVATE = 0x08000000
            WS_EX_TOPMOST = 0x00000008
            WS_EX_TRANSPARENT = 0x00000020 if self._click_through else 0

            ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TOPMOST | WS_EX_TRANSPARENT)
        except Exception:
            pass

    def _position_window(self):
        """Positions the HUD at the top-right of the primary screen."""
        try:
            self.window.update_idletasks()
            sw = self.window.winfo_screenwidth()
            w = self.window.winfo_reqwidth()
            h = self.window.winfo_reqheight()

            # 20px padding from right, 12px from top
            x = max(10, sw - w - 24)
            y = 12
            self.window.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def update_telemetry(
        self,
        cpu_temp: Optional[float] = None,
        cpu_usage: float = 0.0,
        gpu_temp: Optional[float] = None,
        gpu_usage: float = 0.0,
        fan_rpm: Optional[int] = None,
        power_mode: str = "Beast",
        refresh_rate: int = 120,
        battery_pct: int = 100,
        on_ac: bool = True,
        battery_watts: float = 0.0
    ):
        """Updates HUD telemetry widgets with live stats."""
        if not self.is_visible or self.window is None or not self.window.winfo_exists():
            return

        try:
            # CPU
            cpu_t_str = f"{cpu_temp:.0f}°C" if cpu_temp is not None else "--°C"
            cpu_color = "#EF4444" if (cpu_temp and cpu_temp > 85) else "#F59E0B" if (cpu_temp and cpu_temp > 75) else "#60A5FA"
            if self.lbl_cpu:
                self.lbl_cpu.configure(text=f"💻 CPU: {cpu_t_str} {cpu_usage:.0f}%", fg=cpu_color)

            # GPU
            gpu_t_str = f"{gpu_temp:.0f}°C" if gpu_temp is not None else "--°C"
            gpu_color = "#EF4444" if (gpu_temp and gpu_temp > 82) else "#F59E0B" if (gpu_temp and gpu_temp > 72) else "#34D399"
            if self.lbl_gpu:
                self.lbl_gpu.configure(text=f"🎮 GPU: {gpu_t_str} {gpu_usage:.0f}%", fg=gpu_color)

            # Fan
            if self.lbl_fan:
                fan_str = f"{fan_rpm:,} RPM" if fan_rpm else "Auto"
                self.lbl_fan.configure(text=f"🌪️ Fan: {fan_str}")

            # Mode & Display
            if self.lbl_mode:
                mode_str = f"⚡ {power_mode.upper()} {refresh_rate}Hz"
                m_color = "#EF4444" if power_mode.lower() == "beast" else "#38BDF8" if power_mode.lower() == "balanced" else "#22C55E"
                self.lbl_mode.configure(text=mode_str, fg=m_color)

            # Power / Battery
            if self.lbl_power:
                if on_ac:
                    w_str = f"+{abs(battery_watts):.1f}W" if battery_watts > 1.0 else "AC"
                    self.lbl_power.configure(text=f"🔌 {battery_pct}% ({w_str})", fg="#22C55E")
                else:
                    w_str = f"-{abs(battery_watts):.1f}W" if battery_watts != 0.0 else "Bat"
                    self.lbl_power.configure(text=f"🔋 {battery_pct}% ({w_str})", fg="#F59E0B" if battery_pct > 25 else "#EF4444")
        except Exception:
            pass

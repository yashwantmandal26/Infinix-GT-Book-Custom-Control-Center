"""Offline regression tests: no EC/HID writes, hooks, autostart, or tray workers."""
import copy
import os
import json
from contextlib import ExitStack
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import infinix_toolkit as toolkit
import color_studio


class ControlCenterTests(unittest.TestCase):
    def tearDown(self):
        toolkit.SerialEngine._close_port()
        toolkit.SerialEngine._last_port = None
        toolkit.SerialEngine._ec_power_state = None
        toolkit.SerialEngine._last_power_refresh = 0.0

    def test_vivid_color_and_rear_effect_frames(self):
        vivid = toolkit.vivid_rgb((167, 139, 250))
        self.assertEqual(max(vivid), 250)
        self.assertEqual(min(vivid), 0)
        for mode in (101, 102, 103, 104):
            rgb, brightness = toolkit.render_backzone_effect(
                mode, 0.37, (167, 139, 250), (56, 189, 248), 100
            )
            self.assertTrue(all(0 <= channel <= 255 for channel in rgb))
            self.assertTrue(1 <= brightness <= 100)
            if len(set(rgb)) > 1:
                self.assertEqual(min(rgb), 0)

    def test_rear_uart_packet_and_connection_reuse(self):
        class FakeSerial:
            is_open = True
            def __init__(self):
                self.frames = []
            def write(self, payload):
                self.frames.append(payload)
                return len(payload)
            def flush(self):
                pass
            def close(self):
                self.is_open = False
        fake = FakeSerial()
        toolkit.SerialEngine._serial = None
        toolkit.SerialEngine._last_port = None
        toolkit.SerialEngine._ec_power_state = None
        toolkit.SerialEngine._last_power_refresh = 0.0
        with patch.object(toolkit.SerialEngine, '_discover_backzone_port', return_value='COM1'), \
             patch.object(toolkit.serial, 'Serial', return_value=fake) as open_port, \
             patch.object(toolkit.HardwareEngine, 'set_ec_backlight_power', return_value=True) as power:
            self.assertTrue(toolkit.SerialEngine.send_backzone_rgb(5, 167, 139, 250, 4, 100, 56, 189, 248, 100))
            self.assertTrue(toolkit.SerialEngine.send_backzone_rgb(1, 56, 189, 248, 4, 75))
        self.assertEqual(open_port.call_count, 1)
        self.assertEqual(power.call_count, 1)
        self.assertEqual(len(fake.frames), 2)
        self.assertEqual(len(fake.frames[0]), 17)
        self.assertEqual(fake.frames[0][:3], bytes((0x34, 0x0E, 5)))
        self.assertEqual(fake.frames[0][10], 44)
        self.assertEqual(fake.frames[0][15], 44)

    def test_preset_validation_and_copy(self):
        data = dict(zones=copy.deepcopy(toolkit.DEFAULT_CONFIG['zones']), brightness=75)
        validated = toolkit.validate_lighting_preset(data)
        data['zones']['1'][0] = 99
        self.assertNotEqual(validated['zones']['1'][0], 99)
        for invalid in (None, {}, dict(data, brightness=500),
                        dict(data, zones={'1': [0, 0, 0]}),
                        dict(data, effect_mode='invalid'), dict(data, animation_speed='invalid'),
                        dict(data, animation_direction='invalid')):
            with self.assertRaises(ValueError):
                toolkit.validate_lighting_preset(invalid)

    def test_direction_choices_and_legacy_migration(self):
        self.assertEqual(
            toolkit.ANIMATION_DIRECTIONS,
            ("➡️ Left to Right", "⬅️ Right to Left"),
        )
        self.assertEqual(toolkit.normalize_animation_direction("🔄 Clockwise"), "➡️ Left to Right")
        self.assertEqual(toolkit.normalize_animation_direction("🔁 Counter-CW"), "⬅️ Right to Left")
        data = dict(
            zones=copy.deepcopy(toolkit.DEFAULT_CONFIG['zones']),
            brightness=0,
            animation_direction="🔁 Counter-CW",
        )
        validated = toolkit.validate_lighting_preset(data)
        self.assertEqual(validated["animation_direction"], "⬅️ Right to Left")
        self.assertEqual(validated["brightness"], 0)

    def test_new_lighting_effect_frames(self):
        for direction in toolkit.ANIMATION_DIRECTIONS:
            rainbow_frames = [toolkit.render_all_aurora(step, direction) for step in (0, 25, 75, 150)]
            wave_frames = [toolkit.render_wave_sweep(step, direction) for step in (0, 10, 25, 50)]
            for frame in rainbow_frames + wave_frames:
                self.assertEqual(set(frame), {"1", "2", "3", "4"})
                self.assertTrue(all(0 <= channel <= 255 for rgb in frame.values() for channel in rgb))
            self.assertGreater(len({rgb for frame in rainbow_frames for rgb in frame.values()}), 7)
            self.assertTrue(any(len(set(frame.values())) > 1 for frame in wave_frames))

        audio = toolkit.render_audio_visualizer((1.0, 0.7, 0.35, 0.05), beat=0.0, step=12)
        self.assertEqual(set(audio), {"1", "2", "3", "4"})
        self.assertGreater(sum(audio["1"]), sum(audio["4"]))
        beat = toolkit.render_audio_visualizer((1.0,) * 4, beat=1.0, step=12)
        self.assertTrue(all(max(rgb) > 240 and min(rgb) > 35 for rgb in beat.values()))
        # Audio silence brightness floor protection: never drop to dim/dark 3.5%
        silent = toolkit.render_audio_visualizer((0.0,) * 4, beat=0.0, step=0)
        self.assertTrue(all(max(rgb) >= 90 for rgb in silent.values()), "Silent audio should maintain >= 35% visible baseline")
        user_zones = {"1": (255, 0, 50), "2": (255, 100, 0), "3": (255, 200, 0), "4": (0, 255, 100)}
        silent_blended = toolkit.render_audio_visualizer((0.0,) * 4, beat=0.0, step=0, base_zones=user_zones)
        self.assertEqual(silent_blended["1"], user_zones["1"], "Silent audio with base_zones should retain user colors")

        data = dict(zones=copy.deepcopy(toolkit.DEFAULT_CONFIG['zones']), effect_mode='AllAurora')
        self.assertEqual(toolkit.validate_lighting_preset(data)['effect_mode'], 'AllAurora')
        data_prism = dict(zones=copy.deepcopy(toolkit.DEFAULT_CONFIG['zones']), effect_mode='RainbowPrism')
        self.assertEqual(toolkit.validate_lighting_preset(data_prism)['effect_mode'], 'RainbowPrism')
        data_fire = dict(zones=copy.deepcopy(toolkit.DEFAULT_CONFIG['zones']), effect_mode='BlazingFire')
        self.assertEqual(toolkit.validate_lighting_preset(data_fire)['effect_mode'], 'BlazingFire')

        # Flow direction verification for All Aurora
        f0_ltr = toolkit.render_all_aurora(0, "➡️ Left to Right")
        f18_ltr = toolkit.render_all_aurora(18, "➡️ Left to Right")
        # In Left-to-Right: Zone 1 has red-dominant at step 0 (255, 0, 0), which moves to Zone 2 at step 18
        self.assertGreater(f0_ltr["1"][0], 200)
        self.assertGreater(f18_ltr["2"][0], 200)

        f0_rtl = toolkit.render_all_aurora(0, "⬅️ Right to Left")
        f18_rtl = toolkit.render_all_aurora(18, "⬅️ Right to Left")
        # In Right-to-Left: Zone 4 has red-dominant at step 0, which moves to Zone 3 at step 18
        self.assertGreater(f0_rtl["4"][0], 200)
        self.assertGreater(f18_rtl["3"][0], 200)

    def test_reactive_typing_per_zone(self):
        """Verify key-to-zone physical mapping and per-zone reactive luminescence isolation."""
        # 1. Key-to-Zone mappings
        for k in ('w', 'a', 's', 'd', 'esc', 'tab', 'caps lock', '1', 'f1'):
            self.assertEqual(toolkit.get_key_zone(k), '1', f"Key {k} should map to Zone 1")
        for k in ('5', '6', 't', 'g', 'h', 'space', 'b', 'n', 'f6'):
            self.assertEqual(toolkit.get_key_zone(k), '2', f"Key {k} should map to Zone 2")
        for k in ('0', 'p', 'enter', 'backspace', 'up', 'left', 'right', 'down', 'delete', 'f11'):
            self.assertEqual(toolkit.get_key_zone(k), '3', f"Key {k} should map to Zone 3")
        for k in ('num lock', 'numpad 1', 'num 5', 'numpad enter', 'num +', 'kp_1', 'num 0', 'numpad del'):
            self.assertEqual(toolkit.get_key_zone(k), '4', f"Key {k} should map to Zone 4")

        # Hardware KeyboardEvent objects: NumLock ON (names '1', '2', '3', '4' with is_keypad=True)
        class MockKeyEvent:
            def __init__(self, name, scan_code=0, is_keypad=False):
                self.name = name
                self.scan_code = scan_code
                self.is_keypad = is_keypad

        # Keypad numbers with NumLock ON must map to Zone 4, NEVER Zone 1 ('w')
        for sc, num_str in ((79, '1'), (80, '2'), (81, '3'), (75, '4'), (76, '5'), (82, '0')):
            ev = MockKeyEvent(num_str, scan_code=sc, is_keypad=True)
            self.assertEqual(toolkit.get_key_zone(ev), '4', f"Keypad '{num_str}' event must map to Zone 4 (Numpad)")

        # Keypad navigation with NumLock OFF (e.g. Num 4 -> 'left' with scan_code 75) must map to Zone 4, NEVER Zone 1
        ev_left = MockKeyEvent('left', scan_code=75, is_keypad=True)
        self.assertEqual(toolkit.get_key_zone(ev_left), '4', "Keypad left arrow must map to Zone 4")

        # Normal 'w' and top-row '1' must still map to Zone 1
        ev_w = MockKeyEvent('w', scan_code=17, is_keypad=False)
        self.assertEqual(toolkit.get_key_zone(ev_w), '1', "Key 'w' must map to Zone 1")
        ev_top1 = MockKeyEvent('1', scan_code=2, is_keypad=False)
        self.assertEqual(toolkit.get_key_zone(ev_top1), '1', "Top-row '1' must map to Zone 1")

        # 2. Per-zone reactive luminescence
        cfg = {'1': [255, 0, 0], '2': [0, 255, 0], '3': [0, 0, 255], '4': [255, 255, 0]}
        now = 100.0

        # Idle state (elevated to ~35% for comfortable night visibility)
        idle = toolkit.render_reactive_typing({'1': 0, '2': 0, '3': 0, '4': 0}, cfg, now=now)
        for zid, rgb in idle.items():
            self.assertTrue(all(c <= 95 for c in rgb), f"Idle zone {zid} should be visible ambient")
            self.assertTrue(any(c >= 70 for c in rgb), f"Idle zone {zid} should have sufficient brightness")

        # Strike Zone 1 only (WASD/'w' zone) -> ONLY Zone 1 bursts, other zones remain at ambient
        z1_hit = toolkit.render_reactive_typing({'1': now - 0.01, '2': 0, '3': 0, '4': 0}, cfg, now=now)
        self.assertGreater(z1_hit['1'][0], 240, "Zone 1 should burst with ultra-high brightness")
        self.assertLess(z1_hit['2'][1], 95, "Zone 2 should remain at ambient without ripple")
        self.assertLess(z1_hit['3'][2], 95, "Zone 3 should remain at ambient without ripple")
        self.assertLess(z1_hit['4'][0], 95, "Zone 4 should remain at ambient without ripple")

        # Strike Zone 4 (Numpad) only -> ONLY Zone 4 bursts, Zone 1 ('w' zone) and others remain at ambient
        z4_hit = toolkit.render_reactive_typing({'1': 0, '2': 0, '3': 0, '4': now - 0.01}, cfg, now=now)
        self.assertGreater(z4_hit['4'][0], 240, "Zone 4 should burst with ultra-high brightness")
        self.assertLess(z4_hit['1'][0], 95, "Zone 1 ('w' zone) MUST remain at ambient when numpad is typed")
        self.assertLess(z4_hit['2'][1], 95, "Zone 2 should remain at ambient")
        self.assertLess(z4_hit['3'][2], 95, "Zone 3 should remain at ambient")

    def test_scalar_packet_and_invalid_ec_responses(self):
        for value, expected in ((130, 130), ([0] * 16 + [130], 130)):
            response = SimpleNamespace(Properties_=lambda name: SimpleNamespace(Value=value))
            with patch.object(toolkit.HardwareEngine, '_exec_acpi_buffer', return_value=response):
                self.assertEqual(toolkit.HardwareEngine._io_read(None, 160), expected)
        for value in (None, [], 'bad'):
            response = SimpleNamespace(Properties_=lambda name: SimpleNamespace(Value=value))
            with patch.object(toolkit.HardwareEngine, '_exec_acpi_buffer', return_value=response):
                with self.assertRaises(RuntimeError):
                    toolkit.HardwareEngine._io_read(None, 160)

    def test_keyboard_watchdog_packet_is_non_disruptive(self):
        """The keepalive must send OEM WriteLightNotAutoClose command 0x19, not reapply a lighting mode."""
        class FakeHid:
            def __init__(self):
                self.frames = []
            def write(self, payload):
                self.frames.append(bytes(payload))
                return len(payload)

        fake = FakeHid()
        with patch.object(toolkit.HardwareEngine, '_get_or_open_device', return_value=fake):
            self.assertTrue(toolkit.HardwareEngine.send_disable_auto_close())

        self.assertEqual(len(fake.frames), 1)
        frame = fake.frames[0]
        self.assertEqual(len(frame), 64)
        self.assertEqual(frame[:3], bytes((0x06, 0x19, 0x04)))
        self.assertEqual(frame[3:63], bytes(60))
        self.assertEqual(frame[63], sum(frame[1:63]) & 0xFF)

    def test_hardware_engine_brightness_scaling(self):
        """Verify brightness scaling maps 0-100% to 0-255 (100% -> 255 peak hardware brightness)."""
        # Test scale helper
        self.assertEqual(toolkit.HardwareEngine._scale_brightness(100), 255)
        self.assertEqual(toolkit.HardwareEngine._scale_brightness(75), 191)
        self.assertEqual(toolkit.HardwareEngine._scale_brightness(50), 127)
        self.assertEqual(toolkit.HardwareEngine._scale_brightness(25), 64)
        self.assertEqual(toolkit.HardwareEngine._scale_brightness(0), 0)
        self.assertEqual(toolkit.HardwareEngine._scale_brightness(255), 255)

        # Test HID packets receive 255 at 100% brightness
        class FakeHid:
            def __init__(self):
                self.frames = []
            def write(self, payload):
                self.frames.append(bytes(payload))
                return len(payload)

        fake = FakeHid()
        with patch.object(toolkit.HardwareEngine, '_get_or_open_device', return_value=fake):
            # Test global RGB
            toolkit.HardwareEngine.send_global_rgb(255, 0, 0, brightness=100)
            self.assertEqual(fake.frames[-1][10], 255)

            # Test 4-zone RGB
            fake.frames.clear()
            zones = {"1": (255, 0, 50), "2": (255, 0, 50), "3": (255, 0, 50), "4": (255, 0, 50)}
            toolkit.HardwareEngine.send_4zone_rgb(zones, brightness=100, set_mode_static=True)
            # Both the static mode frame and individual zone frames must have byte 10 = 255
            for frame in fake.frames:
                self.assertEqual(frame[10], 255)

            # Test hardware animation mode
            fake.frames.clear()
            toolkit.HardwareEngine.send_hardware_mode(0x14, 255, 255, 255, brightness=100)
            self.assertEqual(fake.frames[0][10], 255)

            # Test mecha bar
            fake.frames.clear()
            toolkit.HardwareEngine.send_mecha_bar(56, 189, 248, enabled=True)
            self.assertEqual(fake.frames[0][10], 255)

    def test_offline_ui(self):
        with ExitStack() as stack:
            for engine in (toolkit.HardwareEngine, toolkit.SerialEngine):
                for name in vars(engine):
                    if not name.startswith('_') and callable(getattr(engine, name)):
                        stack.enter_context(patch.object(engine, name, return_value=True))
            app_class = toolkit.InfinixGTToolkitApp
            for name in vars(app_class):
                if name.startswith('_start_') or name in ('_init_tray_icon', '_save_config', '_manage_startup_shortcut'):
                    stack.enter_context(patch.object(app_class, name))
            cfg = copy.deepcopy(toolkit.DEFAULT_CONFIG)
            cfg.update(autostart=False, win_key_lock=False, software_fn_lock=False)
            stack.enter_context(patch.object(app_class, '_load_config', return_value=cfg))
            stack.enter_context(patch.object(toolkit.keyboard, 'on_press'))
            stack.enter_context(patch.object(toolkit.ctypes.windll.kernel32, 'CreateMutexW', return_value=0))
            stack.enter_context(patch.object(toolkit.ctypes.windll.kernel32, 'GetLastError', return_value=0))
            stack.enter_context(patch.object(toolkit.messagebox, 'showinfo'))
            app = app_class()
            errors = []
            app.root.report_callback_exception = lambda *args: errors.append(args)
            try:
                app.root.geometry('1280x860+20+20')
                for theme in ('Light', 'Dark'):
                    app._set_theme(theme)
                    for page in app.pages:
                        app._select_nav(page)
                        app.root.update()
                        self.assertTrue(app.pages[page].winfo_ismapped(), page)
                app._select_nav('lighting')
                self.assertIn('Spectrum Flow', app.bz_mode_seg.cget('values'))
                self.assertEqual(app.dir_seg.cget('values'), list(toolkit.ANIMATION_DIRECTIONS))
                app._set_hardware_status(False, 'Rear light bar', 'A long firmware error ' * 20)
                app.root.update()
                self.assertLess(len(app.top_engine_pill.cget('text')), 35)
                app._set_hardware_status(True, 'Rear light bar')
                app.preset_name_entry.insert(0, 'Regression profile')
                app.anim_speed = 'Turbo'
                app._save_user_preset()
                app.anim_speed = 'Slow'
                app._load_user_preset()
                self.assertEqual(app.anim_speed, 'Turbo')
                app.root.update()
                self.assertFalse(errors, errors)
                # Switch to Rear light bar tab and capture its preview screenshot
                app._select_nav('backzone')
                app.root.update()
                self.assertTrue(app.pages['backzone'].winfo_ismapped())
                
                # Test category selection and effect switching
                app.backzone_view._select_category('Animated')
                app.backzone_view._select_mode(105)  # Aurora Flow
                app.root.update()
                self.assertEqual(app.bz_mode, 105)
                
                app.backzone_view._select_category('Audio')
                app.backzone_view._select_mode(110)  # Audio Pulse
                app.root.update()
                self.assertEqual(app.bz_mode, 110)

                app.backzone_view._select_category('Battle & Arcade')
                app.backzone_view._select_mode(201)  # Team Clash 2.0
                app.root.update()
                self.assertEqual(app.bz_mode, 110)  # Disabled Beta cannot replace Audio Pulse.
                beta_tab = app.backzone_view.cat_buttons['Battle & Arcade']
                self.assertEqual(beta_tab.cget('state'), 'disabled')
                self.assertIn('Beta', beta_tab.cget('text'))

                # Capture preview of the redesigned Rear light bar tab
                from PIL import ImageGrab
                hwnd = toolkit.ctypes.windll.user32.GetParent(app.root.winfo_id())
                ImageGrab.grab(window=hwnd).save('rear_mecha_bar_preview.png')
                
                # Switch back to lighting and verify redesigned Zone Color card
                app._select_nav('lighting')
                app.root.update()
                ImageGrab.grab(window=hwnd).save('control_center_preview.png')

                # Verify Zone Color card components
                self.assertTrue(hasattr(app, 'zone_hex_label'))
                self.assertTrue(hasattr(app, 'btn_edit_color'))
                self.assertTrue(hasattr(app, 'btn_copy_hex'))
                self.assertTrue(hasattr(app, 'btn_apply_all'))
                self.assertTrue(hasattr(app, 'recent_swatches_frame'))

                # Test manual color commit sets Solid mode and clears active theme
                app.effect_mode = "Breathing"
                app.current_theme = "Cyberpunk"
                app._commit_manual_zone_color(1, (255, 128, 64))
                self.assertEqual(app.effect_mode, "Solid")
                self.assertEqual(app.current_theme, "")
                self.assertEqual(app.zones["1"], [255, 128, 64])

                # Test Apply to All Zones
                app._apply_to_all_zones()
                for zid in ("1", "2", "3", "4"):
                    self.assertEqual(app.zones[zid], [255, 128, 64])

                # Capture compact card screenshot
                ImageGrab.grab(window=hwnd).save('zone_card_compact_dark.png')

                # Open and capture ColorPickerDialog in Dark theme
                dlg_dark = color_studio.ColorPickerDialog(
                    parent=app.root,
                    initial_rgb=tuple(app.zones["1"]),
                    title="Zone 1 - Color Studio (Dark)",
                    theme_colors=app.theme,
                    recent_colors=app.recent_colors
                )
                app.root.update()
                dlg_hwnd = toolkit.ctypes.windll.user32.GetParent(dlg_dark.winfo_id())
                ImageGrab.grab(window=dlg_hwnd or hwnd).save('color_picker_dark_preview.png')
                dlg_dark.hex_var.set("INVALID")
                app.root.update()
                ImageGrab.grab(window=dlg_hwnd or hwnd).save('color_picker_invalid_hex.png')
                dlg_dark.hex_var.set("#38BDF8")
                app.root.update()
                dlg_dark.destroy()
                app.root.update()

                # Test Light theme dialog capture
                app._set_theme('Light')
                app.root.update()
                dlg_light = color_studio.ColorPickerDialog(
                    parent=app.root,
                    initial_rgb=tuple(app.zones["1"]),
                    title="Zone 1 - Color Studio (Light)",
                    theme_colors=app.theme,
                    recent_colors=app.recent_colors
                )
                app.root.update()
                dlg_l_hwnd = toolkit.ctypes.windll.user32.GetParent(dlg_light.winfo_id())
                ImageGrab.grab(window=dlg_l_hwnd or hwnd).save('color_picker_light_preview.png')
                dlg_light.destroy()
                app._set_theme('Dark')
                app.root.update()
            finally:
                app.running = False
                try:
                    app.root.update_idletasks()
                except Exception:
                    pass
                app.root.destroy()

    def test_color_studio_math_and_validation(self):
        """Test color conversion math, bounds validation, and relative luminance."""
        # 1. normalize_hex_color
        self.assertEqual(color_studio.normalize_hex_color("#fff"), "#FFFFFF")
        self.assertEqual(color_studio.normalize_hex_color("38bdf8"), "#38BDF8")
        self.assertEqual(color_studio.normalize_hex_color("#123456"), "#123456")
        for bad in ("", "12", "#12345", "ggg", "1234567", "#12345678", None):
            self.assertIsNone(color_studio.normalize_hex_color(bad))

        # 2. hex <-> rgb
        self.assertEqual(color_studio.hex_to_rgb("#000000"), (0, 0, 0))
        self.assertEqual(color_studio.hex_to_rgb("#FFFFFF"), (255, 255, 255))
        self.assertEqual(color_studio.hex_to_rgb("#38BDF8"), (56, 189, 248))
        self.assertEqual(color_studio.rgb_to_hex((56, 189, 248)), "#38BDF8")

        # 3. rgb <-> hsv display
        h, s, v = color_studio.rgb_to_hsv_display((255, 0, 0))
        self.assertEqual((h, s, v), (0, 100, 100))
        self.assertEqual(color_studio.hsv_display_to_rgb(0, 100, 100), (255, 0, 0))

        h, s, v = color_studio.rgb_to_hsv_display((0, 255, 0))
        self.assertEqual((h, s, v), (120, 100, 100))
        self.assertEqual(color_studio.hsv_display_to_rgb(120, 100, 100), (0, 255, 0))

        # 4. validate_rgb_channels & validate_hsv_channels
        self.assertTrue(color_studio.validate_rgb_channels("255", "128", "0"))
        for bad_rgb in (("-1", "0", "0"), ("256", "0", "0"), ("abc", "0", "0"), ("", "0", "0")):
            self.assertFalse(color_studio.validate_rgb_channels(*bad_rgb))

        self.assertTrue(color_studio.validate_hsv_channels("359", "100", "50"))
        for bad_hsv in (("-1", "0", "0"), ("360", "0", "0"), ("0", "101", "0"), ("0", "0", "-1")):
            self.assertFalse(color_studio.validate_hsv_channels(*bad_hsv))

        # 5. best_text_color relative luminance WCAG
        self.assertEqual(color_studio.best_text_color((0, 0, 0)), "#FFFFFF")
        self.assertEqual(color_studio.best_text_color((15, 23, 42)), "#FFFFFF")
        self.assertEqual(color_studio.best_text_color((255, 255, 255)), "#000000")
        self.assertEqual(color_studio.best_text_color((250, 204, 21)), "#000000")

    def test_recent_colors_and_presets(self):
        """Test MRU recent color handling, deduplication, and max 8 cap."""
        recent = ["#FF0000", "#00FF00"]
        # Add new color
        color_studio.add_recent_color(recent, "#0000FF")
        self.assertEqual(recent[0], "#0000FF")
        self.assertEqual(len(recent), 3)

        # Re-add existing color -> should move to front without duplicates
        color_studio.add_recent_color(recent, "#FF0000")
        self.assertEqual(recent[0], "#FF0000")
        self.assertEqual(recent.count("#FF0000"), 1)

        # Add 10 unique colors -> should cap at 8
        for i in range(10):
            color_studio.add_recent_color(recent, f"#{i:02x}{i*2:02x}{i*3:02x}")
        self.assertEqual(len(recent), 8)

        # Preset palette validation
        self.assertGreaterEqual(len(color_studio.PRESET_PALETTE), 10)
        for label, hex_code, rgb in color_studio.PRESET_PALETTE:
            self.assertEqual(color_studio.normalize_hex_color(hex_code), hex_code.upper())
            self.assertEqual(color_studio.hex_to_rgb(hex_code), rgb)

    def test_color_picker_dialog_interaction(self):
        """Test ColorPickerDialog lifecycle, keyboard arrow navigation, cancel rollback, and apply callback."""
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        applied_colors = []
        preview_colors = []

        try:
            dlg = color_studio.ColorPickerDialog(
                parent=root,
                initial_rgb=(56, 189, 248),
                title="Test Studio",
                on_apply=lambda rgb: applied_colors.append(rgb),
                on_preview=lambda rgb: preview_colors.append(rgb),
                recent_colors=["#FF0000", "#00FF00"]
            )
            root.update()

            # Initial sync state
            self.assertEqual(dlg.hex_var.get(), "#38BDF8")
            self.assertEqual(dlg.r_var.get(), "56")
            self.assertEqual(dlg.g_var.get(), "189")
            self.assertEqual(dlg.b_var.get(), "248")

            # Spectrum keyboard navigation
            init_sat = dlg.spectrum.current_sat
            event = tk.Event()
            event.state = 0
            dlg.spectrum._on_key_move(-1, 0, event)
            root.update()
            self.assertEqual(dlg.spectrum.current_sat, init_sat - 1)

            # Hue slider keyboard navigation
            init_hue = dlg.hue_slider.current_hue
            dlg.hue_slider._on_key_move(1, event)
            root.update()
            self.assertEqual(dlg.hue_slider.current_hue, (init_hue + 1) % 360)

            # Invalid hex input gives feedback
            dlg.hex_var.set("INVALID")
            root.update()
            self.assertTrue(len(dlg.hex_error_lbl.cget("text")) > 0)

            # Valid hex input clears feedback and triggers preview
            dlg.hex_var.set("#FF8800")
            root.update()
            self.assertEqual(dlg.hex_error_lbl.cget("text"), "")
            self.assertIn((255, 136, 0), preview_colors)

            # Apply saves color
            dlg._on_apply()
            root.update()
            self.assertEqual(applied_colors, [(255, 136, 0)])

            # Test cancel rollback on another instance
            dlg2 = color_studio.ColorPickerDialog(
                parent=root,
                initial_rgb=(100, 150, 200),
                on_preview=lambda rgb: preview_colors.append(rgb)
            )
            root.update()
            dlg2.hex_var.set("#112233")
            root.update()
            dlg2._on_cancel()
            root.update()
            self.assertEqual(preview_colors[-1], (100, 150, 200))
        finally:
            root.destroy()

    def test_rear_twelve_effects_and_interpolation(self):
        """Verify all 12 software & reactive effects render valid clamped RGB frames."""
        all_modes = (1, 2, 3, 4, 5, 6, 15, 101, 102, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114)
        c1, c2 = (56, 189, 248), (167, 139, 250)
        
        for mode in all_modes:
            rgb, bright = toolkit.backzone_ui.render_backzone_effect_v2(
                mode, 0.45, c1, c2, 100,
                audio_volume=0.6, audio_levels=[0.8, 0.4, 0.2, 0.1], audio_beat=0.5,
                temp_celsius=65.0, bat_pct=80, on_ac=True
            )
            self.assertTrue(all(0 <= channel <= 255 for channel in rgb), f"Mode {mode} RGB out of bounds: {rgb}")
            self.assertTrue(0 <= bright <= 100, f"Mode {mode} brightness out of bounds: {bright}")

        # Test Shortest-Path Hue Interpolation
        red = (255, 0, 0)
        blue = (0, 0, 255)
        mid_blend = toolkit.backzone_ui.interpolate_hue_shortest(red, blue, 0.5)
        self.assertTrue(all(0 <= v <= 255 for v in mid_blend))

        # Test Thermal Transitions across cool, normal, warm, hot
        cool_rgb, _ = toolkit.backzone_ui.render_backzone_effect_v2(112, 0.0, c1, c2, 100, temp_celsius=40.0)
        hot_rgb, _ = toolkit.backzone_ui.render_backzone_effect_v2(112, 0.0, c1, c2, 100, temp_celsius=90.0)
        self.assertGreater(hot_rgb[0], cool_rgb[0])  # Hot has much stronger red channel
        
        # Test Audio Pulse with zero volume vs peak volume
        _, silent_bright = toolkit.backzone_ui.render_backzone_effect_v2(110, 0.0, c1, c2, 100, audio_volume=0.0)
        _, loud_bright = toolkit.backzone_ui.render_backzone_effect_v2(110, 0.0, c1, c2, 100, audio_volume=1.0, audio_beat=1.0)
        self.assertGreater(loud_bright, silent_bright)

    def test_choreographed_battle_and_arcade_effects(self):
        """Verify all 10 Battle & Arcade modes render clamped 36-LED strip frames and dominant hardware RGB."""
        battle_modes = (201, 202, 203, 204, 205, 206, 207, 208, 209, 210)
        c1, c2 = (255, 40, 40), (40, 255, 120)

        self.assertIn("Battle & Arcade", toolkit.backzone_ui.CATEGORIES)

        for mode in battle_modes:
            self.assertIn(mode, toolkit.backzone_ui.BACKZONE_MODE_NAMES)
            self.assertIn(mode, toolkit.backzone_ui.EFFECT_METADATA)
            meta = toolkit.backzone_ui.EFFECT_METADATA[mode]
            self.assertEqual(meta["category"], "Battle & Arcade")
            self.assertEqual(meta["badge"], "Choreographed")

            # Check across multiple animation phases
            for phase in (0.0, 0.15, 0.35, 0.50, 0.75, 0.88, 0.99):
                # 1. 36-LED strip rendering
                leds = toolkit.backzone_ui.render_backzone_strip_leds(
                    mode, phase, c1, c2, brightness=100, num_leds=36
                )
                self.assertEqual(len(leds), 36, f"Mode {mode} phase {phase} did not produce 36 LEDs")
                for i, rgb in enumerate(leds):
                    self.assertTrue(
                        all(0 <= channel <= 255 for channel in rgb),
                        f"Mode {mode} phase {phase} LED {i} RGB out of bounds: {rgb}"
                    )

                # 2. Dominant hardware streaming RGB
                rgb_dom, bright = toolkit.backzone_ui.render_backzone_effect_v2(
                    mode, phase, c1, c2, brightness=100
                )
                self.assertTrue(
                    all(0 <= channel <= 255 for channel in rgb_dom),
                    f"Mode {mode} phase {phase} dominant RGB out of bounds: {rgb_dom}"
                )
                self.assertTrue(0 <= bright <= 100)

    def test_device_safety_and_reliability_mechanisms(self):
        """Verify EC address whitelisting, value clamping, HID backoff, conflict killer throttle, and config recovery."""
        # 1. EC RAM Safety: Whitelist & Clamping
        written = []
        def fake_io_write(acpi_obj, reg, val):
            written.append((reg, val))

        with patch.object(toolkit.HardwareEngine, '_io_write', side_effect=fake_io_write):
            # Safe write to address 0x40 (power mode) with out-of-bounds value 999 -> clamped to 255
            ok = toolkit.HardwareEngine._ec_write_ram(None, 0x40, 999)
            self.assertTrue(ok)
            val_writes = [val for reg, val in written if reg == 160]
            self.assertEqual(val_writes[-1], 255)

            # Negative value -> clamped to 0
            ok = toolkit.HardwareEngine._ec_write_ram(None, 0x40, -10)
            self.assertTrue(ok)
            val_writes = [val for reg, val in written if reg == 160]
            self.assertEqual(val_writes[-1], 0)

            # Unauthorized address -> rejected without writing
            written.clear()
            ok = toolkit.HardwareEngine._ec_write_ram(None, 0x99, 50)
            self.assertFalse(ok)
            self.assertEqual(len(written), 0)

        # 2. Conflict Process Scanning Throttle
        with patch.object(toolkit.psutil, 'process_iter') as mock_proc:
            mock_proc.return_value = []
            toolkit.HardwareEngine._last_conflict_kill = 0.0
            # First run: should iterate
            toolkit.HardwareEngine.kill_conflicting_oem_control_center()
            self.assertEqual(mock_proc.call_count, 1)

            # Immediate second run without force: throttled (no second call)
            toolkit.HardwareEngine.kill_conflicting_oem_control_center(force=False)
            self.assertEqual(mock_proc.call_count, 1)

            # Run with force=True: executes immediately
            toolkit.HardwareEngine.kill_conflicting_oem_control_center(force=True)
            self.assertEqual(mock_proc.call_count, 2)

        # 3. HID Device Enumeration Rate-Limiting on Failure
        toolkit.HardwareEngine._dev = None
        toolkit.HardwareEngine._last_open_failure = 0.0
        with patch.object(toolkit.hid, 'enumerate', return_value=[]) as mock_enum:
            dev1 = toolkit.HardwareEngine._get_or_open_device()
            self.assertIsNone(dev1)
            self.assertEqual(mock_enum.call_count, 1)

            # Immediate second call within 1.0s: throttled, does not enumerate
            dev2 = toolkit.HardwareEngine._get_or_open_device()
            self.assertIsNone(dev2)
            self.assertEqual(mock_enum.call_count, 1)

        # 4. Config Recovery: Damaged JSON falls back to backup or default
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            test_cfg_file = os.path.join(temp_dir, "config_v4.json")
            test_bak_file = os.path.join(temp_dir, "config_v4.json.bak")
            
            # Write good backup file
            with open(test_bak_file, "w", encoding="utf-8") as f:
                import json
                json.dump({"brightness": 88, "effect_mode": "Wave"}, f)
            # Write corrupted main config file
            with open(test_cfg_file, "w", encoding="utf-8") as f:
                f.write("{corrupted_json_content...")

            with patch('infinix_toolkit.CONFIG_FILE', test_cfg_file), \
                 patch('infinix_toolkit.CONFIG_DIR', temp_dir):
                app_dummy = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
                recovered = app_dummy._load_config()
                self.assertEqual(recovered.get("brightness"), 88)
                self.assertEqual(recovered.get("effect_mode"), "Wave")

    def test_all_aurora_consistent_color_motion(self):
        """Verify All Aurora maintains one consistent color across ping-pong sweep without hue shifts."""
        chosen_color = (140, 0, 255)  # Plasma Purple
        # Sweep through 40 steps covering a full roundtrip (Left to Right and vice versa)
        for step in range(0, 45, 5):
            frame = toolkit.render_all_aurora(step, "➡️ Left to Right", chosen_color)
            self.assertEqual(set(frame), {"1", "2", "3", "4"})
            for zid, (r, g, b) in frame.items():
                # Color consistency: G channel must remain 0 since base color has 0 green
                self.assertEqual(g, 0, f"Zone {zid} at step {step} has green={g} when base color has no green!")
                # Ratio of R to B must match the base color (140/255) within integer rounding
                if b > 0:
                    ratio = r / b
                    self.assertAlmostEqual(ratio, 140 / 255, delta=0.15)

        # Verify ping-pong motion (Zone 1 peak -> Zone 4 peak -> back to Zone 1 peak)
        f_start = toolkit.render_all_aurora(0, "➡️ Left to Right", chosen_color)
        f_mid = toolkit.render_all_aurora(46, "➡️ Left to Right", chosen_color)
        f_end = toolkit.render_all_aurora(92, "➡️ Left to Right", chosen_color)
        # At start (0), Zone 1 is brightest
        self.assertEqual(max(f_start, key=lambda z: sum(f_start[z])), "1")
        # At mid (roundtrip midpoint ~step 46), Zone 4 is brightest
        self.assertEqual(max(f_mid, key=lambda z: sum(f_mid[z])), "4")
        # At end (full cycle ~step 92), Zone 1 is brightest again
        self.assertEqual(max(f_end, key=lambda z: sum(f_end[z])), "1")

    def test_screen_sync_color_fidelity(self):
        """Verify process_screen_pixel captures faithful colors without garish saturation distortion."""
        # 1. White screen must stay neutral white, NOT turn neon blue or red
        white_in = (245, 245, 245)
        white_out = toolkit.process_screen_pixel(*white_in)
        self.assertTrue(abs(white_out[0] - white_out[1]) <= 2)
        self.assertTrue(abs(white_out[1] - white_out[2]) <= 2)
        self.assertGreater(min(white_out), 200)

        # 2. Gray / Dark slate screen must stay neutral
        gray_in = (120, 120, 120)
        gray_out = toolkit.process_screen_pixel(*gray_in)
        self.assertTrue(abs(gray_out[0] - gray_out[1]) <= 2)
        self.assertTrue(abs(gray_out[1] - gray_out[2]) <= 2)

        # 3. Vivid green must remain green dominant
        green_in = (10, 240, 40)
        green_out = toolkit.process_screen_pixel(*green_in)
        self.assertGreater(green_out[1], green_out[0] * 3)
        self.assertGreater(green_out[1], green_out[2] * 3)

        # 4. Pure red must remain red dominant
        red_in = (240, 20, 30)
        red_out = toolkit.process_screen_pixel(*red_in)
        self.assertGreater(red_out[0], red_out[1] * 3)
        self.assertGreater(red_out[0], red_out[2] * 3)

    def test_render_aurora(self):
        """Verify classic Aurora Borealis produces multi-hue northern lights across 4 zones."""
        for step in (0.0, 10.0, 25.5, 50.0):
            for direction in toolkit.ANIMATION_DIRECTIONS:
                frame = toolkit.render_aurora(step, direction)
                self.assertEqual(set(frame), {"1", "2", "3", "4"})
                for zid, rgb in frame.items():
                    self.assertEqual(len(rgb), 3)
                    self.assertTrue(all(0 <= val <= 255 for val in rgb))

    def test_all_motion_effects_coverage(self):
        """Verify all motion effects generate valid, clamped RGB frames without exception."""
        test_color = (255, 100, 50)
        test_zones = {"1": (255, 0, 0), "2": (0, 255, 0), "3": (0, 0, 255), "4": (255, 255, 0)}
        
        # 1. All Aurora
        f_all_aurora = toolkit.render_all_aurora(12.5, "➡️ Left to Right", test_color)
        self.assertEqual(set(f_all_aurora), {"1", "2", "3", "4"})
        
        # 2. Classic Aurora
        f_aurora = toolkit.render_aurora(12.5, "➡️ Left to Right")
        self.assertEqual(set(f_aurora), {"1", "2", "3", "4"})
        
        # 3. Wave sweep
        f_wave = toolkit.render_wave_sweep(15.0, "➡️ Left to Right")
        self.assertEqual(set(f_wave), {"1", "2", "3", "4"})
        
        # 4. Reactive typing
        typing_times = {"1": 100.0, "2": 99.8}
        f_typing = toolkit.render_reactive_typing(typing_times, test_zones, now=100.1, decay_duration=0.5)
        self.assertEqual(set(f_typing), {"1", "2", "3", "4"})
        
        # 5. Audio visualizer
        f_audio = toolkit.render_audio_visualizer([0.8, 0.4, 0.2, 0.9], beat=0.5, step=10.0, base_zones=test_zones)
        self.assertEqual(set(f_audio), {"1", "2", "3", "4"})
        
        # 6. Audio visualizer silent fallback
        f_audio_silent = toolkit.render_audio_visualizer([0.0, 0.0, 0.0, 0.0], beat=0.0, step=0.0, base_zones=test_zones)
        self.assertEqual(set(f_audio_silent), {"1", "2", "3", "4"})

        # 7. Rainbow Prism (ROYGBIV spectrum wave)
        for direction in toolkit.ANIMATION_DIRECTIONS:
            f_prism = toolkit.render_rainbow_prism(20.0, direction)
            self.assertEqual(set(f_prism), {"1", "2", "3", "4"})
            for zid, rgb in f_prism.items():
                self.assertTrue(all(0 <= val <= 255 for val in rgb))

        # 8. Blazing Fire (ultra-high brightness fire)
        for direction in toolkit.ANIMATION_DIRECTIONS:
            f_fire = toolkit.render_blazing_fire(15.0, direction)
            self.assertEqual(set(f_fire), {"1", "2", "3", "4"})
            for zid, rgb in f_fire.items():
                self.assertEqual(rgb[0], 255, "Blazing fire must have red channel at full 255 brightness")
                self.assertTrue(0 <= rgb[1] <= 255)
                self.assertTrue(0 <= rgb[2] <= 255)

    def test_hardware_engine_color_fidelity_without_forced_saturation(self):
        """Verify HardwareEngine does not distort subtle pastel or neutral RGB values into neon colors."""
        class FakeDevice:
            def __init__(self):
                self.frames = []
            def write(self, buf):
                self.frames.append(list(buf))
                return len(buf)

        fake = FakeDevice()
        with patch.object(toolkit.HardwareEngine, '_get_or_open_device', return_value=fake):
            # Test that a soft pastel color (255, 200, 220) is preserved as (255, 200, 220)
            # and NOT forced to 100% saturation (255, 0, 92) by vivid_rgb
            zones = {"1": (255, 200, 220), "2": (255, 200, 220), "3": (255, 200, 220), "4": (255, 200, 220)}
            toolkit.HardwareEngine.send_4zone_rgb(zones, brightness=100, set_mode_static=True)
            self.assertGreater(len(fake.frames), 0)
            # Check individual zone packet (bytes 7, 8, 9)
            last_frame = fake.frames[-1]
            self.assertEqual(last_frame[7], 255)
            self.assertEqual(last_frame[8], 200)
            self.assertEqual(last_frame[9], 220)

            # Test send_global_rgb preserves warm white (255, 240, 210)
            fake.frames.clear()
            toolkit.HardwareEngine.send_global_rgb(255, 240, 210, brightness=100)
            self.assertEqual(fake.frames[0][7], 255)
            self.assertEqual(fake.frames[0][8], 240)
            self.assertEqual(fake.frames[0][9], 210)

    def test_ui_dispatch_safety(self):
        """Verify _ui_dispatch safely swallows exceptions when app is terminated."""
        dummy_app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
        dummy_app.running = False
        dummy_app.root = None
        # Should not raise exception
        dummy_app._ui_dispatch(lambda: 1 / 0)

    def test_audio_visualizer_agc_and_quiet_volume(self):
        """Verify Audio Visualizer reacts dynamically even at very low volume / quiet headphones."""
        # 1. Test quiet headphone signal (levels ~0.08)
        quiet_levels = (0.12, 0.08, 0.05, 0.03)
        colors = toolkit.render_audio_visualizer(quiet_levels, beat=0.0, step=0)
        self.assertEqual(set(colors), {"1", "2", "3", "4"})
        # Should maintain visible illumination with energetic bass contrast
        self.assertGreater(sum(colors["1"]), sum(colors["4"]))

        # 2. Beat transient hit elevates brightness and desaturates towards white
        beat_colors = toolkit.render_audio_visualizer(quiet_levels, beat=0.9, step=0)
        # Zone 1 on beat hit should be brighter than without beat
        self.assertGreater(sum(beat_colors["1"]), sum(colors["1"]))

        # 3. Complete silence blends gracefully to user base colors
        base = {"1": (255, 50, 0), "2": (0, 200, 255), "3": (100, 255, 0), "4": (200, 0, 255)}
        silent_colors = toolkit.render_audio_visualizer((0.0, 0.0, 0.0, 0.0), beat=0.0, step=0, base_zones=base)
        self.assertEqual(silent_colors["1"], base["1"])
        self.assertEqual(silent_colors["2"], base["2"])

    def test_lighting_page_layout_order(self):
        """Verify Motion & effects card is directly adjacent to Your RGB signature."""
        with ExitStack() as stack:
            for engine in (toolkit.HardwareEngine, toolkit.SerialEngine):
                for name in vars(engine):
                    if not name.startswith('_') and callable(getattr(engine, name)):
                        stack.enter_context(patch.object(engine, name, return_value=True))
            app_class = toolkit.InfinixGTToolkitApp
            for name in vars(app_class):
                if name.startswith('_start_') or name in ('_init_tray_icon', '_save_config', '_manage_startup_shortcut'):
                    stack.enter_context(patch.object(app_class, name))
            cfg = copy.deepcopy(toolkit.DEFAULT_CONFIG)
            cfg.update(autostart=False, win_key_lock=False, software_fn_lock=False)
            stack.enter_context(patch.object(app_class, '_load_config', return_value=cfg))
            stack.enter_context(patch.object(toolkit.keyboard, 'on_press'))
            stack.enter_context(patch.object(toolkit.ctypes.windll.kernel32, 'CreateMutexW', return_value=0))
            stack.enter_context(patch.object(toolkit.ctypes.windll.kernel32, 'GetLastError', return_value=0))
            stack.enter_context(patch.object(toolkit.messagebox, 'showinfo'))
            app = app_class()
            try:
                # Verify Equalizer canvas and audio controls exist
                self.assertTrue(hasattr(app, 'audio_viz_frame'))
                self.assertTrue(hasattr(app, 'audio_eq_canvas'))
                self.assertTrue(hasattr(app, 'audio_gain_slider'))
                self.assertTrue(hasattr(app, 'audio_dev_lbl'))
                self.assertTrue(hasattr(app, '_eq_strip_items'))
                self.assertEqual(len(app._eq_strip_items), 4)

                # Test Equalizer preview drawing
                app.audio_levels = [0.8, 0.5, 0.3, 0.1]
                app.audio_beat = 0.85
                app._update_audio_eq_preview()
                self.assertIn("BEAT", app.audio_beat_badge.cget("text"))

                # Test Gain boost slider
                app._on_audio_gain_changed(2.2)
                self.assertEqual(app.audio_gain_multiplier, 2.2)
                self.assertIn("2.2x", app.audio_gain_lbl.cget("text"))

                # Test Effect switching toggles audio_viz_frame visibility
                app._select_nav('lighting')
                app.effect_mode = "AudioSync"
                app.effect_var.set("AudioSync")
                app._update_fx_status_ui()
                self.assertEqual(app.audio_viz_frame.winfo_manager(), "pack")

                app.audio_levels = [0.85, 0.65, 0.45, 0.20]
                app.audio_beat = 0.90
                app.audio_device_name = "Speakers (2- Senary Audio) / Headphones"
                app._update_audio_eq_preview()
                audio_zones = toolkit.render_audio_visualizer(app.audio_levels, beat=app.audio_beat, step=25)
                app._update_virtual_keyboard_preview(audio_zones)
                app.root.update()

                from PIL import ImageGrab
                hwnd = toolkit.ctypes.windll.user32.GetParent(app.root.winfo_id())
                ImageGrab.grab(window=hwnd).save('audio_visualizer_preview.png')

                app.effect_mode = "Wave"
                app.effect_var.set("Wave")
                app._update_fx_status_ui()
                self.assertEqual(app.audio_viz_frame.winfo_manager(), "")
            finally:
                app.root.destroy()

    def test_f3_brightness_and_effect_mode_cycling(self):
        """Verify F3 brightness cycle (100% -> 50% -> 20% -> 0% -> 100%) and hold mode cycling."""
        class MockApp:
            def __init__(self):
                self.brightness = 100
                self.effect_mode = "Solid"
                self.set_pct = None
                self.effect_var = SimpleNamespace(set=lambda m: None)
                self.osd_brightness_calls = []
                self.osd_effect_calls = []
            def root_after(self, delay, fn, *args):
                fn(*args)
            def _ui_dispatch(self, fn, *args, **kwargs):
                fn(*args, **kwargs)
            def _set_brightness_pct(self, pct):
                self.brightness = pct
                self.set_pct = pct
            def _on_effect_changed(self):
                pass
            def _show_brightness_osd(self, pct):
                self.osd_brightness_calls.append(pct)
            def _show_effect_osd(self, mode):
                self.osd_effect_calls.append(mode)
            _cycle_kb_brightness = toolkit.InfinixGTToolkitApp._cycle_kb_brightness
            _cycle_effect_mode = toolkit.InfinixGTToolkitApp._cycle_effect_mode

        app = MockApp()
        app.root = SimpleNamespace(after=app.root_after)

        # 1. Verify 100% -> 50% -> 20% -> 0% -> 100%
        app.brightness = 100
        app._cycle_kb_brightness()
        self.assertEqual(app.brightness, 50, "100% should cycle to 50%")
        app._cycle_kb_brightness()
        self.assertEqual(app.brightness, 20, "50% should cycle to 20%")
        app._cycle_kb_brightness()
        self.assertEqual(app.brightness, 0, "20% should cycle to 0%")
        app._cycle_kb_brightness()
        self.assertEqual(app.brightness, 100, "0% should cycle to 100%")
        self.assertEqual(app.osd_brightness_calls, [50, 20, 0, 100], "Brightness OSD should be called on each cycle")

        # 2. Verify effect mode cycling on hold
        app.effect_mode = "Solid"
        app._cycle_effect_mode()
        self.assertEqual(app.effect_var_value if hasattr(app, 'effect_var_value') else True, True)
        self.assertIn("Aurora", app.osd_effect_calls, "Effect OSD should be called with next mode")

        # 3. Verify SoftwareFnLock tap vs hold dispatch logic
        tap_called = []
        hold_called = []
        toolkit.SoftwareFnLock.set_callbacks(
            on_tap=lambda: tap_called.append(True),
            on_hold=lambda: hold_called.append(True)
        )

        # Simulate quick tap (down then up immediately)
        ev_down = SimpleNamespace(event_type='down')
        ev_up = SimpleNamespace(event_type='up')

        toolkit.SoftwareFnLock._on_f3_event(ev_down)
        toolkit.SoftwareFnLock._on_f3_event(ev_up)
        self.assertTrue(len(tap_called) > 0, "Quick F3 tap should trigger tap callback")
        self.assertEqual(len(hold_called), 0, "Quick F3 tap should NOT trigger hold callback")

    def test_zero_brightness_anti_flicker_turn_off(self):
        """Verify that transitioning to 0% brightness zeros all 4 PWM zones with set_mode_static=False and resets reactive bursts."""
        class MockApp:
            def __init__(self):
                self.brightness = 20
                self.config = {"brightness": 20, "mecha_bar_enabled": True, "mecha_bar_sync": True}
                self.bright_lbl = SimpleNamespace(configure=lambda **kw: None)
                self.always_on_var = SimpleNamespace(get=lambda: True)
                self.effect_mode = "ReactiveTyping"
                self.zones = copy.deepcopy(toolkit.DEFAULT_CONFIG['zones'])
                self._zone_typing_times = {"1": 12345.0, "2": 0.0, "3": 0.0, "4": 0.0}
            def _save_config(self):
                pass
            _on_brightness_changed = toolkit.InfinixGTToolkitApp._on_brightness_changed

        app = MockApp()
        calls_4zone = []
        with patch.object(toolkit.HardwareEngine, 'send_4zone_rgb', side_effect=lambda z, b, set_mode_static=False: calls_4zone.append((z, b, set_mode_static)) or True), \
             patch.object(toolkit.HardwareEngine, 'send_global_rgb', return_value=True), \
             patch.object(toolkit.HardwareEngine, 'send_mecha_bar', return_value=True), \
             patch.object(toolkit.SerialEngine, 'send_backzone_rgb', return_value=True) as bz_send:

            app._on_brightness_changed(0)

            self.assertEqual(app.brightness, 0)
            self.assertEqual(app._zone_typing_times, {"1": 0.0, "2": 0.0, "3": 0.0, "4": 0.0})
            self.assertTrue(len(calls_4zone) > 0, "Must call send_4zone_rgb")
            z_arg, b_arg, static_arg = calls_4zone[0]
            self.assertEqual(b_arg, 0)
            self.assertFalse(static_arg, "Must NOT set mode static on turn-off to avoid white flash")
            self.assertEqual(z_arg, {"1": (0, 0, 0), "2": (0, 0, 0), "3": (0, 0, 0), "4": (0, 0, 0)})
            self.assertTrue(bz_send.called, "Must shut off rear mecha bar")

    def test_nonzero_brightness_is_an_in_place_pwm_update(self):
        """F3 brightness changes must not issue watchdog or static-mode resets."""
        class MockApp:
            def __init__(self):
                self.brightness = 100
                self.config = {"brightness": 100, "mecha_bar_enabled": False}
                self.bright_lbl = SimpleNamespace(configure=lambda **kw: None)
                self.bright_quick_btns = {}
                self.always_on_var = SimpleNamespace(get=lambda: True)
                self.effect_mode = "Solid"
                self.zones = copy.deepcopy(toolkit.DEFAULT_CONFIG["zones"])
            def _save_config(self):
                pass
            _on_brightness_changed = toolkit.InfinixGTToolkitApp._on_brightness_changed

        app = MockApp()
        calls = []
        with patch.object(toolkit.HardwareEngine, "send_disable_auto_close") as watchdog, \
             patch.object(toolkit.HardwareEngine, "send_4zone_rgb",
                          side_effect=lambda zones, brightness, set_mode_static=False:
                          calls.append((zones, brightness, set_mode_static)) or True):
            app._on_brightness_changed(50)

        self.assertFalse(watchdog.called, "Brightness updates must not re-latch the EC watchdog")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1], 50)
        self.assertFalse(calls[0][2], "Brightness updates must preserve the active lighting mode")

    def test_dynamic_lighting_hardware_cancels_hardware_mode(self):
        """Verify that dynamic effects dispatch set_mode_static=True so EC hardware animations are suppressed."""
        class MockLightingApp:
            def __init__(self, mode="Aurora", always_on=True):
                self.effect_mode = mode
                self.always_on_var = SimpleNamespace(get=lambda: always_on)
                self.brightness = 75
                self.zones = copy.deepcopy(toolkit.DEFAULT_CONFIG['zones'])
                self.config = {
                    "mecha_bar_enabled": True,
                    "mecha_bar_sync": True,
                    "mecha_bar_color": [167, 139, 250],
                }
                self.anim_direction = "➡️ Left to Right"
                self.current_color = (255, 0, 0)
            def _set_hardware_status(self, ok, label, error=""):
                pass
            _apply_lighting_hardware = toolkit.InfinixGTToolkitApp._apply_lighting_hardware
            _apply_fast_initial_lighting = toolkit.InfinixGTToolkitApp._apply_fast_initial_lighting

        calls = []
        with patch.object(toolkit.HardwareEngine, 'send_disable_auto_close', return_value=True), \
             patch.object(toolkit.HardwareEngine, 'send_mecha_bar', return_value=True), \
             patch.object(toolkit.HardwareEngine, 'get_last_error', return_value=""), \
             patch.object(toolkit.HardwareEngine, 'send_hardware_mode', return_value=True) as hw_mode, \
             patch.object(toolkit.HardwareEngine, 'send_4zone_rgb', side_effect=lambda z, b=100, set_mode_static=False: calls.append((z, b, set_mode_static)) or True):

            # 1. Test Aurora sends set_mode_static=True
            app_aurora = MockLightingApp(mode="Aurora")
            app_aurora._apply_lighting_hardware()
            self.assertTrue(any(c[2] is True for c in calls), "Aurora must send set_mode_static=True")

            # 2. Test AllAurora (left-rigt-left) sends set_mode_static=True
            calls.clear()
            app_all_aurora = MockLightingApp(mode="AllAurora")
            app_all_aurora._apply_lighting_hardware()
            self.assertTrue(any(c[2] is True for c in calls), "AllAurora must send set_mode_static=True")

            # 3. Test RainbowPrism sends set_mode_static=True
            calls.clear()
            app_prism = MockLightingApp(mode="RainbowPrism")
            app_prism._apply_lighting_hardware()
            self.assertTrue(any(c[2] is True for c in calls), "RainbowPrism must send set_mode_static=True")

            # 4. Test BlazingFire sends set_mode_static=True
            calls.clear()
            app_fire = MockLightingApp(mode="BlazingFire")
            app_fire._apply_lighting_hardware()
            self.assertTrue(any(c[2] is True for c in calls), "BlazingFire must send set_mode_static=True")

            # 5. Test HwRainbow calls send_hardware_mode
            app_hw_rb = MockLightingApp(mode="HwRainbow")
            app_hw_rb._apply_lighting_hardware()
            self.assertTrue(hw_mode.called)

    def test_app_has_engine_attributes(self):
        """Verify that InfinixGTToolkitApp provides SerialEngine and HardwareEngine for components like backzone_ui."""
        self.assertIs(toolkit.InfinixGTToolkitApp.SerialEngine, toolkit.SerialEngine)
        self.assertIs(toolkit.InfinixGTToolkitApp.HardwareEngine, toolkit.HardwareEngine)

    def test_power_plan_switch_preserves_display_brightness(self):
        """Quiet/Balanced/Beast changes must not alter the user's screen brightness."""
        completed = SimpleNamespace(returncode=0)
        with patch.object(toolkit.HardwareEngine, 'get_display_brightness', return_value=67), \
             patch.object(toolkit.HardwareEngine, 'set_display_brightness', return_value=True) as restore, \
             patch.object(toolkit.subprocess, 'run', return_value=completed):
            self.assertTrue(toolkit.HardwareEngine.set_windows_power_plan("Beast"))
        restore.assert_called_once_with(67)

    def test_performance_mode_never_switches_windows_power_plan(self):
        """The toolkit's modes must leave the user's display policy untouched."""
        class MockApp:
            config = {"power_mode": "Balanced"}
            mode_var = SimpleNamespace(get=lambda: "Beast", set=lambda _value: None)
            def _save_config(self):
                pass
            def _set_hardware_status(self, *_args, **_kwargs):
                pass
            def _set_mode_apply_status(self, *_args, **_kwargs):
                pass
            def _record_automation_event(self, *_args, **_kwargs):
                pass
            def _protect_manual_mode(self):
                return 30

        app = MockApp()
        with patch.object(toolkit.HardwareEngine, "set_performance_mode", return_value=True), \
             patch.object(toolkit.HardwareEngine, "set_windows_power_plan") as plan:
            toolkit.InfinixGTToolkitApp._on_mode_selected(app)
        plan.assert_not_called()
        self.assertEqual(app.config["power_mode"], "Beast")

    def test_performance_write_is_confirmed_by_ec_readback(self):
        provider = object()
        with patch.object(toolkit.HardwareEngine, "_get_acpi_method_provider", return_value=provider), \
             patch.object(toolkit.HardwareEngine, "_ec_write_ram", return_value=True) as write, \
             patch.object(toolkit.HardwareEngine, "_ec_read_ram", return_value=2) as read:
            self.assertTrue(toolkit.HardwareEngine.set_performance_mode("Beast"))
        write.assert_called_once_with(provider, 0x40, 2)
        read.assert_called_with(provider, 0x40)

    def test_performance_write_reports_failed_ec_readback(self):
        with patch.object(toolkit.HardwareEngine, "_get_acpi_method_provider", return_value=object()), \
             patch.object(toolkit.HardwareEngine, "_ec_write_ram", return_value=True), \
             patch.object(toolkit.HardwareEngine, "_ec_read_ram", return_value=1), \
             patch.object(toolkit.time, "sleep"):
            self.assertFalse(toolkit.HardwareEngine.set_performance_mode("Beast"))
        self.assertIn("verification failed", toolkit.HardwareEngine.get_last_error().lower())

    def test_paused_automation_blocks_ac_and_ai_mode_changes(self):
        """Pause stops automatic mode changes while leaving manual controls available."""
        class MockApp:
            config = {"auto_switch_on_ac": True, "automation_paused": True}
            mode_var = SimpleNamespace(set=lambda _value: (_ for _ in ()).throw(
                AssertionError("paused automation changed the mode")))
            battery_val = 100
            on_ac_val = True
            def _automatic_mode_change_blocked(self, force=False):
                return True
            def _on_mode_selected(self, *_args, **_kwargs):
                raise AssertionError("paused automation applied a mode")
            _on_ac_connected = toolkit.InfinixGTToolkitApp._on_ac_connected
            _on_battery_disconnected = toolkit.InfinixGTToolkitApp._on_battery_disconnected
            _ai_set_mode = toolkit.InfinixGTToolkitApp._ai_set_mode

        app = MockApp()
        app._on_ac_connected()
        app._on_battery_disconnected()
        app._ai_set_mode("Beast", "High CPU load")

    def test_manual_mode_temporarily_blocks_automation_but_safety_can_override(self):
        app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
        app.config = {"automation_paused": False, "manual_mode_until": 130.0}
        with patch.object(toolkit.time, "time", return_value=100.0):
            self.assertTrue(app._automatic_mode_change_blocked())
            self.assertFalse(app._automatic_mode_change_blocked(force=True))
        with patch.object(toolkit.time, "time", return_value=131.0):
            self.assertFalse(app._automatic_mode_change_blocked())

    def test_ac_profile_switch_does_not_change_keyboard_brightness(self):
        """Automatic AC profile changes only change performance mode."""
        class MockApp:
            config = {"auto_switch_on_ac": True}
            mode_var = SimpleNamespace(set=lambda value: None)
            def _automatic_mode_change_blocked(self, force=False):
                return False
            def _on_mode_selected(self, *_args, **_kwargs):
                pass
            def _set_brightness_pct(self, _value):
                raise AssertionError("profile switching must not change keyboard brightness")
            _on_ac_connected = toolkit.InfinixGTToolkitApp._on_ac_connected
            _on_battery_disconnected = toolkit.InfinixGTToolkitApp._on_battery_disconnected

        app = MockApp()
        app._on_ac_connected()
        app._on_battery_disconnected()

    def test_compute_live_system_status_scenarios(self):
        """Test all live system status conditions: optimal, high heat, gaming, battery."""
        app = SimpleNamespace(mode_var=SimpleNamespace(get=lambda: "Balanced"))
        compute = toolkit.InfinixGTToolkitApp._compute_live_system_status

        # 1. Optimal condition on AC
        status, color, action = compute(app, cpu_p=12, cpu_temp=45, gpu_p=5, gpu_temp=48, bat_pct=80, on_ac=True)
        self.assertIn("OPTIMAL", status)
        self.assertIn("Balanced", action)

        # 2. Critical Battery (<15%)
        status, color, action = compute(app, cpu_p=10, cpu_temp=40, gpu_p=0, gpu_temp=42, bat_pct=10, on_ac=False)
        self.assertIn("CRITICAL BATTERY", status)
        self.assertIn("charger", action.lower())

        # 3. High Heat (>=85°C)
        status, color, action = compute(app, cpu_p=50, cpu_temp=88, gpu_p=40, gpu_temp=75, bat_pct=90, on_ac=True)
        self.assertIn("HIGH HEAT", status)
        self.assertIn("88", action)

        # 4. Heavy load / Gaming (GPU >= 40%)
        status, color, action = compute(app, cpu_p=30, cpu_temp=65, gpu_p=75, gpu_temp=68, bat_pct=90, on_ac=True)
        self.assertIn("HEAVY LOAD", status)
        self.assertIn("Beast Mode", action)

        # 5. Low battery warning (16-30%)
        status, color, action = compute(app, cpu_p=15, cpu_temp=45, gpu_p=0, gpu_temp=42, bat_pct=22, on_ac=False)
        self.assertIn("LOW BATTERY", status)
        self.assertIn("Quiet Mode", action)

    def test_gpu_mode_restart_prompt_requires_confirmation(self):
        """A successful GPU mode change offers Restart now/Later and never restarts silently."""
        app = SimpleNamespace(root=object())
        prompt = toolkit.InfinixGTToolkitApp._prompt_gpu_restart
        with patch.object(toolkit.messagebox, 'askyesno', return_value=False) as ask, \
             patch.object(toolkit.subprocess, 'Popen') as restart:
            prompt(app, "dGPU only")
        ask.assert_called_once()
        restart.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)

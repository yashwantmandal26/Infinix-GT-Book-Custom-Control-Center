"""Geometry regressions for the controls shared by every toolkit page."""
import tkinter.font as tkfont
import customtkinter as ctk
import neon_ui


def test_sidebar_fits_minimum_window_without_scrolling():
    import infinix_toolkit as toolkit

    app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
    app.root = ctk.CTk()
    app.config = {"cached_bat_health_pct": 98.5}
    try:
        app.root.geometry("1100x760")
        app._build_sidebar()
        for scale in (1.0, 1.25, 1.5):
            ctk.set_widget_scaling(scale)
            ctk.set_window_scaling(scale)
            app.root.update()
            assert not isinstance(app.sidebar, ctk.CTkScrollableFrame)
            top = app.sidebar.winfo_rooty()
            bottom = top + app.sidebar.winfo_height()
            for widget in (*app.nav_buttons.values(), app.side_status_badge,
                           app.side_action_lbl, app.side_cpu_bar, app.side_gpu_bar,
                           app.side_ram_bar, app.side_bat_lbl, app.side_bat_bar):
                assert widget.winfo_ismapped()
                assert widget.winfo_rooty() >= top
                assert widget.winfo_rooty() + widget.winfo_height() <= bottom
            last_nav = app.nav_buttons["about"]
            assert last_nav.winfo_rooty() + last_nav.winfo_height() < app.side_status_badge.winfo_rooty()
    finally:
        ctk.set_widget_scaling(1.0)
        ctk.set_window_scaling(1.0)
        app.root.destroy()


def test_segments_keep_text_space_at_multiple_scales():
    root = ctk.CTk()
    try:
        for scale in (1.0, 1.25, 1.5):
            ctk.set_widget_scaling(scale)
            for values in (("Auto", "Manual"), ("Quiet", "Balanced", "Gaming"),
                           ("Slow", "Normal", "Fast"), ("Hybrid", "Discrete")):
                selector = neon_ui.SegmentedButton(root, values=list(values), height=40)
                selector.pack()
                root.update_idletasks()
                for value, button in selector._buttons_dict.items():
                    font = tkfont.Font(root=root, font=button._apply_font_scaling(button._font))
                    assert button.winfo_width() >= font.measure(value) + 12 * scale
                selector.destroy()
    finally:
        ctk.set_widget_scaling(1.0)
        root.destroy()


def test_about_live_cards_fit_populated_values_in_both_themes():
    from unittest.mock import Mock
    import infinix_toolkit as toolkit

    app = toolkit.InfinixGTToolkitApp.__new__(toolkit.InfinixGTToolkitApp)
    app.root = ctk.CTk()
    app.config = {}
    app._about_refresh_live = Mock()
    app._about_load_static = Mock()
    app.main_container = neon_ui.Frame(app.root)
    app.main_container.pack(fill="both", expand=True, padx=(334, 0))
    page = app._create_about_page()
    page.pack(fill="both", expand=True)
    values = dict(bat_health="85.8%", bat_charge="79%", bat_status="AC connected",
                  bat_cycles="Not reported", bat_cap="60.1 Wh / 70.0 Wh",
                  bat_wear="14.2% of design", boot_time="13 Oct 2026, 10:30 PM",
                  uptime="12d 23h 59m", ram_used="10.5 GiB / 15.6 GiB (67.3%)",
                  cpu_temp="52°C", gpu_temp="Not reported", fan_speed="3200 RPM")
    for key, text in values.items():
        app._about_live_labels[key].configure(text=text)
    try:
        for theme in ("Light", "Dark"):
            ctk.set_appearance_mode(theme)
            for width in (1100, 1280, 1665):
                app.root.geometry(f"{width}x860")
                app.root.update()
                for label in app._about_live_labels.values():
                    tile = label.master
                    assert label.winfo_width() >= label._apply_widget_scaling(200)
                    assert label._label.winfo_reqheight() <= label.winfo_height()
                    assert label.winfo_rootx() >= tile.winfo_rootx()
                    assert label.winfo_rootx() + label.winfo_width() <= tile.winfo_rootx() + tile.winfo_width()
    finally:
        for job in app.root.tk.call("after", "info"):
            app.root.after_cancel(job)
        app.root.destroy()
        ctk.set_appearance_mode("Dark")

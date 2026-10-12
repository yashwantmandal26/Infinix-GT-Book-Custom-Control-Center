"""Geometry regressions for the controls shared by every toolkit page."""
import tkinter.font as tkfont
import customtkinter as ctk
import neon_ui


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

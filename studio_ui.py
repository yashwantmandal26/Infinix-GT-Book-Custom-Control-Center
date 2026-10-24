"""Presentation helpers for the GT desktop UI. No hardware access."""
import ctypes
import customtkinter as ctk


def configure_controls(theme):
    """Use the same surface and focus colors for default controls on every page."""
    defaults = ctk.ThemeManager.theme
    for name in ("CTkButton", "CTkEntry", "CTkOptionMenu", "CTkComboBox", "CTkSegmentedButton"):
        values = defaults.get(name, {})
        values["corner_radius"] = 8
        if "text_color" in values:
            values["text_color"] = theme["text_primary"]
        if "fg_color" in values:
            values["fg_color"] = theme["button_bg"]
        if "border_color" in values:
            values["border_color"] = theme["entry_border"]
    for name in ("CTkSwitch", "CTkCheckBox", "CTkRadioButton", "CTkSlider"):
        values = defaults.get(name, {})
        if "progress_color" in values:
            values["progress_color"] = theme["accent_blue"]
    defaults["CTkEntry"]["fg_color"] = theme["entry_bg"]
    defaults["CTkSegmentedButton"].update(
        unselected_color=theme["button_bg"], unselected_hover_color=theme["button_hover"],
        selected_color=theme["nav_active_bg"], selected_hover_color=theme["nav_hover"])


def style_titlebar(root, background):
    """Best-effort Windows 11 caption color; older Windows keeps its native chrome."""
    try:
        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        rgb = tuple(int(background[i:i + 2], 16) for i in (1, 3, 5))
        color = ctypes.c_int(rgb[0] | rgb[1] << 8 | rgb[2] << 16)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(color), 4)
    except (AttributeError, OSError):
        pass


def initial_window_geometry(screen_width, screen_height, scaling):
    """Fit the wide Control Center composition inside the usable display."""
    scaling = max(1.0, scaling)
    width = max(1100, min(1665, int(screen_width / scaling) - 36))
    height = max(760, min(969, int(screen_height / scaling) - 72))
    x = max(0, int((screen_width - width * scaling) / 2))
    y = max(0, int((screen_height - height * scaling - 48 * scaling) / 2))
    return f"{width}x{height}+{x}+{y}"


def block_slider_mousewheel(widget):
    """Keep wheel gestures from changing sliders while the pointer crosses them."""
    if isinstance(widget, ctk.CTkSlider):
        def stop_wheel(_event):
            return "break"
        for target in (widget, getattr(widget, "_canvas", None)):
            if target is None:
                continue
            for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                try:
                    # Replace any widget/class wheel handler so the slider value
                    # cannot change while the pointer is over its track or thumb.
                    target.bind(sequence, stop_wheel)
                except Exception:
                    pass
    for child in widget.winfo_children():
        block_slider_mousewheel(child)



def _key_layout():
    """Rows transcribed from the owner's straight-on GT Book photograph."""
    keys = []
    def row(y, labels, widths=None, x=0, h=1):
        for label, w in zip(labels, widths or [1]*len(labels)):
            keys.append((label,x,y,w,h))
            x += w
    row(0, ["Esc  ᶻ", "F1  ☼−", "F2  ☼+", "F3  ▰", "F4  ▣", "F5  ◁×",
            "F6  ◁−", "F7  ◁+", "F8  ▱", "F9", "F10", "F11", "F12",
            "Insert\nPrt Sc", "Pause\nScr Lk", "Delete", "◉", "❂", "❂", "⏻"], [.9]*20, h=.62)
    row(.72, ["~\n`", "!\n1","@\n2","#\n3","$\n4","%\n5","^\n6","&\n7","*\n8","(\n9",")\n0","_\n−","+\n=","Backspace"], [1]*13+[1.4])
    row(1.72, ["Tab"]+list("QWERTYUIOP")+["{\n[","}\n]","|\n\\"], [1.3]+[1]*12+[1.1])
    row(2.72, ["CapsLk"]+list("ASDFGHJKL")+[":\n;",'"\n\x27',"Enter"], [1.6]+[1]*11+[1.8])
    row(3.72, ["Shift"]+list("ZXCVBNM")+["<\n,",">\n.","?\n/","Shift"], [2.1]+[1]*10+[2.3])
    row(4.72, ["Ctrl","Fn","⊞","Alt","☀","Alt","Ctrl"], [1.1,1,1,1,5,1,1])
    row(4.72, ["▲"], [1.1], x=12.3)
    row(5.72, ["◀","▼","▶"], [1.1]*3,x=11.2)
    row(.72, ["Num\nLock","/","*","−"], [.9]*4,x=14.4)
    row(1.72, ["7\nHome","8\n↑","9\nPgUp"], [.9]*3,x=14.4)
    row(2.72, ["4\n←","5","6\n→"], [.9]*3,x=14.4)
    row(3.72, ["1\nEnd","2\n↓","3\nPgDn"], [.9]*3,x=14.4)
    row(4.72, ["0\nIns",".\nDel"], [1.8,.9],x=14.4)
    row(1.72, ["+"], [.9],x=17.1,h=2)
    row(3.72, ["Enter"], [.9],x=17.1,h=2)
    return keys


def _rounded(c,x1,y1,x2,y2,r=5,**options):
    r = min(r,(x2-x1)/2,(y2-y1)/2)
    return c.create_polygon(x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,
        x2,y2-r,x2,y2,x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1,
        smooth=True,splinesteps=12,**options)


def _light(rgb,strength,base=(10,15,23)):
    return "#" + "".join(f"{round(b+(v-b)*strength):02x}" for b,v in zip(base,rgb))


def draw_keyboard(app):
    """Interactive vector keycaps matching the GT Book's compact keyboard."""
    c = app.kb_canvas
    c.delete("all")
    width,height = max(320,c.winfo_width()),max(200,c.winfo_height())
    u = min((width-48)/24,(height-50)/6.72,48)
    ux = u * 1.32
    left,top = (width-18*ux)/2,(height-6.72*u)/2+12
    # Shaped deck follows the lowered arrow cluster instead of enclosing empty space.
    deck = [left-12,top-12,left+18*ux+12,top-12,
            left+18*ux+12,top+5.72*u+9,left+14.5*ux,top+5.72*u+9,
            left+14.5*ux,top+6.72*u+9,left+11.1*ux,top+6.72*u+9,
            left+11.1*ux,top+5.72*u+9,left-12,top+5.72*u+9]
    c.create_polygon(deck,fill="#07141E",outline="#29485D",width=1)
    app.zone_shapes = {str(z):{} for z in range(1,5)}
    for label,x,y,w,h in _key_layout():
        center = x+w/2
        # The photograph places E/D/C in the middle band; all four arrows
        # remain in zone 3. Numpad starts at x=14.4, not the arrow's center.
        zid = str(4 if x>=14.4 else 1 if center<3.45 else 2 if center<8.4 else 3)
        if (y == 4.72 and x < 4.1) or label == "X":
            zid = "1"
        if y == 0 and 2.7 <= center < 8.1:
            zid = "2"
        tag = f"zone{zid}"
        x1,y1,x2,y2 = left+x*ux+2.5,top+y*u+2.5,left+(x+w)*ux-2.5,top+(y+h)*u-2.5
        for spread,role in ((5,"haze"),(4,"halo"),(3,"bloom"),(2,"spill"),(1,"rim")):
            _rounded(c,x1-spread,y1-spread,x2+spread,y2+spread,
                     fill="#101721",outline="",tags=(tag,f"{tag}_{role}"))
        _rounded(c,x1,y1,x2,y2,r=4,fill="#080b10",outline="",tags=(tag,))
        _rounded(c,x1+1,y1+1,x2-1,y2-3,r=4,fill="#14191e",outline="",tags=(tag,f"{tag}_face"))
        c.create_line(x1+4,y1+2,x2-4,y1+2,fill="#343b43",tags=(tag,))
        c.create_line(x1+4,y2-1,x2-4,y2-1,width=2,fill="#394454",tags=(tag,f"{tag}_edge"))
        c.create_line(x1+5,y2-1,x1+(x2-x1)*.38,y2-1,width=1,
                      tags=(tag,f"{tag}_hotspot"))
        if label in ("W","A","S","D"):
            c.create_rectangle(x1+5,y1+5,x2-5,y2-6,width=1.5,
                               tags=(tag,f"{tag}_wasd"))
        size = max(11,round(u*(.25 if "\n" in label or len(label)>3 else .34)))
        if y == 0:
            size = max(9,round(u*.20))
        tx = x1+u*.35 if w>=4 else (x1+x2)/2
        c.create_text(tx,(y1+y2)/2-1,text=label,font=("Segoe UI",-size),
                      justify="center",fill="#c8e5ef",tags=(tag,f"{tag}_legend"))
        if label in ("F","J"):
            c.create_line((x1+x2)/2-3,y2-7,(x1+x2)/2+3,y2-7,
                          fill="#626b73",tags=(tag,))
    for zid in app.zone_shapes:
        tag = f"zone{zid}"
        bx = left+(int(zid)-.5)*4.5*ux
        badge = c.create_text(bx,top-25,font=("Segoe UI", -max(10,min(14,round(ux*.30))),"bold"),tags=(tag,))
        marker = c.create_rectangle(bx-23,top-18,bx+23,top-16,width=0)
        app.zone_shapes[zid] = dict(badge=badge,overlay=marker)
        c.tag_bind(tag,"<Button-1>",lambda event,z=zid:app._on_zone_clicked(z, switch_tab=True))
        c.tag_bind(tag,"<Enter>",lambda event:c.configure(cursor="hand2"))
        c.tag_bind(tag,"<Leave>",lambda event:c.configure(cursor=""))
        colors = getattr(app,"_keyboard_preview_colors",app.zones)
        set_keyboard_zone_color(app,zid,colors.get(zid,(56,189,248)))


def set_keyboard_zone_color(app,zid,rgb):
    """Recolor persistent key objects without rebuilding geometry on each frame."""
    if zid not in getattr(app,"zone_shapes",{}):
        return
    rgb = tuple(max(0,min(255,int(v))) for v in rgb)
    if not hasattr(app,"_keyboard_preview_colors"):
        app._keyboard_preview_colors = dict(app.zones)
    app._keyboard_preview_colors[zid] = rgb
    c,tag = app.kb_canvas,f"zone{zid}"
    for role,strength in (("haze",.035),("halo",.08),("bloom",.17),
                           ("spill",.38),("rim",.83),("edge",1),("face",.025)):
        c.itemconfig(f"{tag}_{role}",fill=_light(rgb,strength))
    intensity = max(rgb)/255
    legend = tuple(round(v*.65+255*.35*intensity) for v in rgb)
    c.itemconfig(f"{tag}_legend",fill=_light(legend,.95))
    c.itemconfig(f"{tag}_hotspot",fill=_light(legend,1))
    c.itemconfig(f"{tag}_wasd",outline=_light(legend,.85))
    shapes = app.zone_shapes[zid]
    color = _light(rgb,1)
    c.itemconfig(shapes["badge"],fill=color if intensity else "#536174",
                 text=f"ZONE {zid}   {color.upper()}")
    c.itemconfig(shapes["overlay"],fill="#dce9f5" if zid==app.selected_zone else "#263243")

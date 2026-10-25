"""Neon presentation controls; hardware state and commands remain in the app.

The button is a CTkButton with a canvas skin, so configure/cget, disabled
states, commands and existing automation retain their normal semantics.
"""
from functools import lru_cache
import math
import tkinter.font as tkfont
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFilter, ImageTk, ImageColor


@lru_cache(maxsize=128)
def surface(width, height, radius, active, light, hover=False):
    width, height = max(2, width), max(2, height)
    scale = 2
    w, h = width * scale, height * scale
    colors = ((0, 119, 255), (78, 30, 246)) if active else (
        ((231, 241, 253), (214, 228, 246)) if light else ((19, 43, 72), (10, 25, 44)))
    strip = Image.new('RGB', (w, 1))
    pixels = []
    for x in range(w):
        t = x / max(1, w - 1)
        pixels.append(tuple(min(255, int(a*(1-t)+b*t)+(9 if hover else 0)) for a,b in zip(*colors)))
    strip.putdata(pixels)
    result = strip.resize((w, h)).convert('RGBA')
    mask = Image.new('L', (w, h))
    ImageDraw.Draw(mask).rounded_rectangle((1, 1, w-2, h-2), radius=radius*scale, fill=255)
    result.putalpha(mask)
    draw = ImageDraw.Draw(result)
    border = '#48DFFF' if active else '#ADC9E5' if light else '#29496D'
    draw.rounded_rectangle((1,1,w-2,h-2), radius=radius*scale, outline=border, width=3 if active else 2)
    if active:
        draw.rounded_rectangle((5,5,w-6,h-6), radius=max(2,radius*scale-3), outline='#7575FF', width=2)
    return result.resize((width,height), Image.Resampling.LANCZOS)


class Button(ctk.CTkButton):
    def _draw(self, no_color_updates=False):
        super()._draw(no_color_updates)
        self._paint_skin()

    def _paint_skin(self):
        if not hasattr(self, '_canvas'):
            return
        self._canvas.delete('neon')
        fg = self._apply_appearance_mode(self._fg_color)
        if fg == 'transparent':
            self._canvas.itemconfigure('inner_parts',state='normal')
            self._canvas.itemconfigure('border_parts',state='normal')
            return
        active = str(fg).lower() in {'#1467d9','#25c7ff','#38bdf8','#69cdfa','#0875b3','#0284c7','#a78bfa','#7c3aed','#dceeff'}
        w = round(self._apply_widget_scaling(self._current_width))
        h = round(self._apply_widget_scaling(self._current_height))
        if w < 2 or h < 2:
            return
        self._skin_image = ImageTk.PhotoImage(surface(w,h,round(self._apply_widget_scaling(self._corner_radius)),
            active,self._get_appearance_mode() == 'light',getattr(self,'_mouse_inside',False)), master=self._canvas)
        self._canvas.itemconfigure('inner_parts',state='hidden')
        self._canvas.itemconfigure('border_parts',state='hidden')
        self._canvas.create_image(0,0,anchor='nw',image=self._skin_image,tags='neon')
        # Canvas text avoids opaque label rectangles over the gradient.
        # Keep the labels' requested space after hiding them. Otherwise Tk
        # loses the content size and width=0 segmented buttons collapse to
        # their border padding (also clipping auto-sized buttons elsewhere).
        if self._text_label is not None:
            text_row, text_col = {'left': (2, 3), 'right': (2, 1),
                                  'top': (3, 2), 'bottom': (1, 2)}[self._compound]
            self.grid_columnconfigure(text_col, minsize=self._text_label.winfo_reqwidth())
            self.grid_rowconfigure(text_row, minsize=self._text_label.winfo_reqheight())
            self._text_label.grid_remove()
        if self._image_label is not None:
            image_row, image_col = {'left': (2, 1), 'right': (2, 3),
                                    'top': (1, 2), 'bottom': (3, 2)}[self._compound]
            self.grid_columnconfigure(image_col, minsize=self._image_label.winfo_reqwidth())
            self.grid_rowconfigure(image_row, minsize=self._image_label.winfo_reqheight())
            self._image_label.grid_remove()
        text = self._textvariable.get() if self._textvariable is not None else self._text
        color = self._apply_appearance_mode(self._text_color_disabled if self._state == 'disabled' else self._text_color)
        if active and self._state != 'disabled':
            color = '#FFFFFF'
        font = self._apply_font_scaling(self._font)
        image_width = 0
        if self._image is not None:
            if isinstance(self._image, ctk.CTkImage):
                self._skin_icon = self._image.create_scaled_photo_image(self._get_widget_scaling(),self._get_appearance_mode())
            else:
                self._skin_icon = self._image
            image_width = self._skin_icon.width() + self._apply_widget_scaling(10)
        text_width = tkfont.Font(master=self, font=font).measure(text or '')
        x = self._apply_widget_scaling(15) if self._anchor == 'w' else (w-text_width-image_width)/2
        if image_width:
            self._canvas.create_image(x,h/2,anchor='w',image=self._skin_icon,tags='neon')
        self._canvas.create_text(x+image_width,h/2,text=text or '',anchor='w',fill=color,font=font,tags='neon')
        if getattr(self, '_nav_chevron', False):
            self._canvas.create_text(w-self._apply_widget_scaling(12),h/2,text='›',
                                     anchor='e',fill=color,font=font,tags='neon')

    def _on_enter(self,event=None):
        super()._on_enter(event)
        self._paint_skin()

    def _on_leave(self,event=None):
        super()._on_leave(event)
        self._paint_skin()


class SegmentedButton(ctk.CTkSegmentedButton):
    def _create_button_grid(self):
        super()._create_button_grid()
        if self._orientation == 'horizontal':
            font = tkfont.Font(master=self, font=self._apply_font_scaling(self._font))
            for index, value in enumerate(self._value_list):
                self.grid_columnconfigure(index, minsize=max(
                    self._apply_widget_scaling(80),
                    font.measure(value) + self._apply_widget_scaling(32)))

    def _create_button(self,index,value):
        font = tkfont.Font(master=self, font=self._apply_font_scaling(self._font))
        content_width = font.measure(value) / self._get_widget_scaling() + 32
        return Button(self,width=max(80, content_width),height=self._current_height,
            corner_radius=self._sb_corner_radius,border_width=self._sb_border_width,
            fg_color=self._sb_unselected_color,border_color=self._sb_fg_color,
            hover_color=self._sb_unselected_hover_color,text_color=self._sb_text_color,
            text_color_disabled=self._sb_text_color_disabled,text=value,font=self._font,
            state=self._state,command=lambda v=value:self.set(v,from_button_callback=True),
            background_corner_colors=None,round_width_to_even_numbers=False,round_height_to_even_numbers=False)


@lru_cache(maxsize=48)
def panel(width,height,radius,base,border):
    # Light catches the perimeter; the center matches the child controls.
    w,h=max(2,width),max(2,height)
    rgb=ImageColor.getrgb(base)
    strip=Image.new('RGB',(1,h))
    strip.putdata([tuple(min(255,round(v+(14 if channel==2 else 7)*math.exp(-min(y,h-1-y)/14)))
                          for channel,v in enumerate(rgb)) for y in range(h)])
    im=strip.resize((w,h)).convert('RGBA')
    mask=Image.new('L',(w,h));ImageDraw.Draw(mask).rounded_rectangle((0,0,w-1,h-1),radius=radius,fill=255)
    im.putalpha(mask)
    draw=ImageDraw.Draw(im)
    draw.rounded_rectangle((0,0,w-1,h-1),radius=radius,outline=border,width=1)
    return im


class Frame(ctk.CTkFrame):
    def _draw(self,no_color_updates=False):
        super()._draw(no_color_updates)
        if not hasattr(self,'_canvas'):
            return
        self._canvas.delete('neon_panel')
        fg=self._apply_appearance_mode(self._fg_color)
        if fg=='transparent' or not self._border_width or self._get_appearance_mode()=='light':
            self._canvas.itemconfigure('inner_parts',state='normal')
            self._canvas.itemconfigure('border_parts',state='normal')
            return
        w,h=round(self._apply_widget_scaling(self._current_width)),round(self._apply_widget_scaling(self._current_height))
        if w<2 or h<2:
            return
        self._panel_image=ImageTk.PhotoImage(panel(w,h,round(self._apply_widget_scaling(self._corner_radius)),
            fg,self._apply_appearance_mode(self._border_color)),master=self._canvas)
        self._canvas.itemconfigure('inner_parts',state='hidden')
        self._canvas.itemconfigure('border_parts',state='hidden')
        self._canvas.create_image(0,0,anchor='nw',image=self._panel_image,tags='neon_panel')


class Slider(ctk.CTkSlider):
    def _draw(self,no_color_updates=False):
        super()._draw(no_color_updates)
        if self._orientation.lower() != 'horizontal':
            return
        c = self._canvas
        c.delete('neon')
        w,h = self._apply_widget_scaling(self._current_width),self._apply_widget_scaling(self._current_height)
        r = self._apply_widget_scaling(8)
        x = r+(w-2*r)*self._value
        y = h/2
        c.create_line(r,y,w-r,y,fill='#344E6D',width=self._apply_widget_scaling(12),capstyle='round',tags='neon')
        c.create_line(r,y,w-r,y,fill='#071420',width=self._apply_widget_scaling(10),capstyle='round',tags='neon')
        for i in range(max(1,int(x-r))):
            t=i/max(1,w-2*r)
            color='#%02x%02x%02x' % (int(154*(1-t)+17*t),int(76*(1-t)+209*t),255)
            c.create_line(r+i,y-4,r+i,y+4,fill=color,tags='neon')
        c.create_oval(x-r-3,y-r-3,x+r+3,y+r+3,fill='#124E76',outline='',tags='neon')
        c.create_oval(x-r,y-r,x+r,y+r,fill='#05BFF4',outline='#E5FCFF',width=2,tags='neon')


def sparkline(canvas, values, color):
    canvas.delete('all')
    w,h=canvas.winfo_width(),canvas.winfo_height()
    if w<10 or h<10:
        return
    for n in range(1,10):
        canvas.create_line(n*w/10,0,n*w/10,h,fill='#142A40')
    for n in range(1,4):
        canvas.create_line(0,n*h/4,w,n*h/4,fill='#142A40')
    if len(values)<2:
        return
    points=[(i*w/(len(values)-1),h-3-min(100,max(0,v))*(h-6)/100) for i,v in enumerate(values)]
    rgb=ImageColor.getrgb(color)
    fill='#%02x%02x%02x' % tuple(round(v*.22) for v in rgb)
    canvas.create_polygon([(0,h),*points,(w,h)],fill=fill,outline='')
    canvas.create_line(points,fill=color,width=2)


def icon(name, color='#92DFFF', size=24):
    """Small consistent line icons, drawn at 3x for clean high-DPI edges."""
    s=3
    im=Image.new('RGBA',(size*s,size*s))
    d=ImageDraw.Draw(im)
    def line(points,fill=color,width=1.7):
        d.line([(int(x*size*s/24),int(y*size*s/24)) for x,y in points],fill=fill,width=max(1,round(width*size*s/24)),joint='curve')
    def box(coords,r=2):
        d.rounded_rectangle(tuple(int(v*size*s/24) for v in coords),radius=r*size*s/24,outline=color,width=max(1,round(1.7*size*s/24)))
    def ellipse(coords):
        d.ellipse(tuple(int(v*size*s/24) for v in coords),outline=color,width=max(1,round(1.7*size*s/24)))
    if name in ('lighting','bulb'):
        ellipse((5,2,19,16)); line([(8,14),(9,19),(15,19),(16,14)]); line([(9,22),(15,22)])
    elif name in ('performance','bolt'):
        line([(14,1),(5,14),(11,14),(9,23),(20,9),(13,9),(14,1)],width=2)
    elif name in ('telemetry','monitor'):
        box((2,3,22,17)); line([(12,17),(12,22),(7,22),(17,22)])
    elif name in ('cpu','chip'):
        box((6,6,18,18)); box((9,9,15,15),0)
        for p in (8,12,16):
            line([(p,2),(p,6)]); line([(p,18),(p,22)]); line([(2,p),(6,p)]); line([(18,p),(22,p)])
    elif name in ('presets','settings'):
        for a in range(0,360,45):
            x,y=math.cos(math.radians(a)),math.sin(math.radians(a));line([(12+7*x,12+7*y),(12+10*x,12+10*y)],width=3)
        ellipse((5,5,19,19));ellipse((9,9,15,15))
    elif name in ('about','info'):
        ellipse((2,2,22,22));line([(12,10),(12,17)]);ellipse((11,6,13,8))
    elif name in ('backzone','rear'):
        ellipse((4,3,20,18));line([(6,14),(9,17),(7,20),(17,20),(15,17),(18,14)]);line([(2,22),(22,22)])
    elif name in ('battery',):
        box((6,4,18,22));line([(9,2),(15,2)]);line([(9,10),(15,10),(15,18),(9,18),(9,10)])
    elif name in ('gpu','game'):
        line([(7,6),(17,6),(21,10),(23,19),(19,20),(15,16),(9,16),(5,20),(1,19),(3,10),(7,6)])
        line([(5,11),(11,11)]);line([(8,8),(8,14)]);ellipse((16,9,18,11));ellipse((18,12,20,14))
    elif name in ('keyboard',):
        box((2,5,22,19));
        for x in (6,10,14,18):
            line([(x,8),(x,10)]);line([(x,12),(x,14)])
        line([(7,17),(17,17)])
    elif name in ('ram',):
        box((2,7,22,17),1)
        for px in (4,6,8,10,14,16,18,20):
            line([(px,17),(px,19)])
        box((4,9,9,14),1); box((15,9,20,14),1)
    elif name in ('refresh',):
        d.arc((3*s*size/24,3*s*size/24,21*s*size/24,21*s*size/24),35,320,fill=color,width=2*s)
        line([(17,2),(22,5),(18,9)])
    elif name in ('grid',):
        for x in (3,14):
            for y in (3,14): box((x,y,x+7,y+7),1)
    elif name in ('sun',):
        ellipse((7,7,17,17))
        for a in range(0,360,45):
            x,y=math.cos(math.radians(a)),math.sin(math.radians(a));line([(12+8*x,12+8*y),(12+11*x,12+11*y)])
    elif name in ('bars',):
        for x,y in ((3,14),(8,7),(13,3),(18,10)): line([(x,y),(x,21)],width=2)
    else:
        line([(2,13),(7,13),(10,4),(13,21),(16,10),(18,13),(23,13)])
    im=im.resize((size,size),Image.Resampling.LANCZOS)
    return ctk.CTkImage(light_image=im,dark_image=im,size=(size,size))

VERSION = "2.0.0"
import os, ctypes
from ctypes import wintypes
SCRIPT = os.path.abspath(__file__)
PATH = os.path.dirname(SCRIPT)
wait = ctypes.windll.user32.LoadCursorFromFileW(r"C:\Windows\Cursors\aero_busy.ani")
ctypes.windll.user32.SetSystemCursor(wait, 32512)
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("LPV2+")
import tkinter as tk
from tkinter import font as tkfonts
import datetime as dt
import threading, asyncio, math, json, time, sys, traceback, atexit, subprocess
import socketio, zoneinfo, queue # LPV2+ specific
from PIL import Image, ImageTk, ImageGrab, ImageDraw, ImageFont
try:
    # import win11toast
    win11toast = None
except ImportError as e:
    win11toast = None

class Hex(str):
    def __init__(self, code):
        super().__init__()
        self.r = code[1:3]
        self.g = code[3:5]
        self.b = code[5:]
    
    def __add__(self, other):
        r = min(int(self.r, 16) + int(other.r, 16), 255)
        g = min(int(self.g, 16) + int(other.g, 16), 255)
        b = min(int(self.b, 16) + int(other.b, 16), 255)
        return Hex(f"#{r:02X}{g:02X}{b:02X}")
    
    def __sub__(self, other):
        r = max(int(self.r, 16) - int(other.r, 16), 0)
        g = max(int(self.g, 16) - int(other.g, 16), 0)
        b = max(int(self.b, 16) - int(other.b, 16), 0)
        return Hex(f"#{r:02X}{g:02X}{b:02X}")
    
    def __mul__(self, num):
        out = [int(self.r, 16), int(self.g, 16), int(self.b, 16)] # split string and convert into denary
        out = [int(num * digit) for digit in out] # multiply each value
        out = [255 if num > 255 else 0 if num < 0 else num for num in out]
        out = "#" + "".join([f"{digit:02X}" for digit in out]) # convert back to hex
        return out
    
    def rgb(self):
        return (int(self.r, 16), int(self.g, 16), int(self.b, 16))

class Dimension:
    def __init__(self, w, h): # width and height
        self.w = w
        self.h = h
        self.cx = lambda win : (self.w - win.w) // 2
        self.cy = lambda win : (self.h - win.h) // 2

class Lesson:
    def __init__(self, startH, startM, length, desc=None):
        self.startH = startH
        self.startM = startM
        self.length = length
        self.endH = startH + (length + startM) // 60
        self.endM = (startM + length) % 60
        self.midH = startH + (startM + 30) // 60
        self.midM = (startM + 30) % 60
        self.desc = desc
    
    def get_percentage(self, hour, minute, second):
        if hour == self.startH:
            minutesDone = minute - self.startM
        else:
            minutesDone = 60 - self.startM + minute
        
        secondsDone = minutesDone * 60 + second
        
        percentage = min([(secondsDone / (self.length * 60)) * 100, 100])
        
        return percentage

class Theme:
    def __init__(self, bg, bgh, acc, h, txt, err, tf, size, mod="", transparent=0, barTxt=0, mono="Courier New", trough=Hex("#FFFFFF"), bar=0, desc="Custom Theme"):
        self.bg = Hex(bg) # backgroud
        self.bgh = Hex(bgh) # background highlight
        self.acc = Hex(acc) # accent colour
        self.h = Hex(h) # highlight
        self.txt = Hex(txt) # text colour
        self.err = Hex(err) # error colour (background of fields)
        self.transparent = bool(transparent) # transparent bar
        self.barTxt = self.acc if barTxt == 1 else self.txt
        self.trough = Hex(trough) # trough colour for progressbar
        self.bar = bar # bar colour mode
        self.description = desc
        self.tf = tf
        self.size = int(size) # settings makes them into strings
        self.font = (tf, self.size, mod) # font
        self.smallFont = (tf, int(self.size * 0.75), mod) # small bold        
        self.monoFont = (mono, int(self.size * 0.75)) # font for calculator
        self.bodyFont = (tf, int(self.size * 0.75)) # font for writing in notepad etc.
        self.largeBody = (tf, self.size)
        self.bgh2 = self.bgh * 0.75
        self.mutedTxt = self.txt * 0.5
        self.transparentKey = Hex("#ffff01")
    
    def mod(self, code):
        modMap = {"b" : "bold", "i": "italic", "s": "overstrike", "u": "underline", "m": "monospace"}
        modString = " ".join([modMap[c] for c in code])
        if "monospace" in modString:
            modString = modString.replace("monospace", "").strip()
            return (*self.monoFont, modString)
        return (self.tf, int(self.size * 0.75), modString)
    
    def bar_colour(self, percentage):
        if self.bar == 0: # default
            blue = 0
            if percentage < 50:
                red = 255
                green = int(255 * (percentage / 50))
            else:
                red = int(255 * (2 - percentage / 50))
                green = 255
                
        elif self.bar == 1: # accent colour
            red = int(self.acc[1:3], 16)
            green = int(self.acc[3:5], 16)
            blue = int(self.acc[5:], 16)
        elif self.bar == 2: # red-blue
            if percentage < 50:
                red = 255
                green = int(255 * (percentage / 50))
                blue = 0
            else:
                red = int(255 * (2 - percentage / 50))
                green = 255
                blue = int(255 * (percentage - 50) / 50)
        
        return f"#{red:02X}{green:02X}{blue:02X}"

class Palette:
    def __init__(self, file=None):
        self.default()
        if file:
            valid = False
            try:
                with open(file, "r") as f:
                    data = json.load(f)
            except:
                return None
            
            for key in data.keys():
                if not hasattr(self, key):
                    print(key)
                    break
            else:
                for key in data.keys():
                    class Sub:
                        def __init__(self):
                            for subkey in data[key]:
                                setattr(self, subkey, data[key][subkey])

                    setattr(self, key, Sub())
                valid = True

            if not valid:
                self.default()
    
    def default(self):
        class ForumTxt:
            def __init__(self):
                self.blue = "#66baff"
                self.green = "#66ff99"
                self.orange = "#ff9955"
                self.purple = "#c586c0"
        
        class ForumBg:
            def __init__(self):
                self.blue = "#33414a"
                self.green = "#334a3d"
                self.orange = "#4a4433"
                self.purple = "#4a3347"
        
        class LogTxt:
            def __init__(self):
                self.yellow = "#d7ba7d"
                self.red = "#be5046"
                self.blue = "#569cd6"
                self.purple = "#e6d7ff"
        
        class LogBg:
            def __init__(self):
                self.yellow = "#4a3b2a"
                self.red = "#3a1f1f"
                self.blue = "#1f2a3a"
                self.purple = "#4b2e83"
        
        self.ft = ForumTxt()
        self.fb = ForumBg()
        self.lt = LogTxt()
        self.lb = LogBg()
    
    def validate_hex(self, colour):
        colour = colour.lower()
        if colour[0] != "#" or len(colour) != 7:
            return False
        for char in colour[1:]:
            if char not in "0123456789abcdef":
                return False
        return True

class Icons(tuple):
    def __new__(obj):
        return super().__new__(obj, ("Segoe MDL2 Assets", 16))
    
    def __init__(self):
        self.MEDIUM = ("Segoe MDL2 Assets", 14)
        self.SMALL = ("Segoe MDL2 Assets", 12)
        self.BOLD = ("Segoe MDL2 Assets", 16, "bold")
        self.SAVE = "\uE74E"
        self.LOAD = "\uED25"
        self.DOWNLOAD = "\uE896"
        self.UPLOAD = "\uE898"
        self.COPY = "\uE8C8"
        self.CLOSE = "\uE894"
        self.DEL = "\uE74D"
        self.EYE = "\uE91C"
        self.LEFT = "\uE76B"
        self.RIGHT  = "\uE76C"
        self.TICK = "\uE8FB"
        self.SEND = "\uE724"
        self.MIC = "\uE720"
        self.PLAY = "\uE768"
        self.SOUND = "\uE767"
        self.STOP = "\uE71A"
        self.WAIT = "\uE10C"
        self.USERS = "\uE902"
        self.BELL = "\uEA8F"
        self.RETRY = "\uE895"
        self.IMG = "\uEB9F"
        self.HELP = "\uE897"
        self.DND = "\uE7ED"
        self.FILE = "\uEC50"
        self.EDIT = "\uE70F"
        self.POPUP = "\uE8A7"
        self.SEARCH = "\uE721"

class Emojifier:
    def __init__(self, mode="default", font=None):
        self.mode = mode
        self.font = font
        self.emojis = []

    def emoji_to_image(self, char, bg):
        line_height = self.font.metrics("linespace")
        size = line_height * 3
        emjfont = ImageFont.truetype("C:/Windows/Fonts/seguiemj.ttf", size)
        overshoot = size // 3
        img = Image.new("RGBA", (size * 2, size * 2 + overshoot), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.text((0, overshoot), char, font=emjfont, embedded_color=True)
        bbox = img.getbbox()
        if not bbox:
            return Image.new("RGBA", (line_height, line_height), (0, 0, 0, 0))

        glyph = img.crop(bbox)
        target_h = int(line_height * 0.85)
        gw, gh = glyph.size
        scale = target_h / gh
        new_w = max(1, int(gw * scale))
        new_h = max(1, int(gh * scale))
        glyph = glyph.resize((new_w, new_h), Image.LANCZOS)
        canvas = Image.new("RGBA", (new_w, line_height), (0, 0, 0, 0))
        top_pad = (line_height - new_h) // 2
        canvas.paste(glyph, (0, top_pad), glyph)
        if bg:
            bgLayer = Image.new("RGBA", canvas.size, bg)
            bgLayer.paste(canvas, (0, 0), canvas)
            return bgLayer

        return canvas

    def render_text(self, widget, text, tag=None):
        import emoji
        if self.mode == "default":
            widget.configure(state="normal")
            widget.delete("1.0", "end")
        for char in text:
            if char in emoji.EMOJI_DATA:
                bg = widget.tag_cget(tag, "background") if tag else ""
                img = self.emoji_to_image(char, bg)
                tk_img = ImageTk.PhotoImage(img)
                self.emojis.append(tk_img)
                widget.image_create(tk.END, image=tk_img)
                if tag:
                    widget.tag_add(tag, tk.END)
            else:
                if tag:
                    widget.insert(tk.END, char, tag)
                else:
                    widget.insert(tk.END, char)
        if self.mode == "default":
            widget.configure(state="disabled")
        
        widget.yview(tk.END)

class Rounded_Rect:
    def __init__(self, canvas, coords, fill, radius=5, text=None, txtColour=None, font=None, outline=False, func=None, emoji=None, smooth=True):
        self.canvas = canvas
        self.coords = coords
        self.fill = Hex(fill)
        self.radius = radius
        self.font = font
        self.func = func
        self.txt = text
        self.win = self.canvas.winfo_parent()
        self.font = font if font else theme.smallFont
        self.txtColour = txtColour if txtColour else theme.txt
        self.outline = outline
        if self.outline:
            self.outlineColour = self.fill * 1.5
        
        if smooth:
            self.make_image()
            self.place_image()
        else:
            self.ref = [canvas.create_rectangle(coords[0] + int(radius), coords[1], coords[2] - int(radius), coords[3],
                                            fill=self.fill, outline=self.fill, width=0),
                    canvas.create_rectangle(coords[0], coords[1] + radius, coords[2], coords[3] - radius,
                                            fill=self.fill, outline=self.fill, width=0),
                    canvas.create_oval(coords[0], coords[1], coords[0] + 2 * radius, coords[1] + 2 * radius,
                                       fill=self.fill, outline=self.fill, width=0),
                    canvas.create_oval(coords[2] - 2 * radius - 1, coords[1], coords[2] - 1, coords[1] + 2 * radius,
                                       fill=self.fill, outline=self.fill, width=0),
                    canvas.create_oval(coords[0], coords[3] - 2 * radius - 1, coords[0] + 2 * radius, coords[3] - 1,
                                       fill=self.fill, outline=self.fill, width=0),
                    canvas.create_oval(coords[2] - 2 * radius - 1, coords[3] - 2 * radius - 1, coords[2] - 1, coords[3] - 1,
                                       fill=self.fill, outline=self.fill, width=0)]
            
            
        if text:
            self.text = canvas.create_text(
                coords[0] + int((coords[2] - coords[0]) / 2),
                coords[1] + int((coords[3] - coords[1]) / 2),
                text=text, fill=self.txtColour, justify=tk.CENTER, font=self.font)
        elif emoji:
            self.emoji = ImageTk.PhotoImage(self.emoji_to_image(emoji, self.fill))
            self.text = canvas.create_image(
                coords[0] + int((coords[2] - coords[0]) / 2),
                coords[1] + int((coords[3] - coords[1]) / 2),
                image=self.emoji)
        self.id = f"rr_{id(self)}"
        if smooth:
            self.canvas.itemconfig(self.imageId, tags=(self.id,))
        if text or emoji:
            self.canvas.itemconfig(self.text, tags=(self.id,))
        if func:
            self.func = func
            canvas.tag_bind(self.id, "<Button-1>", self.click)
            canvas.tag_bind(self.id, "<ButtonRelease-1>", self.release)
            if text or emoji:
                canvas.tag_bind(self.text, "<Button-1>", self.click)
                canvas.tag_bind(self.text, "<ButtonRelease-1>", self.release)
    
    def make_image(self, fill=None):
        if not fill:
            fill = self.fill
        x1, y1, x2, y2 = self.coords
        w = x2 - x1
        h = y2 - y1
        scale = 4
        r = self.radius * scale
        img = Image.new("RGBA", (w*scale, h*scale), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        if self.outline:
            draw.rounded_rectangle((0, 0, w*scale, h*scale), radius=r, fill=self.outlineColour)
            inset = scale
        else:
            inset = 0

        draw.rounded_rectangle((inset, inset, w*scale-inset, h*scale-inset), radius=r, fill=fill)
        self.img = img.resize((w, h), Image.LANCZOS)
        self.tk_img = ImageTk.PhotoImage(self.img)
    
    def place_image(self):
        x1, y1, *_ = self.coords
        self.imageId = self.canvas.create_image(x1, y1, anchor="nw", image=self.tk_img)
    
    def emoji_to_image(self, char, bg):
        font = tkfonts.Font(family=self.font[0], size=self.font[1])
        line_height = font.metrics("linespace")
        size = line_height * 3
        emjfont = ImageFont.truetype("C:/Windows/Fonts/seguiemj.ttf", size)
        overshoot = size // 3
        img = Image.new("RGBA", (size * 2, size * 2 + overshoot), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.text((0, overshoot), char, font=emjfont, embedded_color=True)
        bbox = img.getbbox()
        if not bbox:
            return Image.new("RGBA", (line_height, line_height), (0, 0, 0, 0))

        glyph = img.crop(bbox)
        target_h = int(line_height * 0.85)
        gw, gh = glyph.size
        scale = target_h / gh
        new_w = max(1, int(gw * scale))
        new_h = max(1, int(gh * scale))
        glyph = glyph.resize((new_w, new_h), Image.LANCZOS)
        canvas = Image.new("RGBA", (new_w, line_height), (0, 0, 0, 0))
        top_pad = (line_height - new_h) // 2
        canvas.paste(glyph, (0, top_pad), glyph)
        if bg:
            bgLayer = Image.new("RGBA", canvas.size, bg)
            bgLayer.paste(canvas, (0, 0), canvas)
            return bgLayer

        return canvas
    
    def config(self, text=None, bg=None, outline=None):
        if text:
            self.canvas.delete(self.text)
            self.text = self.canvas.create_text(self.coords[0] + int((self.coords[2] - self.coords[0]) / 2),
                                                self.coords[1] + int((self.coords[3] - self.coords[1]) / 2),
                                                text=text, fill=self.txtColour, justify=tk.CENTER, font=self.font) 
        if bg:
            self.make_image(fill=bg)
            self.canvas.itemconfig(self.imageId, image=self.tk_img)
        
        if outline:
            self.outlineColour = outline
            self.make_image()
            self.canvas.itemconfig(self.imageId, image=self.tk_img)

    def move(self, x1, y1, x2, y2):
        self.coords = (x1, y1, x2, y2)
        self.canvas.coords(self.imageId, x1, y1)
        if self.txt:
            self.canvas.coords(self.text,
                x1 + (x2 - x1) // 2,
                y1 + (y2 - y1) // 2)
               
    def click(self, event):
        self.config(bg=self.fill * 1.5)
        bar.win.update_idletasks()
    
    def release(self, event):
        self.config(bg=self.fill)
        self.func()
        bar.win.update_idletasks()

class Button:
    def __init__(self, master, coords, bg, text, function, radius=5, font=None, outline=True, txtColour=None, emoji=None, desc=""):
        self.bg = Hex(bg)
        if not font:
            font = theme.smallFont
        self.roundedRect = Rounded_Rect(master, coords, bg, radius=radius, text=text, func=function, outline=outline, font=font, txtColour=txtColour, emoji=emoji)
        self.text = self.roundedRect.text
        tag = f"button_{id(self)}"
        self.roundedRect.canvas.addtag_withtag(tag, self.roundedRect.id)
        if outline:
            self.roundedRect.canvas.tag_bind(tag, "<Enter>", self.hover)
            self.roundedRect.canvas.tag_bind(tag, "<Leave>", self.un_hover)
        if desc:
            self.toolTip = ToolTip(self.roundedRect.canvas, tag, desc)
    
    def hover(self, event):
        self.roundedRect.canvas.config(cursor="hand2")
        self.roundedRect.config(outline=theme.h)
    
    def un_hover(self, event):
        self.roundedRect.canvas.config(cursor="")
        self.roundedRect.config(outline=self.bg * 1.5)

class Field(tk.Entry):
    def __init__(self, master, row, col, colspan=1, placeholder="", bg=None, font=None, justify="center", width=None, sticky="nsew", padx=0, pady=0, cb=None, icon=None, **kwargs):
        if not font:
            font = theme.bodyFont
        if not bg:
            self.bg = theme.bgh
        else:
            self.bg = Hex(bg)
        
        self.state = kwargs.get("state", "normal")
        self.err = False
        self.master = master
        self.frame = tk.Frame(self.master, bg=self.bg * 2)
        self.frame.grid(row=row, column=col, columnspan=colspan, sticky=sticky, padx=padx, pady=pady)
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)
        if width:
            super().__init__(self.frame, bg=self.bg, disabledbackground=self.bg, fg=theme.mutedTxt, disabledforeground=theme.mutedTxt, font=font, justify=justify, width=width, bd=0, relief="flat", insertbackground=theme.txt, insertwidth=1, **kwargs)
        else:
            super().__init__(self.frame, bg=self.bg, disabledbackground=self.bg, fg=theme.mutedTxt, disabledforeground=theme.mutedTxt, font=font, justify=justify, bd=0, relief="flat", insertbackground=theme.txt, insertwidth=1, **kwargs)
        
        if icon:
            self.frame.columnconfigure(1, weight=5)
            self.icon = tk.Label(self.frame, bg=self.bg, fg=theme.mutedTxt, font=ICONS.SMALL, text=icon)
            self.icon.grid(row=0, column=0, sticky="nsew", padx=(1, 0), pady=1)
            self.icon.bind("<Button-1>", self.focus)
            self.grid(row=0, column=1, sticky="nsew", padx=(0, 1), pady=1)
            self.icon.bind("<Enter>", self.hover)
            self.icon.bind("<Leave>", self.un_hover)
            self.bind("<Button-1>", self.click)
            self.bind("<ButtonRelease-1>", self.click)
        else:
            self.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        if cb:
            self.bind("<Return>", lambda event : cb())
        
        self.blank = True
        self.bind("<Key>", lambda event : self.clear_placeholder())            
        self.bind("<Button-1>", self.click)
        self.bind("<ButtonRelease-1>", self.click)
        self.bind("<Control-BackSpace>", self.delete_word)
        self.bind("<Shift-Control-BackSpace>", lambda event : self.clear())
        self.bind("<Enter>", self.hover)
        self.bind("<Leave>", self.un_hover)
        self.frame.bind("<FocusIn>", self.focus)
        self.frame.bind("<FocusOut>", self.un_focus)
        self.placeholder = placeholder
        self.set_placeholder()
    
    def clear_placeholder(self):
        if self.blank:
            self.clear()
            self.config(fg=theme.txt)
            self.config(disabledforeground=theme.txt)
            if hasattr(self, "icon"):
                self.icon.config(fg=theme.txt)
            self.blank = False
    
    def set_placeholder(self):
        self.blank = True
        self.config(fg=theme.mutedTxt)
        self.config(disabledforeground=theme.mutedTxt)
        if hasattr(self, "icon"):
            self.icon.config(fg=theme.mutedTxt)
        self.clear()
        self.config(state="normal")
        self.insert(tk.END, self.placeholder)
        self.config(state=self.state)
    
    def hover(self, event):
        if self.err:
            bg = theme.err
        else:
            bg = self.bg
        self.config(bg=bg * 1.5)
        self.config(disabledbackground=bg * 1.5)
        if hasattr(self, "icon"):
            self.icon.config(bg=bg*1.5)
    
    def un_hover(self, event):
        if self.err:
            bg = theme.err
        else:
            bg = self.bg
        self.config(bg=bg)
        self.config(disabledbackground=bg)
        if hasattr(self, "icon"):
            self.icon.config(bg=bg)
    
    def focus(self, event):
        super().focus()
        self.frame.config(bg=theme.h)
        self.clear_placeholder()
        return None
    
    def un_focus(self, event):
        self.frame.config(bg=self.bg * 2)
        if not self.get():
            self.set_placeholder()
    
    def click(self, event):
        toggle_drag(event)
        if self.state == "normal":
            self.clear_placeholder()
    
    def clear(self):
        self.config(state="normal")
        self.delete(0, tk.END)
        self.config(state=self.state)
    
    def set(self, value):
        self.clear()
        self.clear_placeholder()
        self.config(state="normal")
        self.insert(0, value)
        self.config(state=self.state)
    
    def append(self, value):
        self.clear_placeholder()
        self.config(state="normal")
        self.insert(tk.END, value)
        self.config(state=self.state)
    
    def error(self):
        self.config(bg=theme.err)
        self.err = True
    
    def valid(self):
        self.config(bg=self.bg)
    
    def delete_word(self, event):
        text = self.get()
        cursor = self.index("insert")
        i = cursor
        while i > 0 and text[i-1].isspace():
            i -=1
        while i > 0 and not text[i-1].isspace():
            i -= 1
        self.delete(i, cursor)
        return "break"

class Textbox(tk.Text):
    def __init__(self, master, row, col, rowspan=1, colspan=1, padx=0, pady=0, font=None, state=True, wrap="word", binds=None, **kwargs):
        if not font:
            font = theme.bodyFont
        self.frame = tk.Frame(master, bg=theme.bgh * 2, highlightthickness=0, bd=0, relief="flat")
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)
        self.frame.grid(row=row, column=col, sticky="nsew", padx=padx, pady=pady, columnspan=colspan)
        super().__init__(self.frame, bg=theme.bgh, fg=theme.txt, font=font, wrap=wrap, bd=0, relief="flat", **kwargs)
        self.tag_config("sel", foreground=PALETTE.ft.green, background=PALETTE.fb.green)
        self.bind("<MouseWheel>", self.scroll)
        self.bind("<Shift-MouseWheel>", lambda event : self.xview_scroll(-1 if event.delta > 0 else 1, "units"))
        self.bind("<Button-1>", toggle_drag)
        self.bind("<ButtonRelease-1>", toggle_drag)
        self.bind("<Enter>", self.hover)
        self.bind("<Leave>", self.un_hover)
        self.state = state
        if binds:
            self.bindings = binds
        if self.state:
            self.bind("<FocusIn>", self.focus)
            self.bind("<FocusOut>", self.un_focus)
            self.bind("<Control-BackSpace>", self.delete_word, add="+")
            self.config(insertbackground=theme.txt, insertwidth=1)
        else:
            if binds:
                self.bind("<KeyPress>", self.key)
            else:
                self.bind("<Key>", lambda event : "break")
            self.config(insertbackground=theme.bgh, insertwidth=0)
        self.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.yview(tk.END)
    
    def key(self, event):
        for binding, func in self.bindings.items():
            keysym = binding.lower()
            key = keysym.split("-")[-1].strip("<>")
            valid = event.keysym.lower() == key
            if not valid:
                continue
            ctrl = bool(event.state & 0x4)
            shift = bool(event.state & 0x1)
            if "control" in keysym:
                valid = valid and ctrl
            if "shift" in keysym:
                valid = valid and shift
            if valid:
                func(event)
        return "break"
    
    def focus(self, event):
        self.frame.config(bg=theme.h)
    
    def un_focus(self, event):
        self.frame.config(bg=theme.bgh * 2)
    
    def hover(self, event):
        self.config(bg=theme.bgh * 1.1)
    
    def un_hover(self, event):
        self.config(bg=theme.bgh)
    
    def txt(self):
        return self.get("1.0", tk.END)
    
    def append(self, text, *tag, scroll=True):
        self.insert(tk.END, text, *tag)
        if scroll:
            self.yview(tk.END)
    
    def clear(self):
        self.delete("1.0", tk.END)
    
    def set(self, text, *tag):
        self.clear()
        self.append(text, *tag)
    
    def copy(self):
        text = self.txt()
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update_idletasks()
    
    def scroll(self, event):
        self.yview_moveto(self.yview()[0] - event.delta / 10000)
        return "break"
    
    def delete_word(self, event):
        pos = self.index("insert")
        while True:
            previous = self.index(f"{pos} -1c")
            if previous == pos:
                break
            if self.get(previous).isspace():
                pos = previous
            else:
                break
        if pos == self.index(f"{pos} wordstart"):
            pos = self.index(f"{pos} -1c")
        self.delete(self.index(f"{pos} wordstart"), "insert")
        return "break"

class Scale:
    def __init__(self, parent, length, bg, fg, command=lambda value : None):
        self.fg = fg
        self.length = length
        self.canvas = tk.Canvas(parent, width=26, height=self.length+25, bg=theme.bg, highlightthickness=0)
        self.trough = Rounded_Rect(self.canvas, (0, 0, 25, self.length+25), bg)
        self.slider = Rounded_Rect(self.canvas, (0, 0, 25, 25), fg)
        self.value = 0
        self.canvas.tag_bind(self.slider.id, "<ButtonPress-1>", self.start_drag)
        self.canvas.tag_bind(self.slider.id, "<ButtonRelease-1>", self.release)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.tag_bind(self.slider.id, "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
        self.canvas.tag_bind(self.slider.id, "<Leave>", lambda e: self.canvas.config(cursor=""))
        self.command = command
        self.offset = 0 # accounts for clicking in the centre of the slider etc.
        self.dragging = False
    
    def grid(self, **kwargs):
        self.canvas.grid(**kwargs)
    
    def start_drag(self, event):
        self.dragging = True
        self.slider.config(bg=self.fg * 0.72)
        _, y, *_ = self.canvas.coords(self.slider.id)
        self.offset = event.y - y
        self.drag(event)
    
    def drag(self, event):
        if not self.dragging:
            return None
        y = event.y - self.offset
        if y < 0:
            y = 0
        elif y > self.length:
            y = self.length
        self.slider.move(0, y, 25, y+25)
        self.value = y
        self.command(self.get())
    
    def release(self, event):
        self.dragging = False
        self.slider.config(bg=self.fg)
    
    def get(self):
        return int(self.length - self.value)
    
    def set(self, value):
        value = self.length - value
        if value < 0:
            value = 0
        if value > self.length:
            value = self.length
        
        self.slider.move(0, value, 25, value+25)
    
    def bind(self, key, cb):
        self.canvas.bind(key, cb)

class RadioButton:
    def __init__(self, parent, text, colour, bg, value):
        self.parent = parent
        self.bg = bg
        self.colour = colour
        self.imgOff, self.imgOn = self._make_images()
        self.button = tk.Label(parent, image=self.imgOff, bg=self.bg)
        self.label = tk.Label(parent, text=text, bg=self.bg, fg=theme.txt, font=theme.bodyFont)
        self.button.bind("<ButtonRelease-1>", self.on_pressed)
        self.label.bind("<ButtonRelease-1>", self.on_pressed)
        self.state = False
        self.value = value
    
    def _make_images(self):
        from PIL import Image, ImageDraw, ImageOps, ImageTk
        img1 = Image.new("RGBA", (60, 60), self.bg)
        draw1 = ImageDraw.Draw(img1)
        draw1.ellipse((0, 0, 59, 59), outline=theme.txt, width=4, fill=self.bg)
        img1_small = img1.resize((15, 15), Image.LANCZOS)
        img2 = Image.new("RGBA", (60, 60), self.bg)
        draw2 = ImageDraw.Draw(img2)
        draw2.ellipse((0, 0, 59, 59), outline=theme.txt, width=4, fill=self.bg)
        draw2.ellipse((15, 15, 44, 44), fill=self.colour)
        img2_small = img2.resize((15, 15), Image.LANCZOS)
        return ImageTk.PhotoImage(img1_small), ImageTk.PhotoImage(img2_small)

    def grid(self, row, col):
        self.parent.rowconfigure(row, weight=1)
        self.parent.columnconfigure(col, weight=1)
        self.parent.columnconfigure(col+1, weight=4)
        self.button.grid(row=row, column=col, padx=2)
        self.label.grid(row=row, column=col+1, sticky="nsw")
    
    def toggle(self):
        self.state = not self.state
        self.button.config(image=self.imgOn if self.state else self.imgOff)
    
    def on_pressed(self, event):
        if not self.state:
            self.toggle()
            self.parent.on_change(self.value)

class Radio(tk.Frame):
    def __init__(self, parent, row, col, orientation=False, cb=lambda:None, bg=None, colspan=1):
        self.bg = bg if bg else theme.bg
        super().__init__(parent, bg=self.bg, highlightthickness=0)
        self.grid(row=row, column=col, sticky="nsew", columnspan=colspan)
        self.orientation = orientation
        self.buttons = []
        self.var = 0
        self.cb = cb
    
    def add(self, text, colour, value):
        radio = RadioButton(self, text, colour, self.bg, value)
        if self.orientation: # horizontal
            row = 0
            col = len(self.buttons) * 2
        else:
            row = len(self.buttons)
            col = 0
        
        radio.grid(row, col)
        self.buttons.append(radio)
        if len(self.buttons) == 1: # selects first radiobutton
            radio.on_pressed(None)
    
    def on_change(self, value):
        self.var = value
        for button in self.buttons:
            if value != button.value and button.state:
                button.toggle()
                break
        self.cb()

class Checkbox(tk.Frame):
    def __init__(self, parent, row, col, text, fill, bg=None, fg=None, cb=lambda : None, rowspan=1, colspan=1):
        self.bg = bg if bg else theme.bg 
        self.fg = fg if fg else theme.txt
        self.fill = fill
        super().__init__(parent, bg=self.bg, highlightthickness=0)
        self.grid(row=row, column=col, rowspan=rowspan, columnspan=colspan, sticky="nsew", padx=5, pady=5)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=9)
        self.state = False
        self.cb = cb
        self.off, self.on = self._make_images()
        self.box = tk.Label(self, image=self.off, bg=self.bg)
        self.box.grid(row=0, column=0, sticky="w")
        self.text = tk.Label(self, text=text, bg=self.bg, fg=self.fg)
        self.text.grid(row=0, column=1, sticky="w")
        self.box.bind("<ButtonRelease-1>", lambda event : self.toggle())
        self.text.bind("<ButtonRelease-1>", lambda event : self.toggle())
    
    def _make_images(self):
        from PIL import Image, ImageDraw, ImageOps, ImageTk
        scale = 4
        big = 15 * scale
        inset = 5
        img1 = Image.new("RGBA", (big, big), self.bg)
        draw1 = ImageDraw.Draw(img1)
        draw1.rounded_rectangle((0, 0, big, big), radius=15, fill=self.fg * 0.4)
        draw1.rounded_rectangle((inset, inset, big-inset, big-inset), radius=15, fill=self.bg)
        img1_small = img1.resize((15, 15), Image.LANCZOS)
        img2 = Image.new("RGBA", (big, big), self.bg)
        draw2 = ImageDraw.Draw(img2)
        draw2.rounded_rectangle((0, 0, big, big), radius=15, fill=self.fill)
        tick = [(15, 29), (27, 41), (45, 14)]
        draw2.line(tick, fill=self.fg, width=6, joint="curve")
        img2_small = img2.resize((15, 15), Image.LANCZOS)
        return ImageTk.PhotoImage(img1_small), ImageTk.PhotoImage(img2_small)
    
    def toggle(self, cb=True):
        self.state = not self.state
        if self.state:
            self.box.config(image=self.on)
        else:
            self.box.config(image=self.off)
        if cb:
            self.cb()
        
class Window:
    def __init__(self, width, height, name, new=True, children=None, padding=10, transparent=False, show=True):
        self.w = width
        self.h = height
        self.name = name
        self.children = children
        self.new = new
        self.padding = padding
        self.show = show
        self.win = self.create_window(transparent)
        self.win.rowconfigure(0, weight=1)
        self.win.columnconfigure(0, weight=1)
        if transparent:
            bg = theme.transparentKey
        else:
            bg = theme.bg
        self.content = tk.Frame(self.win, width=self.w-2 * padding, height=self.h-2 * padding,
                                 bg=bg, highlightthickness=0, bd=0, relief="flat")
        self.content.grid(row=0, column=0, padx=padding, pady=padding, sticky="nsew")
        if show:
            self.win.deiconify()
    
    def __str__(self):
        return self.name
    
    def create_window(self, transparent): # default window creation
        if self.new == True: # win can have multiple data types so can't use if self.new:
            window = tk.Toplevel(root)
        else:
            window = self.new.win # update a window instead of making a new one
            self.new.canvas.destroy()
            [w.destroy() for w in window.winfo_children()]
        window.overrideredirect(1)
        window.geometry(f"{self.w}x{self.h}+{screen.cx(self)}+{screen.cy(self)}")
        window.config(bg=theme.transparentKey)
        window.wm_attributes("-topmost", True)
        window.wm_attributes("-transparentcolor", theme.transparentKey)
        window.bind("<Escape>", lambda event : close_window(event, self))
        window.bind("<Button-1>", start_move)
        window.bind("<B1-Motion>", lambda event : do_move(event, window))
        window.bind("<ButtonRelease-1>", lambda event : end_move(event, self))
        
        if self.children:
            for feature in self.children:
                for key in feature.keys:
                    if len(key) == 1:
                        window.bind(f"<KeyPress-{key.lower()}>", self.toggle)
                        window.bind(f"<KeyPress-{key.upper()}>", self.toggle)
                    else:
                        window.bind(f"<{key}>", self.toggle)

        self.canvas = tk.Canvas(window, width=self.w, height=self.h, bg=theme.transparentKey, highlightthickness=0)
        frame = self.canvas
        frame.place(x=0, y=0, anchor="nw")
        bg = theme.transparentKey if transparent else theme.bg
        radius = 5 if self.padding == 5 else 12.5
        self.rr = Rounded_Rect(frame, (0, 0, self.w, self.h), bg, radius=radius, smooth=False)
        return window
    
    def toggle(self, event, keysym=None):
        for feature in self.children:
            if event is not None:
                if (0x0004 | 0x0008) & event.state != 0:
                    continue
                if event.keysym.lower() in [key.lower() for key in feature.keys]:
                    func = feature.func
                    name = feature.name
                    break
            if keysym in feature.keys:
                func = feature.func
                name = feature.name
                break
        
        else:
            return None
        
        active[name] = not active[name]
        func(active[name])
    
    def go_to(self, tx, ty, x, y, i=0, endFunc=None):
        SPEED = 25
        nx = round((i / SPEED) * (tx - x)) + x
        ny = round((i / SPEED) * (ty - y)) + y
        self.win.geometry(f"+{nx}+{ny}")
        if i < SPEED:
            self.win.after(1, lambda : self.go_to(tx, ty, x, y, i=i+1, endFunc=endFunc))
        elif endFunc is control_edges:
            control_edges(tx, ty)
        elif endFunc:
            endFunc()
    
    def copy(self, text):
        self.win.clipboard_clear()
        self.win.clipboard_append(text)
        self.win.update_idletasks()
    
    def close(self):
        self.win.destroy()

class ToolTip(tk.Toplevel):
    def __init__(self, parent, tag, text):
        self.exists = False
        self.parent = parent
        self.text = text
        self.parent.tag_bind(tag, "<Enter>", self.wait, add="+")
        self.parent.tag_bind(tag, "<Leave>", self.leave, add="+")
        self.parent.tag_bind(tag, "<ButtonRelease-1>", self.leave, add="+")
    
    def wait(self, event):
        self.hover = True
        root.after(1000, lambda : self.show(event.x_root, event.y_root))
    
    def leave(self, event):
        self.hover = False
        if self.exists:
            self.destroy()
            self.exists = False
    
    def show(self, x, y):
        if self.exists or not self.hover:
            return None
        super().__init__(root)
        self.wm_attributes("-topmost", True)
        self.overrideredirect(1)
        self.config(bg=theme.bgh)
        self.geometry(f"+{x}+{y}")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.inner = tk.Label(self, bg=theme.bg, fg=theme.mutedTxt, text=self.text)
        self.inner.grid(row=0, column=0, padx=1, pady=1)
        self.exists = True

class Feature:
    def __init__(self, name, func, *keys):
        self.name = name
        self.func = func
        self.keys = list(keys)

class Logger:
    def __init__(self, tag="[ERROR]"):
        self.logger = True
        self.file = open("lpv2.log", "a", buffering=1)
        self.reader = open("lpv2.log", "r")
        self.last = time.time()
        self.start = True
        self.tag = tag
    
    def write(self, message):
        if not message:
            return None

        prefix = time_now().strftime(f"{self.tag}   [%H:%M:%S] ")
        for line in message.splitlines(keepends=False):
            if self.tag == "[PRINT]" and not line.strip():
                continue
            if line.startswith("Traceback (most recent call last):") or self.tag == "[PRINT]":
                self.start = True
            if self.start:
                self.file.write("\n" + prefix + line + "\n")
                self.start = False
            else:
                self.file.write(" " * len(prefix) + line + "\n")

        if "root" in globals() and root.winfo_exists():
            root.after(0, self.notify)
    
    def notify(self):
        now = time.time()
        if active["log"]:
            update_log()
        elif now - self.last > 1:
            toast("Warning", "An error occurred. Check the log for details.", button=True, func=lambda : bar.toggle(None, keysym="x"))
            self.last = now

    def flush(self):
        self.file.flush()

stderr = sys.stderr
sys.stderr = Logger()
stdout = sys.stdout
sys.stdout = Logger(tag="[PRINT]")

def log_exception(exc_type, exc, tb):
    traceback.print_exception(exc_type, exc, tb, file=sys.stderr)

def tk_exception_handler(exc_type, exc, tb):
    traceback.print_exception(exc_type, exc, tb, file=sys.stderr)

def asyncio_exception_handler(loop, context):
    msg = context.get("exception") or context.get("message")
    print(f"Asyncio error: {msg}", file=sys.stderr)

def update_log():
    with open("lpv2.log", "r") as f:
        text = f.read()
    filter = debug.radios.var
    logBox.clear()
    errors = 0
    tag = ""
    for line in text.splitlines(keepends=False)[1:]: # first line always blank
        if line.startswith("[WARNING]") or line.startswith("[PRINT]"):
            tag = "w"
            errors += 1
        elif line.startswith("[ERROR]"):
            tag = "e"
            errors += 1
        elif line.startswith("[ONLINE]"):
            tag = "o"
            errors += 1
        
        if tag == "w" and filter not in [0, 1]:
            continue
        if tag == "e" and filter not in [0, 2]:
            continue
        if tag == "o" and filter not in [0, 3]:
            continue
        
        if debug.showInfo.state:
            final = line + "\n"
        else:
            final = line[20:] + "\n"
        if tag:
            logBox.append(final, tag, scroll=debug.autoScroll.state)
        else:
            logBox.append(final, scroll=debug.autoScroll.state)
    
    if filter == 1:
        suffix = "warnings"
    else:
        suffix = "errors"

    debug.numLabel.config(text=f"{errors} {suffix}")

def log(error, tag="WARNING"):
    try:
        with open("lpv2.log", "x") as f:
            f.close()
    except FileExistsError: pass
    finally:
        with open("lpv2.log", "a") as f:
            prefix = time_now().strftime(f"[{tag}] {' ' * (7 - len(tag))}[%H:%M:%S] ")
            f.write("\n" + prefix + error.splitlines(keepends=True)[0])
            for line in error.splitlines(keepends=True)[1:]:
                f.write(" " * len(prefix) + line)
        
        if active["log"]:
            update_log()
        toast("Warning", "An error occurred. Check the log for details.", button=True, func=lambda : bar.toggle(None, keysym="x"))

def restart(event):
    end_program(event, restart=True)

def restart_program():
    openApps = []
    for app, state in active.items():
        if state and app != "bar":
            openApps.append(app)
    subprocess.Popen([sys.executable, SCRIPT] + openApps)
    os._exit(0)

def cmd(event):
    subprocess.Popen("cmd.exe")

def raise_error(event):
    raise Exception("Test")

def slide_away(toast):
    def close_helper(toast):
        toast.close()
        toasts.remove(toast)
        for i, t in enumerate(toasts):
            if t.win.winfo_exists():
                t.win.geometry(f"+{screen.w-t.w-16}+{screen.h-(i+1)*(t.h+16)}")

    if not (toast.win.winfo_exists() and toast.slide):
        return None
    
    if not getattr(toast, "ready", False):
        root.after(50, lambda : slide_away(toast))
    toast.win.update_idletasks()
    y = toast.win.winfo_y()
    toast.go_to(screen.w, y, screen.w-toast.w-16, y, endFunc=lambda : close_helper(toast))

def toast(title, message, button=False, entry=False, func=lambda : None):
    if settings["dnd"]:
        return None
    
    if win11toast is not None:
        from winreg import CreateKey, HKEY_CURRENT_USER
        from platform import release

        async def run_toast():
            try:
                await win11toast.toast_async(title, message, on_dismissed=lambda args : None,
                                             audio={"src" : r".\SOUNDS\toast_sound.wav"}, icon=icon, app_id="LPV2+")
            except asyncio.CancelledError:
                pass
            
        key_path = r"Software\Classes\AppUserModelId\LPV2+"
        CreateKey(HKEY_CURRENT_USER, key_path)
        if int(release()) == 10: # icons do not work on windows 10
            icon = None
        else:
            icon = "IMAGES/lp_logo.ico"
        loop.call_soon_threadsafe(asyncio.create_task, run_toast())
    else:
        def toast_tk(title, message, button, entry, func):
            from winsound import PlaySound, SND_ASYNC
            def truncate(text, widget):
                emojifier.render_text(widget, text)
                widget.update_idletasks()

                def lines():
                    return int(widget.count("1.0", tk.END, "displaylines")[0])

                if lines() <= 2:
                    return text

                while lines() > 2 and len(text) > 0:
                    text = text[:-1] + "…"
                    emojifier.render_text(widget, text)
                    widget.update_idletasks()
                    text = text[:-1]
                
                emojifier.render_text(widget, text + "…")

            w, h = 240, 90 + 30 * int(button and entry)
            emojifier = Emojifier(font=tkfonts.Font(family=theme.largeBody[0], size=theme.largeBody[1]))
            for i, toast in enumerate(toasts):
                if toast.win.winfo_exists():
                    toast.win.geometry(f"+{screen.w-w-16}+{screen.h-(i+2)*(h+16)}")
            toastTk = Window(w, h, "toast")
            toastTk.slide = True
            toasts.append(toastTk)
            toastTk.win.geometry(f"+{screen.w}+{screen.h-h-16}")
            toastTk.win.bind("<Button-1>", lambda event : (setattr(toastTk, "slide", False)))
            toastTk.win.bind("<B1-Motion>", lambda event : None)
            toastTk.win.bind("<ButtonRelease-1>", lambda event : None)
            toastTk.content.rowconfigure(0, weight=1)
            toastTk.content.rowconfigure(1, weight=2)
            toastTk.content.columnconfigure(0, weight=4)
            toastTk.content.columnconfigure(1, weight=1, minsize=35)
            if entry:
                toastTk.content.rowconfigure(2, weight=1)
            tk.Label(toastTk.content, text=title, bg=theme.bg, fg=theme.txt, font=theme.font, wraplength=w-35, justify=tk.LEFT, anchor="w").grid(row=0, column=0, sticky="nsew")
            toastTk.msg = tk.Text(toastTk.content, font=theme.largeBody, bg=theme.bg, fg=theme.txt, bd=0, highlightthickness=0, relief="flat", wrap="word", cursor="arrow", height=2)
            toastTk.msg.configure(state="disabled")
            toastTk.msg.grid(row=1, column=0, sticky="nsew", columnspan=2-int(button and not entry), pady=5)
            toastTk.win.update_idletasks()
            toastTk.win.after_idle(lambda : truncate(message, toastTk.msg))
            closeCanvas = tk.Canvas(toastTk.content, width=15, height=15, bg=theme.bg, highlightthickness=0)
            closeCanvas.grid(row=0, column=1, sticky="ne")
            Button(closeCanvas, (0, 0, 15, 15), theme.bg, ICONS.CLOSE, lambda : toastTk.close(), font=ICONS.SMALL, outline=False)
            if button and entry:
                toastTk.field = Field(toastTk.content, 2, 0, justify=tk.LEFT, padx=(0, 5), pady=5, cb=lambda : func(toastTk))
                buttonCanvas = tk.Canvas(toastTk.content, width=35, height=35, bg=theme.bg, highlightthickness=0)
                buttonCanvas.grid(row=2, column=1, sticky="nsew", padx=5, pady=5)
                Button(buttonCanvas, (0, 0, 35, 35), theme.bgh, ICONS.TICK, lambda : func(toastTk), font=ICONS.SMALL)
            elif button:
                def click_wrapper(toast):
                    func()
                    toastTk.slide = True
                    slide_away(toastTk)
                buttonCanvas = tk.Canvas(toastTk.content, width=35, height=35, bg=theme.bg, highlightthickness=0)
                Button(buttonCanvas, (0, 0, 35, 35), theme.bgh, ICONS.POPUP, lambda : click_wrapper(toastTk), font=ICONS.SMALL)
                buttonCanvas.grid(row=1, column=1, sticky="nsew", padx=5)
            
            if settings["sounds"]:
                PlaySound(r".\SOUNDS\toast_sound.wav", SND_ASYNC)
            toastTk.go_to(screen.w-w-16, screen.h-h-16, screen.w, screen.h-h-16)
            root.after(5000, lambda : slide_away(toastTk))
            toastTk.ready = True
        
        root.after_idle(lambda : toast_tk(title, message, button, entry, func))
    
def save_settings():
    with open('settings.json', 'w') as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)

def time_now():
    global last_sync_attempt_mono, base_mono
    
    async def refresh_time():
        global accurate_time, timeSource, clockErrorLogged
        import aiohttp
        url = "https://timeapi.io/api/Time/current/zone?timeZone=Europe/London"
        newTime = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json()
                    raw = data["dateTime"]
                    try:
                        newTime = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
                    except ValueError:
                        no_ms = raw.split(".")[0].replace("Z", "+00:00")
                        newTime = dt.datetime.fromisoformat(no_ms)
                    finally:
                        newTime = newTime.replace(tzinfo=uk)
        except:
            if not clockErrorLogged: # can only log once
                log(traceback.format_exc(), tag="ONLINE")
                clockErrorLogged = True
            newTime = dt.datetime.now(uk)
            timeSource = 0
        else:
            timeSource = 1
        finally:
            accurate_time = newTime

    now_mono = time.monotonic()

    if last_sync_attempt_mono is None:
        last_sync_attempt_mono = now_mono
        base_mono = now_mono
        accurate_time = dt.datetime.now(uk)
    
    if now_mono - last_sync_attempt_mono > 5.0:
        last_sync_attempt_mono = now_mono
        loop.create_task(refresh_time())
    
    elapsed = now_mono - base_mono

    try:
        t = accurate_time + dt.timedelta(seconds=elapsed)
    except:
        t = dt.datetime.now(uk)
    return t

def check_period(hour, minute):
    weekday = now.strftime("%a")
    current = dt.time(hour, minute)
    lessons = monFri if weekday in ["Mon", "Fri"] else tueThu
    for lesson in lessons:
        start = dt.time(lesson.startH, lesson.startM)
        end = dt.time(lesson.endH, lesson.endM)
        if start <= current < end:
            return lesson
    
    return None
    
def calculate_percentage(event=None):
    lesson = check_period(now.hour, now.minute)
    if lesson:
        return lesson.get_percentage(now.hour, now.minute, now.second)
    return 100

def toggle_drag(event):
    global canMove
    if int(event.type) == 4: # Button Pressed
        canMove = False
    else:
        canMove = True

def start_move(event): # finds mouse position
    global mouse
    mouse = event.x, event.y

def do_move(event, window): # allows windows to be dragged
    global paused
    if canMove:
        coords = window.winfo_x(), window.winfo_y()
        newCoords = (coords[0] + int(event.x) - mouse[0], coords[1] + int(event.y) - mouse[1])
        window.geometry(f"+{newCoords[0]}+{newCoords[1]}")
        paused = True
        pause[0].place(x=507, y=8, anchor="ne")
        pause[2].place(x=15, y=437, anchor="sw")
        pause[1].place(x=513, y=8, anchor="ne")
        pause[3].place(x=11, y=437, anchor="se")
        if window is bar.win:
            edgeRect.place_forget()

def end_move(event, window):
    global paused
    paused = False
    [x.place_forget() for x in pause]
    x, y = window.win.winfo_x(), window.win.winfo_y()
    if window is bar:
        snap(x, y, alt=event.state & 0x20000, ctrl=event.state & 0x00004)
    elif event.state & 0x20000: # alt
        window.go_to(25 * round(x / 25) + 10, 25 * round(y / 25) + 10, x, y)
    elif event.state & 0x00004: # ctrl
        window.go_to(screen.cx(window), screen.cy(window), x, y)
    main()

def rotate(event):
    global orientation
    orientation = not orientation
    x, y = bar.win.winfo_x(), bar.win.winfo_y()
    init_bar(orientation, new=False)
    bar.win.geometry(f"+{x}+{y}")
    if orientation:
        progressbar[1].place_forget()
        progressbar[0].place(x=13, y=3, anchor="nw")
    else:
        progressbar[0].place_forget()
        progressbar[1].place(x=3, y=13, anchor="nw")
    snap(x, y)
    
def align(event):
    edge = {"Up" : 0, "Right" : 1, "Down" : 2, "Left" : 3}[event.keysym]
    if int(orientation) == edge % 2:
        rotate(event)
    
    x = [screen.cx(bar), screen.w - bar.w, screen.cx(bar), 0][edge]
    y = [0, screen.cy(bar), screen.h - bar.h, screen.cy(bar)][edge]    
    bar.win.geometry(f"+{x}+{y}")
    control_edges(x, y)

def control_edges(x, y):
    if 0 in (x, y): # top left if the window is on top or left edge
        edgeRect.place(x=0, y=0, anchor="nw")
    elif orientation: # bottom
        edgeRect.place(x=0, y=13, anchor="nw")
    else: # right
        edgeRect.place(x=13, y=0, anchor="nw")

def snap(x, y, alt=False, ctrl=False):
    area = (200, 60)
    cx, cy = screen.cx(bar), screen.cy(bar)
    if orientation: # horizontal
        if y <= area[1] or screen.h - area[1] <= y: # top/bottom
            if cx - area[0] <= x and x <= cx + area[0]:
                if y <= area[1]:
                    ny = 0
                else:
                    ny = screen.h - bar.h
                bar.go_to(cx, ny, x, y, endFunc=control_edges)
                return None
    else: # vertical
        if x <= area[1] or screen.w - area[1] <= x: # left/right
            if cy - area[0] <= y and y <= cy + area[0]:
                if x <= area[1]:
                    nx = 0
                else:
                    nx = screen.w - bar.w
                bar.go_to(nx, cy, x, y, endFunc=control_edges)
                return None
    
    if alt:
        bar.go_to(25 * round(x / 25) + 10, 25 * round(y / 25) + 10, x, y)
    elif ctrl:
        bar.go_to(screen.cx(bar), screen.cy(bar), x, y)

def close_window(event, window):
    if not window.name: # sticky note
        stickyNotes.remove(window)
        window.close()
        return None
    if window.name in ["toast", "img"]:
        window.close()
        return None
    parent = bar
    try:
        if window is eyedropper:
            parent = colourPicker
    except: pass
    try:
        if window is edit_music:
            parent = music
    except: pass
    for feature in parent.children:
        if feature.name == window.name:
            key = feature.keys[0]
            break
    parent.toggle(None, keysym=key)
    try:
        if window is forum:
            close_client()
    except NameError:
        pass

def change_theme(event, num=None):
    global theme
    x, y = bar.win.winfo_x(), bar.win.winfo_y()
    if num is None:
        num = int(event.keysym)
    theme = themes[num - 1]
    init_bar(orientation, new=False) # refreshes the window
    bar.win.geometry(f"+{x}+{y}")
    snap(x, y)
    settings["theme"] = num - 1
        
def init_bar(orient, new=True, show=True):
    global apps, bar, orientation, edgeRect, progressbar, progress, percentLabel, pause, barHwnd
    from os import startfile, path
    import keyboard
    if theme.transparent:
        if orient:
            barDims = Dimension(532, 25)
        else:
            barDims = Dimension(462, 25)
    else:
        barDims = Dimension(600, 25)
    
    apps = Apps()
    functions = [
        Feature("menu", apps.menu_, "space"),
        Feature("timetable", apps.timetable_, "t"),
        Feature("note", apps.notepad_, "n"),
        Feature("clock", apps.clock_, "Return"),
        Feature("periodic", apps.periodicTable_, "p"),
        Feature("music", apps.music_, "m"),
        Feature("uni", apps.unicode_, "u"),
        Feature("map", apps.worldMap_, "w"),
        Feature("help", apps.shortcuts_, "h", "slash", "question"),
        Feature("calc", apps.calculator_, "equal"),
        Feature("quad", apps.quadratic_, "q"),
        Feature("settings", apps.config_, "s"),
        Feature("colour", apps.colourPicker_, "c"),
        Feature("forum", apps.forum_, "f"),
        Feature("translate", apps.translator_, "l"),
        Feature("tuner", apps.tuner_, "a"),
        Feature("voice", apps.voice_, "v"),
        Feature("info", apps.info_, "i"),
        Feature("log", apps.debug_, "x"),
        Feature("terminal", apps.terminal_, "z")]
    
    if new:
        bar = Window(barDims.w, barDims.h, "bar", children=functions, transparent=theme.transparent)
        bar.win.wm_attributes("-topmost", False)
        bar.win.geometry(f"+{screen.cx(bar)}+{-bar.h}")
    elif orient:
        bar = Window(barDims.w, barDims.h, "bar", new=bar, children=functions, transparent=theme.transparent)
    else:
        bar = Window(barDims.h, barDims.w, "bar", new=bar, children=functions, transparent=theme.transparent)
    if not show:
        bar.win.withdraw()
    
    bar.win.bind("<Control-KeyPress-c>", cmd)
    bar.win.bind("<Control-KeyPress-r>", restart)
    bar.win.bind("<Control-KeyPress-e>", raise_error)
    bar.win.bind("<Control-KeyPress-w>", lambda event : log("Test"))
    bar.win.bind("<Control-KeyPress-p>", lambda event : print("Test"))
    bar.win.bind("<KeyPress-r>", rotate)
    bar.win.bind("<Escape>", end_program)
    bar.win.bind("<Pause>", toggle_alpha)
    bar.win.bind("<BackSpace>", hide)
    bar.win.bind("<Enter>", mouse_over)
    bar.win.bind("<Leave>", mouse_over)
    bar.win.bind("<KeyPress-Delete>", lock)
    bar.win.bind("<KeyPress-Insert>", sticky_note)
    bar.win.bind("<Control-KeyPress-Insert>", close_stickies)
    [bar.win.bind(f"<KeyPress-F{i}>", lambda event, num=i : run_macro(num)) for i in range(1, 13)]
    [bar.win.bind(f"<Alt-KeyPress-F{i}>", lambda event, num=i : set_macro(num)) for i in range(1, 13)]
    bar.win.bind("<Control-o>", lambda event : startfile(path.dirname(path.abspath(sys.argv[0]))))
    [bar.win.bind(f"<{key}>", align) for key in ["Up", "Right", "Down", "Left"]]
    [bar.win.bind(f"<KeyPress-{num}>", change_theme) for num in range(10)]
    active["bar"] = True
    orientation = orient # True = horizontal, False = vertical
    if theme.transparent:
        bg = theme.transparentKey
    else:
        bg = theme.bg
    if orient:
        edgeRect = tk.Canvas(bar.win, width=bar.w, height=bar.h // 2, bg=theme.transparentKey, highlightthickness=0)
        edgeRect.create_rectangle(0, 0, bar.w, bar.h // 2, fill=bg, outline=bg, width=0)
    else:
        edgeRect = tk.Canvas(bar.win, width=bar.w // 2, height=bar.h, bg=theme.transparentKey, highlightthickness=0)
        edgeRect.create_rectangle(0, 0, bar.w // 2, bar.h, fill=bg, outline=bg, width=0)
    
    progressbar = [tk.Canvas(bar.win, width=506, height=20, bg=bg, highlightthickness=0),
                   tk.Canvas(bar.win, width=20, height=436, bg=bg, highlightthickness=0)]
    if orient:
        progressbar[0].place(x=13, y=3, anchor="nw")
    else:
        progressbar[1].place(x=3, y=13, anchor="nw")
        
    progressbar[0].create_rectangle(0, 0, 506, 20, fill=theme.acc, outline=theme.acc, width=0) # surrounding rect
    progressbar[1].create_rectangle(0, 0, 20, 436, fill=theme.acc, outline=theme.acc, width=0)
    progressbar[0].create_rectangle(2, 2, 504, 18, fill=theme.bgh, outline=theme.bgh, width=0) # inner rect - can be trough, bg or bgh
    progressbar[1].create_rectangle(2, 2, 18, 434, fill=theme.bgh, outline=theme.bgh, width=0)
    progressbar[0].create_rectangle(3, 3, 503, 17, fill=theme.trough, outline=theme.trough, width=0) # trough
    progressbar[1].create_rectangle(3, 3, 17, 433, fill=theme.trough, outline=theme.trough, width=0)
    [progressbar[i].create_rectangle(0, 0, 1, 1, fill=bg, outline=bg, width=0) for i in [0, 1]]
    progressbar[0].create_rectangle(0, 19, 1, 20, fill=bg, outline=bg, width=0)
    progressbar[1].create_rectangle(19, 0, 20, 1, fill=bg, outline=bg, width=0)
    progressbar[0].create_rectangle(505, 0, 506, 1, fill=bg, outline=bg, width=0)
    progressbar[1].create_rectangle(0, 435, 1, 436, fill=bg, outline=bg, width=0)
    progressbar[0].create_rectangle(505, 19, 506, 20, fill=bg, outline=bg, width=0)
    progressbar[1].create_rectangle(19, 435, 20, 436, fill=bg, outline=bg, width=0)
    progress = [progressbar[0].create_rectangle(3, 3, 503, 17, fill=theme.bar_colour(100), outline=theme.bar_colour(100), width=0),
                progressbar[1].create_rectangle(3, 3, 17, 433, fill=theme.bar_colour(100), outline=theme.bar_colour(100), width=0)]
    
    percentLabel = [tk.Label(bar.win, text="100.00%", bg=theme.bg, fg=theme.barTxt, font=theme.font),
                    tk.Label(bar.win, text="100.00%", bg=theme.bg, fg=theme.barTxt, font=theme.font, wraplength=10)]
    [label.bind("<ButtonRelease-3>", lambda event : bar.toggle(event, keysym="space")) for label in percentLabel]
    if not theme.transparent:
        percentLabel[0].place(x=520, y=bar.h // 2, anchor="w")
        percentLabel[1].place(x=bar.w // 2, y=450, anchor="n")
    
    pause = [tk.Canvas(bar.win, width=3, height=10, bg=theme.trough, highlightthickness=0) for i in range(4)]
    [canvas.create_rectangle(0, 0, 3, 10, fill=theme.bgh, outline=theme.bgh, width=0) for canvas in pause]
        
    if new:
        for feature in functions:
            if feature.name in sys.argv[1:]:
                bar.toggle(None, keysym=feature.keys[0])
        drop_bar(0)
        control_edges(bar.win.winfo_x(), bar.win.winfo_y())
        bar.win.update_idletasks()
        barHwnd = ctypes.windll.user32.GetParent(bar.win.winfo_id())
        keyboard.on_press_key("alt", lambda event : init_clickthrough())
        keyboard.on_release_key("alt", lambda event : disable_clickthrough())
        main()
    else:
        snap(bar.win.winfo_x(), bar.win.winfo_y())
        bar.win.update_idletasks()
        barHwnd = ctypes.windll.user32.GetParent(bar.win.winfo_id())
        keyboard.on_press_key("alt", lambda event : init_clickthrough())
        keyboard.on_release_key("alt", lambda event : disable_clickthrough())
        update_bar()

def end_program(event, restart=False):
    from winsound import PlaySound, SND_ASYNC
    save_settings() # e.g. theme number
    if settings["sounds"]:
        PlaySound(r".\SOUNDS\end_sound.wav", SND_ASYNC)
    
    x, y = bar.win.winfo_x(), bar.win.winfo_y()
    coords = [(screen.cx(bar), 0),
              (screen.w - bar.w, screen.cy(bar)),
              (screen.cx(bar), screen.h - bar.h),
              (0, screen.cy(bar))]
    if (x, y) in coords:
        side = coords.index((x, y))
        if side % 2 == int(not orientation):
            raise_bar(0, side=side, restart=restart)
        else:
            root.destroy()
            disconnect_server()
            loop.stop()
            loop.close()
            if restart:
                restart_program()
    else:
        root.destroy()
        disconnect_server()
        loop.stop()
        loop.close()
        if restart:
            restart_program()

def disconnect_server():
    if bgConnected:
        bg_sio.emit("leave_bg", {"room": "general", "user": DEFAULTUSER})
    bg_sio.disconnect()
    if "sio" in globals():
        sio.disconnect()

def fit_vertical(text):
    from tkinter import font
    label = percentLabel[1]
    f = font.Font(font=label["font"])
    size = f.cget("size")
    lines = len(text)
    while size > 1:
        f.configure(size=size)
        height = lines * f.metrics("linespace")
        if height <= 125:
            break
        size -= 1
    f.configure(size=size)
    label.configure(font=f)

def update_bar():
    global percentage
    percentage = calculate_percentage()
    
    if orientation:
        progressX = round(percentage * 5) + 3
        progressY = 17
    else:
        progressX = 17
        progressY = round(percentage * 4.3) + 3
    
    progressbar[int(not orientation)].coords(progress[int(not orientation)], 3, 3, progressX, progressY)
    progressbar[int(not orientation)].itemconfigure(progress[int(not orientation)], fill=theme.bar_colour(percentage))
    percentageText = f"{percentage:.2f}%"
    percentageText = percentageText.replace(".", " . ") # adds a small amount of space around the point - U+200A hair space
    percentLabel[0].config(text=percentageText)
    percentageText = f"{percentage:.2f}%".replace(".", "·")
    percentLabel[1].config(text=percentageText)
    root.update_idletasks()
    fit_vertical(percentageText)

def update_clock():
    if not active["clock"]:
        return None
        
    lesson = check_period(now.hour, now.minute)
    if lesson:
        timeLeft = dt.datetime(now.year, now.month, now.day, lesson.endH, lesson.endM, tzinfo=uk) - now # timeDelta
        hours = timeLeft.seconds // 3600
        minutes = (timeLeft.seconds % 3600) // 60
        seconds = (timeLeft.seconds % 3600) % 60
        if timeLeft < dt.timedelta(0):
            hours, minutes, seconds = 0, 0, 0
        clock.endTime.config(text=f"{lesson.desc}: {lesson.endH:02}:{lesson.endM:02} | {f'{hours:02}:' if hours > 0 else ''}{minutes:02}:{seconds:02}")
    else:
        clock.endTime.config(text="Not in Lesson")
    clockTime.config(text=now.strftime("%a %d/%m/%y %H:%M:%S"))

def check_music():
    global lessonReminderShown
    lessons = settings["music"]
    for instrument in lessons.keys():
        if instrument == "None":
            continue
        time = dt.datetime.fromisoformat(lessons[instrument])
        lesson = Lesson(time.hour, time.minute, 30)
        if now.strftime("%a") != time.strftime("%a"): # checks day
            continue
        
        start = dt.datetime(now.year, now.month, now.day, lesson.startH, lesson.startM).replace(tzinfo=uk)
        end = dt.datetime(now.year, now.month, now.day, lesson.endH, lesson.endM).replace(tzinfo=uk)
        warn = start - dt.timedelta(minutes=3)
        if start <= now <= end: # in lesson
            if not lessonReminderShown[1]:
                toast("Music", f"You have a{'n' if instrument[0].lower() in 'aeiou' and instrument[:2].lower() != 'eu' else ''} {instrument} lesson now!")
                lessonReminderShown[1] = True
        elif warn <= now <= end: # 3 min warning
            if not lessonReminderShown[0]:
                toast("Music", f"You have a{'n' if instrument[0].lower() in 'aeiou' and instrument[:2].lower() != 'eu' else ''} {instrument} lesson in 3 minutes!")
                lessonReminderShown[0] = True
        else:
            lessonReminderShown = [False, False]

def update_performance():
    if active["info"]:
        text = str(interval)
        uptime = now - programStart
        days = uptime.days
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60
        seconds = (uptime.seconds % 3600) % 60
        performance.config(text=f"{text}{(3 - len(text)) * ' '} ms")
        connectedLabel.config(text=str(bgConnected))
        uptimeText = ""
        if days > 0:
            uptimeText += f"{days}d "
        if hours > 0:
            uptimeText += f"{hours}h "
        if minutes > 0:
            uptimeText += f"{minutes}m "
        uptimeText += f"{seconds}s"
        uptimeLabel.config(text=uptimeText)

def animate_performance_graph(i, height, previous):
    if active["info"]:
        perfGraph.coords(perfBar, 0, (i / 50) * (height - previous) + previous, 25, 105)
    if i < 50:
        root.after(1, lambda : animate_performance_graph(i+1, height, previous))
    else:
        root.after(500, lambda : update_performance_graph(height))
        
def update_performance_graph(previous):
    if active["info"]:
        update_performance()
    height = interval / 25
    if height > 1:
        height = 1
    height = 105 - (height * 105)
    animate_performance_graph(0, height, previous)

def update_eye():
    from pyautogui import position, pixel
    from keyboard import is_pressed as pressed
    if active["eye"]:
        x, y = position()
        widget = eyedropper.win.winfo_containing(x, y)
        if widget is not None and widget.winfo_toplevel() is eyedropper.win or pressed("alt"):
            return None
        r, g, b = pixel(x, y)
        hex_colour = f"#{r:02x}{g:02x}{b:02x}" # formats as hex
        eyeSquare.config(bg=hex_colour)
        eyeLabel.config(text=hex_colour)
        
def main():
    global interval, startTime, now
    now = time_now()
    interval = round((time.perf_counter() - startTime) * 1000)
    update_bar()
    update_clock()
    update_eye()
    check_music()
    startTime = time.perf_counter()
    if running and not paused:
        root.update_idletasks()
        root.after(10, main)

def init_clickthrough():
    if alpha:
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        GWL_EXSTYLE = -20
        style = ctypes.windll.user32.GetWindowLongW(barHwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(barHwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)

def disable_clickthrough():
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020
    GWL_EXSTYLE = -20
    style = ctypes.windll.user32.GetWindowLongW(barHwnd, GWL_EXSTYLE)
    ctypes.windll.user32.SetWindowLongW(barHwnd, GWL_EXSTYLE, (style | WS_EX_LAYERED) & ~WS_EX_TRANSPARENT)

def change_alpha(i, direction, high=1, end=lambda : None):
    if direction == 1:
        new = 0.3 + 0.02 * i
    else:
        new = high - 0.02 * i
    bar.win.wm_attributes("-alpha", new)
    if i < (high - 0.3) / 0.02:
        bar.win.after(1, lambda : change_alpha(i + 1, direction, high=high))
    else:
        end()

def toggle_alpha(event):
    global alpha
    alpha = not alpha
    if alpha:
        change_alpha(0, -1, end=init_clickthrough)
    else:
        change_alpha(0, 1, end=disable_clickthrough)

def hide(event):
    if not orientation:
        rotate(event)
    if (bar.win.winfo_x(), bar.win.winfo_y()) == (screen.cx(bar), 0):
        bar.go_to(screen.cx(bar), 1-bar.h, bar.win.winfo_x(), bar.win.winfo_y())
    else:
        bar.win.geometry(f"+{screen.cx(bar)}+{1-bar.h}")

def mouse_over(event):
    if event.widget is not bar.win:
        return None
    if not alpha:
        return None
    if int(event.type) == 7:
        change_alpha(0, 1, high=0.6)
    else:
        change_alpha(0, -1, high=0.6)

def lock(event):
    global locked, lockScreen, lockImgFrame
    
    def fade_in(alpha):
        alpha += 0.005
        lockScreen.wm_attributes("-alpha", alpha)
        if alpha < 0.5:
            lockScreen.after(5, lambda : fade_in(alpha))        
            
    if globals().get("locked", False):
        return None
    locked = True
    lockScreen = tk.Toplevel(root)
    lockScreen.geometry(f"{screen.w+2}x{screen.h+2}+-1+-1")
    lockScreen.config(bg="#FFFFFF")
    lockScreen.overrideredirect(1)
    lockScreen.wm_attributes("-topmost", True)
    lockScreen.wm_attributes("-alpha", 0.005)
    passcode = "praisebetoxiaokun"
    lockScreen.bind(passcode, unlock)
    lockScreen.bind("<Alt-F4>", lambda event : "break")
    lockScreen.config(cursor="none")
    try:
        with open(r"IMAGES\lock.png", "r") as f:
            f.close()
    except FileNotFoundError:
        pass
    else:
        lockImgFrame = tk.Canvas(lockScreen, width=screen.w, height=screen.h, bg="#FFFFFF", highlightthickness=0)
        lockImgFrame.img = ImageTk.PhotoImage(Image.open(r"IMAGES\lock.png").resize((screen.w, screen.h), Image.LANCZOS))
        lockImgFrame.create_image(0, 0, image=lockImgFrame.img, anchor="nw")
        lockImgFrame.place(x=0, y=0, anchor="nw")

    fade_in(0.005)

def unlock(event):
    global locked
    def fade_out(alpha):
        alpha -= 0.005
        lockScreen.wm_attributes("-alpha", alpha)
        if alpha > 0:
            lockScreen.after(5, lambda : fade_out(alpha))
        else:
            lockScreen.destroy()

    locked = False
    fade_out(alpha=0.5)

def sticky_note(event):
    stickyNotes.append(Window(150, 100, "", padding=5))
    note = stickyNotes[-1]
    note.content.rowconfigure(0, weight=1)
    note.content.columnconfigure(0, weight=1)
    Textbox(note.content, 0, 0) 

def close_stickies(event):
    global stickyNotes
    [note.close() for note in stickyNotes]
    stickyNotes = []

def set_macro(num):
    import importlib.util, pathlib
    from tkinter import filedialog
    global macros
    path = pathlib.Path(filedialog.askopenfilename(initialdir="MACROS", title=f"Select Macro {num}", filetypes=[("Python files", "*.py")]))
    if str(path) == ".":
        return False
    name = path.stem
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if "macros" in globals():
        macros[num] = module
    else:
        macros = {num : module}
    return True

def run_macro(num):
    try:
        macros[num].run()
    except:
        if set_macro(num):
            macros[num].run()
    
def drop_bar(i, x=None): # drops progress bar from top
    if not x:
        x = screen.cx(bar)
    y = i - bar.h
        
    bar.win.geometry(f"+{x}+{y}")
    if i < bar.h:
        bar.win.after(1, lambda : drop_bar(i + 1, x=x))
    else:
        ctypes.windll.user32.SystemParametersInfoW(0x0057, 0, None, 0)

def raise_bar(i, side=0, restart=False):
    if side == 0:
        x, y = screen.cx(bar), 0 - i
    elif side == 1:
        x, y = screen.w - bar.w + i, screen.cy(bar)
    elif side == 2:
        x, y = screen.cx(bar), screen.h - bar.h + i
    elif side == 3:
        x, y = 0 - i, screen.cy(bar)
            
    bar.win.geometry(f"+{x}+{y}")
    if i < bar.h:
        root.after(1, lambda : raise_bar(i + 1, side=side, restart=restart))
    else:
        root.destroy()
        disconnect_server()
        if restart:
            restart_program()

def start_animation():
    def skip(event):
        start_window.destroy()
        bar.win.deiconify()
        
    def grow_circle(i): # circle growing animation
        frame.coords(circle, (screen.w - 64) / 2 - i, screen.h - 64 - i, (screen.w + 64) / 2 + i, screen.h + i) # makes circle bigger
        if i == 10 * math.ceil((screen.w + 64) * 0.05):
            bar.win.deiconify()
        elif i > (screen.w + 64) * 0.5: # time for the second circle
            frame.coords(
                transparent_circle,
                screen.w / 2 - (i - (screen.w + 64) * 0.5),
                screen.h / 2 - (i - (screen.w + 64) * 0.5),
                screen.w / 2 + (i - (screen.w + 64) * 0.5),
                screen.h / 2 + (i - (screen.w + 64) * 0.5))
        if i < (screen.w + 64) * 1.5: # repeats recursively
            start_window.after(1, lambda : grow_circle(i + 10))
        else:
            start_window.after(1000, start_window.destroy) # stops the start sequence
            bar.win.wm_attributes("-topmost", True)
    
    def move_circle(dy, *coords_to_move): # moves ball by dy
        coords = frame.coords(circle)
        new_coords = [coords[i] + int(i in coords_to_move) * dy for i in range(4)]
        if new_coords[3] - new_coords[1] != 64 and len(coords_to_move) == 2: # squish when it bounces
            new_coords[1] = new_coords[3] - 64
        
        frame.coords(circle, *new_coords)
    
    def control_circle(i):
        nonlocal vy
        restitution = 0.73 # coefficient of restitution
        mass = 1
        coords = frame.coords(circle)
        if vy < 2: # terminal velocity
            if coords[3] <= screen.h: # ball cannot fall off screen
                vy += 0.01 * mass # gravity
        else:
            vy = 2
        
        if coords[1] < screen.h - 64:
            move_circle(vy, 1, 3)
        elif screen.h - 64 <= coords[1]: # if it has hit the ground
            move_circle(vy, 1)
            if vy > 0 and screen.h - 48 <= coords[1]:
                vy = -1 * math.sqrt(restitution * vy ** 2) # kinetic energy, not speed
        
        if i <= 2800:
            start_window.after(1, lambda : control_circle(i + 1)) # repeats recursively
        else:
            grow_circle(0) # triggers growth animation
    
    start_window = tk.Toplevel(root) # window for animation
    start_window.bind("<Escape>", skip)
    start_window.wm_attributes("-transparentcolor", "#010101")
    start_window.wm_attributes("-topmost", True)
    start_window.overrideredirect(1)
    start_window.geometry(f"{screen.w}x{screen.h}+0+0")
    start_window.config(bg="#010101")
    frame = tk.Canvas(start_window, width=screen.w, height=screen.h, bg="#010101", highlightthickness=0)
    circle = frame.create_oval((screen.w - 64) / 2, -64, (screen.w + 64) / 2, 0, fill="#0A0A0A", outline="#0A0A0A", width=0)
    transparent_circle = frame.create_oval(-32, -32, -16, -16, fill="#010101", outline="#010101", width=0)
    frame.pack()
    vy = 0
    control_circle(0)

async def read_settings():
    global settings
    with open("settings.json", "r") as f:
        settings = json.load(f)
    
    if settings["sounds"]:
        from winsound import PlaySound, SND_ASYNC
        PlaySound(r".\SOUNDS\start_sound.wav", SND_ASYNC)
    
    try:
        with open("lpv2.log", "x") as f:
            f.close()
    except FileExistsError:
        pass
    with open("lpv2.log", "w") as f:
        f.write("")

def init_themes():
    global themes
    themes = [Theme(**t) for t in settings["themes"]]
        
def create_root():
    global root, active, apps, paused, running, canMove, lessonReminderShown, bar, screen, monFri, tueThu, theme, alpha, locked
    root = tk.Tk() # parent window
    root.report_callback_exception = tk_exception_handler # errors
    root.geometry(f"1x1+0+0")
    root.config(bg="#000000")
    root.overrideredirect(1)
    root.wm_attributes("-topmost", True)
    root.bind("<ButtonRelease-3>", lambda event : root.destroy())
    root.bind("<Up>", align)
    apps = Apps()
    active = {key : False for key in apps.appList}
    paused = locked = alpha = False
    running = canMove = True
    lessonReminderShown = [False, False]
    bar = None
    root.update_idletasks()
    screen = Dimension(root.winfo_screenwidth(), root.winfo_screenheight())
    root.geometry(f"+{screen.w - 1}+{screen.h - 1}")
    root.bind("<Enter>", lambda event : root.geometry(f"5x5+{screen.w - 5}+{screen.h - 5}"))
    root.bind("<Leave>", lambda event : root.geometry(f"1x1+{screen.w - 1}+{screen.h - 1}"))
    monFri = [Lesson(*settings["lessontimes"]["monFri"][i], desc=settings["lessonnames"][i]) for i in range(len(settings["lessontimes"]["monFri"]))]        
    tueThu = [Lesson(*settings["lessontimes"]["tueThu"][i], desc="Period 3¾" if i == 4 else settings["lessonnames"][i - int(i > 4)]) for i in range(len(settings["lessontimes"]["tueThu"]))]
    init_themes()
    theme = themes[settings["theme"]] # default theme
    play_animation = bool(settings["animation"]) # option to disable animation
    if play_animation:
        init_bar(True, show=False)
        start_animation()
    else:
        init_bar(True)
        bar.win.wm_attributes("-topmost", True)
        bar.win.geometry(f"+{screen.cx(bar)}+{-bar.h}")
        drop_bar(0)
    
    update_performance_graph(105)

async def start_bg(room="general"):
    from cryptography.fernet import Fernet
    FERNET_KEY = b"pBXI8RFiVSmIYK9GWjpfDjiED7otg8eCCtPNiUNjfeE="
    cipher = Fernet(FERNET_KEY)
    username = DEFAULTUSER

    def load_token():
        with open("token.enc", "rb") as f:
            encrypted = f.read()
        return cipher.decrypt(encrypted).decode()

    @bg_sio.on("connect")
    def auth_ok():
        global bgConnected
        bgConnected = True
        toast("[BG] Forum", "Connected")
        bg_sio.emit("join_bg", {"room": room, "user": username})

    @bg_sio.event
    def ping_alert(data):
        sender = data.get("from", "Unknown")
        message = data.get("message", "")
        if settings.get("dnd", False): # dnd is off by default
            bg_sio.emit("ping_dnd", {"to": sender})
        else:
            toast(f"{sender} – Ping", f"{message if message else f'{sender} wants you online!'}")
            
    @bg_sio.event
    def disconnect():
        global bgConnected
        bgConnected = False
        toast("[BG] Forum", "Disconnected")
        bg_sio.emit("leave_bg", {"room": "general", "user": username})
    
    try:
        bg_sio.connect(BASE, auth={"token" : load_token()}, transports=["websocket"])
    except Exception as e:
        toast("[BG] Forum", f"Couldn't connect: {e}")

async def start_program():
    global BASE, ICONS, PALETTE, DEFAULTUSER
    global bg_sio, bgConnected
    global startTime, interval, programStart, now, last_sync_attempt_mono, timeSource, clockErrorLogged, base_mono, uk
    global noteText, stickyNotes, toasts
    uk = zoneinfo.ZoneInfo("Europe/London")
    base_mono = time.monotonic()
    last_sync_attempt_mono = None
    clockErrorLogged = False
    timeSource = 0
    now = dt.datetime.now(uk)
    programStart = now
    startTime = time.perf_counter()
    interval = 0
    ICONS = Icons()
    PALETTE = Palette()
    noteText = ""
    toasts = []
    BASE = "https://lpv2forum.onrender.com"
    bgConnected = False
    bg_sio = socketio.Client()
    await read_settings() # reads the settings while bgTask is running
    DEFAULTUSER = settings["user"]
    create_root() # starts the gui after settings are loaded
    stickyNotes = []
    root.after(2000, lambda : loop.create_task(start_bg()))

class Apps:  
    def __init__(self):
        self.appList = [
            "menu", "timetable", "note", "clock", "periodic", "map", "music", "uni", 
            "help", "calc", "quad", "colour", "settings", "forum", "translate", "tuner", 
            "eye", "voice", "info", "log", "terminal", "edit", "bar"]

    def menu_(self, active):
        global menu
        if active:
            funcs = [lambda event : bar.toggle(event, keysym="t"),
                     lambda event : bar.toggle(event, keysym="m"),
                     lambda event : bar.toggle(event, keysym="n"),
                     lambda event : bar.toggle(event, keysym="s"),
                     lambda event : bar.toggle(event, keysym="p"),
                     lambda event : bar.toggle(event, keysym="equal"),
                     lambda event : bar.toggle(event, keysym="u"),
                     lambda event : bar.toggle(event, keysym="h"),
                     lambda event : bar.toggle(event, keysym="w"),
                     lambda event : bar.toggle(event, keysym="c"),
                     lambda event : bar.toggle(event, keysym="q"),
                     lambda event : bar.toggle(event, keysym="Return"),
                     lambda event : bar.toggle(event, keysym="l"),
                     lambda event : bar.toggle(event, keysym="f"),
                     lambda event : bar.toggle(event, keysym="a"),
                     lambda event : bar.toggle(event, keysym="i")] # features in menu
            menu = Window(250, 250, "menu", padding=5)
            menuText = [
                "\ue787", "\ue189", "\ue70b", "\ue713",
                "\uf22c", "\ue1d0", "\ue8dc", "\ue11b",
                "\ue128", "\ue790", "\ue94b", "\ue121",
                "\ue8ef", "\ue8f2", "\ue767", "\ue946"]
            menuCanvas = tk.Canvas(menu.content, width=240, height=240, bg=theme.bg, highlightthickness=0)
            menuCanvas.grid(row=0, column=0, sticky="nsew")
            menuButtons = [[Rounded_Rect(menuCanvas, (x+5, y+5, x+55, y+55),
                                         settings["menucolours"][int(x / 60 + 4 * (y / 60))],
                                         text=menuText[x // 60 + 4 * (y // 60)], txtColour="#000000",
                                         font=ICONS.BOLD)
                            for x in range(0, 240, 60)] for y in range(0, 240, 60)]
            [menuCanvas.tag_bind(menuButtons[i // 4][i % 4].id, "<Button-1>", funcs[i]) for i in range(len(funcs))]
        else:
            menu.close()
    
    def timetable_(self, active):            
        global timetable, timetableCanvas
        
        def change_text(newKey):
            nonlocal key
            key = newKey
            for row in range(5):
                for col in range(5):
                    newFill = settings["lessoncolours"]
                    lesson = settings["timetable-" + week][row][col]
                    newFill = Hex(newFill[lesson])
                    lesson = settings["timetable-" + week][col][row]
                    textColour = f"{'#FFFFFF' if lesson in ['Biology', 'Chemistry', 'Music'] else '#000000'}"
                    timetableCanvas.itemconfigure(timetableButtons[row][col].text,
                                                    text=settings[newKey + "-" + week][col][row], fill=textColour)
                    timetableButtons[col][row].roundedRect.fill = newFill
                    timetableButtons[col][row].roundedRect.config(bg=newFill)
        
        def change_week(newWeek):
            nonlocal week
            week = newWeek
            change_text(key)
            settings["week"] = "ab".index(week)
            save_settings()
        
        if active:
            # week = "ab"[settings["week"]] # 0 = a, 1 = b (OUTDATED)
            weekNum = time_now().strftime("%W")
            week = "0bababa0babab00abababa0bababab000000abababa00bababa00"[weekNum] # Week a/b pattern
            while week == 0:
                weekNum -= 1
                week = "0bababa0babab00abababa0bababab000000abababa00bababa00"[weekNum] # Week a/b pattern
            key = "timetable"
            timetable = Window(400, 275, "timetable")
            timetable.win.bind("<space>", lambda event : change_week("ba"["ab".index(week)]))
            timetable.win.bind("<Left>", lambda event : change_text(["timetable", "rooms", "teachers"][(["timetable", "rooms", "teachers"].index(key) - 1) % 3]))
            timetable.win.bind("<Right>", lambda event : change_text(["timetable", "rooms", "teachers"][(["timetable", "rooms", "teachers"].index(key) + 1) % 3]))
            timetableButtons = [[] for _ in range(5)]
            timetableCanvas = tk.Canvas(timetable.content, width=380, height=380, bg=theme.bg, highlightthickness=0)
            timetableCanvas.grid(row=0, column=0, sticky="nsew")
            coords = lambda x, y : (x * 76 + 1, (y + 1) * 42 + 1, (x + 1) * 76 - 1, (y + 2) * 42 - 1)
            for y in range(5):
                for x in range(5):
                    lesson = settings[f"timetable-{week}"][x][y]
                    colour = settings["lessoncolours"][lesson]
                    txtColour = ["#FFFFFF" if lesson in ["Biology", "Chemistry", "Music"] else "#000000"]
                    timetableButtons[y].append(Button(timetableCanvas, coords(x, y), colour, lesson, lambda : None, radius=1, txtColour=txtColour, outline=False))
            Button(timetableCanvas, (5, 5, 71, 35), theme.bgh, "Week A", lambda : change_week("a"))
            Button(timetableCanvas, (81, 5, 147, 35), theme.bgh, "Week B", lambda : change_week("b"))
            Button(timetableCanvas, (157, 5, 223, 35), theme.bgh, "Lessons", lambda : change_text("timetable"))
            Button(timetableCanvas, (233, 5, 299, 35), theme.bgh, "Rooms", lambda : change_text("rooms"))
            Button(timetableCanvas, (309, 5, 375, 35), theme.bgh, "Teachers", lambda : change_text("teachers"))
        else:
            timetable.close()
    
    def notepad_(self, active):
        global notepad, canMove, noteText
        from tkinter import messagebox as mb
        
        def note_files(mode):
            global fileWindow
            
            def saveTxtFile(slot):
                text = textEntry.txt()
                try:
                    with open(fr"NOTES\notes-{slot}", "x") as f: # creates new file
                        f.write(text) 
                except FileExistsError: # slot occupied
                    with open(fr"NOTES\notes-{slot}", "r") as f:
                        existingText = f"\"{f.read()[:10]}...\""
                    if mb.askokcancel(title="File exists", message=f"Overwrite file {slot}?", detail=existingText): # user confirms to overwrite
                        with open(fr"NOTES\notes-{slot}", "w") as f:
                            f.write(text) # updates file
                    else:
                        return None # window does not close if overwrite confirmation canceled
                finally:
                    fileWindow.win.destroy()
                
            def loadTxtFile(slot):
                try:
                    with open(fr"NOTES\notes-{slot}", "r") as f:
                        textEntry.set(f.read())  
                except FileNotFoundError:
                    mb.showinfo(title="File Does Not Exist", message=f"No file found in slot {slot}") # file may not be created
                else:
                    fileWindow.close()
            
            try: # stops many windows being opened
                fileWindow.close()
            except:
                pass
            fileWindow = Window(500, 75, "note-files", padding=5)
            if mode == "SAVE":
                func = saveTxtFile
            else:
                func = loadTxtFile
            
            [fileWindow.win.bind(f"<KeyPress-{num}>", lambda event : func(event.keysym)) for num in range(10)] # keyboard shortcut
            canvas = tk.Canvas(fileWindow.content, width=490, height=65, bg=theme.bg, highlightthickness=0)
            canvas.grid(row=0, column=0, sticky="nsew")
            [Button(canvas, (50 * i, 12, 50 * i + 40, 52), theme.bgh, str(i), lambda slot=i : func(slot), desc=f"Slot {i}") for i in range(10)]
        
        def toggle_bold(event):
            selection = textEntry.tag_ranges("sel")
            if len(selection) == 0:
                return None
            textEntry.tag_remove("sel", *selection)
            bold = [float(str(tag)) for tag in textEntry.tag_ranges("bold")]
            bold = [(bold[i], bold[i + 1]) for i in range(0, len(bold), 2)]
            if len(bold) == 0:
                textEntry.tag_add("bold", *selection)
                return None
            [textEntry.tag_remove("bold", *selection) if float(str(selection[0])) >= tagRange[0] and float(str(selection[1])) <= tagRange[1] else textEntry.tag_add("bold", *selection) for tagRange in bold]
            
        if active:
            notepad = Window(375, 500, "note")
            noteButtons = tk.Canvas(notepad.content, width=notepad.w - 20, height=50, bg=theme.bg, highlightthickness=0)
            notepad.content.rowconfigure(0, weight=19)
            notepad.content.rowconfigure(1, weight=1)
            notepad.content.columnconfigure(0, weight=1)
            notepad.textEntry = Textbox(notepad.content, 0, 0)
            textEntry = notepad.textEntry
            textEntry.tag_config("bold", font=theme.smallFont, foreground="#c586c0")
            textEntry.tag_config("sel", foreground="#66ff99", background="#334a3d")
            textEntry.tag_raise("sel")
            textEntry.tag_bind("sel", "<ButtonRelease-3>", toggle_bold)
            textEntry.tag_bind("bold", "<ButtonRelease-3>", toggle_bold)
            textEntry.append(noteText)
            Button(noteButtons, (0, 5, 80, 45), theme.bgh, ICONS.SAVE, lambda : note_files("SAVE"), font=ICONS, desc="Save")
            Button(noteButtons, (90, 5, 170, 45), theme.bgh, ICONS.LOAD, lambda : note_files("LOAD"), font=ICONS, desc="Open")
            Button(noteButtons, (185, 5, 265, 45), theme.bgh, ICONS.COPY, lambda : notepad.copy(textEntry.txt()), font=ICONS, desc="Copy")
            Button(noteButtons, (275, 5, 355, 45), theme.bgh, ICONS.DEL, lambda : textEntry.clear(), font=ICONS, desc="Clear")
            noteButtons.grid(row=1, column=0, sticky="nsew", pady=(5, 0))
            
        else:
            noteText = notepad.textEntry.txt()
            notepad.close()
            canMove = True # Otherwise, if the window was closed while attempting to drag the text, canMove would be stuck at False
    
    def clock_(self, active):
        global clock, clockTime
        
        def toggle_clock_mode(event):
            nonlocal clockMode
            if clockMode == "time":
                clockMode = "end"
                clockTime.place_forget()
                clock.endTime.place(x=clock.w // 2, y=clock.h // 2, anchor="center")
            else:
                clockMode = "time"
                clock.endTime.place_forget()
                clockTime.place(x=clock.w // 2, y=clock.h // 2, anchor="center")
        
        if active:
            now = time
            clock = Window(200, 25, "clock")
            x = screen.cx(clock) # centre top of screen
            clock.win.geometry(f"+{x}+-{clock.h}")
            clockTime = tk.Label(clock.win, text=now.strftime("%a %d/%m/%y %H:%M:%S"),
                                 fg=theme.txt, bg=theme.bg, font=theme.font)
            clockTime.place(x=clock.w // 2, y=clock.h // 2, anchor="center")
            clock.endTime = tk.Label(clock.win, text="END", fg=theme.txt, bg=theme.bg, font=theme.font)
            clockMode = "time"
            clock.win.bind("<Return>", toggle_clock_mode)
            clock.go_to(x, 0, x, -clock.h)
        else:
            x = screen.cx(clock) # centre top of screen
            clock.go_to(x, -clock.h, x, 0, endFunc=clock.close)
    
    def periodicTable_(self, active):
        global periodicTable, imgTable # otherwise the photoimage is not defined after function is run so does not display
        if active:
            periodicTable = Window(1366, 768, "periodic")
            imgFrame = tk.Canvas(periodicTable.win, width=periodicTable.w, height=periodicTable.h, bg=theme.bg, highlightthickness=0)
            imgTable = ImageTk.PhotoImage(Image.open(r"IMAGES\periodic_table.png").resize((screen.w, screen.h), Image.LANCZOS))
            imgFrame.create_image(0, 0, image=imgTable, anchor="nw")
            imgFrame.place(x=0, y=0, anchor="nw")
            periodicTable.win.geometry("+0+-768")
            periodicTable.go_to(screen.cx(periodicTable), screen.cy(periodicTable), screen.cx(periodicTable), -768)
        elif (periodicTable.win.winfo_x(), periodicTable.win.winfo_y()) == (screen.cx(periodicTable), screen.cy(periodicTable)):
            periodicTable.go_to(screen.cx(periodicTable), -768, screen.cx(periodicTable), screen.cy(periodicTable), endFunc=periodicTable.close)
        else:
            periodicTable.close()
                
    def worldMap_(self, active):
        global worldMap, imgMap
        if active:
            worldMap = Window(1366, 768, "map")
            imgFrame = tk.Canvas(worldMap.win, width=worldMap.w, height=worldMap.h, bg="#000000", highlightthickness=0)
            imgMap = ImageTk.PhotoImage(Image.open(r"IMAGES\world_map.png").resize((screen.w, screen.h), Image.LANCZOS))
            # imgMap = tk.PhotoImage(file=r"IMAGES\world_map.png")
            imgFrame.create_image(0, 0, image=imgMap, anchor="nw")
            imgFrame.place(x=0, y=0, anchor="nw")
            worldMap.win.geometry("+0+-768")
            worldMap.go_to(screen.cx(worldMap), screen.cy(worldMap), screen.cx(worldMap), -768)
        elif (worldMap.win.winfo_x(), worldMap.win.winfo_y()) == (screen.cx(worldMap), screen.cy(worldMap)):
            worldMap.go_to(screen.cx(worldMap), -768, screen.cx(worldMap), screen.cy(worldMap), endFunc=worldMap.win.destroy)
        else:
            worldMap.close()
    
    def music_(self, active):
        global music
        if active:
            music = Window(200, 75, "music", children=[Feature("edit", self.edit_music_, "e")])
            music.content.columnconfigure(0, weight=4)
            music.content.columnconfigure(1, weight=1)
            [music.content.rowconfigure(i, weight=1) for i in [0, 1]]
            lessonLabels = [tk.Label(music.content, text=dt.datetime.fromisoformat(settings["music"][key]).strftime(f"{key}: %a %H:%M"), bg=theme.bg, fg=theme.txt, font=theme.font) for key in settings["music"].keys()]            
            lessonLabels[0].grid(row=0, column=0, sticky="nsew")
            lessonLabels[1].grid(row=1, column=0, sticky="nsew")
            buttonFrame = tk.Canvas(music.content, width=35, height=55, bg=theme.bg, highlightthickness=0)
            buttonFrame.grid(row=0, column=1, rowspan=2, sticky="nsew")
            Button(buttonFrame, (0, 10, 35, 45), theme.bgh, ICONS.EDIT, lambda : music.toggle(None, keysym="e"), font=ICONS, desc="Edit")
        else:
            music.close()
    
    def edit_music_(self, active):
        global edit_music
        
        def get_selected(listbox):
            nonlocal day, lessonNo, half, instrument
            
            value = listbox.curselection()
            if len(value) == 0: # nothing selected
                value = (0,)
            if listbox is dayList:
                day = value[0]
            elif listbox is lessonList:
                lessonNo = value[0]
            elif listbox is halfList:
                half = value[0]
            elif listbox is instrumentList:
                instrument = value[0]
        
        def cancel_edit():
            music.toggle(None, keysym="e")
            
        def save_music():
            nonlocal day, lessonNo, half, instrument
            if lessonNo == 3: # 3 3/4 selected
                half = 0
            elif lessonNo == 4: # lunch selected
                half = 1
            
            currentDayNumber = int(now.date().strftime("%w")) # current weekday from 1 (Mon) to 7 (Sun)
            lessonDayNumber = day + 1 # Mon = 1 etc.
            daysFromNow = (lessonDayNumber - currentDayNumber) % 7
            lessonDate = now.date() + dt.timedelta(days=daysFromNow)
            if lessonDate.strftime("%a") in ["Mon", "Fri"]:
                lesson = monFri[lessonNo + int(lessonNo <= 3)] # skips 3 3/4
            else:
                lesson = tueThu[lessonNo + 1]
            
            lesson = Lesson(lesson.startH + (lesson.startM + 30 * half) // 60, (lesson.startM + 30 * half) % 60, 30) # adjusts for half
            lesson = dt.datetime(lessonDate.year, lessonDate.month, lessonDate.day, lesson.startH, lesson.startM)
            lesson = dt.datetime.isoformat(lesson)
            settings["music"][instruments[instrument]] = lesson
            save_settings() # saves new time
            [bar.toggle(None, keysym="m") for _ in range(2)] # updates music
            cancel_edit() # closes window
            
        if active:
            edit_music = Window(350, 150, "edit", padding=5)
            frame = edit_music.content
            frame.rowconfigure(0, weight=1)
            frame.rowconfigure(1, weight=1)
            frame.rowconfigure(2, weight=2)
            [frame.columnconfigure(i, weight=3) for i in [0, 1]]
            [frame.columnconfigure(i, weight=2) for i in [2, 3]]
            day, lessonNo, half, instrument = 0, 0, 0, 0
            dayLabel = tk.Label(frame, text="Day:", bg=theme.bg, fg=theme.txt, font=theme.smallFont, justify="center")
            dayLabel.grid(row=0, column=0, padx=2, sticky="nsew")
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            dayList = tk.Listbox(frame, width=11, height=5, bg=theme.bgh2, font=theme.bodyFont, fg=theme.txt,
                                 selectbackground=theme.bgh, highlightbackground=theme.bgh, relief="flat")
            [dayList.insert(i, days[i]) for i in range(5)]
            dayList.bind("<ButtonRelease-1>", lambda event : get_selected(dayList))
            dayList.grid(row=1, column=0, padx=2, pady=2, sticky="nsew", rowspan=2)
            lessonLabel = tk.Label(frame, text="Lesson:", bg=theme.bg, fg=theme.txt, font=theme.smallFont, justify="center")
            lessonLabel.grid(row=0, column=1, padx=2, sticky="nsew")
            lessons = [lesson.desc for lesson in tueThu][1:] # excludes registration
            lessonList = tk.Listbox(frame, width=11, height=7, bg=theme.bgh2, font=theme.bodyFont, fg=theme.txt,
                                    selectbackground=theme.bgh, highlightbackground=theme.bgh, relief="flat")
            [lessonList.insert(i, lessons[i]) for i in range(7)]
            lessonList.bind("<ButtonRelease-1>", lambda event : get_selected(lessonList))
            lessonList.grid(row=1, column=1, padx=2, pady=2, sticky="nsew", rowspan=2)
            halfLabel = tk.Label(frame, text="Half:", bg=theme.bg, fg=theme.txt, font=theme.smallFont, justify="center")
            halfLabel.grid(row=0, column=2, padx=2, sticky="nsew")
            halves = ["First", "Second"]
            halfList = tk.Listbox(frame, width=7, height=2, bg=theme.bgh2, font=theme.bodyFont, fg=theme.txt,
                                  selectbackground=theme.bgh, highlightbackground=theme.bgh, relief="flat")
            [halfList.insert(i, halves[i]) for i in range(2)]
            halfList.bind("<ButtonRelease-1>", lambda event : get_selected(halfList))
            halfList.grid(row=1, column=2, padx=2, pady=2, sticky="nsew")
            instrumentLabel = tk.Label(frame, text="Instrument:", bg=theme.bg, fg=theme.txt, font=theme.smallFont, justify="center")
            instrumentLabel.grid(row=0, column=3, padx=2, sticky="nsew")
            instruments = list(settings["music"].keys())
            instrumentList = tk.Listbox(frame, width=9, height=2, bg=theme.bgh2, font=theme.bodyFont, fg=theme.txt,
                                        selectbackground=theme.bgh, highlightbackground=theme.bgh, relief="flat")
            [instrumentList.insert(i, instruments[i]) for i in range(2)]
            instrumentList.bind("<ButtonRelease-1>", lambda event : get_selected(instrumentList))
            instrumentList.grid(row=1, column=3, padx=2, pady=2, sticky="nsew")
            buttonFrame = tk.Canvas(frame, width=100, height=50, bg=theme.bg, highlightthickness=0)
            Button(buttonFrame, (5, 5, 140, 30), theme.bgh, ICONS.CLOSE, cancel_edit, desc="Cancel")
            Button(buttonFrame, (5, 35, 140, 60), theme.bgh, ICONS.SAVE, save_music, font=ICONS, desc="Save")
            buttonFrame.grid(row=2, column=2, padx=2, pady=2, sticky="nsew", columnspan=2)
        else:
            edit_music.close()
    
    def shortcuts_(self, active):
        global shortcuts
        if active:
            keybinds = {"a"     : "Tone Generator",
                        "c"     : "Colour Picker",
                        "f"     : "Forum",
                        "h, ?"  : "Help",
                        "i"     : "Info",
                        "l"     : "Translator",
                        "m"     : "Music Lessons",
                        "n"     : "Notepad",
                        "p"     : "Periodic Table",
                        "q"     : "Quadratic Solver",
                        "r"     : "Rotate",
                        "s"     : "Settings",
                        "t"     : "Timetable",
                        "u"     : "Unicode",
                        "w"     : "World Map",
                        "="     : "Calculator",
                        "Space" : "Menu",
                        "Enter" : "Clock",
                        "Pause" : "Fade",
                        "1-9"   : "Change Theme",
                        "F1-12" : "Run Macro",
                        "Ctrl+C": "Command Prompt",
                        "Ctrl+R": "Restart",
                        "Ctrl+O": "Open Files",
                        "←↑→↓"  : "Align",
                        "Ins"   : "Quick Note",
                        "Del"   : "Lock Screen",
                        "Esc"   : "Close window"}
            
            shortcuts = Window(200, 450, "help")
            shortcuts.content.columnconfigure(0, weight=1)
            shortcuts.content.columnconfigure(1, weight=9)
            [shortcuts.content.rowconfigure(i, weight=1) for i in range(len(keybinds))]
            tk.Label(shortcuts.content, text="Key", bg=theme.bg, fg=theme.txt, font=theme.font).grid(row=0, column=0, sticky="nsw", pady=5)
            tk.Label(shortcuts.content, text="Feature", bg=theme.bg, fg=theme.txt, font=theme.font).grid(row=0, column=1, sticky="nsw", pady=5)
            for i in range(1, len(keybinds) + 1):
                key = list(keybinds.keys())[i - 1]
                tk.Label(shortcuts.content, text=key, bg=theme.bg, fg=theme.txt, font=theme.smallFont).grid(row=i, column=0, sticky="w", pady=3)
                tk.Label(shortcuts.content, text=keybinds[key], bg=theme.bg, fg=theme.txt, font=theme.bodyFont).grid(row=i, column=1, sticky="w", pady=3)
            
        else:
            shortcuts.close()
    
    def unicode_(self, active):
        global unicode
                
        def copy_symbol():
             if len(uniInp.get()) == 1:
                 unicode.copy(uniInp.get())
        
        def clear_uni():
            hexInp.clear()
            uniInp.clear()
            clear_error()
            hexInp.set_placeholder()
            uniInp.set_placeholder()
        
        def clear_error():
            hexInp.valid()
            uniInp.valid()
            
        def insert_common_char(index):
            clear_error()
            commonChars = settings["common-chars"]
            hexInp.set(commonChars[index])
            uniInp.set(chr(int(commonChars[index], 16)))
            copy_symbol()
        
        def hex_to_uni():
            hexCode = hexInp.get().strip().lower()
            if len(hexCode) == 0:
                clear_uni()
                clear_error()
                return None
            if hexCode == "[hex]":
                return None
            
            for char in hexCode:
                if char not in "0123456789abcdef": # ensures string is hex
                    hexInp.error()
                    return None
            
            denaryCode = int(hexCode, 16)
            if denaryCode < 32 or denaryCode > 65535: # swap to 255 for utf-8
                hexInp.error()
                return None
            clear_error()
            char = chr(denaryCode)
            uniInp.set(char)
        
        def uni_to_hex():
            char = uniInp.get()
            if len(char) == 0:
                clear_uni()
                clear_error()
                return None
            if len(char) != 1 and char != "[char]":
                uniInp.error()
                return None
            
            clear_error()
            denaryCode = ord(char)
            hexCode = hex(denaryCode)[2:] # removes 0x
            hexInp.set(hexCode)
            
        if active:
            unicode = Window(225, 100, "uni")
            [unicode.content.rowconfigure(i, weight=1) for i in range(3)]
            [unicode.content.columnconfigure(i, weight=1) for i in range(6)]
            commonChars = settings["common-chars"]
            charLabels = [tk.Label(unicode.content, text=chr(int(commonChars[i], 16)), bg=theme.bg, justify="center", fg=theme.txt, font=theme.smallFont) for i in range(6)]
            [charLabels[i].grid(row=0, column=i, sticky="nsew") for i in range(6)]
            hexInp = Field(unicode.content, 1, 0, cb=hex_to_uni, colspan=3, placeholder="[hex]")
            uniInp = Field(unicode.content, 1, 3, cb=uni_to_hex, colspan=3, placeholder="[char]")
            [charLabels[i].bind("<ButtonRelease-1>", lambda event, index=i : insert_common_char(index)) for i in range(6)]
            bottomRow = tk.Canvas(unicode.content, width=205, height=25, bg=theme.bg, highlightthickness=0)
            bottomRow.grid(row=2, column=0, columnspan=6)
            Button(bottomRow, (25, 1, 75, 24), theme.bgh, ICONS.CLOSE, clear_uni, font=ICONS.SMALL, desc="Close")
            Button(bottomRow, (130, 1, 180, 24), theme.bgh, ICONS.COPY, copy_symbol, font=ICONS.SMALL, desc="Copy")
        else:
            unicode.close()
    
    def calculator_(self, active):
        global calculator
        
        def clear_all():
            inp.clear()
            out.clear()
        
        def copy_ans():
            ans = evaluate()
            if len(ans) > 0: # stops from copying [char] or "" etc.
                inp.set(ans)
                out.clear()
                calculator.copy(ans)
            
        def evaluate():
            nonlocal ans
            global sin, cos, tan, deg, rad, pi
            deg = lambda r : math.degrees(r)
            rad = lambda d : math.radians(d)
            sqrt = lambda x : math.sqrt(x)
            pi = math.pi
            if settings["unit"] == 0: # Radians
                sin = lambda x : math.sin(x)
                cos = lambda x : math.cos(x)
                tan = lambda x : math.tan(x)
                arcsin = lambda x : math.asin(x)
                arccos = lambda x : math.acos(x)
                atan = lambda x : math.atan(x)
            else: # Degrees
                sin = lambda x : math.sin(rad(x))
                cos = lambda x : math.cos(rad(x))
                tan = lambda x : math.tan(rad(x))
                arcsin = lambda x : deg(math.asin(x))
                arccos = lambda x : deg(math.acos(x))
                atan = lambda x : deg(math.atan(x))
            
            expression = inp.get().strip()
            if len(expression) == 0:
                return "ERROR"
            
            for char in expression:
                if char.lower() not in "1234567890-+/*%().mathsincoprdegq ":
                    return "ERROR"
            
            try: answer = eval(expression)
            except: return "ERROR"
            try: float(answer) # checks output is numerical
            except: return "ERROR"
            ans = answer
            return answer
        
        def insert_answer(answer):
            out.set(f"{f'{answer:.3f}' if len(str(answer)) > 5 else f'{answer}'}")
            inp.clear()
            
        if active:
            ans = None
            calculator = Window(225, 125, "calc")
            [calculator.content.rowconfigure(i, weight=1) for i in range(3)]
            calculator.content.columnconfigure(0, weight=7)
            calculator.content.columnconfigure(1, weight=34)
            inp = Field(calculator.content, 0, 0, font=theme.monoFont, justify="left", colspan=2, pady=5, cb=lambda : insert_answer(evaluate()))
            buttonFrame = tk.Canvas(calculator.content, width=35, height=35, bg=theme.bg, highlightthickness=0)
            buttonFrame.grid(row=1, column=0, sticky="nsew")
            Button(buttonFrame, (5, 5, 30, 30), theme.bgh, "=", lambda : insert_answer(evaluate()), font=("Segoe UI", 14), desc="Evaluate")
            out = Field(calculator.content, 1, 1, font=theme.monoFont, justify="left", pady=5, state="disabled")
            bottomRow = tk.Canvas(calculator.content, width=200, height=35, bg=theme.bg, highlightthickness=0)
            bottomRow.grid(row=2, column=0, sticky="nsew", columnspan=2)
            Button(bottomRow, (10, 5, 90, 30), theme.bgh, ICONS.CLOSE, clear_all, font=ICONS.SMALL, desc="Clear")
            Button(bottomRow, (115, 5, 195, 30), theme.bgh, ICONS.COPY, copy_ans, font=ICONS.SMALL, desc="Copy ANS")
        else:
            calculator.close()
    
    def quadratic_(self, active):
        global quadratic
        
        def submit():
            def format_as_int(num):
                if num.is_integer():
                    if abs(num) == 1:
                        return ""
                    return str(abs(int(num)))
                return str(abs(num))
                
            try:
                a, b, c = inp.get().strip().split(" ")
            except ValueError: # not three values separated by spaces
                inp.error()
                return None
            
            try:
                a, b, c = float(a), float(b), float(c)
            except ValueError:
                inp.error()
                return None
            
            inp.valid()
            
            ea, eb, ec = format_as_int(a), format_as_int(b), format_as_int(c)
            if ec == "":
                ec = "1"
            
            terms = []
            if a < 0:
                terms.append("-")
            if ea != "0":
                terms.append(f"{ea}x²")
            if b < 0:
                terms.append(" - ")
            elif eb != "0":
                terms.append(" + ")
            if eb != "0":
                terms.append(f"{eb}x")
            if c < 0:
                terms.append(" - ")
            elif ec not in "0":
                terms.append(" + ")
            if ec != "0":
                terms.append(ec)
            equation = "".join(terms) + " = 0"
            equationDisplay.config(state="normal")
            equationDisplay.delete(0, tk.END)
            equationDisplay.insert(0, equation)
            equationDisplay.config(state="disabled")
            
            x = []
            try:
                sol = ((-1 * b) - math.sqrt(b ** 2 - 4 * a * c)) / (2 * a)
                if sol.is_integer():
                    x.append(int(sol))
                else:
                    x.append(sol)
            except:
                pass
            try:
                sol = ((-1 * b) + math.sqrt(b ** 2 - 4 * a * c)) / (2 * a)
                if sol.is_integer() and int(sol) not in x:
                    x.append(int(sol))
                elif sol not in x:
                    x.append(sol)
            except:
                pass
            
            formattedX = [f"x = {sol:.3f}" for sol in x]
            solutions = " or ".join(formattedX)
            out.set(solutions)
            
        if active:
            quadratic = Window(200, 125, "quad")
            quadratic.content.columnconfigure(0, weight=1)
            [quadratic.content.rowconfigure(i, weight=1) for i in range(3)]
            inp = Field(quadratic.content, 0, 0, font=theme.monoFont, justify="left", pady=5, cb=submit, placeholder="{a} {b} {c}")
            equationDisplay = Field(quadratic.content, 1, 0, font=theme.monoFont, pady=5, state="disabled", placeholder="[equation]")            
            out = Field(quadratic.content, 2, 0, font=theme.monoFont, pady=5, state="disabled", placeholder="[solutions]")
        else:
            quadratic.close()
    
    def colourPicker_(self, active):
        global colourPicker, hexInp
        
        def clear_inputs():
            hexInp.clear()
            rInp.clear()
            gInp.clear()
            bInp.clear()
        
        def raise_error(entry):
            if str(type(entry)) != "<class 'tkinter.Event'>":
                entry.error()
        
        def clear_errors():
            hexInp.valid()
            rInp.valid()
            gInp.valid()
            bInp.valid()
            
        def submit_hex():
            hexCode = hexInp.get().strip().lower()
            if len(hexCode) == 0:
                clear_errors()
                return None
            if hexCode[0] == "#":
                hexCode = hexCode[1:]
            if len(hexCode) != 6:
                raise_error(hexInp)
                return None
            for char in hexCode:
                if char not in "1234567890abcdef":
                    raise_error(hexInp)
                    return None
            
            red = int(hexCode[0:2], 16)
            green = int(hexCode[2:4], 16)
            blue = int(hexCode[4:6], 16)
            clear_inputs()
            clear_errors()
            preview.RR.config(bg=f"#{hexCode}")
            hexInp.set(f"#{hexCode}")
            rInp.set(red)
            gInp.set(green)
            bInp.set(blue)
            rScale.set(red)
            gScale.set(green)
            bScale.set(blue)
        
        def submit_rgb(entry):
            red = rInp.get().strip()
            green = gInp.get().strip()
            blue = bInp.get().strip()
            for colour in [red, green, blue]:
                if len(colour) == 0:
                    clear_errors()
                    return None
                if not colour.isdigit() and entry:
                    raise_error(entry)
                    return None
                if int(colour) > 255 and entry:
                    raise_error(entry)
                    return None
            
            clear_errors()
            red, green, blue = int(red), int(green), int(blue)
            hexInp.set(f"#{red:02X}{green:02X}{blue:02X}")
            submit_hex()
        
        def submit_scale(value, colour):
            if not scalePressed:
                return None
            if rInp.get() == "" or rInp.blank:
                rInp.set(255)
            if gInp.get() == "" or gInp.blank:
                gInp.set(255)
            if bInp.get() == "" or bInp.blank:
                bInp.set(255)
            
            if colour == "red":
                rInp.set(value)
            elif colour == "green":
                gInp.set(value)
            elif colour == "blue":
                bInp.set(value)
            
            submit_rgb(None)
        
        def toggle_scale_press(event):
            nonlocal scalePressed
            toggle_drag(event)
            scalePressed = int(event.type) == 4
            
        if active:
            scalePressed = False
            colourPicker = Window(500, 300, "colour", children=[Feature("eye", self.eyedropper_, "Control-e")])
            colourPicker.submit_hex = submit_hex
            [colourPicker.content.columnconfigure(i, weight=1) for i in range(9)]
            [colourPicker.content.rowconfigure(i, weight=1) for i in range(2)]
            colourPicker.content.rowconfigure(2, weight=5)
            eyeFrame = tk.Canvas(colourPicker.content, width=75, height=35, bg=theme.bg, highlightthickness=0)
            eyeFrame.grid(row=0, column=0, padx=5, pady=5)
            Button(eyeFrame, (0, 0, 75, 35), theme.bgh, ICONS.EYE, lambda : colourPicker.toggle(None, keysym="Control-e"), font=ICONS.MEDIUM, desc="Eyedropper")
            hexInp = Field(colourPicker.content, 0, 1, colspan=4, padx=5, pady=10, cb=submit_hex, placeholder="[hex]")
            copyFrame = tk.Canvas(colourPicker.content, width=75, height=35, bg=theme.bg, highlightthickness=0)
            copyFrame.grid(row=0, column=5, padx=5, pady=5)
            Button(copyFrame, (0, 0, 75, 35), theme.bgh, ICONS.COPY, lambda : colourPicker.copy(hexInp.get().strip()), font=ICONS.MEDIUM, desc="Copy hex")
            rInp = Field(colourPicker.content, 1, 0, colspan=2, padx=5, pady=5, cb=submit_rgb, placeholder="[red]")
            gInp = Field(colourPicker.content, 1, 2, colspan=2, padx=5, pady=5, cb=submit_rgb, placeholder="[green]")
            bInp = Field(colourPicker.content, 1, 4, colspan=2, padx=5, pady=5, cb=submit_rgb, placeholder="[blue]")
            preview = tk.Canvas(colourPicker.content, width=240, height=110, bg=theme.bg, highlightthickness=0)
            preview.grid(row=2, column=0, sticky="nsew", columnspan=6, padx=5, pady=5)
            preview.RR = Rounded_Rect(preview, (0, 0, 384, 172), "#ffffff") # actual width/height
            rScale = Scale(colourPicker.content, 255, "#1a0f0f", Hex("#3a1a1a"), command=lambda value : submit_scale(value, "red"))
            rScale.bind("<Button-1>", toggle_scale_press)
            rScale.bind("<ButtonRelease-1>", toggle_scale_press)
            rScale.grid(row=0, column=6, rowspan=3, padx=2, sticky="nsew")
            gScale = Scale(colourPicker.content, 255, "#0f1a0f", Hex("#1a3a1a"), command=lambda value : submit_scale(value, "green"))
            gScale.bind("<Button-1>", toggle_scale_press)
            gScale.bind("<ButtonRelease-1>", toggle_scale_press)
            gScale.grid(row=0, column=7, rowspan=3, padx=2, sticky="nsew")
            bScale = Scale(colourPicker.content, 255, "#0f0f1a", Hex("#1a1a3a"), command=lambda value : submit_scale(value, "blue"))
            bScale.bind("<Button-1>", toggle_scale_press)
            bScale.bind("<ButtonRelease-1>", toggle_scale_press)
            bScale.grid(row=0, column=8, rowspan=3, padx=2, sticky="nsew")
        else:
            colourPicker.close()
    
    def config_(self, active):
        global config
        
        class Check_Box(Checkbox):
            def __init__(self, master, text, row, col, key):
                self.key = key
                super().__init__(master, row, col, text, theme.h, bg=theme.bgh2)
                self.cb = lambda : change_setting(*self.get_keys(), check=self)
            
            def get_keys(self):
                if self.key == "themes":
                    self.keys = ("themes", themeNo.get() - 1, "transparent")
                else:
                    self.keys = (self.key, )
                return self.keys
        
        class HexField(Field):
            def __init__(self, master, title, row, width=11):
                self.label = tk.Label(master, text=f"{title}:", bg=theme.bgh2, fg=theme.txt, font=theme.smallFont, justify="left")
                self.label.grid(row=row, column=0, sticky="w", padx=5, pady=3)
                super().__init__(master, row, 1, sticky="w", padx=5, pady=5, width=width)
        
        class ThemeNoSelect:
            def __init__(self):
                self.label = tk.Label(themeSettings, text="Theme Number:", bg=theme.bgh2, fg=theme.txt, font=theme.smallFont, justify="left")
                self.label.grid(row=1, column=0, sticky="w", padx=5)
                self.buttonFrame = tk.Canvas(themeSettings, width=90, height=25, bg=theme.bgh2, highlightthickness=0)
                self.buttonFrame.grid(row=1, column=1, sticky="w", padx=5)
                self.numberLabel = Rounded_Rect(self.buttonFrame, (30, 0, 55, 25), theme.bgh, text="1")
                self.minus = Button(self.buttonFrame, (0, 0, 25, 25), theme.bgh * 1.25, ICONS.LEFT, lambda : change_theme_no(-1), font=ICONS.SMALL)
                self.plus = Button(self.buttonFrame, (60, 0, 85, 25), theme.bgh * 1.25, ICONS.RIGHT, lambda : change_theme_no(1), font=ICONS.SMALL)
                
        class Settings_Group(tk.Canvas):
            def __init__(self, row, col, rowspan, title=None):
                super().__init__(config.content, width=250, height=50 * rowspan, bg=theme.bgh2, highlightthickness=1, highlightbackground=theme.bgh, highlightcolor=theme.bgh)
                self.grid(row=row, column=col, rowspan=rowspan, sticky="nsew")
                if title:
                    self.title = tk.Label(self, text=title, bg=theme.bgh2, fg=theme.txt, font=theme.font, justify="left")
                    self.title.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        def init_boxes():
            [box.toggle() if configSettings[box.key] else None for box in [animation, sounds, dnd]]            
            if configSettings["themes"][themeNo.get() - 1]["transparent"]:
                transparentCheck.toggle()
            elif transparentCheck.state:
                transparentCheck.toggle()
        
        def init_radio():
            barButtons.on_change(configSettings["themes"][themeNo.get() - 1]["bar"])
            txtButtons.on_change(configSettings["themes"][themeNo.get() - 1]["barTxt"])
            units.on_change(configSettings["unit"])
        
        def validate_hex(*keys, entry=None):
            hexCode = entry.get().upper()
            entry.delete(0, tk.END)
            entry.insert(0, hexCode)
            if hexCode[0] == "#":
                hexCode = hexCode[1:]
            else:
                entry.insert(0, "#")
            if len(hexCode) != 6:
                entry.config(bg=theme.err)
                return None
            for char in hexCode:
                if char not in "1234567890ABCDEF":
                    entry.config(bg=theme.err)
                    return None
            
            entry.config(bg=theme.bgh)
            change_setting(*keys, entry=entry)
        
        def validate_num(*keys, entry=None):
            num = entry.get()
            if not num.isdigit():
                entry.config(bg=theme.err)
                return None
            
            entry.config(bg=theme.bgh)
            change_setting(*keys, entry=entry)
        
        def validate_char(*keys, entry=None):
            char = entry.get()
            if len(char) != 1:
                entry.config(bg=theme.err)
                return None
            
            entry.config(bg=theme.bgh)
            change_setting(*keys, entry=entry, uni=True)
        
        def validate_font(*keys, entry=None):
            font = entry.get().lower()
            fonts = [f.lower() for f in list(tkfonts.families())]
            fonts.append("systemfixed")
            if font not in fonts:
                entry.config(bg=theme.err)
                return None
            
            entry.config(bg=theme.bgh)
            change_setting(*keys, entry=entry)
        
        def change_setting(*keys, var=None, value=None, entry=None, check=None, uni=False):
            nonlocal configSettings
            if entry:
                value = entry.get()
                if value.isdigit():
                    value = int(value)
                if uni:
                    value = hex(ord(value))[2:].lower()
            elif var:
                value = var.get()
            elif check:
                value = int(check.state)
            
            current = configSettings
            for key in keys[:-1]:
                current = current[key]
            current[keys[-1]] = value
        
        def change_instrument_names(event):
            times = list(configSettings["music"].values())
            newKeys = [instrumentFields[i].get() for i in range(2)]
            newDict = {newKeys[0] : times[0],
                       newKeys[1] : times[1]}
            configSettings["music"] = newDict
        
        def change_theme_no(changeBy):
            nonlocal themeNo
            themeNo.set(themeNo.get() + changeBy)
            if themeNo.get() < 1:
                themeNo.set(1)
            elif themeNo.get() > 9:
                themeNo.set(9)
            
            themeNoSelect.numberLabel.config(text=themeNo.get())
            [themeFields[i].set(configSettings["themes"][themeNo.get() - 1][themeKeys[i]]) for i in range(len(themeFields))]
            init_boxes()
            init_radio()
        
        def change_bar_mode():
            configSettings["themes"][themeNo.get() - 1]["bar"] = barButtons.var
        
        def change_bar_text():
            configSettings["themes"][themeNo.get() - 1]["barTxt"] = txtButtons.var
        
        def change_unit():
            configSettings["unit"] = units.var
        
        def save():
            global settings
            settings = configSettings.copy()
            save_settings()
            init_themes()
            change_theme(None, num=themeNo.get())
            submit.roundedRect.config(text=ICONS.TICK)
            config.win.after(1000, lambda : submit.roundedRect.config(text=ICONS.SAVE))
        
        if active:
            configSettings = settings.copy()
            config = Window(770, 550, "settings") # not part of window snapping sizes because of size and complexity
            [config.content.columnconfigure(i, weight=1) for i in range(3)] # settings organised into columns
            [config.content.rowconfigure(i, weight=1) for i in range(10)]
            
            general = Settings_Group(0, 0, 4, "General")
            animation = Check_Box(general, "Start Animation", 1, 0, "animation")
            sounds = Check_Box(general, "Sounds", 2, 0, "sounds")
            dnd = Check_Box(general, "Do Not Disturb", 3, 0, "dnd")

            lessonColours = Settings_Group(4, 0, 6, "Lesson Colours")
            lessons = list(settings["lessoncolours"].keys())
            lessonFields = [HexField(lessonColours, lessons[i].replace("\n", ""), i+1) for i in range(len(lessons))]
            for i in range(len(lessons)):
                lessonFields[i].set(settings["lessoncolours"][lessons[i]])
                lessonFields[i].bind("<Return>", lambda event, field=lessonFields[i], key2=lessons[i] : validate_hex("lessoncolours", key2, entry=field))
                    
            themeSettings = Settings_Group(0, 1, 10, "Themes")
            themeNo = tk.IntVar()
            themeNo.set(1)
            themeNoSelect = ThemeNoSelect()
            themeLabels = ["Background", "Background Highlight", "Text Colour", "Accent", "Highlight", "Error", "Trough Colour", "Typeface", "Font Size"]
            themeKeys = ["bg", "bgh", "txt", "acc", "h", "err", "trough", "tf", "size"]
            themeFields = [HexField(themeSettings, themeLabels[i], i+2) for i in range(len(themeLabels))]
            for i in range(len(themeFields)):
                themeFields[i].set(settings["themes"][themeNo.get() - 1][themeKeys[i]])
                if i < 7:
                    func = validate_hex
                elif i == 7:
                    func = validate_font
                elif i == 8:
                    func = validate_num
                
                themeFields[i].bind("<Return>", lambda event, key=themeKeys[i], field=themeFields[i], function=func : function("themes", themeNo.get() - 1, key, entry=field))
            
            barModeTitle = tk.Label(themeSettings, text="Bar Mode:", bg=theme.bgh2, fg=theme.txt, font=theme.smallFont)
            barModeTitle.grid(row=11, column=0, sticky="w", padx=5, pady=3)
            barModes = ["Default",  "Accent", "Red-Blue"]
            barButtons = Radio(themeSettings, 12, 0, orientation=True, bg=theme.bgh2, colspan=2, cb=change_bar_mode)
            [barButtons.add(barModes[i], theme.h, i) for i in range(3)]
            barTextTitle = tk.Label(themeSettings, text="Percent Text Colour:", bg=theme.bgh2, fg=theme.txt, font=theme.smallFont)
            barTextTitle.grid(row=13, column=0, sticky="w", padx=5, pady=3)
            barTexts = ["Default",  "Accent"]
            txtButtons = Radio(themeSettings, 14, 0, orientation=True, bg=theme.bgh2, colspan=2, cb=change_bar_text)
            [txtButtons.add(barTexts[i], theme.h, i) for i in range(2)]
            transparentTitle = tk.Label(themeSettings, text="Transparent:", bg=theme.bgh2, fg=theme.txt, font=theme.smallFont)
            transparentTitle.grid(row=15, column=0, sticky="w", padx=5, pady=3)
            transparentCheck = Check_Box(themeSettings, "Transparent", 16, 0, "themes")

            musicSettings = Settings_Group(0, 2, 2, "Instruments")
            instrumentFields = [HexField(musicSettings, f"Instrument {i+1}", i+2, width=15) for i in range(2)]
            for i in range(2):
                instrumentFields[i].set(list(settings["music"].keys())[i])
                instrumentFields[i].bind("<Return>", change_instrument_names)
            
            unicodeSettings = Settings_Group(2, 2, 5, "Unicode Characters")
            chars = configSettings["common-chars"]
            charFields = [HexField(unicodeSettings, f"Character {i+1}", i+1) for i in range(6)]
            [charFields[i].set(chr(int(chars[i], 16))) for i in range(6)]
            [charFields[i].bind("<Return>", lambda event, index=i : validate_char("common-chars", index, entry=charFields[index])) for i in range(6)]
            
            calculatorSettings = Settings_Group(7, 2, 2, "Calculator")
            unitTitle = tk.Label(calculatorSettings, text="Angle Unit:", bg=theme.bgh2, fg=theme.txt, font=theme.smallFont)
            unitTitle.grid(row=1, column=0, sticky="w", padx=5, pady=3)
            unitTexts = ["Radians", "Degrees"]
            units = Radio(calculatorSettings, 1, 0, bg=theme.bgh2, colspan=2, cb=change_unit)
            [units.add(unitTexts[i], theme.h, i) for i in range(len(unitTexts))]
            
            buttonFrame = Settings_Group(9, 2, 1)
            Button(buttonFrame, (10, 10, 50, 50), theme.bgh * 1.25, ICONS.CLOSE, lambda : bar.toggle(None, keysym="s"), font=ICONS, desc="Close window")
            submit = Button(buttonFrame, (70, 10, 110, 50), theme.bgh * 1.25, ICONS.SAVE, save, font=ICONS, desc="Save settings")
            init_boxes()
            init_radio()
        else:
            config.close()
    
    def forum_(self, active):
        global forum, sio, close_client, canMove
        from re import findall
        from cryptography.fernet import Fernet
        from tkinter import filedialog
        import io, emoji, itertools

        def add_system(text):
            try:
                if chat.winfo_exists():
                    chat.append(f">>> {text}\n", "system")
            except:
                pass

        def emit(func, **data):
            try:
                if data:
                    sio.emit(func, data)
                else:
                    sio.emit(func)
            except Exception as e:
                add_system(f"ERROR: {e}")

        def close_client():
            if "current_room" not in globals():
                current_room, username = "general", DEFAULTUSER
            try:
                emit("leave_room", room=current_room, user=username)
                time.sleep(0.1)
                sio.disconnect()
            finally:
                forum.close()
        
        if active:
            FERNET_KEY = b"pBXI8RFiVSmIYK9GWjpfDjiED7otg8eCCtPNiUNjfeE="
            cipher = Fernet(FERNET_KEY)

            def load_token():
                with open("token.enc", "rb") as f:
                    encrypted = f.read()
                return cipher.decrypt(encrypted).decode()

            messages = []
            file_buffers = {}
            username = DEFAULTUSER
            current_room = "general"
            sio = socketio.Client()
            
            @sio.on("connect")
            def auth_ok():
                nonlocal username
                try:
                    username = usernameField.get().strip()
                except:
                    username = DEFAULTUSER
                
                add_system("CONNECTED TO SERVER")
                add_system("AUTH SUCCESSFUL")
                add_system("WELCOME")
                emit("request_history", room=current_room)
                emit("join_room", room=current_room, user=username)
            
            @sio.on("chat_history")
            def load_chat_history(data):
                nonlocal messages
                chat.clear()
                add_system(f"CHAT HISTORY LOADED FROM ROOM '{current_room}'")
                [add_message(msg) for msg in data]
            
            @sio.on("new_message")
            def new_message(data):
                nonlocal messages
                messages.append(data)
                add_message(data)
            
            @sio.on("highlight_message")
            def on_reply(data):
                pos = chat.search(f"[{data.get('timestamp')}]", "1.0", tk.END)
                if not pos:
                    return None
                line = pos.split(".")[0]
                chat.tag_add("reply", f"{line}.0", f"{line}.end")
            
            @sio.event
            def online_list(data):
                users = data.get("users", [])
                room = data.get("room", "unknown")
                
                if len(users) == 0:
                    add_system(f"NOBODY ONLINE IN {room}")
                    return None
                if panelShowing:
                    panelInner.delete(0, tk.END)
                    [panelInner.insert(i, user) for i, user in enumerate(users)]
                else:
                    add_system(f"ONLINE IN {room}: " + ", ".join(users))
            
            @sio.event
            def users_typing(data):
                typing = data.get("typing", {})
                if panelShowing:
                    users = panelInner.get(0, tk.END)
                    for index, user in enumerate(users):
                        base = user.rstrip("…")
                        ellipsis = typing.get(base, False)
                        new = base + "…" * ellipsis
                        if new != user:
                            panelInner.delete(index)
                            panelInner.insert(index, new)
            
            @sio.event
            def ping_alert(data):
                def quick_reply(toast):
                    send_message(text=toast.field.get())
                    toast.field.clear()
                    toast.slide = True
                    slide_away(toast)
                    
                sender = data.get("from", "Unknown")
                message = data.get("message", "")                
                if bool(settings["dnd"]):
                    emit("ping_dnd", to=sender)
                else:
                    add_system(f"PING RECEIVED FROM {sender}{': ' + message if message else ''}")
                    toast(f"{sender} – Ping", f"{message if message else f'{sender} wants you online!'}", entry=True, button=True, func=quick_reply)
                
            @sio.on("ping_failed")
            def ping_failed(data):
                target = data.get("to", "Unknown")
                add_system(f"{target} is not online")
            
            @sio.on("ping_dnd")
            def ping_dnd(data):
                target = data.get("to", "Unknown")
                add_system(f"{target} has do not disturb enabled")
            
            @sio.event
            def server_uploads(data):
                if len(data["files"]) == 0:
                    add_system("No files in server")
                else:
                    add_system("Files in server:")
                    [add_system(file) for file in data["files"]]
            
            @sio.event
            def upload_complete(data):
                name = data["file"]
                add_system(f"Successfully uploaded {name}")
                timestamp = now.strftime("%H:%M:%S")
                emit("send_message", room=current_room, user=username, text=f"uploaded {name}", timestamp=timestamp)
            
            @sio.event
            def download_chunk(data):
                name = data["file"]
                chunk = data["chunk"]
                file_buffers.setdefault(name, bytearray()).extend(chunk)
            
            @sio.event
            def download_complete(data):
                name = data["file"]
                path = filedialog.asksaveasfilename(initialdir="DOWNLOADS", title=f"Download {name}", initialfile=name, defaultextension="", filetypes=[("All files", "*.*")])
                if not path:
                    del file_buffers[name]
                    add_system("Download cancelled")
                    return None
                with open(path, "wb") as f:
                    f.write(file_buffers[name])
                del file_buffers[name]
                pathName = os.path.basename(path)
                add_system(f"Download complete: {pathName}")
            
            @sio.event
            def view_download_complete(data):
                name = data["file"]
                if os.path.splitext(name)[-1] not in  [".png", ".jpg", ".jpeg"]:
                    add_system("/view only accepts image files")
                    return None
                try:
                    with open(fr"DOWNLOADS\{name}", "wb") as f:
                        f.write(file_buffers[name])
                except FileExistsError:
                    name += "-2"
                    with open(fr"DOWNLOADS\{name}", "wb") as f:
                        f.write(file_buffers[name])
                del file_buffers[name]
                add_image(name)
            
            @sio.event
            def upload_error(data):
                add_system(f"Error uploading {data['file']}")
            
            @sio.event
            def download_error(data):
                add_system(f"Error downloading {data['file']}: File could not be found")
            
            @sio.event
            def disconnect(*args):
                nonlocal connected
                connected = False
                add_system("DISCONNECTED FROM SERVER")
            
            def forum_help():
                add_system("COMMAND LIST")
                add_system("/online - returns a list of people online in a room")
                add_system("/ping <target> - sends a notificiation to a user")
                add_system("/dnd - toggles do not disturb mode")
                add_system("/files - lists files in server")
                add_system("/upload - uploads a file")
                add_system("/download - downloads a file from the server")
                add_system("/view <file> - downloads and views an image file - latest if <file> is empty")
            
            def dnd():
                settings["dnd"] = 1 - settings["dnd"]
                save_settings()
                add_system(f"{'ACTIVATED' if bool(settings['dnd']) else 'DISABLED'} DO NOT DISTURB MODE")
            
            def upload():
                filePath = filedialog.askopenfilename(initialdir=PATH, title="Upload file", filetypes=[("All files", "*.*")])
                if not filePath:
                    return None
                file = os.path.basename(filePath)
                with open(filePath, "rb") as f:
                    while chunk := f.read(4096):
                        emit("upload_chunk", file=file, chunk=chunk)
                    emit("upload_complete", file=file)
            
            def download(downloadMessage):
                if len(downloadMessage) not in [1, 2]:
                    add_system("USAGE: /download <file>")
                    return None
                if len(downloadMessage) == 1:
                    emit("request_latest", on_complete=0)
                    return None
                emit("download", file=downloadMessage[1], on_complete=0)
            
            def insert_ping():
                messageField.clear()
                messageField.set("/ping ")
            
            def send_message(event=None, text=None):
                nonlocal username, current_room

                def stop():
                    messageField.clear()
                    return None
                
                now = time
                username = usernameField.get().strip()
                if username == "SYSTEM" or username == "":
                    add_system("USERNAME CANNOT BE EMPTY")
                    usernameField.error()
                    return None
                
                usernameField.valid()
                if not text:
                    text = messageField.get().strip()
                if not text:
                    return None
                
                if text == "/online":
                    emit("online_request", room=current_room)
                    return stop()
                elif text.startswith("/ping"):
                    pingMessage = text.split(" ")
                    if len(pingMessage) < 2:
                        add_system("USAGE: /ping <username>")
                        return stop()
                    message = ""
                    targets = pingMessage[1].strip().split(",") # gets target users
                    if len(pingMessage) >= 3:
                        message = " ".join(pingMessage[2:])
                    if targets == [""] or targets is None:
                        add_system("USAGE: /ping <username>")
                        return stop()
                    message = emoji.emojize(message, language="alias")
                    for target in targets:
                        emit("ping_user", **{"from": username, "to": target, "message": message})
                    add_system(f"PING SENT TO {', '.join(targets)}")
                    return stop()
                elif text == "/dnd":
                    dnd()
                    return stop()
                elif text == "/help":
                    forum_help()
                    return stop()
                elif text == "/upload":
                    upload()
                    return stop()
                elif text.startswith("/download"):
                    download(text.split())
                    return stop()
                elif text.startswith("/view"):
                    viewMessage = text.split()
                    if len(viewMessage) == 1:
                        emit("request_latest", on_complete=1)
                        return stop()
                    elif len(viewMessage) == 2:
                        emit("download", file=viewMessage[1], on_complete=1)
                        return stop()
                    add_system("USAGE: /view <file>")
                    return stop()
                elif text == "/files":
                    emit("files", **{})
                    return stop()
                elif len(findall("@[0-2][0-9]:[0-5][0-9]:[0-5][0-9]", text)) == 1: # reply
                    emit("reply", room=current_room, timestamp=text[1:9])
                elif len(findall("@[0-5][0-9]:[0-5][0-9]", text)) == 1: # short reply
                    emit("reply", room=current_room, timestamp=now.strftime(f"%H:{text[1:6]}"))

                targets_pinged = []
                for word in text.split():
                    if word.startswith("@"):
                        target = word[1:]
                        reply = len(findall("@[0-5][0-9]:[0-5][0-9]", target)) == 1 or len(findall("@[0-2][0-9]:[0-5][0-9]:[0-5][0-9]", target)) == 1
                        if target in targets_pinged and not reply:
                            break
                        emit("ping_user", **{"from": username, "to": target, "message": f"{username} mentioned you!", "offlineReturn": False})
                        targets_pinged.append(target)
                
                if not current_room:
                    current_room = "general"
                text = emoji.emojize(text, language="alias")
                emit("send_message", room=current_room, user=username, text=text, timestamp=now.strftime("%H:%M:%S"))
                return stop()
            
            def change_username():
                nonlocal username
                username = usernameField.get().strip()
            
            def change_room():
                nonlocal current_room, messages, username
                new_username = usernameField.get().strip()
                if not new_username:
                    add_system("INVALID USERNAME")
                    usernameField.error()
                    return None
                username = new_username
                new_room = roomField.get().strip()
                if not new_room:
                    add_system("INVALID ROOM")
                    roomField.error()
                    return None
                if new_room == current_room:
                    add_system(f"ALREADY IN '{current_room}'.")
                    return None
                roomField.valid()
                emit("leave_room", room=current_room, user=username)
                current_room = new_room
                messages = []
                chat.clear()
                add_system(f"SWITCHED TO '{current_room}'.")
                emit("request_history", room=current_room)
                emit("join_room", room=current_room, user=username)
            
            def paste(event):
                try:
                    img = ImageGrab.grabclipboard()
                    if isinstance(img, list):
                        path = img[0]
                        file = os.path.basename(path)
                        with open(path, "rb") as f:
                            while chunk := f.read(4096):
                                emit("upload_chunk", file=file, chunk=chunk)
                            emit("upload_complete", file=file)
                        return "break"
                    elif img is not None:
                        file = now.strftime("img-%H%M%S.png")
                        buffer = io.BytesIO()
                        img.save(buffer, format="PNG")
                        buffer.seek(0)
                        while chunk := buffer.read(4096):
                            emit("upload_chunk", file=file, chunk=chunk)
                        emit("upload_complete", file=file)
                        return "break"
                except: pass
                return None
            
            def open_url(event):
                index = chat.index(f"@{event.x},{event.y}")
                ranges = chat.tag_ranges("url")
                for i in range(0, len(ranges), 2):
                    start = ranges[i]
                    end = ranges[i+1]
                    if (chat.compare(start, "<=", index) and chat.compare(index, "<", end)):
                        url = chat.get(start, end)
                        if not url.startswith(("http://", "https://")):
                            url = "https://" + url
                        os.startfile(url)
                        return None
                
                return None
            
            def list_ping(event):
                index = panelInner.curselection()
                if index:
                    user = panelInner.get(index[0])
                    if user.endswith("…"):
                        user = user[:-1]
                    emit("ping_user", **{"from": username, "to": user, "message": ""})
            
            def toggle_menu(event):
                nonlocal menuShowing, emojiShowing
                colspan = 1 + int(not panelShowing)
                rowspan = 1 + int(menuShowing)
                if emojiShowing:
                    emojiRow.grid_forget()
                    emojiShowing = False
                if menuShowing:
                    menuRow.grid_forget()
                else:
                    menuRow.grid(row=3, column=0, columnspan=2, sticky="nsew")
                chat.frame.grid(row=2, column=0, columnspan=colspan, rowspan=rowspan, pady=5)
                if panelShowing:
                    panel.grid(row=2, column=1, rowspan=rowspan, pady=5, sticky="nsew")
                menuShowing = not menuShowing
                forum.win.update_idletasks()
                forum.win.after_idle(lambda: chat.yview_moveto(1.0))
                return None

            def toggle_panel(event):
                nonlocal panelShowing
                rowspan = 1 + int(not (menuShowing or emojiShowing))
                colspan = 1 + int(panelShowing)
                if panelShowing:
                    panel.grid_forget()
                else:
                    panel.grid(row=2, column=1, rowspan=rowspan, pady=5, sticky="nsew")
                    emit("online_request", room=current_room)
                chat.frame.grid(row=2, column=0, columnspan=colspan, rowspan=rowspan, pady=5, sticky="nsew")
                panelShowing = not panelShowing
                return "break"
            
            def toggle_emoji(event):
                nonlocal emojiShowing, menuShowing
                colspan = 1 + int(not panelShowing)
                rowspan = 1 + int(emojiShowing)
                if menuShowing:
                    menuRow.grid_forget()
                    menuShowing = False
                
                if emojiShowing:
                    emojiRow.grid_forget()
                else:
                    emojiRow.grid(row=3, column=0, columnspan=2, sticky="nsew")
                
                chat.frame.grid(row=2, column=0, columnspan=colspan, rowspan=rowspan, pady=5)
                if panelShowing:
                    panel.grid(row=2, column=1, rowspan=rowspan, pady=5, sticky="nsew")
                emojiShowing = not emojiShowing
                forum.win.update_idletasks()
                forum.win.after_idle(lambda: chat.yview_moveto(1.0))
                return "break"
            
            def send_type(event):
                messageField.frame.config(bg=theme.h)
                if connected:
                    emit("typing", typing=True)

            def send_untype(event):
                messageField.frame.config(bg=messageField.bg * 2)
                if connected:
                    emit("typing", typing=False)
            
            def reconnect():
                try:
                    emit("leave_room", room=current_room, user=username)
                    time.sleep(0.1)
                    sio.disconnect()
                except: pass
                finally: start_client()
            
            menuShowing = False
            panelShowing = False
            emojiShowing = False
            connected = False
            messageQueue = queue.Queue()
            emojifier = Emojifier(mode="append", font=tkfonts.Font(family=theme.smallFont[0], size=theme.smallFont[1], weight=theme.smallFont[2]))
            commands = {
                "<Control-space>": toggle_menu,
                "<Control-period>": toggle_emoji,
                "<Tab>": toggle_panel,
                "<Control-u>" : lambda event : upload(),
                "<Control-Up>": lambda event : upload(),
                "<Control-d>" : lambda event : download("/download"),
                "<Control-Down>" : lambda event : download("/download"),
                "<Control-p>" : lambda event : insert_ping(),
                "<Control-i>" : lambda event : emit("request_latest", on_complete=1),
                "<Control-f>" : lambda event : emit("files", **{}),
                "<Control-o>" : lambda event : emit("online_request", room=current_room),
                "<Control-r>" : lambda event : reconnect()}
            forum = Window(425, 525, "forum")
            [forum.win.bind(key, commands[key]) for key in commands.keys()]
            forum.content.columnconfigure(0, weight=3, uniform="main")
            forum.content.columnconfigure(1, weight=1, uniform="main")
            forum.content.rowconfigure(2, weight=10) # chat
            forum.content.rowconfigure(3, weight=1)
            [forum.content.rowconfigure(i, weight=1, minsize=30) for i in [0, 1, 4]] # fields
            commands["<Control-c>"] = lambda event : chat.event_generate("<<Copy>>")
            chat = Textbox(forum.content, 2, 0, state=False, colspan=2, rowspan=2, pady=5, binds=commands)
            chat.photos = []
            chat.rawPhotos = []
            chat.tag_config("system", foreground=PALETTE.ft.green, font=theme.smallFont)
            chat.tag_config("bsystem", foreground=PALETTE.ft.green, font=theme.smallFont)
            mods = "bisum"
            all_codes = [""]
            for r in range(1, len(mods) + 1):
                for combo in itertools.combinations(mods, r):
                    all_codes.append("".join(combo))
            for base in ["username", "myself"]:
                for code in all_codes:
                    tag_name = code + base
                    font_tuple = theme.mod(code)
                    chat.tag_config(tag_name, foreground=PALETTE.ft.orange if base == "username" else PALETTE.ft.blue, font=font_tuple)

            chat.tag_config("time", foreground=PALETTE.ft.purple, font=theme.smallFont)
            chat.tag_config("reply", foreground=PALETTE.ft.orange, background=PALETTE.fb.orange)
            chat.tag_config("url", foreground=PALETTE.ft.purple, underline=True)
            chat.tag_bind("url", "<Enter>", lambda event : chat.config(cursor="hand2"))
            chat.tag_bind("url", "<Leave>", lambda event : chat.config(cursor=""))
            chat.tag_bind("url", "<Control-Button-1>", open_url)
            chat.tag_config("sel", foreground=PALETTE.ft.green, background=PALETTE.fb.green)
            chat.tag_raise("sel")
            chat.bind("<Escape>", lambda event : bar.toggle(event, keysym="f"))
            userRow = tk.Frame(forum.content, width=405, height=35, bg=theme.bg, highlightthickness=0)
            userRow.columnconfigure(0, weight=4)
            userRow.columnconfigure(1, weight=5)
            userRow.columnconfigure(2, weight=1)
            userRow.grid(row=0, column=0, columnspan=2, sticky="nsew")
            usernameLabel = tk.Label(userRow, text="Username: ", bg=theme.bg, fg=theme.txt, font=theme.font)
            usernameLabel.configure(width=1)
            usernameLabel.grid(row=0, column=0, sticky="nsew", pady=2)
            usernameField = Field(userRow, 0, 1, colspan=2, pady=5, font=theme.smallFont, cb=change_username)
            usernameField.set(username)
            roomRow = tk.Frame(forum.content, width=405, height=35, bg=theme.bg, highlightthickness=0)
            roomRow.columnconfigure(0, weight=4)
            roomRow.columnconfigure(1, weight=5)
            roomRow.columnconfigure(2, weight=1)
            roomRow.grid(row=1, column=0, columnspan=2, sticky="nsew")
            roomLabel = tk.Label(roomRow, text="Channel: ", bg=theme.bg, fg=theme.txt, font=theme.font)
            roomLabel.configure(width=1)
            roomLabel.grid(row=0, column=0, sticky="nsew", pady=2)
            roomField = Field(roomRow, 0, 1, colspan=2, pady=5, font=theme.smallFont, cb=change_room)
            roomField.set(current_room)
            messageRow = tk.Frame(forum.content, width=405, height=35, bg=theme.bg, highlightthickness=0)
            messageRow.columnconfigure(0, weight=4)
            messageRow.columnconfigure(1, weight=5)
            messageRow.columnconfigure(2, weight=1)
            messageRow.grid(row=4, column=0, columnspan=2, sticky="nsew")
            messageLabel = tk.Label(messageRow, text="Message: ", bg=theme.bg, fg=theme.txt, font=theme.font)
            messageLabel.configure(width=1)
            messageLabel.grid(row=0, column=0, sticky="nsew", pady=2)
            messageField = Field(messageRow, 0, 1, colspan=2, pady=5, justify="left", cb=send_message)
            messageField.bind("<Control-v>", paste)
            messageField.bind("<FocusIn>", send_type)
            messageField.bind("<FocusOut>", send_untype)
            menuRow = tk.Frame(forum.content, width=405, height=25, bg=theme.bg, highlightthickness=0)
            [menuRow.columnconfigure(i, weight=1) for i in range(10)]
            menu = [tk.Canvas(menuRow, width=35, height=25, bg=theme.bg, highlightthickness=0) for _ in range(10)]
            [menu[i].grid(row=0, column=i, sticky="nsew", padx=2) for i in range(10)]
            icons = [ICONS.DOWNLOAD, ICONS.UPLOAD, ICONS.USERS, ICONS.BELL, ICONS.DND, ICONS.IMG, ICONS.FILE, ICONS.HELP, ICONS.RETRY, ICONS.CLOSE]
            funcs = [lambda : messageField.set("/download "), upload, lambda : emit("online_request", room=current_room),
                     lambda : messageField.set("/ping "), dnd, lambda : emit("request_latest", on_complete=1), lambda : emit("files", **{}),
                     forum_help, reconnect, lambda : bar.toggle(None, keysym="f")]
            descs = ["Download a file", "Upload a file", "Online users", "Send ping", "Do not disturb", "View image", "List files", "Help", "Reconnect", "Close"]
            [Button(menu[i], (0, 0, 35, 25), theme.bgh, icons[i], funcs[i], font=ICONS.SMALL, desc=descs[i]) for i in range(10)]
            emojiRow = tk.Frame(forum.content, width=405, height=25, bg=theme.bg, highlightthickness=0)
            [menuRow.columnconfigure(i, weight=1) for i in range(10)]
            emojis = [tk.Canvas(emojiRow, width=30, height=25, bg=theme.bg, highlightthickness=0) for _ in range(12)]
            [emojis[i].grid(row=0, column=i, sticky="nsew", padx=2) for i in range(12)]
            codes = [":+1:", ":smiley:", ":sob:", ":open_mouth:", ":pensive:", ":wave:", ":pray:", ":leg:", ":fire:", ":horse:", ":potable_water:", ":non-potable_water:"]
            emojiList = "".join([emoji.emojize(code, language="alias") for code in codes])
            [Button(emojis[i], (0, 0, 30, 25), theme.bgh, "", lambda code=codes[i]: messageField.append(code), font=("Segoe UI Emoji", 11), emoji=emojiList[i], desc=codes[i]) for i in range(12)]
            [messageField.bind(f"<Alt-KeyPress-{i+1}>", lambda event, c=codes[i] : messageField.append(f":{c}:")) for i in range(9)]
            messageField.bind("<Alt-KeyPress-0>", lambda event : messageField.append(f":{codes[9]}:"))
            messageField.bind("<Alt-KeyPress-minus>", lambda event : messageField.append(f":{codes[10]}:"))
            messageField.bind("<Alt-KeyPress-equal>", lambda event : messageField.append(f":{codes[11]}:"))
            panel = tk.Frame(forum.content, width=135, height=390, bg=theme.bgh*2, highlightthickness=0)
            panel.rowconfigure(0, weight=1)
            panel.columnconfigure(0, weight=1)
            panelMid = tk.Frame(panel, width=133, height=388, bg=theme.bgh2, highlightthickness=0)
            panelMid.grid(row=0, column=0, padx=1, pady=1, sticky="nsew")
            panelMid.rowconfigure(0, weight=1)
            panelMid.rowconfigure(1, weight=14)
            panelMid.columnconfigure(0, weight=1)
            tk.Label(panelMid, text=f"Online:", bg=theme.bgh2, fg=theme.txt, font=theme.smallFont).grid(row=0, column=0, sticky="nsw", padx=5)
            panelInner = tk.Listbox(panelMid, bg=theme.bgh2, selectbackground=theme.bgh, selectforeground=PALETTE.ft.blue, relief="flat", font=theme.bodyFont, fg=theme.txt, highlightthickness=0)
            panelInner.bind("<Double-Button-1>", list_ping)
            panelInner.bind("<FocusOut>", lambda event : panelInner.selection_clear(0, tk.END))
            panelInner.grid(row=1, column=0, padx=5, sticky="nsew")

            def format_text(text, tag):
                bold = italic = strike = under = mono = False
                i = 0
                sub = f"@{username}"
                indices = []
                start = 0
                while True:
                    idx = text.find(sub, start)
                    if idx == -1:
                        break
                    indices.extend(range(idx, idx + len(sub)))
                    start = idx + 1

                while i < len(text):
                    special = False
                    sequence = text[i:i+2]
                    if sequence == "**":
                        special = True
                        bold = not bold
                    if sequence == "__":
                        special = True
                        italic = not italic
                    if sequence == "~~":
                        special = True
                        strike = not strike
                    if sequence == "++":
                        special = True
                        under = not under
                    if sequence == "``":
                        special = True
                        mono = not mono
                    if not special:
                        oldBold = bold
                        if i in indices:
                            bold = True
                        prefix = "" + "b" * bold + "i" * italic + "s" * strike + "u" * under + "m" * mono
                        emojifier.render_text(chat, text[i], prefix + tag)
                        bold = oldBold
                    i += 1 + int(special)

            def process_queue():
                import re
                while not messageQueue.empty():
                    timestamp, user, text, tag = messageQueue.get()
                    urlRegex = re.compile(r"(https?://\S+|www\.\S+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/|\?|\#)\S*)", re.VERBOSE)
                    emojifier.render_text(chat, f"[{timestamp}]", tag="time")
                    emojifier.render_text(chat, f" {user}: ", tag=f"b{tag}")
                    start = chat.index("end-1c")
                    format_text(text + "\n", tag)
                    end = chat.index("end-1c")
                    lineText = chat.get(start, end)
                    for match in urlRegex.finditer(lineText):
                        s = f"{start}+{match.start()}c"
                        e = f"{start}+{match.end()}c"
                        chat.tag_add("url", s, e) 

                forum.win.after(50, process_queue)
                
            def add_message(message):
                if chat.winfo_exists():
                    timestamp = message.get("timestamp", "??:??:??")
                    user = message.get("user", "Unknown")
                    text = message.get("text", "")                    
                    if user == "SYSTEM":
                        tag = "system"
                    elif user == username:
                        tag = "myself"
                    else:
                        tag = "username"

                    messageQueue.put((timestamp, user, text, tag))
            
            def add_image(img):
                targetHeight = 128
                img = Image.open(fr"DOWNLOADS\{img}")
                width1, height1 = img.size
                width = int(width1 * (targetHeight / height1))
                original = img
                img = original.resize((width, targetHeight), Image.LANCZOS)
                image = ImageTk.PhotoImage(img)
                index = chat.image_create(tk.END, image=image, padx=5, pady=5)
                chat.tag_add(f"img-{len(chat.photos)+1}", index)
                chat.insert(tk.END, "\n")
                chat.yview(tk.END)
                chat.photos.append(image)
                chat.rawPhotos.append(original)
                chat.tag_bind(f"img-{len(chat.photos)}", "<Double-Button-1>", lambda event : image_viewer(chat.rawPhotos[-1], Dimension(width1, height1)))
            
            def image_viewer(img, size):
                global imgViewer
                imgViewer = Window(size.w+20, size.h+20, "img")
                imgViewer.photos = []
                canvas = tk.Canvas(imgViewer.content, width=size.w, height=size.h, bg=theme.bg, highlightthickness=0)
                imgViewer.content.columnconfigure(0, weight=1)
                imgViewer.content.rowconfigure(0, weight=1)
                canvas.grid(row=0, column=0, sticky="nsew")
                img = ImageTk.PhotoImage(img.resize((size.w, size.h), Image.LANCZOS))
                imgViewer.photos.append(img)
                canvas.create_image(0, 0, image=imgViewer.photos[-1], anchor="nw")
            
            def start_client(showMessage=True):
                async def start_client_async():
                    nonlocal connected
                    for _ in range(50):
                        try:
                            await asyncio.to_thread(lambda : sio.connect(BASE, auth={"token" : load_token()}, transports=["websocket"]))
                        except:
                            exception = traceback.format_exc()
                            await asyncio.sleep(0.1)
                        else:
                            connected = True
                            break
                    else:
                        log(exception, tag="ONLINE")

                    return True

                asyncio.run_coroutine_threadsafe(start_client_async(), loop)
                process_queue()
            
            usernameButton = tk.Canvas(userRow, width=25, height=25, bg=theme.bg, highlightthickness=0)
            usernameButton.grid(row=0, column=3, padx=5, pady=5)
            Button(usernameButton, (0, 0, 25, 25), theme.bgh, ICONS.TICK, change_username, font=ICONS.SMALL)
            roomButton = tk.Canvas(roomRow, width=25, height=25, bg=theme.bg, highlightthickness=0)
            roomButton.grid(row=0, column=3, padx=5, pady=5)
            Button(roomButton, (0, 0, 25, 25), theme.bgh, ICONS.TICK, change_room, font=ICONS.SMALL)
            sendButton = tk.Canvas(messageRow, width=25, height=25, bg=theme.bg, highlightthickness=0)
            sendButton.grid(row=0, column=3, padx=5, pady=5)
            Button(sendButton, (0, 0, 25, 25), theme.bgh, ICONS.SEND, send_message, font=ICONS.SMALL)
            forum.win.after(5, start_client)
        else:
            close_client()
            canMove = True
    
    def translator_(self, active):
        global translator, canMove
        import requests
        
        def swap(event):
            if event.state & 0x0001:
                return None
            target = toField.get().strip()
            toField.set(fromField.get().strip())
            fromField.set(target)
            fromText.clear()
            fromText.append(toText.txt())
            toText.clear()
            translate(event)
        
        def translate(event):
            if event.state & 0x0001:
                return None
            toText.clear()
            toText.append("Translating...")
            toText.update_idletasks()
            source, target = fromField.get().strip(), toField.get().strip()
            text = fromText.txt()
            try:
                translatedText = requests.get(f"https://lingva.ml/api/v1/{source}/{target}/{text}")
                if translatedText.status_code != 200: # invalid language code
                    translatedText = "Could not translate.\nCheck language codes"
                    fromField.error()
                    toField.error()
                else:
                    fromField.valid()
                    toField.valid()
                    translatedText = translatedText.json()["translation"]
            except:
                translatedText = "Could not translate.\nCheck internet connection and language codes"
                
            toText.clear()
            toText.append(translatedText)
            return "break"
            
        if active:
            translator = Window(400, 200, "translate")
            [translator.content.columnconfigure(i, weight=[3, 1][i % 2]) for i in range(4)]
            translator.content.rowconfigure(0, weight=1, minsize=30)
            translator.content.rowconfigure(1, weight=5)
            fromText = Textbox(translator.content, 1, 0, colspan=2, padx=5, pady=5)
            fromText.bind("<Return>", translate)
            toText = Textbox(translator.content, 1, 2, colspan=2, padx=5, pady=5)
            toText.bind("<Return>", swap)
            fromLabel = tk.Label(translator.content, text="Source:", bg=theme.bg, fg=theme.txt, font=theme.smallFont)
            fromLabel.grid(row=0, column=0, sticky="nsw", padx=5, pady=5)
            fromField = Field(translator.content, 0, 1, padx=5, pady=5, width=5, font=theme.monoFont)
            fromField.set("en")
            toLabel = tk.Label(translator.content, text="Target:", bg=theme.bg, fg=theme.txt, font=theme.smallFont)
            toLabel.grid(row=0, column=2, sticky="nsw", padx=5, pady=5)
            toField = Field(translator.content, 0, 3, padx=5, pady=5, width=5, font=theme.monoFont)
            toField.set("de")
        else:
            translator.close()
            canMove = True
    
    def tuner_(self, active):
        global tuner
        
        def change_note(index):
            nonlocal note
            note = index
            frequency.config(text=f"Frequency: {440 * 2 ** (note / 12 + octave - 4):.2f} Hz")
            play_tone()
        
        def change_octave(by):
            nonlocal octave
            octave += by
            octaveSelect.numberLabel.config(text=octave)
            frequency.config(text=f"Frequency: {440 * 2 ** (note / 12 + octave - 4):.2f} Hz")
        
        class OctaveSelect:
            def __init__(self):
                self.buttonFrame = tk.Canvas(tuner.content, width=90, height=25, bg=theme.bg, highlightthickness=0)
                self.buttonFrame.place(x=0, y=132, anchor="w")
                self.numberLabel = Rounded_Rect(self.buttonFrame, (35, 0, 60, 25), theme.bgh, text="3")
                self.minus = Button(self.buttonFrame, (5, 0, 30, 25), theme.bgh, ICONS.LEFT, lambda : change_octave(-1), font=ICONS)
                self.plus = Button(self.buttonFrame, (65, 0, 90, 25), theme.bgh, ICONS.RIGHT, lambda : change_octave(1), font=ICONS)
                
        def tone():
            from sounddevice import play, wait
            import numpy as np
            frequency = round(440 * 2 ** (note / 12 + octave - 4))
            play(np.sin(2 * np.pi * frequency * np.arange(44100 * 0.5) / 44100), 44100)
            wait()
        
        def play_tone():
            loop.call_soon_threadsafe(loop.create_task, asyncio.to_thread(tone))
            
        if active:
            tuner = Window(350, 175, "tuner")
            note = 0
            octave = 3
            notes = ["A", "A#/Bb", "B", "C", "C#/Db", "D", "D#/Eb", "E", "F", "F#/Gb", "G", "G#/Ab"]
            grid = lambda i : (55 * (i % 6) + 5, 55 * (i // 6) + 5, 55 * (i % 6 + 1) - 5, 55 * (i // 6 + 1) - 5)
            tunerCanvas = tk.Canvas(tuner.content, width=330, height=165, bg=theme.bg, highlightthickness=0)
            tunerCanvas.place(x=0, y=0, anchor="nw")
            [Button(tunerCanvas, grid(i), theme.bgh, notes[i], lambda index=i : change_note(index)) for i in range(12)]
            octaveSelect = OctaveSelect()
            frequency = tk.Label(tuner.content, text="Frequency: 440.00 Hz", bg=theme.bg, fg=theme.txt, font=theme.monoFont)
            frequency.place(x=330, y=132, anchor="e")
        else:
            tuner.close()
    
    def eyedropper_(self, activeLocal):
        global eyedropper, eyeSquare, eyeLabel
        cross = ctypes.windll.user32.LoadCursorW(0, 32515)
        ctypes.windll.user32.SetSystemCursor(cross, 32512)
        
        def insert_eye(event):
            if active["colour"]:
                hexInp.set(eyeLabel.cget("text"))
                colourPicker.submit_hex()
                
        if activeLocal:
            eyedropper = Window(125, 50, "eye")
            eyedropper.content.columnconfigure(0, weight=1)
            eyedropper.content.columnconfigure(1, weight=4)
            eyeSquare = tk.Canvas(eyedropper.content, bg="#ffffff", width=10, height=10, highlightthickness=0)
            eyeSquare.grid(row=0, column=0, padx=3, pady=3, sticky="nsew")
            eyeLabel = tk.Label(eyedropper.content, bg=theme.bg, fg=theme.txt, font=theme.font, text="#ffffff")
            eyeLabel.grid(row=0, column=1, pady=3, sticky="nsew")
            eyeLabel.bind("<ButtonRelease-3>", insert_eye)
        else:
            eyedropper.close()
            ctypes.windll.user32.SystemParametersInfoW(0x0057, 0, None, 0)
    
    def voice_(self, active):
        global voice
        import sounddevice as sd
        import numpy as np
        import soundfile as sf
        from tkinter import filedialog

        sample_rate = 44100
        channels = 1
        recording = False
        audio_chunks = []
        stream = None
        
        def record():
            if recording:
                stop_recording()
            else:
                start_recording()

        def audio_callback(indata, frames, time, status):
            if recording:
                audio_chunks.append(indata.copy())

        def start_recording():
            nonlocal recording, audio_chunks, stream
            audio_chunks = []
            recording = True
            stream = sd.InputStream(
                samplerate=sample_rate,
                channels=channels,
                dtype='float32',
                callback=audio_callback)
            stream.start()
            recordButton.roundedRect.config(text=ICONS.STOP)

        def stop_recording():
            nonlocal recording, stream
            recording = False
            if stream:
                stream.stop()
                stream.close()
            recordButton.roundedRect.config(text=ICONS.WAIT)
            audio = np.concatenate(audio_chunks, axis=0)
            filename = filedialog.asksaveasfilename(initialdir="SOUNDS", title="Save Audio", initialfile="recording.wav", defaultextension=".wav", filetypes=[("WAV files", "*.wav"), ("All files", "*.*")])
            if filename:
                sf.write(filename, audio, sample_rate)
                recordButton.roundedRect.config(text=ICONS.TICK)
            else:
                recordButton.roundedRect.config(text=ICONS.CLOSE)
            voice.win.after(500, lambda : recordButton.roundedRect.config(text=ICONS.MIC))
        
        def play(data, samplerate):
            nonlocal audioPlaying
            audioPlaying = True
            sd.play(data, samplerate, blocking=False)
            sd.wait()
            audioPlaying = False
            playButton.roundedRect.config(text=ICONS.PLAY)
        
        def update_audio_progress(start, duration):
            if audioPlaying:
                progress = time.time() - start
                playLabel.config(text=f"{int(progress // 60):02d}:{int(progress % 60):02d} / {int(duration // 60):02d}:{int(duration % 60):02d}")
                voice.win.after(1000, lambda : update_audio_progress(start, duration))
        
        def play_click():
            file = filedialog.askopenfilename(initialdir=PATH, title="Select Audio", filetypes=[("WAV files", "*.*")])
            if not file:
                return None
            data, samplerate = sf.read(file, dtype='float32')
            duration = len(data) / samplerate
            playLabel.config(text=f"00:00 / {int(duration // 60):02d}:{int(duration % 60):02d}")
            playButton.roundedRect.config(text=ICONS.SOUND)
            threading.Thread(target=lambda : play(data, samplerate)).start()
            voice.win.after(1000, lambda : update_audio_progress(time.time(), duration))
            
        if active:
            audioPlaying = False
            voice = Window(250, 125, "voice")
            voice.content.rowconfigure(0, weight=1)
            voice.content.rowconfigure(1, weight=1)
            voice.content.columnconfigure(0, weight=1)
            voice.content.columnconfigure(1, weight=9)
            voiceCanvas = tk.Canvas(voice.content, width=50, height=105, bg=theme.bg, highlightthickness=0)
            voiceCanvas.grid(row=0, column=0, sticky="nsew", rowspan=2)
            recordButton = Button(voiceCanvas, (0, 0, 50, 50), theme.bgh, ICONS.MIC, record, font=ICONS, desc="Record")
            playButton = Button(voiceCanvas, (0, 55, 50, 105), theme.bgh, ICONS.PLAY, play_click, font=ICONS, desc="Play")
            playLabel = tk.Label(voice.content, text="--:-- / --:--", bg=theme.bg, fg=theme.txt, font=theme.font)
            playLabel.grid(row=1, column=1, sticky="nsw")
        else:
            voice.close()
    
    def info_(self, active):
        global info, performance, connectedLabel, perfGraph, perfBar, uptimeLabel
        from socket import gethostbyname, gethostname
        from platform import python_version
        if active:
            info = Window(250, 125, "info")
            [info.content.rowconfigure(i, weight=1) for i in range(7)]
            tk.Label(info.content, text="Performance: ", bg=theme.bg, fg=theme.txt, font=theme.smallFont).grid(row=0, column=0, sticky="w")
            performance = tk.Label(info.content, bg=theme.bg, fg=theme.txt, font=theme.monoFont)
            performance.grid(row=0, column=1, sticky="w")
            tk.Label(info.content, text="Connected: ", bg=theme.bg, fg=theme.txt, font=theme.smallFont).grid(row=1, column=0, sticky="w")
            connectedLabel = tk.Label(info.content, text=str(bgConnected), bg=theme.bg, fg=theme.txt, font=theme.monoFont)
            connectedLabel.grid(row=1, column=1, sticky="w")
            tk.Label(info.content, text="Clock: ", bg=theme.bg, fg=theme.txt, font=theme.smallFont).grid(row=2, column=0, sticky="w")
            timeLabel = tk.Label(info.content, text=f"{'External' if timeSource == 1 else 'Local'}", bg=theme.bg, fg=theme.txt, font=theme.monoFont)
            timeLabel.grid(row=2, column=1, sticky="w")
            tk.Label(info.content, text="Screen size: ", bg=theme.bg, fg=theme.txt, font=theme.smallFont).grid(row=3, column=0, sticky="w")
            screenSize = tk.Label(info.content, text=f"{screen.w}x{screen.h}", bg=theme.bg, fg=theme.txt, font=theme.monoFont)
            screenSize.grid(row=3, column=1, sticky="w")
            tk.Label(info.content, text="IP Address: ", bg=theme.bg, fg=theme.txt, font=theme.smallFont).grid(row=4, column=0, sticky="w")
            tk.Label(info.content, text=gethostbyname(gethostname()), bg=theme.bg, fg=theme.txt, font=theme.monoFont).grid(row=4, column=1, sticky="w")
            tk.Label(info.content, text="Python Version: ", bg=theme.bg, fg=theme.txt, font=theme.smallFont).grid(row=5, column=0, sticky="w")
            tk.Label(info.content, text=python_version(), bg=theme.bg, fg=theme.txt, font=theme.monoFont).grid(row=5, column=1, sticky="w")
            tk.Label(info.content, text="Uptime: ", bg=theme.bg, fg=theme.txt, font=theme.smallFont).grid(row=6, column=0, sticky="w")
            uptimeLabel = tk.Label(info.content, text="0m 0s", bg=theme.bg, fg=theme.txt, font=theme.monoFont)
            uptimeLabel.grid(row=6, column=1, sticky="w")
            perfGraph = tk.Canvas(info.content, width=25, height=105, bg=theme.bg, highlightthickness=0)
            perfGraph.grid(row=0, column=2, rowspan=7, sticky="nsew", padx=5)
            perfBar = perfGraph.create_rectangle(0, 0, 25, 105, fill=theme.acc)
        
        else:
            info.close()
    
    def debug_(self, active):
        global debug, logBox, canMove
        
        def clear_log():
            with open("lpv2.log", "w") as f:
                f.write("")
            update_log()
        
        def find():
            logBox.tag_remove("sw", "1.0", tk.END)
            logBox.tag_remove("se", "1.0", tk.END)
            logBox.tag_remove("so", "1.0", tk.END)
            phrase = search.get()
            if not phrase.strip():
                return None
            
            matches = 0
            start = "1.0"
            while True:
                pos = logBox.search(phrase, start, stopindex="end", nocase=not caseCheck.state)
                if not pos:
                    break
                matches += 1
                end = f"{pos}+{len(phrase)}c"
                tags = logBox.tag_names(pos)
                if "w" in tags:
                    logBox.tag_add("sw", pos, end)
                elif "e" in tags:
                    logBox.tag_add("se", pos, end)
                elif "o" in tags:
                    logBox.tag_add("so", pos, end)
                start = end
            debug.numLabel.config(text=f"{matches} matches")
        
        def swap_stdout():
            if hasattr(sys.stdout, "logger"):
                sys.stdout = stdout
            else:
                sys.stdout = Logger(tag="[PRINT]")
        
        def swap_stderr():
            if hasattr(sys.stderr, "logger"):
                sys.stderr = stderr
            else:
                sys.stderr = Logger()
            
        if active:
            debug = Window(750, 600, "log")
            debug.content.columnconfigure(0, weight=1)
            debug.content.rowconfigure(0, weight=1, minsize=30)
            debug.content.rowconfigure(1, weight=23)
            debug.content.rowconfigure(2, weight=1)
            top = tk.Frame(debug.content, width=730, height=30, bg=theme.bg, highlightthickness=0)
            top.grid(row=0, column=0, sticky="nsew", pady=5)
            top.rowconfigure(0, weight=1)
            top.columnconfigure(0, weight=2)
            top.columnconfigure(1, weight=3)
            top.columnconfigure(2, weight=3)
            search = Field(top, 0, 2, justify=tk.LEFT, font=theme.bodyFont, padx=5, pady=10, cb=find, placeholder="Search (Ctrl+F)", icon=ICONS.SEARCH)
            commands = {"<Control-KeyPress-c>": lambda event : logBox.event_generate("<<Copy>>"), "<Control-KeyPress-f>": search.focus, "<Control-KeyPress-l>": lambda event : clear_log()}
            for key, func in commands.items():
                debug.win.bind(key, func)
            logBox = Textbox(debug.content, 1, 0, font=theme.monoFont, state=False, wrap="none", binds=commands)
            logBox.tag_config("e", foreground=PALETTE.lt.red, font=theme.monoFont)
            logBox.tag_config("w", foreground=PALETTE.lt.yellow, font=theme.monoFont)
            logBox.tag_config("o", foreground=PALETTE.lt.blue, font=theme.monoFont)
            logBox.tag_config("se", background=PALETTE.lb.red, font=theme.monoFont)
            logBox.tag_config("sw", background=PALETTE.lb.yellow, font=theme.monoFont)
            logBox.tag_config("so", background=PALETTE.lb.blue, font=theme.monoFont)
            logBox.tag_config("sel", foreground=PALETTE.ft.purple, background=PALETTE.fb.purple)
            logBox.tag_raise("sel")
            logBox.bind("<Escape>", lambda event : bar.toggle(event, keysym="x"))
            bottom = tk.Frame(debug.content, width=730, height=30, bg=theme.bg, highlightthickness=0)
            bottom.grid(row=2, column=0, sticky="nsew", pady=5)
            bottom.rowconfigure(0, weight=1)
            [bottom.columnconfigure(i, weight=2) for i in range(5)]
            bottom.columnconfigure(5, weight=15)
            [bottom.columnconfigure(i, weight=1) for i in [6, 7]]
            stdoutCheck = Checkbox(bottom, 0, 0, "STDOUT", theme.h, cb=swap_stdout)
            stdoutCheck.toggle(cb=False)
            stderrCheck = Checkbox(bottom, 0, 1, "STDERR", theme.h, cb=swap_stderr)
            stderrCheck.toggle(cb=False)
            debug.showInfo = Checkbox(bottom, 0, 2, "Show Info", theme.h, cb=update_log)
            debug.showInfo.toggle(cb=False)
            debug.autoScroll = Checkbox(bottom, 0, 3, "Auto-Scroll", theme.h)
            debug.autoScroll.toggle(cb=False)
            caseCheck = Checkbox(bottom, 0, 4, "Case Sensitive", theme.h)
            span = tk.Frame(bottom, bg=theme.bg, highlightthickness=0)
            span.grid(row=0, column=5, sticky="nsew")
            copy = tk.Canvas(bottom, width=35, height=35, bg=theme.bg, highlightthickness=0)
            copy.grid(row=0, column=6, padx=5)
            Button(copy, (0, 0, 35, 35), theme.bgh, ICONS.COPY, lambda : logBox.copy(), font=ICONS, desc="Copy")
            clear = tk.Canvas(bottom, width=35, height=35, bg=theme.bg, highlightthickness=0)
            clear.grid(row=0, column=7, padx=5)
            Button(clear, (0, 0, 35, 35), theme.bgh, ICONS.DEL, clear_log, font=ICONS, desc="Clear log")
            debug.numLabel = tk.Label(top, bg=theme.bg, fg=theme.txt, font=theme.font, text="42 errors")
            debug.numLabel.grid(row=0, column=0, sticky="nsew")
            debug.radios = Radio(top, 0, 1, orientation=True, cb=update_log)
            debug.radios.add("All", "#c678dd", 0)
            debug.radios.add("Warnings", "#e5c07b", 1)
            debug.radios.add("Errors", "#e06c75", 2)
            debug.radios.add("Online", "#5da9e9", 3)
            closeCanvas = tk.Canvas(top, width=35, height=35, bg=theme.bg, highlightthickness=0)
            closeCanvas.grid(row=0, column=3, padx=5)
            Button(closeCanvas, (0, 0, 35, 35), theme.bgh, ICONS.CLOSE, lambda : bar.toggle(None, keysym="x"), font=ICONS, desc="Close")
            update_log()
        else:
            debug.close()
            canMove = True
    
    def terminal_(self, active):
        global terminal, canMove
        
        def handle_backspace(event):
            try:
                start = terminal.text.index("sel.first")
                end = terminal.text.index("sel.last")
            except tk.TclError:
                if event.keysym == "BackSpace":
                    start = terminal.text.index("insert -1c")
                    end = terminal.text.index("insert")
                elif event.keysym == "Delete":
                    start = terminal.text.index("insert")
                    end = terminal.text.index("insert +1c")
                else:
                    return None

            for tag in ["prompt", "output", "submitted"]:
                ranges = terminal.text.tag_ranges(tag)
                for i in range(0, len(ranges), 2):
                    p_start = ranges[i]
                    p_end = ranges[i+1]
                    if not (terminal.text.compare(end, "<=", p_start) or terminal.text.compare(start, ">=", p_end)):
                        return "break"
            
            return None
        
        def handle_ctrl_backspace(event):
            pos = terminal.text.index("insert")
            probe = pos
            while True:
                previous = terminal.text.index(f"{probe} -1c")
                if previous == probe:
                    break
                if terminal.text.get(previous).isspace():
                    probe = previous
                else:
                    break

            if probe == terminal.text.index(f"{probe} wordstart"):
                probe = terminal.text.index(f"{probe} -1c")

            start = terminal.text.index(f"{probe} wordstart")
            end = terminal.text.index("insert")
            for tag in ["prompt", "output", "submitted"]:
                ranges = terminal.text.tag_ranges(tag)
                for i in range(0, len(ranges), 2):
                    p_start = ranges[i]
                    p_end = ranges[i+1]
                    if not (terminal.text.compare(end, "<=", p_start) or
                        terminal.text.compare(start, ">=", p_end)):
                        return "break"

            return terminal.text.delete_word(event)
        
        def handle_left_right(event):
            try:
                start = terminal.text.index("sel.first")
                end = terminal.text.index("sel.last")
            except tk.TclError:
                if event.keysym == "Left":
                    start = terminal.text.index("insert -1c")
                    end = terminal.text.index("insert")
                elif event.keysym == "Right":
                    start = terminal.text.index("insert")
                    end = terminal.text.index("insert +1c")
                else:
                    return None

            for tag in ["prompt", "output", "submitted"]:
                ranges = terminal.text.tag_ranges(tag)
                for i in range(0, len(ranges), 2):
                    p_start = ranges[i]
                    p_end = ranges[i+1]
                    if not (terminal.text.compare(end, "<=", p_start) or terminal.text.compare(start, ">=", p_end)):
                        return "break"
            
            return None
        
        def handle_up(event):
            if len(terminal.commands) > 0:
                terminal.commandIndex -= 1
                terminal.commandIndex %= len(terminal.commands)
                terminal.text.delete("end-1c linestart", "end-1c")
                terminal.text.append(">>> ", "prompt")
                terminal.text.append(terminal.commands[terminal.commandIndex])
            return "break"
        
        def handle_down(event):
            if len(terminal.commands) > 0:
                terminal.commandIndex += 1
                terminal.commandIndex %= len(terminal.commands)
                terminal.text.delete("end-1c linestart", "end-1c")
                terminal.text.append(">>> ", "prompt")
                terminal.text.append(terminal.commands[terminal.commandIndex])
            return "break"

        def handle_command(event):
            command = terminal.text.get("end-1c linestart", "end-1c")[4:]
            line = terminal.text.index("end-1c").split(".")[0]
            helpText = {
                "exit": "closes the terminal",
                "cls": "clears the terminal",
                "quit": "ends the program",
                "restart": "restarts the program",
                "time": "gets the current time",
                "python": "opens a python interpreter",
                "open": "opens the program's directory",
                "install": "installs a module from PyPI",
                "toast": "changes the program's notification system",
                "help": "shows these commands"}
            
            if command == "exit":
                bar.toggle(None, keysym="z")
            elif command == "cls":
                clear_terminal()
                return "break"
            elif command == "quit":
                end_program(event)
            elif command == "restart":
                end_program(event, restart=True)
            elif command == "time":
                output(f"{time_now()} ({'External' if timeSource else 'Local'})")
            elif command == "python":
                subprocess.Popen(["cmd.exe", "/k", "py -3.14"])
            elif command == "open":
                os.startfile(os.path.dirname(os.path.abspath(sys.argv[0])))
            elif command.split()[0] == "install":
                modules = " ".join(command.split()[1:])
                output(f"Installing modules: {modules}")
                subprocess.Popen(["cmd.exe", "/k", f"py -3.14 -m pip install {modules}"])
            elif command.split()[0] == "toast" and len(command.split()) == 2:
                global win11toast
                if command.split()[1] in ["1", "w", "win11toast"]:
                    import win11toast
                    output("Toasts now use win11toast")
                elif command.split()[1] in ["0", "t", "tkinter"]:
                    win11toast = None
                    output("Toasts now use tkinter")
                else:
                    output("Command not recognised. Type \"help\" for a list of commands.")
            elif command == "help":
                [output(f"{key} - {helpText[key]}") for key in helpText.keys()]
            else:
                output("Command not recognised. Type \"help\" for a list of commands.")
            
            terminal.text.append("\n>>> ", "prompt")
            terminal.commands.append(command)
            terminal.commandIndex = len(terminal.commands)
            terminal.text.tag_add("submitted", f"{line}.4", f"{line}.end")
            return "break"
        
        def clear_terminal():
            terminal.text.clear()
            terminal.commands = []
            terminal.commandIndex = 0
            terminal.text.append(f"Lesson Progress Counter [Version {VERSION}]\n", "prompt")
            terminal.text.append("Do not distribute without the author's permission.\n\n", "prompt")
            terminal.text.append(">>> ", "prompt")

        if active:
            terminal = Window(800, 475, "terminal")
            terminal.content.rowconfigure(0, weight=1)
            terminal.content.columnconfigure(0, weight=1)
            terminal.text = Textbox(terminal.content, 0, 0, font=theme.monoFont)
            terminal.text.tag_config("prompt", foreground=PALETTE.ft.green)
            terminal.text.tag_config("output", foreground=PALETTE.ft.purple)
            terminal.text.bind("<Return>", handle_command)
            terminal.text.bind("<BackSpace>", handle_backspace)
            terminal.text.bind("<Delete>", handle_backspace)
            terminal.text.bind("<Control-BackSpace>", handle_ctrl_backspace)
            terminal.text.bind("<Left>", handle_left_right)
            terminal.text.bind("<Right>", handle_left_right)
            terminal.text.bind("<Up>", handle_up)
            terminal.text.bind("<Down>", handle_down)
            output = lambda text : terminal.text.append(f"\n{text}", "output")
            clear_terminal()
        else:
            terminal.close()
            canMove = True

if __name__ == "__main__":
    atexit.register(lambda : ctypes.windll.user32.SystemParametersInfoW(0x0057, 0, None, 0))
    loop = asyncio.new_event_loop()
    loop.set_exception_handler(asyncio_exception_handler)
    def loop_thread():
        asyncio.set_event_loop(loop)
        loop.run_forever()

    threading.Thread(target=loop_thread, daemon=True).start()
    asyncio.run(start_program())
    try:
        root.mainloop()
    finally:
        ctypes.windll.user32.SystemParametersInfoW(0x0057, 0, None, 0)

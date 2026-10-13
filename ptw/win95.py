"""Windows 95 look for tkinter: grey 3D widgets, navy selection, small sans font."""
import time
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

BG = "#c0c0c0"
DARK = "#808080"
LIGHT = "#ffffff"
NAVY = "#000080"
TEAL = "#008080"
WHITE = "#ffffff"

FONT = ("MS Sans Serif", 8)
FONT_BOLD = ("MS Sans Serif", 8, "bold")


def _pick_font(root, size):
    """Microsoft Sans Serif looks like the Win95 system font and has Cyrillic."""
    global FONT, FONT_BOLD
    families = set(tkfont.families(root))
    for name, extra in (("Microsoft Sans Serif", 0), ("MS Sans Serif", 0), ("Tahoma", 0),
                        ("DejaVu Sans", 0), ("Helvetica", 1)):
        if name in families:
            FONT, FONT_BOLD = (name, size + extra), (name, size + extra, "bold")
            return


def apply_style(root, size=8):
    _pick_font(root, size)
    root.configure(bg=BG)
    opts = {
        "*Background": BG,
        "*Font": FONT,
        "*Foreground": "black",
        "*activeBackground": BG,
        "*highlightBackground": BG,
        "*highlightThickness": 0,
        "*selectBackground": NAVY,
        "*selectForeground": WHITE,
        "*Entry.Background": WHITE,
        "*Entry.Relief": "sunken",
        "*Entry.BorderWidth": 2,
        "*Listbox.Background": WHITE,
        "*Listbox.Relief": "sunken",
        "*Listbox.BorderWidth": 2,
        "*Text.Background": WHITE,
        "*Text.Relief": "sunken",
        "*Text.BorderWidth": 2,
        "*Spinbox.Background": WHITE,
        "*Button.Relief": "raised",
        "*Button.BorderWidth": 2,
        "*Button.Padx": 8,
        "*Button.Pady": 1,
        "*Checkbutton.selectColor": WHITE,
        "*Radiobutton.selectColor": WHITE,
        "*Menu.Background": BG,
        "*Menu.activeBackground": NAVY,
        "*Menu.activeForeground": WHITE,
        "*Menu.Relief": "raised",
        "*Menu.activeBorderWidth": 0,
    }
    for k, v in opts.items():
        root.option_add(k, v)

    st = ttk.Style(root)
    st.theme_use("classic")
    st.configure(".", background=BG, font=FONT, foreground="black",
                 fieldbackground=WHITE, troughcolor=BG, borderwidth=2)
    st.configure("Treeview", background=WHITE, fieldbackground=WHITE,
                 rowheight=FONT[1] * 2 + 2, borderwidth=2, relief="sunken")
    st.map("Treeview", background=[("selected", NAVY)], foreground=[("selected", WHITE)])
    st.configure("Treeview.Heading", background=BG, relief="raised", borderwidth=2, font=FONT)
    st.map("Treeview.Heading", background=[("active", BG)])
    st.configure("TCombobox", fieldbackground=WHITE, background=BG, arrowsize=13)
    st.map("TCombobox", fieldbackground=[("readonly", WHITE)],
           selectbackground=[("readonly", WHITE)], selectforeground=[("readonly", "black")])
    st.configure("TNotebook", background=BG, borderwidth=2, tabmargins=(2, 4, 2, 0))
    st.configure("TNotebook.Tab", background=BG, padding=(10, 2), borderwidth=2)
    st.map("TNotebook.Tab", background=[("selected", BG)],
           expand=[("selected", (2, 2, 2, 0))])
    st.configure("Vertical.TScrollbar", background=BG, arrowsize=16)
    st.configure("Horizontal.TScrollbar", background=BG, arrowsize=16)
    root.option_add("*TCombobox*Listbox.Background", WHITE)
    root.option_add("*TCombobox*Listbox.selectBackground", NAVY)
    return st


def calendar_options(locale="en_GB"):
    """Colours for tkcalendar widgets in the Date/Time Properties look."""
    return dict(
        font=FONT, headersfont=FONT_BOLD, background=BG, foreground="black",
        bordercolor=DARK, headersbackground=BG, headersforeground="black",
        normalbackground=WHITE, normalforeground="black",
        weekendbackground=WHITE, weekendforeground="black",
        othermonthbackground="#e8e8e8", othermonthwebackground="#e8e8e8",
        othermonthforeground=DARK, othermonthweforeground=DARK,
        selectbackground=NAVY, selectforeground=WHITE,
        showweeknumbers=False, firstweekday="monday", locale=locale,
        date_pattern="dd/mm/yyyy", cursor="arrow",
    )


class Banner(tk.Canvas):
    """Navy-to-teal gradient strip like a Win95 setup screen."""

    def __init__(self, master, text, sub="", height=46, **kw):
        super().__init__(master, height=height, highlightthickness=0, bd=0, **kw)
        self.text, self.sub = text, sub
        self.bind("<Configure>", self._draw)

    def _draw(self, _e=None):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        steps = 64
        for i in range(steps):
            r = 0
            g = int(0x80 * i / steps)
            b = 0x80
            x0 = w * i // steps
            x1 = w * (i + 1) // steps + 1
            self.create_rectangle(x0, 0, x1, h, outline="", fill=f"#{r:02x}{g:02x}{b:02x}")
        big = (FONT[0], 14, "bold italic")
        self.create_text(13, h // 2 - (6 if self.sub else 0) + 1, text=self.text, anchor="w",
                         fill="black", font=big)
        self.create_text(12, h // 2 - (6 if self.sub else 0), text=self.text, anchor="w",
                         fill=WHITE, font=big)
        if self.sub:
            self.create_text(14, h // 2 + 13, text=self.sub, anchor="w", fill=WHITE, font=FONT)


class StatusBar(tk.Frame):
    def __init__(self, master, **kw):
        super().__init__(master, bg=BG, **kw)
        self.var = tk.StringVar(value="Ready")
        tk.Label(self, textvariable=self.var, relief="sunken", bd=1, anchor="w",
                 padx=4).pack(side="left", fill="x", expand=True, padx=2, pady=2)
        self.right = tk.StringVar()
        tk.Label(self, textvariable=self.right, relief="sunken", bd=1, anchor="w",
                 width=24, padx=4).pack(side="right", padx=2, pady=2)

    def set(self, text):
        self.var.set(text)
        self.update_idletasks()


def group(master, text, **kw):
    return tk.LabelFrame(master, text=text, relief="groove", bd=2, padx=6, pady=4, **kw)


def button(master, text, command=None, width=12, **kw):
    return tk.Button(master, text=text, command=command, width=width, **kw)


def scrolled_tree(master, columns, widths, height=12):
    """Treeview with a vertical scrollbar; returns (frame, tree)."""
    f = tk.Frame(master, bg=BG)
    tree = ttk.Treeview(f, columns=[c for c, _ in columns], show="headings",
                        height=height, selectmode="extended")
    for (key, title), w in zip(columns, widths):
        tree.heading(key, text=title, anchor="w")
        tree.column(key, width=w, minwidth=30, anchor="w", stretch=w >= 250)
    sb = ttk.Scrollbar(f, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    def fit(event):
        """Shrink the wide column so that all columns stay visible."""
        stretch = [c for (c, _), w in zip(columns, widths) if w >= 250]
        if not stretch:
            return
        fixed = sum(w for w in widths if w < 250)
        room = max(120, event.width - fixed - 4)
        for c in stretch:
            tree.column(c, width=room // len(stretch))
    tree.bind("<Configure>", fit, add="+")
    return f, tree


def center(win, parent=None):
    win.update_idletasks()
    if parent is not None:
        x = parent.winfo_rootx() + (parent.winfo_width() - win.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - win.winfo_height()) // 3
    else:
        x = (win.winfo_screenwidth() - win.winfo_width()) // 2
        y = (win.winfo_screenheight() - win.winfo_height()) // 3
    win.geometry(f"+{max(x, 0)}+{max(y, 0)}")


def fix_calendar_arrows(cal):
    """The 'classic' theme draws 3D arrows with the background colour only:
    make the month/year buttons raised grey triangles instead of invisible ones.
    Also use nominative month names ("Октябрь", not "Октября") in the header."""
    from babel.dates import get_month_names
    from tkcalendar import DateEntry
    if isinstance(cal, DateEntry):  # DateEntry keeps its Calendar inside
        cal = cal._calendar
    try:
        cal._month_names = get_month_names("wide", context="stand-alone",
                                           locale=cal["locale"])
        cal._display_calendar()
    except Exception:  # noqa: BLE001 - only cosmetics, keep the default names
        pass
    prefix = cal._style_prefixe
    for side in "LR":
        name = f"{side}.{prefix}.TButton"
        cal.style.configure(name, relief="raised", background=BG, arrowcolor="black")
        cal.style.map(name, relief=[("active", "raised"), ("pressed", "sunken")],
                      background=[("active", BG)])


# ----------------------------------------------------------------------
# Icons drawn on a canvas (no image files needed)
# ----------------------------------------------------------------------

def draw_icon(c, kind, x=0, y=0):
    """32x32 message icons in the Win95 spirit: info, warning, error, question."""
    if kind == "warning":
        c.create_polygon(x + 16, y + 2, x + 31, y + 29, x + 1, y + 29,
                         fill="#ffff00", outline="black", width=1)
        c.create_rectangle(x + 15, y + 10, x + 17, y + 21, fill="black", outline="")
        c.create_rectangle(x + 15, y + 24, x + 17, y + 26, fill="black", outline="")
    elif kind == "error":
        c.create_oval(x + 3, y + 3, x + 31, y + 31, fill=DARK, outline="")  # shadow
        c.create_oval(x + 1, y + 1, x + 29, y + 29, fill="#ff0000", outline="#800000")
        c.create_line(x + 9, y + 9, x + 21, y + 21, fill=WHITE, width=3)
        c.create_line(x + 21, y + 9, x + 9, y + 21, fill=WHITE, width=3)
    else:  # info / question: white speech bubble
        c.create_oval(x + 3, y + 3, x + 31, y + 27, fill=DARK, outline="")
        c.create_oval(x + 1, y + 1, x + 29, y + 25, fill=WHITE, outline="black")
        c.create_polygon(x + 8, y + 21, x + 6, y + 31, x + 15, y + 24, fill=WHITE, outline="black")
        c.create_line(x + 9, y + 22, x + 14, y + 23, fill=WHITE, width=2)
        mark = "i" if kind == "info" else "?"
        c.create_text(x + 15, y + 13, text=mark, fill=NAVY, font=("Times New Roman", 15, "bold"))


# ----------------------------------------------------------------------
# Message box in Win95 style
# ----------------------------------------------------------------------

class MessageBox(tk.Toplevel):
    """buttons: list of (value, label); the first one is the default."""

    def __init__(self, parent, title, text, kind, buttons, cancel_value=None):
        super().__init__(parent)
        self.withdraw()
        self.title(title)
        self.configure(bg=BG)
        self.resizable(False, False)
        if parent is not None and parent.winfo_viewable():
            self.transient(parent)
        self.result = cancel_value
        body = tk.Frame(self, bg=BG, padx=12, pady=12)
        body.pack(fill="both", expand=True)
        icon = tk.Canvas(body, width=34, height=34, bg=BG, highlightthickness=0)
        icon.pack(side="left", anchor="n", padx=(0, 12))
        draw_icon(icon, kind)
        tk.Label(body, text=text, justify="left", anchor="w", wraplength=420
                 ).pack(side="left", fill="both", expand=True)
        bar = tk.Frame(self, bg=BG)
        bar.pack(pady=(0, 10))
        self.buttons = []
        for value, label in buttons:
            b = tk.Button(bar, text=label, width=10, command=lambda v=value: self._done(v))
            b.pack(side="left", padx=4)
            # the button with the keyboard focus shows the thick default frame
            b.bind("<FocusIn>", lambda e, b=b: self._mark(b))
            self.buttons.append(b)
        first = self.buttons[0]
        # Enter presses the button that has the focus (Tab / arrows move it), like Win95
        self.bind("<Return>", lambda e: self._focused().invoke())
        self.bind("<KP_Enter>", lambda e: self._focused().invoke())
        self.bind("<Left>", lambda e: self._move(-1))
        self.bind("<Right>", lambda e: self._move(1))
        self.bind("<Escape>", lambda e: self._done(cancel_value))
        self.protocol("WM_DELETE_WINDOW", lambda: self._done(cancel_value))
        self.deiconify()
        center(self, parent if parent is not None and parent.winfo_viewable() else None)
        self.lift()
        first.focus_set()
        self._mark(first)
        # a dialog that opened this box keeps its own modal grab afterwards
        self._old_grab = self.grab_current()
        self.grab_set()
        self.wait_window()

    def _focused(self):
        w = self.focus_get()
        return w if w in self.buttons else self.buttons[0]

    def _mark(self, button):
        for b in self.buttons:
            b.configure(default="active" if b is button else "normal")

    def _move(self, step):
        i = self.buttons.index(self._focused())
        b = self.buttons[(i + step) % len(self.buttons)]
        b.focus_set()

    def _done(self, value):
        self.result = value
        self.grab_release()
        self.destroy()
        old = self._old_grab
        if old is not None:
            try:
                if old.winfo_exists():
                    old.grab_set()
            except tk.TclError:
                pass


# ----------------------------------------------------------------------
# Splash screen
# ----------------------------------------------------------------------

def _mix(c1, c2, t):
    return "#%02x%02x%02x" % tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


class Splash(tk.Toplevel):
    """Small borderless start-up window in the Win95 boot-screen mood:
    sky with clouds, the program name in the middle and a running colour band."""

    W, H = 460, 270
    BAND = ((0, 0, 128), (0, 128, 255), (0, 200, 200), (255, 255, 255), (0, 128, 255))

    def __init__(self, master, title, subtitle, version, steps, icon=None, duration=2000,
                 on_done=None, footer=""):
        super().__init__(master)
        self.overrideredirect(True)
        self.configure(bg="black")
        try:
            self.attributes("-topmost", True)
        except tk.TclError:
            pass
        W, H = self.W, self.H
        x = (self.winfo_screenwidth() - W) // 2
        y = (self.winfo_screenheight() - H) // 3
        self.geometry(f"{W}x{H}+{x}+{y}")
        self.c = c = tk.Canvas(self, width=W, height=H, highlightthickness=0, bd=0, bg=BG)
        c.pack()
        self.steps, self.duration, self.on_done = steps, duration, on_done
        self.icon = icon
        sky_h = H - 40
        # sky: deep blue at the top to pale blue at the horizon
        for i in range(0, sky_h, 2):
            c.create_rectangle(0, i, W, i + 2, outline="",
                               fill=_mix((24, 72, 176), (150, 190, 238), i / sky_h))
        self._clouds(sky_h)
        # title block
        cx = W // 2
        if icon is not None:
            c.create_image(cx - 150, 96, image=icon)
        big = (FONT[0], 24, "bold italic")
        tx = cx - 108 if icon is not None else cx - 140
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1), (0, 2), (2, 2)):
            c.create_text(tx + dx, 86 + dy, text=title, anchor="w", fill=WHITE, font=big)
        c.create_text(tx, 86, text=title, anchor="w", fill=NAVY, font=big)
        c.create_text(tx + 2, 118, text=subtitle, anchor="w", fill="black",
                      font=(FONT[0], 11, "bold italic"))
        c.create_text(W - 9, 13, text=version, anchor="ne", fill="black", font=FONT_BOLD)
        c.create_text(W - 10, 12, text=version, anchor="ne", fill=WHITE, font=FONT_BOLD)
        # running band
        self.band_y = sky_h - 14
        self.cells = []
        step = 4
        for i in range(0, W, step):
            self.cells.append(c.create_rectangle(i, self.band_y, i + step, self.band_y + 10,
                                                 outline="", fill=NAVY))
        # status strip with a progress line
        c.create_rectangle(0, sky_h, W, H, fill=BG, outline="")
        c.create_line(0, sky_h, W, sky_h, fill=LIGHT)
        self.status = c.create_text(10, sky_h + 14, text=steps[0][1] if steps else "",
                                    anchor="w", fill="black", font=FONT)
        c.create_text(W - 10, sky_h + 14, text=footer, anchor="e", fill=DARK, font=FONT)
        c.create_line(10, H - 9, W - 10, H - 9, fill=DARK)
        c.create_line(10, H - 8, W - 10, H - 8, fill=LIGHT)
        self.bar = c.create_rectangle(10, H - 12, 10, H - 7, fill=NAVY, outline="")
        # 3D border
        c.create_rectangle(0, 0, W - 1, H - 1, outline="black")
        c.create_line(1, H - 2, 1, 1, W - 2, 1, fill=LIGHT)
        c.create_line(1, H - 2, W - 2, H - 2, W - 2, 1, fill=DARK)
        self.lift()
        self.update()
        self.start = time.monotonic()  # wall clock: exactly `duration` even if the app is busy
        self.after(30, self._tick)

    def _clouds(self, sky_h):
        import random
        rnd = random.Random(95)
        for _ in range(9):
            x = rnd.randint(-30, self.W - 150)
            y = rnd.choice((rnd.randint(18, 50), rnd.randint(140, sky_h - 40)))
            w = rnd.randint(60, 130)
            puffs = [(x + rnd.randint(0, w), y + rnd.randint(-6, 8), rnd.randint(14, 26))
                     for _ in range(7)]
            for px, py, r in puffs:  # bluish shade under every puff
                self.c.create_oval(px - r, py - r // 2 + 5, px + r, py + r // 2 + 9,
                                   fill="#c7d8ef", outline="")
            for px, py, r in puffs:
                self.c.create_oval(px - r, py - r // 2, px + r, py + r // 2,
                                   fill="#f4f8fd", outline="")

    def _tick(self):
        elapsed = time.monotonic() - self.start
        frac = min(1.0, elapsed * 1000 / self.duration)
        # colour band moving to the right
        n = len(self.BAND)
        shift = elapsed * 1.6
        for i, item in enumerate(self.cells):
            t = (i / len(self.cells) * 2 - shift) % 1.0 * n
            k = int(t)
            self.c.itemconfigure(item, fill=_mix(self.BAND[k % n], self.BAND[(k + 1) % n], t - k))
        self.c.coords(self.bar, 10, self.H - 12, 10 + (self.W - 20) * frac, self.H - 7)
        for at, text in self.steps:
            if frac >= at:
                self.c.itemconfigure(self.status, text=text)
        if frac >= 1.0:
            self.after(60, self._finish)
        else:
            self.after(30, self._tick)

    def _finish(self):
        self.destroy()
        if self.on_done:
            self.on_done()

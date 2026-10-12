"""Windows 95 look for tkinter: grey 3D widgets, navy selection, small sans font."""
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

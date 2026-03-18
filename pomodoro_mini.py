import json, os, sys, tkinter as tk
from datetime import datetime, timedelta

APP = "PomodoroMini"
CFG = os.path.join(os.path.expanduser("~"), ".pomodoromini.json")

def res(p):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, p)

def now(): return datetime.now()
def clamp(x, lo, hi):
    try: return max(lo, min(hi, int(x)))
    except: return lo
def mmss(s): s = max(0, s); return f"{s//60:02d}:{s%60:02d}"

def load():
    d = {}
    try:
        with open(CFG, encoding="utf-8") as f: d = json.load(f)
    except: pass
    s = d.get("s", {})
    t = d.get("t", {})
    return (
        {"focus": clamp(s.get("focus", 25), 1, 180),
         "break": clamp(s.get("break",  5), 1,  60),
         "auto":  bool(s.get("auto",  True)),
         "sound": bool(s.get("sound", True)),
         "top":   bool(s.get("top",   True)),
         "geo":   str(s.get("geo", "120x55+50+50"))},
        {"phase":   t.get("phase",   "FOCUS") if t.get("phase") in ("FOCUS","BREAK") else "FOCUS",
         "running": bool(t.get("running", False)),
         "end":     t.get("end")}
    )

def save(s, t):
    try:
        with open(CFG, "w", encoding="utf-8") as f:
            json.dump({"s": s, "t": t}, f, ensure_ascii=False, indent=2)
    except: pass

def beep(root):
    try:
        if sys.platform.startswith("win"):
            import winsound; winsound.MessageBeep(winsound.MB_ICONASTERISK)
        elif root: root.bell()
    except: pass

def parse_end(v):
    try: return datetime.fromisoformat(v)
    except: return None


class App:
    BG_F = "#1e1e1e"; BG_B = "#1b2a1f"; BG_FL = "#3b3b3b"; BG_BTN = "#2b2b2b"

    def __init__(self):
        self.s, self.t = load()
        self.root = r = tk.Tk()
        r.title(APP)

        # Windows AppID
        if sys.platform.startswith("win"):
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"local.{APP}.1")
            except: pass

        # Icon
        ico = res("pomodoro.ico")
        if os.path.exists(ico):
            try: r.iconbitmap(default=ico)
            except: pass

        r.overrideredirect(True)
        r.geometry(self.s["geo"])
        r.attributes("-topmost", self.s["top"])
        r.resizable(False, False)

        # Taskbar visibility on Windows
        if sys.platform.startswith("win"):
            def _show():
                try:
                    import ctypes
                    hwnd = ctypes.windll.user32.GetParent(r.winfo_id())
                    style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
                    ctypes.windll.user32.SetWindowLongW(hwnd, -20, (style & ~0x80) | 0x40000)
                    r.wm_withdraw(); r.after(10, r.wm_deiconify)
                except: pass
            r.after(100, _show)

        # Drag
        self._drag = None
        r.bind("<ButtonPress-1>", lambda e: setattr(self, "_drag", (e.x_root, e.y_root, r.winfo_x(), r.winfo_y())))
        r.bind("<B1-Motion>", self._move)

        # UI
        self.pv = tk.StringVar(value=self.t["phase"])
        self.tv = tk.StringVar(value="25:00")
        tk.Label(r, textvariable=self.pv,  fg="#d0d0d0", bg=self.BG_F, font=("Segoe UI", 7, "bold")).pack()
        self.tl = tk.Label(r, textvariable=self.tv, fg="white", bg=self.BG_F, font=("Consolas", 18, "bold"))
        self.tl.pack()

        bf = tk.Frame(r, bg=self.BG_F); bf.pack(fill="both", expand=True)
        for i in range(4): bf.grid_columnconfigure(i, weight=1, uniform="c")
        bf.grid_rowconfigure(0, weight=1)

        def btn(t, cmd): return tk.Button(bf, text=t, command=cmd, font=("Segoe UI",7,"bold"),
            width=1, relief="flat", bg=self.BG_BTN, fg="white",
            activebackground="#444", activeforeground="white", bd=0, highlightthickness=0)

        self.bs = btn("▶", self.toggle); self.bs.grid(row=0, column=0, sticky="nsew")
        btn("⟲", self.reset)          .grid(row=0, column=1, sticky="nsew")
        btn("≫", self.skip)            .grid(row=0, column=2, sticky="nsew")
        self.bsnd = btn("🔊" if self.s["sound"] else "🔇", self.toggle_sound)
        self.bsnd.grid(row=0, column=3, sticky="nsew")

        lc = tk.Label(r, text="✕", font=("Segoe UI",6), bg=self.BG_F, fg="#666", cursor="hand2")
        lc.place(relx=1.0, x=-2, y=0, anchor="ne")
        lc.bind("<Button-1>", lambda e: self.quit())

        # Context menu
        m = tk.Menu(r, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#444")
        m.add_command(label="Start / Pause", command=self.toggle)
        m.add_command(label="Reset",         command=self.reset)
        m.add_command(label="Toggle Sound",  command=self.toggle_sound)
        m.add_separator()
        m.add_command(label="Quit",          command=self.quit)
        r.bind("<Button-3>", lambda e: (m.tk_popup(e.x_root, e.y_root), m.grab_release()))

        self._widgets = [self.tl, bf, lc]  # for theme updates
        self.bf = bf
        self._theme(); self._sync(); self._updbtn(); self._tick()

    # ── helpers ──
    def _secs(self, ph=None):
        ph = ph or self.t["phase"]
        return self.s["focus" if ph == "FOCUS" else "break"] * 60

    def _bg(self): return self.BG_F if self.t["phase"] == "FOCUS" else self.BG_B

    def _theme(self, bg=None):
        bg = bg or self._bg()
        for w in [self.root, self.tl, self.bf] + [c for c in self.root.winfo_children()
                  if isinstance(c, (tk.Label, tk.Frame))]:
            try: w.configure(bg=bg)
            except: pass

    def _move(self, e):
        if not self._drag: return
        x0, y0, wx, wy = self._drag
        self.root.geometry(f"+{wx+e.x_root-x0}+{wy+e.y_root-y0}")
        self.s["geo"] = self.root.winfo_geometry(); save(self.s, self.t)

    def _flash(self):
        self._theme(self.BG_FL)
        self.root.after(220, self._theme)

    def _sync(self):
        end = self.t.get("end", "")
        if isinstance(end, str) and end.startswith("PAUSED:"):
            self.tv.set(mmss(int(end.split(":",1)[1])))
        elif self.t["running"] and end:
            e = parse_end(end)
            sec = int((e - now()).total_seconds()) if e else self._secs()
            self.tv.set(mmss(sec))
        else:
            self.tv.set(mmss(self._secs()))

    def _updbtn(self):
        end = self.t.get("end", "")
        paused = isinstance(end, str) and end.startswith("PAUSED:")
        self.bs.configure(text="▶" if (paused or not self.t["running"]) else "⏸")

    def _start(self, ph):
        self.t["phase"] = ph; self.t["running"] = True
        self.t["end"] = (now() + timedelta(seconds=self._secs(ph))).isoformat()
        self.pv.set(ph); self._theme(); save(self.s, self.t); self._updbtn()

    # ── actions ──
    def toggle(self):
        end = self.t.get("end", "")
        if isinstance(end, str) and end.startswith("PAUSED:"):
            sec = int(end.split(":",1)[1])
            self.t["running"] = True
            self.t["end"] = (now() + timedelta(seconds=sec)).isoformat()
        elif self.t["running"] and end:
            e = parse_end(end)
            rem = max(0, int((e - now()).total_seconds())) if e else 0
            self.t["running"] = False; self.t["end"] = f"PAUSED:{rem}"
        else:
            self._start(self.t["phase"]); return
        save(self.s, self.t); self._updbtn()

    def reset(self):
        self.t = {"phase": "FOCUS", "running": False, "end": None}
        save(self.s, self.t); self.pv.set("FOCUS"); self._theme(); self._sync(); self._updbtn()

    def skip(self):
        nxt = "BREAK" if self.t["phase"] == "FOCUS" else "FOCUS"
        beep(self.root); self._flash(); self._start(nxt)

    def toggle_sound(self):
        self.s["sound"] = not self.s["sound"]
        self.bsnd.configure(text="🔊" if self.s["sound"] else "🔇")
        save(self.s, self.t)

    def quit(self):
        try: self.s["geo"] = self.root.winfo_geometry()
        except: pass
        save(self.s, self.t); self.root.destroy()

    # ── tick ──
    def _tick(self):
        end = self.t.get("end", "")
        if isinstance(end, str) and end.startswith("PAUSED:"):
            self.tv.set(mmss(int(end.split(":",1)[1])))
        elif self.t["running"] and end:
            e = parse_end(end)
            sec = int((e - now()).total_seconds()) if e else 0
            if sec <= 0:
                self.tv.set("00:00"); beep(self.root); self._flash()
                nxt = "BREAK" if self.t["phase"] == "FOCUS" else "FOCUS"
                self._start(nxt)
            else:
                self.tv.set(mmss(sec))
        self.root.after(200, self._tick)

    def run(self): self.root.mainloop()


if __name__ == "__main__":
    App().run()

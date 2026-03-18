import json
import os
import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
import tkinter as tk
# Tray depends removed per user request
APP_NAME = "PomodoroMini"
CONFIG_PATH = os.path.join(os.path.expanduser("~"), f".{APP_NAME.lower()}_config.json")
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)
def now_ts():
    return datetime.now()
def clamp_int(x, lo, hi):
    try:
        x = int(x)
    except Exception:
        x = lo
    return max(lo, min(hi, x))
def parse_end_time(iso_str: str | None):
    if not iso_str:
        return None
    try:
        return datetime.fromisoformat(iso_str)
    except Exception:
        return None
def fmt_mmss(seconds: int) -> str:
    seconds = max(0, seconds)
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"
def beep(root: tk.Tk | None):
    try:
        if sys.platform.startswith("win"):
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        elif root is not None:
            root.bell()
    except Exception:
        pass
@dataclass
class Settings:
    focus_min: int = 25
    break_min: int = 5
    auto_advance: bool = True
    sound: bool = True
    topmost: bool = True
    # ★横長のサイズ、少し小さく調整 (120x55)
    geometry: str = "120x55+50+50"
@dataclass
class State:
    phase: str = "FOCUS"          # FOCUS / BREAK
    running: bool = False
    end_time: str | None = None   # ISO or "PAUSED:<sec>"
def load_config() -> tuple[Settings, State]:
    s = Settings()
    st = State()
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            s_data = data.get("settings", {})
            st_data = data.get("state", {})
            s.focus_min = clamp_int(s_data.get("focus_min", s.focus_min), 1, 180)
            s.break_min = clamp_int(s_data.get("break_min", s.break_min), 1, 60)
            s.auto_advance = bool(s_data.get("auto_advance", s.auto_advance))
            s.sound = bool(s_data.get("sound", s.sound))
            s.topmost = bool(s_data.get("topmost", s.topmost))
            s.geometry = str(s_data.get("geometry", s.geometry))
            st.phase = st_data.get("phase", st.phase) if st_data.get("phase") in ("FOCUS", "BREAK") else st.phase
            st.running = bool(st_data.get("running", st.running))
            st.end_time = st_data.get("end_time", st.end_time)
        except Exception:
            pass
    return s, st
def save_config(settings: Settings, state: State):
    data = {
        "settings": {
            "focus_min": settings.focus_min,
            "break_min": settings.break_min,
            "auto_advance": settings.auto_advance,
            "sound": settings.sound,
            "topmost": settings.topmost,
            "geometry": settings.geometry,
        },
        "state": {
            "phase": state.phase,
            "running": state.running,
            "end_time": state.end_time,
        },
    }
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
class PomodoroMini:
    def __init__(self):
        self.settings, self.state = load_config()
        self.root = tk.Tk()
        self.root.title(APP_NAME)

        # Windowsのタスクバー分離とアイコン設定
        if sys.platform.startswith("win"):
            try:
                import ctypes
                myappid = f"local.pomodoromini.{APP_NAME}.1"
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except Exception:
                pass

        icon_path = resource_path("apple.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(default=icon_path)
            except Exception:
                pass
        # 枠線・タイトルバーを完全に消して余白をゼロにする
        self.root.overrideredirect(True)
        self.root.geometry(self.settings.geometry)
        # overrideredirect(True)にするとタスクバーから消えるため、Windows APIでタスクバーに強制表示させる
        if sys.platform.startswith("win"):
            def set_appwindow():
                try:
                    import ctypes
                    hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
                    style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
                    style = style & ~0x00000080
                    style = style | 0x00040000
                    ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
                    self.root.wm_withdraw()
                    self.root.after(10, self.root.wm_deiconify)
                except Exception:
                    pass
            self.root.after(100, set_appwindow)
        # ウィンドウサイズを強制で固定するための追加設定
        self.root.pack_propagate(False)
        self.root.grid_propagate(False)
        self.root.update_idletasks()
        self.root.minsize(0, 0)
        self.root.resizable(False, False)
        # さらにこれで強制固定
        self.root.geometry(self.settings.geometry)
        self.root.attributes("-topmost", True if self.settings.topmost else False)
        # ドラッグ移動 (タイトルバーがないため全体でドラッグ可能にする)
        self._drag_start = None
        self.root.bind("<ButtonPress-1>", self._on_drag_start)
        self.root.bind("<B1-Motion>", self._on_drag_move)
        # 右クリックメニューの作成
        self._create_context_menu()
        self.root.bind("<Button-3>", self._show_context_menu)
        # Theme
        self.bg_focus = "#1e1e1e"
        self.bg_break = "#1b2a1f"
        self.flash_bg = "#3b3b3b"
        self.btn_bg = "#2b2b2b"
        self.btn_bg_active = "#444444"
        # ===== UI (Square layout) =====
        self.phase_var = tk.StringVar(value=self.state.phase)
        self.time_var = tk.StringVar(value="25:00")
        self.phase_label = tk.Label(
            self.root, textvariable=self.phase_var,
            fg="#d0d0d0", bg=self.bg_focus,
            font=("Segoe UI", 7, "bold"),
            padx=0, pady=0, bd=0
        )
        self.phase_label.pack(pady=0)
        self.time_label = tk.Label(
            self.root, textvariable=self.time_var,
            fg="white", bg=self.bg_focus,
            font=("Consolas", 18, "bold"),
            padx=0, pady=0, bd=0
        )
        self.time_label.pack(pady=0)
        # Buttons frame
        self.btn_frame = tk.Frame(self.root, bg=self.bg_focus)
        self.btn_frame.pack(pady=0, fill="both", expand=True)
        self.btn_frame.grid_columnconfigure(0, weight=1, uniform="c")
        self.btn_frame.grid_columnconfigure(1, weight=1, uniform="c")
        self.btn_frame.grid_columnconfigure(2, weight=1, uniform="c")
        self.btn_frame.grid_columnconfigure(3, weight=1, uniform="c")
        self.btn_frame.grid_rowconfigure(0, weight=1)
        def mk_btn(text, cmd):
            return tk.Button(
                self.btn_frame, text=text, command=cmd,
                font=("Segoe UI", 7, "bold"),
                width=1,
                padx=0, pady=0,
                relief="flat",
                bg=self.btn_bg, fg="white",
                activebackground=self.btn_bg_active, activeforeground="white",
                bd=0, highlightthickness=0
            )
        self.btn_start = mk_btn("▶", self.toggle_start_pause)
        self.btn_reset = mk_btn("⟲", self.reset)
        self.btn_skip  = mk_btn("≫", self.skip_phase)
        self.btn_sound = mk_btn("🔊" if self.settings.sound else "🔇", self.toggle_sound)
        self.btn_start.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.btn_reset.grid(row=0, column=1, padx=0, pady=0, sticky="nsew")
        self.btn_skip .grid(row=0, column=2, padx=0, pady=0, sticky="nsew")
        self.btn_sound.grid(row=0, column=3, padx=0, pady=0, sticky="nsew")
        # 右上の極小の閉じるボタン (x) をラベルとして追加
        self.lbl_close = tk.Label(self.root, text="✕", font=("Segoe UI", 6), bg=self.bg_focus, fg="#666666", cursor="hand2")
        self.lbl_close.place(relx=1.0, x=-2, y=0, anchor="ne")
        self.lbl_close.bind("<Button-1>", lambda e: self.quit_app())
        self._apply_phase_theme()
        self._sync_display_from_state()
        self._update_buttons()
        # Tick
        self._tick()
    # ===== Dragging =====
    def _on_drag_start(self, e):
        self._drag_start = (e.x_root, e.y_root, self.root.winfo_x(), self.root.winfo_y())
    def _on_drag_move(self, e):
        if not self._drag_start:
            return
        x0, y0, wx0, wy0 = self._drag_start
        dx = e.x_root - x0
        dy = e.y_root - y0
        self.root.geometry(f"+{wx0 + dx}+{wy0 + dy}")
        self._save_geometry()
    def _save_geometry(self):
        try:
            self.settings.geometry = self.root.winfo_geometry()
            save_config(self.settings, self.state)
        except Exception:
            pass
    # ===== Context Menu =====
    def _create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#444444")
        self.context_menu.add_command(label="Start / Pause", command=self.toggle_start_pause)
        self.context_menu.add_command(label="Reset", command=self.reset)
        self.context_menu.add_command(label="Toggle Sound", command=self.toggle_sound)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Quit", command=self.quit_app)
    def _show_context_menu(self, e):
        try:
            self.context_menu.tk_popup(e.x_root, e.y_root)
        finally:
            self.context_menu.grab_release()
    # ===== Settings toggles =====
    def toggle_sound(self):
        self.settings.sound = not self.settings.sound
        self.btn_sound.configure(text="🔊" if self.settings.sound else "🔇")
        save_config(self.settings, self.state)
    # ===== Timer core =====
    def _phase_seconds(self, phase: str) -> int:
        return (self.settings.focus_min if phase == "FOCUS" else self.settings.break_min) * 60
    def _apply_phase_theme(self):
        bg = self.bg_focus if self.state.phase == "FOCUS" else self.bg_break
        self.root.configure(bg=bg)
        self.phase_label.configure(bg=bg)
        self.time_label.configure(bg=bg)
        self.btn_frame.configure(bg=bg)
        self.lbl_close.configure(bg=bg)
    def _notify_phase_change(self):
        if self.settings.sound:
            beep(self.root)
        # flash briefly
        self.root.configure(bg=self.flash_bg)
        self.phase_label.configure(bg=self.flash_bg)
        self.time_label.configure(bg=self.flash_bg)
        self.btn_frame.configure(bg=self.flash_bg)
        self.lbl_close.configure(bg=self.flash_bg)
        def restore():
            self._apply_phase_theme()
        self.root.after(220, restore)
    def _start_phase(self, phase: str):
        self.state.phase = phase
        self.phase_var.set(phase)
        self._apply_phase_theme()
        self.state.running = True
        end = now_ts() + timedelta(seconds=self._phase_seconds(phase))
        self.state.end_time = end.isoformat()
        save_config(self.settings, self.state)
        self._update_buttons()
    def toggle_start_pause(self):
        # Start if stopped
        if not self.state.end_time and not self.state.running:
            self._start_phase(self.state.phase)
            return
        # Resume if paused
        if isinstance(self.state.end_time, str) and self.state.end_time.startswith("PAUSED:"):
            sec = int(self.state.end_time.split(":", 1)[1])
            self.state.running = True
            self.state.end_time = (now_ts() + timedelta(seconds=sec)).isoformat()
            save_config(self.settings, self.state)
            self._update_buttons()
            return
        # Pause if running
        if self.state.running and self.state.end_time:
            end = parse_end_time(self.state.end_time)
            remaining = int((end - now_ts()).total_seconds()) if end else 0
            remaining = max(0, remaining)
            self.state.running = False
            self.state.end_time = f"PAUSED:{remaining}"
            save_config(self.settings, self.state)
            self._update_buttons()
            return
        # Fallback: start fresh
        self._start_phase(self.state.phase)
    def reset(self):
        self.state.phase = "FOCUS"
        self.state.running = False
        self.state.end_time = None
        save_config(self.settings, self.state)
        self.phase_var.set("FOCUS")
        self._apply_phase_theme()
        self._sync_display_from_state()
        self._update_buttons()
    def skip_phase(self):
        nxt = "BREAK" if self.state.phase == "FOCUS" else "FOCUS"
        self._notify_phase_change()
        # 仕様：即移行
        self._start_phase(nxt)
    def _sync_display_from_state(self):
        if isinstance(self.state.end_time, str) and self.state.end_time.startswith("PAUSED:"):
            sec = int(self.state.end_time.split(":", 1)[1])
            self.time_var.set(fmt_mmss(sec))
        elif self.state.running and self.state.end_time:
            end = parse_end_time(self.state.end_time)
            sec = int((end - now_ts()).total_seconds()) if end else self._phase_seconds(self.state.phase)
            self.time_var.set(fmt_mmss(sec))
        else:
            self.time_var.set(fmt_mmss(self._phase_seconds(self.state.phase)))
    def _update_buttons(self):
        # ▶/⏸ only (no text)
        if isinstance(self.state.end_time, str) and self.state.end_time.startswith("PAUSED:"):
            self.btn_start.configure(text="▶")
        else:
            self.btn_start.configure(text="⏸" if self.state.running else "▶")
    def _tick(self):
        if isinstance(self.state.end_time, str) and self.state.end_time.startswith("PAUSED:"):
            sec = int(self.state.end_time.split(":", 1)[1])
            self.time_var.set(fmt_mmss(sec))
        elif self.state.running and self.state.end_time:
            end = parse_end_time(self.state.end_time)
            sec = int((end - now_ts()).total_seconds()) if end else 0
            if sec <= 0:
                self.time_var.set("00:00")
                self._notify_phase_change()
                nxt = "BREAK" if self.state.phase == "FOCUS" else "FOCUS"
                self._start_phase(nxt)
            else:
                self.time_var.set(fmt_mmss(sec))
        self.root.after(200, self._tick)
    # ===== Quit =====
    def quit_app(self):
        try:
            self.settings.geometry = self.root.winfo_geometry()
        except Exception:
            pass
        save_config(self.settings, self.state)
        self.root.destroy()
    def run(self):
        self.root.mainloop()
if __name__ == "__main__":
    app = PomodoroMini()
    app.run()

import tkinter as tk
from tkinter import font as tkfont
import random
import ctypes
import json
import os
import sys

# ── Resolve paths relative to the exe / script ──
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "settings.json")

# ── Default config ──
DEFAULTS = {
    "countdown_seconds":    90,
    "auto_restart_seconds": 1,
    "remind_show_seconds":  5,
    "opacity":              0.35,
    "messages": [
        "🌟 Nghỉ ngơi chút nha! 🌟",
        "💖 Uống nước đi bạn ơi~ 💖",
        "🍵 Hít thở sâu nào~ 🍵",
        "✨ Giỏi lắm, nghỉ tí nha! ✨",
        "🌈 Duỗi người 1 cái~ 🌈",
    ],
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # merge with defaults for any missing keys
            for k, v in DEFAULTS.items():
                data.setdefault(k, v)
            return data
        except Exception:
            pass
    return dict(DEFAULTS)


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ── Sizes ──
FULL_W, FULL_H = 320, 460
MINI_SCALE     = 0.35
MINI_W         = int(FULL_W * MINI_SCALE)
MINI_H         = int(FULL_H * MINI_SCALE)

# ── Colours ──
BG          = "#1a1a2e"
BG_DARK     = "#16213e"
ACCENT      = "#e94560"
ACCENT_GLOW = "#ff6b81"
TEXT        = "#edf2f4"
TEXT_DIM    = "#8d99ae"
RING_BG     = "#2b2d42"
SUCCESS     = "#00e396"
MINI_BTN    = "#0f3460"


# ═══════════════════════════════════════════════════════
#  SETTINGS DIALOG
# ═══════════════════════════════════════════════════════
class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, cfg, on_save):
        super().__init__(parent)
        self.parent   = parent
        self.cfg      = cfg
        self.on_save  = on_save

        self.title("⚙ Cài đặt")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.grab_set()

        w, h = 380, 540
        sx = parent.winfo_x() - w - 10
        sy = parent.winfo_y()
        if sx < 0:
            sx = parent.winfo_x() + parent.winfo_width() + 10
        self.geometry(f"{w}x{h}+{sx}+{sy}")

        lbl_font = tkfont.Font(family="Segoe UI", size=10)
        entry_font = tkfont.Font(family="Consolas", size=11)
        btn_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        head_font = tkfont.Font(family="Segoe UI Emoji", size=13, weight="bold")

        # Title
        tk.Label(self, text="⚙ Cài Đặt", font=head_font,
                 bg=BG, fg=ACCENT_GLOW).pack(pady=(14, 10))

        # ── Countdown duration ──
        f1 = tk.Frame(self, bg=BG)
        f1.pack(fill="x", padx=20, pady=4)
        tk.Label(f1, text="⏱ Thời gian đếm ngược (giây):",
                 font=lbl_font, bg=BG, fg=TEXT).pack(anchor="w")
        self.countdown_var = tk.StringVar(value=str(cfg["countdown_seconds"]))
        tk.Entry(f1, textvariable=self.countdown_var, font=entry_font,
                 bg=BG_DARK, fg=TEXT, insertbackground=TEXT,
                 bd=0, relief="flat").pack(fill="x", ipady=4, pady=(2, 0))

        # ── Auto restart delay ──
        f2 = tk.Frame(self, bg=BG)
        f2.pack(fill="x", padx=20, pady=4)
        tk.Label(f2, text="🔄 Auto-restart sau (giây):",
                 font=lbl_font, bg=BG, fg=TEXT).pack(anchor="w")
        self.restart_var = tk.StringVar(value=str(cfg["auto_restart_seconds"]))
        tk.Entry(f2, textvariable=self.restart_var, font=entry_font,
                 bg=BG_DARK, fg=TEXT, insertbackground=TEXT,
                 bd=0, relief="flat").pack(fill="x", ipady=4, pady=(2, 0))

        # ── Remind show duration ──
        f3 = tk.Frame(self, bg=BG)
        f3.pack(fill="x", padx=20, pady=4)
        tk.Label(f3, text="📢 Hiện nhắc nhở (giây, khi minimize):",
                 font=lbl_font, bg=BG, fg=TEXT).pack(anchor="w")
        self.remind_var = tk.StringVar(value=str(cfg["remind_show_seconds"]))
        tk.Entry(f3, textvariable=self.remind_var, font=entry_font,
                 bg=BG_DARK, fg=TEXT, insertbackground=TEXT,
                 bd=0, relief="flat").pack(fill="x", ipady=4, pady=(2, 0))

        # ── Opacity ──
        f_op = tk.Frame(self, bg=BG)
        f_op.pack(fill="x", padx=20, pady=4)
        self.opacity_val = tk.DoubleVar(value=cfg.get("opacity", 0.35))
        op_label_frame = tk.Frame(f_op, bg=BG)
        op_label_frame.pack(fill="x")
        tk.Label(op_label_frame, text="👻 Độ mờ khi nhắc nhở (minimize):",
                 font=lbl_font, bg=BG, fg=TEXT).pack(side="left")
        self.opacity_display = tk.Label(op_label_frame,
                 text=f"{self.opacity_val.get():.2f}",
                 font=lbl_font, bg=BG, fg=ACCENT_GLOW)
        self.opacity_display.pack(side="right")
        self.opacity_scale = tk.Scale(f_op, from_=0.05, to=1.0,
                 resolution=0.05, orient="horizontal",
                 variable=self.opacity_val,
                 bg=BG_DARK, fg=TEXT, troughcolor=RING_BG,
                 highlightthickness=0, bd=0, sliderlength=18,
                 showvalue=False, length=320,
                 command=self._update_opacity_label)
        self.opacity_scale.pack(fill="x", pady=(2, 0))

        # ── Messages ──
        f4 = tk.Frame(self, bg=BG)
        f4.pack(fill="x", padx=20, pady=4)
        tk.Label(f4, text="💬 Tin nhắn nhắc nhở (mỗi dòng 1 tin):",
                 font=lbl_font, bg=BG, fg=TEXT).pack(anchor="w")
        self.msg_text = tk.Text(f4, font=entry_font, bg=BG_DARK, fg=TEXT,
                                insertbackground=TEXT, bd=0, relief="flat",
                                height=6, wrap="word")
        self.msg_text.pack(fill="x", pady=(2, 0))
        self.msg_text.insert("1.0", "\n".join(cfg["messages"]))

        # ── Buttons ──
        bf = tk.Frame(self, bg=BG)
        bf.pack(pady=(14, 10))

        tk.Button(bf, text="💾  Lưu", font=btn_font,
                  bg=SUCCESS, fg=BG, activebackground="#2ecc71",
                  bd=0, padx=20, pady=6, cursor="hand2",
                  command=self._save).pack(side="left", padx=6)

        tk.Button(bf, text="✖  Hủy", font=btn_font,
                  bg=RING_BG, fg=TEXT_DIM, activebackground=BG_DARK,
                  bd=0, padx=20, pady=6, cursor="hand2",
                  command=self.destroy).pack(side="left", padx=6)

    def _update_opacity_label(self, val):
        self.opacity_display.config(text=f"{float(val):.2f}")

    def _save(self):
        try:
            cd = max(1, int(self.countdown_var.get()))
        except ValueError:
            cd = self.cfg["countdown_seconds"]
        try:
            ar = max(1, int(self.restart_var.get()))
        except ValueError:
            ar = self.cfg["auto_restart_seconds"]
        try:
            rs = max(1, int(self.remind_var.get()))
        except ValueError:
            rs = self.cfg["remind_show_seconds"]

        opacity = max(0.05, min(1.0, self.opacity_val.get()))

        raw = self.msg_text.get("1.0", "end").strip()
        msgs = [m.strip() for m in raw.split("\n") if m.strip()]
        if not msgs:
            msgs = list(DEFAULTS["messages"])

        new_cfg = {
            "countdown_seconds":    cd,
            "auto_restart_seconds": ar,
            "remind_show_seconds":  rs,
            "opacity":              opacity,
            "messages":             msgs,
        }
        save_config(new_cfg)
        self.on_save(new_cfg)
        self.destroy()


# ═══════════════════════════════════════════════════════
#  MAIN APP
# ═══════════════════════════════════════════════════════
class CountdownApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # load config
        self.cfg = load_config()

        # ── Window setup ──
        self.title("⏰ Countdown Timer")
        self.configure(bg=BG)
        self.attributes("-topmost", True)
        self.resizable(False, False)

        # ── Geometry helpers ──
        self.scr_w = self.winfo_screenwidth()
        self.scr_h = self.winfo_screenheight()

        self.is_mini = False
        self._set_geometry(FULL_W, FULL_H)

        # ── Fonts ──
        self._build_fonts("full")

        # ── State ──
        self.remaining       = self.cfg["countdown_seconds"]
        self.running         = False
        self.after_id        = None
        self.pulse_phase     = 0
        self.auto_restart_id = None
        self.remind_hide_id  = None
        self.was_minimized   = False

        self._build_ui()

        # ── Cache the Win32 HWND ──
        self.update_idletasks()
        self._hwnd = ctypes.windll.user32.GetParent(self.winfo_id())

        # auto-start
        self.after(300, self._start)

    # ── apply config changes from settings ──
    def _apply_config(self, new_cfg):
        self.cfg = new_cfg
        was_running = self.running
        self._reset()
        self.remaining = self.cfg["countdown_seconds"]
        self._draw_ring()
        if was_running:
            self.after(200, self._start)

    # ────────────────────── FONTS ──────────────────────
    def _build_fonts(self, mode):
        if mode == "mini":
            self.title_font = tkfont.Font(family="Segoe UI Emoji", size=7,  weight="bold")
            self.time_font  = tkfont.Font(family="Consolas",        size=14, weight="bold")
            self.label_font = tkfont.Font(family="Segoe UI",        size=6)
            self.btn_font   = tkfont.Font(family="Segoe UI",        size=7,  weight="bold")
            self.msg_font   = tkfont.Font(family="Segoe UI Emoji",  size=8,  weight="bold")
        else:
            self.title_font = tkfont.Font(family="Segoe UI Emoji", size=13, weight="bold")
            self.time_font  = tkfont.Font(family="Consolas",        size=36, weight="bold")
            self.label_font = tkfont.Font(family="Segoe UI",        size=10)
            self.btn_font   = tkfont.Font(family="Segoe UI",        size=11, weight="bold")
            self.msg_font   = tkfont.Font(family="Segoe UI Emoji",  size=14, weight="bold")

    # ────────────────────── GEOMETRY ──────────────────────
    def _set_geometry(self, w, h):
        x = self.scr_w - w - 20
        y = self.scr_h - h - 60
        self.geometry(f"{w}x{h}+{x}+{y}")

    # ────────────────────── UI ──────────────────────
    def _build_ui(self):
        # Top bar with title + gear
        self._top_frame = tk.Frame(self, bg=BG)
        self._top_frame.pack(fill="x", padx=10, pady=(10, 0))

        self.title_lbl = tk.Label(self._top_frame, text="🌸 Nhắc Nhở 🌸",
                                  font=self.title_font, bg=BG, fg=ACCENT_GLOW)
        self.title_lbl.pack(side="left", expand=True)

        self.gear_btn = tk.Button(self._top_frame, text="⚙", font=self.btn_font,
                                  bg=BG, fg=TEXT_DIM, activebackground=BG_DARK,
                                  activeforeground=TEXT, bd=0, padx=6, pady=0,
                                  cursor="hand2", command=self._open_settings)
        self.gear_btn.pack(side="right")

        # Canvas
        self.canvas_size = 220
        self.canvas = tk.Canvas(self, width=self.canvas_size,
                                height=self.canvas_size,
                                bg=BG, highlightthickness=0)
        self.canvas.pack(pady=6)
        self._draw_ring()

        # State label
        self.state_label = tk.Label(self, text="Sẵn sàng đếm ngược ✨",
                                    font=self.label_font, bg=BG, fg=TEXT_DIM)
        self.state_label.pack()

        # Message
        self.msg_label = tk.Label(self, text="", font=self.msg_font,
                                  bg=BG, fg=SUCCESS, wraplength=280)
        self.msg_label.pack(pady=4)

        # Buttons
        self._btn_frame = tk.Frame(self, bg=BG)
        self._btn_frame.pack(pady=(4, 6))

        self.start_btn = tk.Button(self._btn_frame, text="▶  Bắt Đầu", font=self.btn_font,
                                   bg=ACCENT, fg=TEXT, activebackground=ACCENT_GLOW,
                                   activeforeground=TEXT, bd=0, padx=16, pady=5,
                                   cursor="hand2", command=self._toggle)
        self.start_btn.pack(side="left", padx=4)

        self.reset_btn = tk.Button(self._btn_frame, text="↻  Reset", font=self.btn_font,
                                   bg=RING_BG, fg=TEXT_DIM, activebackground=BG_DARK,
                                   activeforeground=TEXT, bd=0, padx=16, pady=5,
                                   cursor="hand2", command=self._reset)
        self.reset_btn.pack(side="left", padx=4)

        # Mini toggle
        self._mini_frame = tk.Frame(self, bg=BG)
        self._mini_frame.pack(pady=(0, 10))

        self.mini_btn = tk.Button(self._mini_frame, text="🔽 Thu Nhỏ", font=self.btn_font,
                                  bg=MINI_BTN, fg=TEXT, activebackground="#1a5276",
                                  activeforeground=TEXT, bd=0, padx=16, pady=5,
                                  cursor="hand2", command=self._toggle_mini)
        self.mini_btn.pack()

    def _open_settings(self):
        SettingsDialog(self, self.cfg, self._apply_config)

    # ────────────────────── MINI / EXPAND ──────────────────────
    def _toggle_mini(self):
        if self.is_mini:
            self._expand()
        else:
            self._shrink()

    def _shrink(self):
        self.is_mini = True
        self._build_fonts("mini")
        self._apply_fonts()

        cs = int(self.canvas_size * MINI_SCALE)
        self.canvas.config(width=cs, height=cs)

        # Forget everything first
        self._top_frame.pack_forget()
        self.canvas.pack_forget()
        self.state_label.pack_forget()
        self.msg_label.pack_forget()
        self._btn_frame.pack_forget()
        self._mini_frame.pack_forget()

        # Re-pack only canvas + expand button
        self.canvas.pack(pady=2)
        self.mini_btn.config(text="🔼 Mở")
        self._mini_frame.pack(pady=(0, 2))

        self._set_geometry(MINI_W, MINI_H)
        self._draw_ring()

    def _expand(self):
        self.is_mini = False
        self._build_fonts("full")
        self._apply_fonts()

        self.canvas.config(width=self.canvas_size, height=self.canvas_size)

        # Forget everything first
        self.canvas.pack_forget()
        self._mini_frame.pack_forget()

        # Re-pack all widgets in correct order
        self.title_lbl.pack(side="left", expand=True, in_=self._top_frame)
        self.gear_btn.pack(side="right", in_=self._top_frame)
        self._top_frame.pack(fill="x", padx=10, pady=(10, 0))

        self.canvas.pack(pady=6)

        self.state_label.pack()

        self.msg_label.config(wraplength=280)
        self.msg_label.pack(pady=4)

        self.start_btn.pack(side="left", padx=4, in_=self._btn_frame)
        self.reset_btn.pack(side="left", padx=4, in_=self._btn_frame)
        self._btn_frame.pack(pady=(4, 6))

        self.mini_btn.config(text="🔽 Thu Nhỏ")
        self._mini_frame.pack(pady=(0, 10))

        self._set_geometry(FULL_W, FULL_H)
        self._draw_ring()

    def _apply_fonts(self):
        self.title_lbl.config(font=self.title_font)
        self.state_label.config(font=self.label_font)
        self.msg_label.config(font=self.msg_font)
        self.start_btn.config(font=self.btn_font)
        self.reset_btn.config(font=self.btn_font)
        self.mini_btn.config(font=self.btn_font)
        self.gear_btn.config(font=self.btn_font)

    # ────────────────────── DRAWING ──────────────────────
    def _draw_ring(self):
        c = self.canvas
        c.delete("all")
        total = self.cfg["countdown_seconds"]

        if self.is_mini:
            sz = int(self.canvas_size * MINI_SCALE)
            cx, cy, r = sz // 2, sz // 2, sz // 2 - 6
            ring_w = 4
        else:
            cx, cy, r = 110, 110, 90
            ring_w = 10

        c.create_oval(cx - r, cy - r, cx + r, cy + r,
                      outline=RING_BG, width=ring_w)

        frac = self.remaining / total if total > 0 else 0
        extent = frac * 360
        color = ACCENT if self.remaining > 10 else "#ff4757"
        c.create_arc(cx - r, cy - r, cx + r, cy + r,
                     start=90, extent=extent, style="arc",
                     outline=color, width=ring_w)

        mins = self.remaining // 60
        secs = self.remaining % 60
        c.create_text(cx, cy - (3 if self.is_mini else 8),
                      text=f"{mins:02d}:{secs:02d}",
                      fill=TEXT, font=self.time_font)
        if not self.is_mini:
            c.create_text(cx, cy + 30, text="phút : giây",
                          fill=TEXT_DIM, font=self.label_font)

    # ────────────────────── LOGIC ──────────────────────
    def _toggle(self):
        if self.running:
            self._pause()
        else:
            self._start()

    def _start(self):
        if self.auto_restart_id:
            self.after_cancel(self.auto_restart_id)
            self.auto_restart_id = None
        if self.remaining <= 0:
            self.remaining = self.cfg["countdown_seconds"]
        self.running = True
        self.start_btn.config(text="⏸  Tạm Dừng" if not self.is_mini else "⏸",
                              bg="#e58e26")
        self.state_label.config(text="Đang đếm ngược… 🔥" if not self.is_mini else "🔥")
        self.msg_label.config(text="")
        self._tick()

    def _pause(self):
        self.running = False
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        self.start_btn.config(text="▶  Tiếp Tục" if not self.is_mini else "▶",
                              bg=ACCENT)
        self.state_label.config(text="Đã tạm dừng ⏸")

    def _reset(self):
        self.running = False
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        if self.auto_restart_id:
            self.after_cancel(self.auto_restart_id)
            self.auto_restart_id = None
        self.remaining = self.cfg["countdown_seconds"]
        self._draw_ring()
        self.start_btn.config(text="▶  Bắt Đầu" if not self.is_mini else "▶",
                              bg=ACCENT)
        self.state_label.config(text="Sẵn sàng đếm ngược ✨" if not self.is_mini else "✨")
        self.msg_label.config(text="")

    def _tick(self):
        if not self.running:
            return
        if self.remaining > 0:
            self.remaining -= 1
            self._draw_ring()
            self.after_id = self.after(1000, self._tick)
        else:
            self._draw_ring()
            self._finish()

    # ────────────────────── FINISH ──────────────────────
    def _finish(self):
        self.running = False
        self.start_btn.config(text="▶  Lại Nào!" if not self.is_mini else "▶",
                              bg=ACCENT)
        self.state_label.config(text="")
        self._show_reminder()
        delay = self.cfg["auto_restart_seconds"] * 1000
        self.auto_restart_id = self.after(delay, self._auto_restart)

    def _auto_restart(self):
        self.auto_restart_id = None
        self.remaining = self.cfg["countdown_seconds"]
        self._draw_ring()
        self.msg_label.config(text="")
        self._start()

    # ────────────────────── REMINDER ──────────────────────
    def _show_reminder(self):
        msgs = self.cfg.get("messages") or list(DEFAULTS["messages"])
        msg = random.choice(msgs)

        self.msg_label.config(text=msg, fg=SUCCESS)
        self.state_label.config(text="Hết giờ rồi! 🎉" if not self.is_mini else "🎉")

        self.pulse_phase = 0
        self._pulse_msg()

        if self.state() == "iconic":
            self.was_minimized = True
            self.attributes("-alpha", self.cfg.get("opacity", 0.35))  # configurable opacity
            ctypes.windll.user32.ShowWindow(self._hwnd, 4)
            self.after(50, self._raise_no_focus)
            delay = self.cfg["remind_show_seconds"] * 1000
            self.remind_hide_id = self.after(delay, self._re_minimize)
        else:
            self._raise_no_focus()

    def _raise_no_focus(self):
        SWP_NOACTIVATE  = 0x0010
        SWP_NOMOVE      = 0x0002
        SWP_NOSIZE      = 0x0001
        SWP_SHOWWINDOW  = 0x0040
        HWND_TOPMOST    = -1
        ctypes.windll.user32.SetWindowPos(
            self._hwnd, HWND_TOPMOST, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
        )
        ctypes.windll.user32.FlashWindow(self._hwnd, False)

    def _re_minimize(self):
        self.remind_hide_id = None
        if self.was_minimized:
            self.attributes("-alpha", 1.0)         # restore full opacity
            self.iconify()
            self.was_minimized = False

    def _pulse_msg(self):
        if self.remaining > 0 and self.running:
            return
        phase = self.pulse_phase % 40
        t = abs(phase - 20) / 20.0
        r = int(0x00 + (0x2e - 0x00) * (1 - t))
        g = int(0xe3 + (0xff - 0xe3) * (1 - t))
        b = int(0x96 + (0xdb - 0x96) * (1 - t))
        self.msg_label.config(fg=f"#{r:02x}{g:02x}{b:02x}")
        self.pulse_phase += 1
        if self.pulse_phase < 100:
            self.after(50, self._pulse_msg)


if __name__ == "__main__":
    app = CountdownApp()
    app.mainloop()

"""
Screen Locker - A full-screen locker that blocks keyboard shortcuts and
requires a password to unlock.  To cancel without the password, restart
the computer.

First run:  Shows a setup window to configure password, hint, and
            lock message.  Settings are saved to screenlocker.json.
Next runs:  Immediately locks the screen using saved settings.
            To reconfigure, delete screenlocker.json or use --setup.

Uses the 'keyboard' library (suppress=True) for reliable OS-level
key blocking — the same approach used by proven screen lockers on GitHub.

** Run as Administrator for maximum effectiveness. **
"""

import tkinter as tk
from tkinter import messagebox
import ctypes
import sys
import os
import json
import argparse
import winreg
import time
import keyboard  # pip install keyboard

# ──────────────────── Theme ────────────────────────────
BG_COLOR       = "#0f0e17"
CARD_COLOR     = "#1a1a2e"
ACCENT         = "#e94560"
ACCENT_HOVER   = "#ff6b81"
ACCENT_PRESS   = "#c0392b"
TEXT_COLOR     = "#eaeaea"
TEXT_DIM       = "#6c6c8a"
ENTRY_BG       = "#16213e"
ENTRY_FOCUS_BG = "#1c2a4a"
ENTRY_BORDER   = "#2a2a4a"
HINT_BG        = "#1e1e3a"
SUCCESS_COLOR  = "#2ecc71"
FONT           = "Segoe UI"

# Config file lives next to the .exe / .py
if getattr(sys, 'frozen', False):
    CONFIG_DIR = os.path.dirname(sys.executable)
else:
    CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(CONFIG_DIR, "screenlocker.json")


def parse_args():
    parser = argparse.ArgumentParser(description="Screen Locker")
    parser.add_argument("--setup", action="store_true",
                        help="Force the setup wizard (reconfigure)")
    parser.add_argument("--reset", action="store_true",
                        help="Delete saved config and re-run setup")
    return parser.parse_args()


# ──────────────────── Animation helpers ────────────────
def _lerp_color(c1: str, c2: str, t: float) -> str:
    """Linearly interpolate between two hex colors."""
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _animate_color(widget, prop, start, end, duration_ms=200, steps=12, root=None):
    """Smoothly transition a widget's color property."""
    target = root or widget
    for i in range(steps + 1):
        t = i / steps
        color = _lerp_color(start, end, t)
        delay = int(duration_ms * t)
        target.after(delay, lambda c=color, p=prop: widget.config(**{p: c}))


def _hover_button(btn, normal_bg, hover_bg, press_bg, root=None):
    """Attach hover + press animations to a button."""
    btn._cur_bg = normal_bg

    def on_enter(e):
        _animate_color(btn, "bg", btn._cur_bg, hover_bg, 150, 8, root)
        btn._cur_bg = hover_bg

    def on_leave(e):
        _animate_color(btn, "bg", btn._cur_bg, normal_bg, 150, 8, root)
        btn._cur_bg = normal_bg

    def on_press(e):
        btn.config(bg=press_bg)
        btn._cur_bg = press_bg

    def on_release(e):
        _animate_color(btn, "bg", press_bg, hover_bg, 100, 6, root)
        btn._cur_bg = hover_bg

    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    btn.bind("<ButtonPress-1>", on_press)
    btn.bind("<ButtonRelease-1>", on_release)


def _hover_entry(entry, normal_bg, focus_bg, root=None):
    """Subtle glow effect when hovering / focusing an entry."""
    entry._is_focused = False

    def on_enter(e):
        if not entry._is_focused:
            _animate_color(entry, "bg", normal_bg, focus_bg, 150, 8, root)

    def on_leave(e):
        if not entry._is_focused:
            _animate_color(entry, "bg", focus_bg, normal_bg, 150, 8, root)

    def on_focus_in(e):
        entry._is_focused = True
        _animate_color(entry, "bg", normal_bg, focus_bg, 120, 8, root)

    def on_focus_out(e):
        entry._is_focused = False
        _animate_color(entry, "bg", focus_bg, normal_bg, 120, 8, root)

    entry.bind("<Enter>", on_enter)
    entry.bind("<Leave>", on_leave)
    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)


def _pulse_label(label, color_a, color_b, period_ms=2000, root=None):
    """Gentle pulsing glow on a label (e.g. the lock icon)."""
    target = root or label
    steps = 30
    half = steps // 2

    def tick(step=0):
        if step <= half:
            t = step / half
        else:
            t = 1.0 - (step - half) / half
        color = _lerp_color(color_a, color_b, t)
        try:
            label.config(fg=color)
        except tk.TclError:
            return
        delay = period_ms // steps
        target.after(delay, lambda: tick((step + 1) % (steps + 1)))

    tick()


# ──────────────────── Config persistence ───────────────
def load_config() -> dict | None:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_config(config: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


# ──────────────────── Setup Wizard ─────────────────────
class SetupWizard:
    """First-time setup window with animated UI."""

    def __init__(self):
        self.result = None
        self.root = tk.Tk()
        self.root.title("Screen Locker \u2014 Setup")
        self.root.configure(bg=BG_COLOR)
        self.root.resizable(False, False)
        self._center(520, 580)
        self._build_ui()

    def _center(self, w, h):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _make_field(self, parent, label_text, show=None, default=""):
        tk.Label(parent, text=label_text, font=(FONT, 11, "bold"),
                 bg=BG_COLOR, fg=TEXT_DIM, anchor="w").pack(fill="x", padx=34, pady=(0, 2))
        entry = tk.Entry(parent, show=show, font=(FONT, 14),
                         bg=ENTRY_BG, fg=TEXT_COLOR,
                         insertbackground=TEXT_COLOR, relief="flat",
                         highlightthickness=2, highlightcolor=ACCENT,
                         highlightbackground=ENTRY_BORDER)
        if default:
            entry.insert(0, default)
        entry.pack(fill="x", padx=32, pady=(0, 14), ipady=7)
        _hover_entry(entry, ENTRY_BG, ENTRY_FOCUS_BG, self.root)
        return entry

    def _build_ui(self):
        # Title row
        title_frame = tk.Frame(self.root, bg=BG_COLOR)
        title_frame.pack(pady=(28, 6))
        icon = tk.Label(title_frame, text="\U0001F512", font=(FONT, 32),
                        bg=BG_COLOR, fg=ACCENT)
        icon.pack(side="left", padx=(0, 10))
        _pulse_label(icon, ACCENT, ACCENT_HOVER, 2500, self.root)
        tk.Label(title_frame, text="Screen Locker",
                 font=(FONT, 22, "bold"), bg=BG_COLOR, fg=TEXT_COLOR).pack(side="left")

        tk.Label(self.root, text="Configure your lock screen settings",
                 font=(FONT, 11), bg=BG_COLOR, fg=TEXT_DIM).pack(pady=(0, 20))

        # Fields
        self.pw_entry = self._make_field(self.root, "PASSWORD", show="\u25CF")
        self.pw_confirm = self._make_field(self.root, "CONFIRM PASSWORD", show="\u25CF")
        self.hint_entry = self._make_field(self.root, "PASSWORD HINT  (shown on lock screen)")
        self.msg_entry = self._make_field(self.root, "LOCK MESSAGE",
                                          default="This Computer is Locked")

        # Error
        self.error_label = tk.Label(self.root, text="", font=(FONT, 11),
                                    bg=BG_COLOR, fg=ACCENT)
        self.error_label.pack(pady=(0, 4))

        # Button
        btn = tk.Button(self.root, text="Save & Lock  \u2192",
                        font=(FONT, 13, "bold"),
                        bg=ACCENT, fg="white", relief="flat", cursor="hand2",
                        command=self._save, width=20, bd=0)
        btn.pack(ipady=8, pady=(4, 0))
        _hover_button(btn, ACCENT, ACCENT_HOVER, ACCENT_PRESS, self.root)

        self.pw_entry.focus_set()
        self.root.bind("<Return>", lambda e: self._save())

    def _save(self):
        pw = self.pw_entry.get()
        pw2 = self.pw_confirm.get()
        hint = self.hint_entry.get().strip()
        msg = self.msg_entry.get().strip() or "This Computer is Locked"

        if not pw:
            self.error_label.config(text="\u26A0  Password cannot be empty.")
            return
        if pw != pw2:
            self.error_label.config(text="\u26A0  Passwords do not match.")
            return

        self.result = {"password": pw, "hint": hint, "message": msg}
        save_config(self.result)
        self.root.destroy()

    def run(self) -> dict | None:
        self.root.mainloop()
        return self.result


# ──────────────── Registry helpers (Task Manager) ──────
TASKMGR_KEY = r"Software\Microsoft\Windows\CurrentVersion\Policies\System"


def _set_disable_taskmgr(value: int):
    try:
        key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, TASKMGR_KEY,
                                 0, winreg.KEY_SET_VALUE)
        if value:
            winreg.SetValueEx(key, "DisableTaskMgr", 0, winreg.REG_DWORD, 1)
        else:
            try:
                winreg.DeleteValue(key, "DisableTaskMgr")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except PermissionError:
        pass


def disable_task_manager():
    _set_disable_taskmgr(1)


def enable_task_manager():
    _set_disable_taskmgr(0)


# ──────────────── Keyboard blocking via 'keyboard' lib ─
class KeyboardBlocker:
    """Suppresses ALL keyboard input at the OS level via keyboard.hook(suppress=True),
    then manually forwards safe characters to the password entry."""

    def __init__(self):
        self._entry = None
        self._root = None

    def set_entry(self, entry, root):
        self._entry = entry
        self._root = root

    def _on_key(self, event):
        if event.event_type != keyboard.KEY_DOWN:
            return
        name = event.name

        if name == 'enter':
            if self._root:
                self._root.event_generate("<<CheckPassword>>")
            return
        if name == 'backspace':
            if self._entry:
                c = self._entry.get()
                if c:
                    self._entry.delete(len(c) - 1, tk.END)
            return
        if len(name) == 1:
            if keyboard.is_pressed('shift'):
                name = name.upper()
            if self._entry:
                self._entry.insert(tk.END, name)
            return
        if name == 'space':
            if self._entry:
                self._entry.insert(tk.END, ' ')
            return

    def install(self):
        keyboard.hook(self._on_key, suppress=True)

    def uninstall(self):
        keyboard.unhook_all()


# ──────────────────── Screen Locker ────────────────────
class ScreenLocker:
    def __init__(self, config: dict):
        self.password = config["password"]
        self.hint = config.get("hint", "")
        self.message = config.get("message", "This Computer is Locked")
        self.kb_blocker = KeyboardBlocker()
        self.root = tk.Tk()
        self.root.title("Screen Locked")
        self._setup_window()
        self._build_ui()
        self._bind_events()
        self.kb_blocker.set_entry(self.entry, self.root)

    def _setup_window(self):
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=BG_COLOR)
        self.root.protocol("WM_DELETE_WINDOW", self._block)
        self.root.overrideredirect(True)
        try:
            user32 = ctypes.windll.user32
            w = user32.GetSystemMetrics(78)
            h = user32.GetSystemMetrics(79)
            x = user32.GetSystemMetrics(76)
            y = user32.GetSystemMetrics(77)
            self.root.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    def _build_ui(self):
        # Card in center
        card = tk.Frame(self.root, bg=CARD_COLOR, padx=50, pady=40,
                        highlightthickness=1, highlightbackground="#2a2a4a")
        card.place(relx=0.5, rely=0.5, anchor="center")

        # Pulsing lock icon
        self.lock_icon = tk.Label(card, text="\U0001F512", font=(FONT, 56),
                                  bg=CARD_COLOR, fg=ACCENT)
        self.lock_icon.pack(pady=(0, 8))
        _pulse_label(self.lock_icon, ACCENT, ACCENT_HOVER, 2500, self.root)

        # Title
        tk.Label(card, text=self.message,
                 font=(FONT, 26, "bold"),
                 bg=CARD_COLOR, fg=TEXT_COLOR).pack(pady=(0, 4))

        # Subtitle
        tk.Label(card, text="Enter your password to unlock  \u2022  Restart to cancel",
                 font=(FONT, 11), bg=CARD_COLOR, fg=TEXT_DIM).pack(pady=(0, 8))

        # Hint
        if self.hint:
            hint_frame = tk.Frame(card, bg=HINT_BG, padx=18, pady=8)
            hint_frame.pack(pady=(4, 16))
            tk.Label(hint_frame, text=f"\U0001F4A1  Hint:  {self.hint}",
                     font=(FONT, 11, "italic"),
                     bg=HINT_BG, fg="#9e9eba").pack()
        else:
            tk.Frame(card, bg=CARD_COLOR, height=12).pack()

        # Separator
        tk.Frame(card, bg=ENTRY_BORDER, height=1).pack(fill="x", pady=(0, 18))

        # Password entry
        self.entry = tk.Entry(card, show="\u25CF", font=(FONT, 18),
                              bg=ENTRY_BG, fg=TEXT_COLOR,
                              insertbackground=TEXT_COLOR,
                              relief="flat", justify="center", width=24,
                              highlightthickness=2, highlightcolor=ACCENT,
                              highlightbackground=ENTRY_BORDER)
        self.entry.pack(ipady=10, pady=(0, 16))
        _hover_entry(self.entry, ENTRY_BG, ENTRY_FOCUS_BG, self.root)

        # Unlock button
        self.btn = tk.Button(card, text="\U0001F513  Unlock",
                             font=(FONT, 14, "bold"),
                             bg=ACCENT, fg="white", relief="flat", cursor="hand2",
                             command=self._check_password, width=22, bd=0)
        self.btn.pack(ipady=8, pady=(0, 12))
        _hover_button(self.btn, ACCENT, ACCENT_HOVER, ACCENT_PRESS, self.root)

        # Status
        self.status = tk.Label(card, text="", font=(FONT, 12),
                               bg=CARD_COLOR, fg=ACCENT)
        self.status.pack()

        # Time at bottom
        self.time_label = tk.Label(self.root, text="", font=(FONT, 40, "bold"),
                                   bg=BG_COLOR, fg="#1a1a3e")
        self.time_label.place(relx=0.5, rely=0.92, anchor="center")
        self._update_time()

    def _update_time(self):
        try:
            self.time_label.config(text=time.strftime("%H:%M"))
            self.root.after(10000, self._update_time)
        except tk.TclError:
            pass

    def _bind_events(self):
        self.root.bind("<<CheckPassword>>", lambda e: self._check_password())
        self.root.bind("<Escape>", lambda e: self._block())
        self.root.bind("<Alt-Tab>", lambda e: "break")
        self.root.bind("<Alt-F4>", lambda e: "break")
        self._keep_on_top()

    def _keep_on_top(self):
        try:
            self.root.attributes("-topmost", True)
            self.root.focus_force()
            self.root.after(300, self._keep_on_top)
        except tk.TclError:
            pass

    def _check_password(self):
        if self.entry.get() == self.password:
            self.status.config(text="\u2714  Unlocked!", fg=SUCCESS_COLOR)
            self.btn.config(bg=SUCCESS_COLOR)
            self.root.after(600, self._unlock)
        else:
            self.status.config(text="\u2716  Wrong password. Try again.", fg=ACCENT)
            self.entry.delete(0, tk.END)
            # Red flash on entry
            _animate_color(self.entry, "bg", ENTRY_BG, "#3d0000", 100, 6, self.root)
            self.root.after(400, lambda: _animate_color(
                self.entry, "bg", "#3d0000", ENTRY_BG, 200, 8, self.root))

    def _unlock(self):
        self._cleanup()
        self.root.destroy()

    def _cleanup(self):
        self.kb_blocker.uninstall()
        enable_task_manager()

    @staticmethod
    def _block():
        return "break"

    def run(self):
        disable_task_manager()
        self.kb_blocker.install()
        try:
            self.root.mainloop()
        finally:
            self._cleanup()


if __name__ == "__main__":
    args = parse_args()

    if args.reset and os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)

    config = load_config()

    if config is None or args.setup:
        config = SetupWizard().run()
        if config is None:
            sys.exit(0)

    locker = ScreenLocker(config)
    locker.run()

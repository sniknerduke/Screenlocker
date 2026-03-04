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
import keyboard  # pip install keyboard

# ──────────────────── Configuration ────────────────────
BG_COLOR = "#1a1a2e"
ACCENT_COLOR = "#e94560"
TEXT_COLOR = "#eaeaea"
ENTRY_BG = "#16213e"
FONT_FAMILY = "Segoe UI"

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


# ──────────────────── Config persistence ───────────────
def load_config() -> dict | None:
    """Load saved config or return None if not found."""
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
    """First-time setup window: password, confirm, hint, lock message."""

    def __init__(self):
        self.result = None  # will hold the config dict on success
        self.root = tk.Tk()
        self.root.title("Screen Locker — Setup")
        self.root.configure(bg=BG_COLOR)
        self.root.resizable(False, False)
        self._center(500, 520)
        self._build_ui()

    def _center(self, w, h):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        pad = {"padx": 30, "pady": (0, 0)}

        # Title
        tk.Label(self.root, text="\U0001F512  Screen Locker Setup",
                 font=(FONT_FAMILY, 20, "bold"),
                 bg=BG_COLOR, fg=TEXT_COLOR).pack(pady=(25, 20))

        # Password
        tk.Label(self.root, text="Password", font=(FONT_FAMILY, 12),
                 bg=BG_COLOR, fg=TEXT_COLOR, anchor="w").pack(fill="x", **pad)
        self.pw_entry = tk.Entry(self.root, show="*", font=(FONT_FAMILY, 14),
                                 bg=ENTRY_BG, fg=TEXT_COLOR,
                                 insertbackground=TEXT_COLOR, relief="flat")
        self.pw_entry.pack(fill="x", padx=30, pady=(4, 12), ipady=6)

        # Confirm password
        tk.Label(self.root, text="Confirm Password", font=(FONT_FAMILY, 12),
                 bg=BG_COLOR, fg=TEXT_COLOR, anchor="w").pack(fill="x", **pad)
        self.pw_confirm = tk.Entry(self.root, show="*", font=(FONT_FAMILY, 14),
                                   bg=ENTRY_BG, fg=TEXT_COLOR,
                                   insertbackground=TEXT_COLOR, relief="flat")
        self.pw_confirm.pack(fill="x", padx=30, pady=(4, 12), ipady=6)

        # Hint
        tk.Label(self.root, text="Password Hint  (shown on lock screen)",
                 font=(FONT_FAMILY, 12),
                 bg=BG_COLOR, fg=TEXT_COLOR, anchor="w").pack(fill="x", **pad)
        self.hint_entry = tk.Entry(self.root, font=(FONT_FAMILY, 14),
                                   bg=ENTRY_BG, fg=TEXT_COLOR,
                                   insertbackground=TEXT_COLOR, relief="flat")
        self.hint_entry.pack(fill="x", padx=30, pady=(4, 12), ipady=6)

        # Lock message
        tk.Label(self.root, text="Lock Message  (optional custom text)",
                 font=(FONT_FAMILY, 12),
                 bg=BG_COLOR, fg=TEXT_COLOR, anchor="w").pack(fill="x", **pad)
        self.msg_entry = tk.Entry(self.root, font=(FONT_FAMILY, 14),
                                  bg=ENTRY_BG, fg=TEXT_COLOR,
                                  insertbackground=TEXT_COLOR, relief="flat")
        self.msg_entry.insert(0, "This Computer is Locked")
        self.msg_entry.pack(fill="x", padx=30, pady=(4, 20), ipady=6)

        # Error label
        self.error_label = tk.Label(self.root, text="", font=(FONT_FAMILY, 11),
                                    bg=BG_COLOR, fg=ACCENT_COLOR)
        self.error_label.pack()

        # Save button
        tk.Button(self.root, text="Save & Lock", font=(FONT_FAMILY, 14, "bold"),
                  bg=ACCENT_COLOR, fg="white", activebackground="#c0392b",
                  activeforeground="white", relief="flat", cursor="hand2",
                  command=self._save, width=18).pack(ipady=6, pady=(8, 0))

        self.pw_entry.focus_set()
        self.root.bind("<Return>", lambda e: self._save())

    def _save(self):
        pw = self.pw_entry.get()
        pw2 = self.pw_confirm.get()
        hint = self.hint_entry.get().strip()
        msg = self.msg_entry.get().strip() or "This Computer is Locked"

        if not pw:
            self.error_label.config(text="Password cannot be empty.")
            return
        if pw != pw2:
            self.error_label.config(text="Passwords do not match.")
            return

        self.result = {
            "password": pw,
            "hint": hint,
            "message": msg,
        }
        save_config(self.result)
        self.root.destroy()

    def run(self) -> dict | None:
        self.root.mainloop()
        return self.result


# ──────────────── Registry helpers (Task Manager) ──────
TASKMGR_KEY = r"Software\Microsoft\Windows\CurrentVersion\Policies\System"


def _set_disable_taskmgr(value: int):
    """Set or remove DisableTaskMgr in HKCU."""
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
        pass  # not running as admin – skip


def disable_task_manager():
    _set_disable_taskmgr(1)


def enable_task_manager():
    _set_disable_taskmgr(0)


# ──────────────── Keyboard blocking via 'keyboard' lib ─
class KeyboardBlocker:
    """Uses the 'keyboard' library to suppress all key presses at the
    OS level, then selectively forwards safe keys to the tkinter Entry.
    This is the same technique used by Mr-Spect3r/Screen-Locker on GitHub.

    keyboard.on_press(callback, suppress=True) installs a proper
    low-level keyboard hook internally and suppresses EVERY key before
    it reaches any application — including Alt+Tab, Win+R, etc.

    We then manually inject allowed characters into the password entry.
    """

    def __init__(self):
        self._entry = None   # set later to the tkinter Entry widget
        self._root = None    # set later to the tkinter root

    def set_entry(self, entry, root):
        self._entry = entry
        self._root = root

    def _on_key(self, event):
        """Called for every key press. Since suppress=True,
        keys are blocked from reaching the OS. We manually
        forward safe characters to the password entry."""
        if event.event_type != keyboard.KEY_DOWN:
            return  # only handle key-down

        name = event.name

        # Allow Enter → trigger password check via tkinter
        if name == 'enter':
            if self._root:
                self._root.event_generate("<<CheckPassword>>")
            return

        # Allow Backspace → delete last char in entry
        if name == 'backspace':
            if self._entry:
                content = self._entry.get()
                if content:
                    self._entry.delete(len(content) - 1, tk.END)
            return

        # Allow single printable characters → insert into entry
        if len(name) == 1:
            # Check if Shift is held for uppercase
            if keyboard.is_pressed('shift'):
                name = name.upper()
            if self._entry:
                self._entry.insert(tk.END, name)
            return

        # Allow space
        if name == 'space':
            if self._entry:
                self._entry.insert(tk.END, ' ')
            return

        # Everything else (Alt, Tab, Win, Ctrl, Esc, F-keys, etc.)
        # is silently swallowed — suppress=True already blocked it.

    def install(self):
        """Start suppressing all keys globally."""
        keyboard.hook(self._on_key, suppress=True)

    def uninstall(self):
        """Stop suppressing keys — restore normal keyboard."""
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
        # Give the blocker access to the entry + root
        self.kb_blocker.set_entry(self.entry, self.root)

    # ── Window setup ──────────────────────────────────
    def _setup_window(self):
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=BG_COLOR)
        self.root.protocol("WM_DELETE_WINDOW", self._block)
        self.root.overrideredirect(True)

        # Cover every monitor
        try:
            user32 = ctypes.windll.user32
            w = user32.GetSystemMetrics(78)   # SM_CXVIRTUALSCREEN
            h = user32.GetSystemMetrics(79)   # SM_CYVIRTUALSCREEN
            x = user32.GetSystemMetrics(76)   # SM_XVIRTUALSCREEN
            y = user32.GetSystemMetrics(77)   # SM_YVIRTUALSCREEN
            self.root.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    # ── UI ────────────────────────────────────────────
    def _build_ui(self):
        frame = tk.Frame(self.root, bg=BG_COLOR)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(frame, text="\U0001F512", font=(FONT_FAMILY, 64),
                 bg=BG_COLOR, fg=ACCENT_COLOR).pack(pady=(0, 10))

        tk.Label(frame, text=self.message,
                 font=(FONT_FAMILY, 28, "bold"),
                 bg=BG_COLOR, fg=TEXT_COLOR).pack(pady=(0, 5))

        tk.Label(frame, text="Enter the password to unlock, or restart to cancel.",
                 font=(FONT_FAMILY, 13),
                 bg=BG_COLOR, fg="#888").pack(pady=(0, 10))

        # Show hint if available
        if self.hint:
            hint_frame = tk.Frame(frame, bg="#16213e", padx=15, pady=8)
            hint_frame.pack(pady=(0, 20))
            tk.Label(hint_frame, text=f"Hint:  {self.hint}",
                     font=(FONT_FAMILY, 12, "italic"),
                     bg="#16213e", fg="#aaa").pack()
        else:
            tk.Label(frame, text="", bg=BG_COLOR).pack(pady=(0, 10))

        self.entry = tk.Entry(frame, show="*", font=(FONT_FAMILY, 18),
                              bg=ENTRY_BG, fg=TEXT_COLOR,
                              insertbackground=TEXT_COLOR,
                              relief="flat", justify="center", width=25)
        self.entry.pack(ipady=8, pady=(0, 15))

        self.btn = tk.Button(frame, text="Unlock", font=(FONT_FAMILY, 14, "bold"),
                             bg=ACCENT_COLOR, fg="white", activebackground="#c0392b",
                             activeforeground="white", relief="flat", cursor="hand2",
                             command=self._check_password, width=20)
        self.btn.pack(ipady=6, pady=(0, 10))

        self.status = tk.Label(frame, text="", font=(FONT_FAMILY, 12),
                               bg=BG_COLOR, fg=ACCENT_COLOR)
        self.status.pack()

    # ── Events ────────────────────────────────────────
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
            pass  # window already destroyed

    # ── Logic ─────────────────────────────────────────
    def _check_password(self):
        if self.entry.get() == self.password:
            self._cleanup()
            self.root.destroy()
        else:
            self.status.config(text="Wrong password. Try again.")
            self.entry.delete(0, tk.END)
            self.entry.config(bg="#3d0000")
            self.root.after(400, lambda: self.entry.config(bg=ENTRY_BG))

    def _cleanup(self):
        """Undo all system changes before exiting."""
        self.kb_blocker.uninstall()
        enable_task_manager()

    @staticmethod
    def _block():
        return "break"

    def run(self):
        # Lock down the system
        disable_task_manager()
        self.kb_blocker.install()
        try:
            self.root.mainloop()
        finally:
            self._cleanup()  # always restore on exit


if __name__ == "__main__":
    args = parse_args()

    # --reset: delete config and force setup
    if args.reset and os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)

    config = load_config()

    # First run or --setup / --reset → show setup wizard
    if config is None or args.setup:
        config = SetupWizard().run()
        if config is None:
            sys.exit(0)  # user closed the setup window

    locker = ScreenLocker(config)
    locker.run()

"""
Screen Locker - A full-screen locker that blocks keyboard shortcuts and
requires a password to unlock.  To cancel without the password, restart
the computer.

Uses the 'keyboard' library (suppress=True) for reliable OS-level
key blocking — the same approach used by proven screen lockers on GitHub.

Blocked shortcuts:
    Alt+Tab, Alt+Esc, Alt+F4, Win+R, Win+D, Win+E, Win+<any>,
    Ctrl+Esc (Start), Ctrl+Shift+Esc (Task Manager).
    Task Manager is also disabled via the registry while locked.

    NOTE: Ctrl+Alt+Del CANNOT be blocked by any user-mode program (Windows
    kernel handles it).  However, Task Manager is disabled so pressing
    Ctrl+Alt+Del won't let the user kill this process easily.

Usage:
    python screenlocker.py                   # default password: 1234
    python screenlocker.py --password SECRET # custom password

** Run as Administrator for maximum effectiveness. **
"""

import tkinter as tk
import ctypes
import sys
import argparse
import winreg
import keyboard  # pip install keyboard

# ──────────────────── Configuration ────────────────────
DEFAULT_PASSWORD = "1234"
BG_COLOR = "#1a1a2e"
ACCENT_COLOR = "#e94560"
TEXT_COLOR = "#eaeaea"
ENTRY_BG = "#16213e"
FONT_FAMILY = "Segoe UI"


def parse_args():
    parser = argparse.ArgumentParser(description="Screen Locker")
    parser.add_argument("--password", "-p", default=DEFAULT_PASSWORD,
                        help="Set the unlock password (default: 1234)")
    return parser.parse_args()


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
    def __init__(self, password: str):
        self.password = password
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

        tk.Label(frame, text="This Computer is Locked",
                 font=(FONT_FAMILY, 28, "bold"),
                 bg=BG_COLOR, fg=TEXT_COLOR).pack(pady=(0, 5))

        tk.Label(frame, text="Enter the password to unlock, or restart to cancel.",
                 font=(FONT_FAMILY, 13),
                 bg=BG_COLOR, fg="#888").pack(pady=(0, 30))

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
    locker = ScreenLocker(password=args.password)
    locker.run()

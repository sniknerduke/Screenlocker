"""
Screen Locker - A full-screen locker that blocks keyboard shortcuts and
requires a password to unlock.  To cancel without the password, restart
the computer.

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
import ctypes.wintypes as wintypes
import sys
import argparse
import threading
import winreg

# ──────────────────── Configuration ────────────────────
DEFAULT_PASSWORD = "1234"
BG_COLOR = "#1a1a2e"
ACCENT_COLOR = "#e94560"
TEXT_COLOR = "#eaeaea"
ENTRY_BG = "#16213e"
FONT_FAMILY = "Segoe UI"

# ──────────────────── Win32 Constants ──────────────────
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

VK_TAB = 0x09
VK_ESCAPE = 0x1B
VK_F4 = 0x73
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_DELETE = 0x2E
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt

# KBDLLHOOKSTRUCT.flags bit masks
LLKHF_ALTDOWN = 0x20

# All key messages we intercept (both down AND up — critical for Win key)
ALL_KEY_MSGS = (WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP)


# ── Proper KBDLLHOOKSTRUCT ───────────────────────────
class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


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


# ──────────────── Low-level keyboard hook ──────────────
class KeyboardBlocker:
    """Installs a Windows low-level keyboard hook that swallows dangerous
    key combinations so the user cannot switch away from the locker.

    Must block BOTH key-down and key-up for every blocked key, otherwise
    Windows still registers the shortcut on key-up.
    """

    def __init__(self):
        self._hook = None
        self._thread = None

        # C callback must be stored as an instance attribute so it
        # is not garbage-collected while the hook is alive.
        self.HOOKPROC = ctypes.CFUNCTYPE(
            ctypes.c_long,            # LRESULT
            ctypes.c_int,             # nCode
            wintypes.WPARAM,          # wParam
            wintypes.LPARAM,          # lParam
        )
        self._callback = self.HOOKPROC(self._low_level_handler)

    # ── decide what to swallow ────────────────────────
    @staticmethod
    def _should_block(vk_code: int, flags: int) -> bool:
        """Return True if the keystroke must be eaten."""
        alt_down = bool(flags & LLKHF_ALTDOWN)
        ctrl_down = bool(ctypes.windll.user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
        shift_down = bool(ctypes.windll.user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)

        # ── Win key (left / right) — kills ALL Win+<x> combos ──
        if vk_code in (VK_LWIN, VK_RWIN):
            return True

        # ── Alt + Tab  (task switcher) ──────────────────────────
        if alt_down and vk_code == VK_TAB:
            return True

        # ── Alt + Esc  (cycle windows) ─────────────────────────
        if alt_down and vk_code == VK_ESCAPE:
            return True

        # ── Alt + F4   (close / shut-down dialog) ──────────────
        if alt_down and vk_code == VK_F4:
            return True

        # ── Ctrl + Esc (Start menu) ────────────────────────────
        if ctrl_down and vk_code == VK_ESCAPE:
            return True

        # ── Ctrl + Shift + Esc (Task Manager) ─────────────────
        if ctrl_down and shift_down and vk_code == VK_ESCAPE:
            return True

        return False

    # ── hook callback ─────────────────────────────────
    def _low_level_handler(self, nCode, wParam, lParam):
        if nCode >= 0 and wParam in ALL_KEY_MSGS:
            # Parse the KBDLLHOOKSTRUCT properly
            kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            if self._should_block(kb.vkCode, kb.flags):
                return 1   # swallow — do NOT pass to next hook

        return ctypes.windll.user32.CallNextHookEx(
            self._hook, nCode, wParam, lParam
        )

    # ── install / uninstall ───────────────────────────
    def _message_loop(self):
        """Pump messages on a dedicated thread so the hook stays alive."""
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        self._hook = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self._callback,
            kernel32.GetModuleHandleW(None),
            0,
        )
        if not self._hook:
            return  # hook failed — nothing we can do

        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def install(self):
        self._thread = threading.Thread(target=self._message_loop, daemon=True)
        self._thread.start()

    def uninstall(self):
        if self._hook:
            ctypes.windll.user32.UnhookWindowsHookEx(self._hook)
            self._hook = None


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
        self.entry.focus_set()

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
        self.root.bind("<Return>", lambda e: self._check_password())
        self.root.bind("<Escape>", lambda e: self._block())
        self.root.bind("<Alt-Tab>", lambda e: "break")
        self.root.bind("<Alt-F4>", lambda e: "break")
        self._keep_on_top()

    def _keep_on_top(self):
        try:
            self.root.attributes("-topmost", True)
            self.root.focus_force()
            self.entry.focus_set()
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

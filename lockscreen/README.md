# 🔒 Screen Locker

A sleek, full-screen Windows screen locker built with Python. Locks the desktop behind a password-protected overlay, blocks keyboard shortcuts (Alt+Tab, Win+R, etc.), and disables Task Manager — all wrapped in a polished dark UI with smooth hover animations.

---

## ✨ Features

| Feature | Description |
|---|---|
| **Full-Screen Lock** | Covers all monitors with an always-on-top overlay |
| **Password Protection** | Unlock only by entering the correct password |
| **First-Time Setup Wizard** | Guided setup for password, hint, and lock message |
| **Keyboard Blocking** | Suppresses **all** keyboard input at the OS level (Alt+Tab, Win+R, Win key, etc.) via the `keyboard` library |
| **Task Manager Disabled** | Temporarily disables Task Manager via the Windows registry while locked |
| **Animated Dark UI** | Card-style lock screen with pulsing lock icon, hover effects on buttons & entries, color transitions, and a live clock |
| **Password Hint** | Optional hint displayed on the lock screen |
| **Wrong Password Feedback** | Red flash animation on incorrect attempts |
| **Success Animation** | Green flash on successful unlock before closing |
| **Portable Config** | Settings saved to `screenlocker.json` next to the executable |
| **Single .exe** | Compiles to a standalone executable with PyInstaller — no Python required on the target machine |

---

## 🖼️ Screenshots

<p align="center">
  <img src="screenshots/setup.png" alt="Setup Wizard" width="45%"/>
  &nbsp;&nbsp;
  <img src="screenshots/lockscreen.png" alt="Lock Screen" width="45%"/>
</p>

> *Add your own screenshots to a `screenshots/` folder.*

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** (for running from source)
- **Windows 10/11**
- **Administrator privileges** (required for keyboard blocking & Task Manager control)

### Install Dependencies

```bash
pip install keyboard pyinstaller
```

### Run from Source

```bash
python screenlocker.py
```

On first launch, the **Setup Wizard** appears — configure your password, hint, and lock message. On subsequent launches, the screen locks immediately.

### Command-Line Options

| Flag | Description |
|---|---|
| `--setup` | Force the setup wizard (reconfigure settings) |
| `--reset` | Delete saved config and re-run setup |

```bash
python screenlocker.py --setup     # Reconfigure
python screenlocker.py --reset     # Wipe config & reconfigure
```

---

## 📦 Build Standalone .exe

```bash
pyinstaller --onefile --noconsole --name "ScreenLocker" --uac-admin --hidden-import keyboard screenlocker.py
```

The compiled executable appears in `dist/ScreenLocker.exe`.

> **`--uac-admin`** ensures the exe requests administrator privileges on launch, which is required for keyboard suppression and registry writes.

---

## 🛡️ UAC Bypass (Optional)

To launch without a UAC prompt every time, you can register a **Scheduled Task** that runs with highest privileges:

1. Run `setup_locker.py` **once** as Administrator:
   ```bash
   python setup_locker.py
   ```
2. From then on, double-click **`Lock Screen.bat`** — it triggers the scheduled task silently.

---

## 🏗️ Project Structure

```
├── screenlocker.py       # Main application (locker + setup wizard)
├── screenlocker.json     # Auto-generated config (password, hint, message)
├── setup_locker.py       # One-time admin setup for scheduled task
├── Lock Screen.bat       # Quick-launch via scheduled task
├── dist/
│   └── ScreenLocker.exe  # Compiled standalone executable
└── README.md
```

---

## ⚙️ How It Works

1. **Keyboard suppression** — Uses `keyboard.hook(callback, suppress=True)` to intercept and swallow every keystroke at a low level. Only password-safe characters are forwarded to the entry field manually.

2. **Task Manager** — Sets `HKCU\...\Policies\System\DisableTaskMgr = 1` while locked; removes it on unlock.

3. **Always on top** — The window is `overrideredirect(True)` + `-topmost` and re-asserts focus every 300 ms.

4. **Ctrl+Alt+Del** — Cannot be intercepted (Windows kernel). Mitigated by disabling Task Manager so the security screen offers no useful escape.

5. **Cancellation** — The only way to bypass without the password is to **restart the computer**, which is the intended fail-safe.

---

## ⚠️ Disclaimer

This tool is intended for **personal use and educational purposes only**. Misusing screen-locking software on computers you do not own or have authorization to lock may violate local laws. The author takes no responsibility for misuse.

---

## 📄 License

MIT License — free to use, modify, and distribute.

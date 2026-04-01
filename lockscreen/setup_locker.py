"""
Setup Script — Registers the screen locker as a Scheduled Task with
"Run with highest privileges" so it can launch WITHOUT a UAC prompt.

Run this ONCE as Administrator:
    python setup_locker.py
    python setup_locker.py --password SECRET   # custom password

After setup:
    • Double-click "Lock Screen.bat" to lock (no UAC prompt!)
    • Or run:  schtasks /run /tn "ScreenLocker"
"""

import os
import sys
import subprocess
import argparse
import ctypes

TASK_NAME = "ScreenLocker"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCKER_SCRIPT = os.path.join(SCRIPT_DIR, "screenlocker.py")
BAT_FILE = os.path.join(SCRIPT_DIR, "Lock Screen.bat")


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def get_python_path() -> str:
    return sys.executable


def create_task(password: str):
    python = get_python_path()
    args = f'"{LOCKER_SCRIPT}"'
    if password:
        args += f" --password {password}"

    # Build the schtasks command
    # /rl HIGHEST  = run with highest privileges (admin, no UAC)
    # /sc ONCE     = one-time trigger (we'll run it manually)
    # /st 00:00    = dummy start time (required by /sc ONCE)
    # /f           = force overwrite if exists
    cmd = [
        "schtasks", "/create",
        "/tn", TASK_NAME,
        "/tr", f'"{python}" {args}',
        "/sc", "ONCE",
        "/st", "00:00",
        "/rl", "HIGHEST",
        "/f"
    ]

    print(f"[*] Creating scheduled task '{TASK_NAME}'...")
    print(f"    Python : {python}")
    print(f"    Script : {LOCKER_SCRIPT}")
    print(f"    Password: {'(custom)' if password else '1234 (default)'}")
    print()

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("[+] Task created successfully!")
    else:
        print(f"[!] Failed to create task:\n{result.stderr}")
        sys.exit(1)


def create_batch_file():
    """Create a .bat shortcut to trigger the task (no UAC)."""
    content = f'@echo off\nschtasks /run /tn "{TASK_NAME}"\n'
    with open(BAT_FILE, "w") as f:
        f.write(content)
    print(f"[+] Created: {BAT_FILE}")
    print("    Double-click this file to lock your screen (no UAC prompt).\n")


def main():
    parser = argparse.ArgumentParser(description="Setup Screen Locker (run as Admin)")
    parser.add_argument("--password", "-p", default="",
                        help="Password for the locker (default: 1234)")
    parser.add_argument("--remove", action="store_true",
                        help="Remove the scheduled task")
    args = parser.parse_args()

    if not is_admin():
        print("[!] This setup script must be run as Administrator.")
        print("    Right-click → Run as administrator, or use:")
        print(f'    Start-Process python -ArgumentList "{__file__}" -Verb RunAs')
        input("\nPress Enter to exit...")
        sys.exit(1)

    if args.remove:
        print(f"[*] Removing scheduled task '{TASK_NAME}'...")
        subprocess.run(["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
                        capture_output=True)
        if os.path.exists(BAT_FILE):
            os.remove(BAT_FILE)
            print(f"[+] Removed: {BAT_FILE}")
        print("[+] Done.")
        return

    create_task(args.password)
    create_batch_file()

    print("=" * 50)
    print("  SETUP COMPLETE")
    print("=" * 50)
    print(f'  To lock:   Double-click "Lock Screen.bat"')
    print(f"  To remove: python setup_locker.py --remove")
    print()
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()

"""Đăng ký / gỡ protocol "flashcard://" trên Windows.

Sau khi chạy script này (1 lần), khi extension hoặc bất kỳ trang web nào mở
link "flashcard://open", Windows sẽ tự chạy:

    Flash_Card_App\\run_app.bat   ->   python main.py

Cách dùng:
    python install_protocol.py              # cài đặt
    python install_protocol.py --uninstall  # gỡ bỏ

Chỉ ghi vào HKEY_CURRENT_USER nên KHÔNG cần quyền Administrator.
"""

import sys
from pathlib import Path

PROTOCOL_NAME = "flashcard"
PROTOCOL_DESC = "URL:Flashcard App Protocol"


def _winreg():
    import winreg  # chỉ tồn tại trên Windows

    return winreg


def _paths():
    base = Path(__file__).resolve().parent
    run_bat = base / "Flash_Card_App" / "run_app.bat"
    return base, run_bat


def install():
    winreg = _winreg()
    base, run_bat = _paths()

    if not run_bat.exists():
        print(f"[X] Không tìm thấy: {run_bat}")
        return 1

    command = f'"{run_bat}" "%1"'
    key = rf"Software\Classes\{PROTOCOL_NAME}"

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, PROTOCOL_DESC)
        winreg.SetValueEx(k, "URL Protocol", 0, winreg.REG_SZ, "")

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key + r"\shell\open\command") as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, command)

    print("[OK] Đã đăng ký protocol:", f"{PROTOCOL_NAME}://")
    print("     Lệnh khi mở link:", command)
    print()
    print("Bây giờ trên extension, bấm nút 'Mở Flashcard App' sẽ tự chạy app.")
    return 0


def uninstall():
    winreg = _winreg()
    base = rf"Software\Classes\{PROTOCOL_NAME}"

    for sub in (
        base + r"\shell\open\command",
        base + r"\shell\open",
        base + r"\shell",
        base,
    ):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
            print("[OK] Đã xoá:", sub)
        except FileNotFoundError:
            pass
        except OSError as error:
            print("[!] Không xoá được", sub, "->", error)

    print("[OK] Đã gỡ protocol", f"{PROTOCOL_NAME}://")
    return 0


def main():
    if sys.platform != "win32":
        print("[X] Script này chỉ dùng cho Windows.")
        return 1

    if "--uninstall" in sys.argv or "-u" in sys.argv:
        return uninstall()

    return install()


if __name__ == "__main__":
    sys.exit(main())

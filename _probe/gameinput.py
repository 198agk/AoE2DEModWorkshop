"""Minimal Win32 mouse/keyboard driver for operating the running game.

Usage:
    python gameinput.py click 730 700
    python gameinput.py key f
    python gameinput.py shot out.png
    python gameinput.py focus
"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

u32 = ctypes.WinDLL("user32", use_last_error=True)

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wt.LONG), ("dy", wt.LONG), ("mouseData", wt.DWORD),
                ("dwFlags", wt.DWORD), ("time", wt.DWORD),
                ("dwExtraInfo", ctypes.POINTER(wt.ULONG))]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ctypes.POINTER(wt.ULONG))]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wt.DWORD), ("wParamL", wt.WORD), ("wParamH", wt.WORD)]


class INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]
    _anonymous_ = ("u",)
    _fields_ = [("type", wt.DWORD), ("u", _U)]


def _send(*inputs):
    n = len(inputs)
    arr = (INPUT * n)(*inputs)
    u32.SendInput(n, ctypes.byref(arr), ctypes.sizeof(INPUT))


def _screen_size():
    return (u32.GetSystemMetrics(0), u32.GetSystemMetrics(1))


def move(x, y):
    w, h = _screen_size()
    ax = int(x * 65535 / (w - 1))
    ay = int(y * 65535 / (h - 1))
    mi = MOUSEINPUT(ax, ay, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, None)
    _send(INPUT(INPUT_MOUSE, INPUT._U(mi=mi)))


def click(x, y, button="left", double=False):
    move(x, y)
    time.sleep(0.05)
    down = MOUSEEVENTF_LEFTDOWN if button == "left" else MOUSEEVENTF_RIGHTDOWN
    up = MOUSEEVENTF_LEFTUP if button == "left" else MOUSEEVENTF_RIGHTUP
    d = MOUSEINPUT(0, 0, 0, down, 0, None)
    u = MOUSEINPUT(0, 0, 0, up, 0, None)
    _send(INPUT(INPUT_MOUSE, INPUT._U(mi=d)))
    time.sleep(0.03)
    _send(INPUT(INPUT_MOUSE, INPUT._U(mi=u)))
    if double:
        time.sleep(0.05)
        _send(INPUT(INPUT_MOUSE, INPUT._U(mi=d)))
        time.sleep(0.03)
        _send(INPUT(INPUT_MOUSE, INPUT._U(mi=u)))


def key(vk_name, up=False):
    vk = ctypes.windll.user32.VkKeyScanW(ord(vk_name)) & 0xFF if len(vk_name) == 1 else 0
    flags = KEYEVENTF_KEYUP if up else 0
    ki = KEYBDINPUT(vk, 0, flags, 0, None)
    _send(INPUT(INPUT_KEYBOARD, INPUT._U(ki=ki)))


VK = {
    "esc": 0x1B, "enter": 0x0D, "space": 0x20, "tab": 0x09,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74,
    "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    ".": 0xBE, ",": 0xBC, "h": 0x48, "a": 0x41, "i": 0x49, "q": 0x51,
    "del": 0x2E, "back": 0x08,
}


def press(name, n=1, delay=0.06):
    vk = VK.get(name.lower())
    if vk is None and len(name) == 1:
        vk = u32.VkKeyScanW(ord(name)) & 0xFF
    if vk is None:
        raise SystemExit("unknown key %r" % name)
    for _ in range(n):
        _send(INPUT(INPUT_KEYBOARD, INPUT._U(ki=KEYBDINPUT(vk, 0, 0, 0, None))))
        time.sleep(0.03)
        _send(INPUT(INPUT_KEYBOARD,
                    INPUT._U(ki=KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP, 0, None))))
        time.sleep(delay)


def find_window(title_sub):
    found = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        n = u32.GetWindowTextLengthW(hwnd)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            u32.GetWindowTextW(hwnd, buf, n + 1)
            if title_sub.lower() in buf.value.lower():
                r = wt.RECT()
                u32.GetWindowRect(hwnd, ctypes.byref(r))
                found.append((hwnd, buf.value, r))
        return True

    u32.EnumWindows(cb, 0)
    return found


def focus():
    ws = find_window("Age of Empires")
    if not ws:
        print("no game window found")
        return
    hwnd, title, r = ws[0]
    # SW_RESTORE un-maximises a fullscreen game window (observed: 2560x1440 ->
    # 925x549), which then makes every coordinate from a previous screenshot
    # wrong.  Always maximise instead.
    u32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
    u32.SetForegroundWindow(hwnd)
    print("focused hwnd=%s title=%r rect=(%d,%d,%d,%d)"
          % (hwnd, title, r.left, r.top, r.right, r.bottom))


def shot(path):
    from PIL import ImageGrab
    ws = find_window("Age of Empires")
    if ws:
        _, title, r = ws[0]
        img = ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom))
        print("window rect", (r.left, r.top, r.right, r.bottom))
    else:
        img = ImageGrab.grab()
    img.save(path)
    print("saved", path, img.size)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "focus"
    if cmd == "click":
        click(int(sys.argv[2]), int(sys.argv[3]),
              sys.argv[4] if len(sys.argv) > 4 else "left")
    elif cmd == "dclick":
        click(int(sys.argv[2]), int(sys.argv[3]), double=True)
    elif cmd == "press":
        press(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    elif cmd == "focus":
        focus()
    elif cmd == "shot":
        shot(sys.argv[2])
    elif cmd == "windows":
        for w in find_window("Age of Empires"):
            print(w[0], repr(w[1]), w[2].left, w[2].top, w[2].right, w[2].bottom)
    else:
        raise SystemExit("unknown command %r" % cmd)

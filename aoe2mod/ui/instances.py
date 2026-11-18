"""instances.py -- which workshop windows this machine is running, and where.

Two workshop windows are two processes on two free ports (the shell picks a
port per launch, desktop/src-tauri/src/main.rs:107), so neither can find the
other by looking inside its own memory.  This module is the one place that
answers the two questions a cross-window drag needs:

* what else is running -- a heartbeat file per instance under
  state_dir()/instances, because the state directory is already the one place
  both processes agree on (aoe2mod/mod/provenance.py:85 def state_dir).
* which of those windows is under a screen point -- the registry holds the
  shell's pid (the window belongs to the Rust process, not to Python), and
  Win32 answers the rectangle question.

Nothing here touches the .dat: it is addressing, not editing.
"""

import json
import os
import threading
import time

#: A file is trusted for this long after its last beat.  Short enough that a
#: window closed a moment ago stops being a drop target; long enough that a
#: busy machine cannot make a live window look dead.
BEAT_EVERY = 5.0
STALE_AFTER = 30.0

_DIR = "instances"

_lock = threading.Lock()
#: {port: info} for the instances THIS process announced.  One heartbeat
#: thread walks it, so a machine running the suites (which build a server per
#: case) does not end up with a thread per case.
_mine = {}
_beater = None


def _dir():
    from aoe2mod.mod import provenance as PV
    return os.path.join(PV.state_dir(), _DIR)


def _path(port):
    return os.path.join(_dir(), "%d.json" % int(port))


def _write(info):
    d = _dir()
    try:
        os.makedirs(d, exist_ok=True)
        tmp = _path(info["port"]) + ".tmp"
        # Keys starting with "_" are this process's own bookkeeping (the .dat
        # hint callable) and are not part of what another window may read.
        pub = {k: v for k, v in info.items() if not k.startswith("_")}
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(pub, fh, ensure_ascii=False)
        os.replace(tmp, _path(info["port"]))
    except OSError:
        # A state directory we cannot write is a machine where a cross-window
        # drag will not find its target; every other feature is unaffected, so
        # this must never be the reason a window fails to open.
        pass


def _beat():
    while True:
        time.sleep(BEAT_EVERY)
        with _lock:
            items = list(_mine.values())
        now = time.time()
        for info in items:
            info["beat"] = now
            # The .dat is only known once the toolkit has parsed it, which
            # happens after the window is already up -- so the hint is asked
            # again on every beat instead of once at announce time.
            hint = info.get("_dat")
            if hint is not None:
                try:
                    info["dat"] = str(hint() or "")
                except Exception:
                    pass
            _write(info)


def announce(port, pid=None, parent=None, dat_hint=None, game_root=None):
    """Publish this instance, and keep its beat fresh until withdraw().

    pid is this Python process; parent is the shell that owns the window and
    is the pid Win32 reports for it.  dat_hint is a callable because the .dat
    in use is only known once the toolkit has resolved it -- the first beat may
    well publish an empty string, and the drop path treats "no answer yet" as
    "do not compare".
    """
    global _beater
    info = {
        "port": int(port),
        "pid": int(pid if pid is not None else os.getpid()),
        "parent": int(parent or 0),
        "root": os.path.abspath(game_root) if game_root else "",
        "dat": "",
        "started": time.time(),
        "beat": time.time(),
    }
    try:
        if dat_hint is not None:
            info["dat"] = str(dat_hint() or "")
    except Exception:
        info["dat"] = ""
    # Kept beside the public fields and stripped by _write: a callable cannot
    # be serialised, but the heartbeat thread needs it every BEAT_EVERY.
    info["_dat"] = dat_hint
    with _lock:
        _mine[int(port)] = info
        need = _beater is None or not _beater.is_alive()
        if need:
            _beater = threading.Thread(target=_beat, name="instance-beat",
                                       daemon=True)
            _beater.start()
    _write(info)
    return info


def withdraw(port):
    """Stop advertising this instance (the window is closing)."""
    with _lock:
        _mine.pop(int(port), None)
    try:
        os.remove(_path(port))
    except OSError:
        pass


def _read(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def live(now=None):
    """Every instance that has beaten recently, oldest window first.

    Stale files are deleted here rather than by a sweeper thread: the only
    moment anybody cares is the moment somebody is looking for a target.
    """
    now = time.time() if now is None else now
    d = _dir()
    try:
        names = os.listdir(d)
    except OSError:
        return []
    out = []
    for name in names:
        if not name.endswith(".json"):
            continue
        p = os.path.join(d, name)
        try:
            age = now - os.path.getmtime(p)
        except OSError:
            continue
        if age > STALE_AFTER:
            try:
                os.remove(p)
            except OSError:
                pass
            continue
        info = _read(p)
        if info and info.get("port"):
            out.append(info)
    out.sort(key=lambda x: x.get("started") or 0)
    return out


# ---------------------------------------------------------------------------
# Where a screen point lands
# ---------------------------------------------------------------------------
try:                                        # pragma: no cover - Windows only
    import ctypes
    from ctypes import wintypes as _W
    _USER32 = ctypes.windll.user32
except Exception:                           # pragma: no cover - not Windows
    _USER32 = None


def _rect_of(hwnd):
    r = _W.RECT()
    if not _USER32.GetWindowRect(hwnd, ctypes.byref(r)):
        return None
    return (r.left, r.top, r.right, r.bottom)


def windows():
    """[(hwnd, pid, (left, top, right, bottom))] for visible top-level windows.

    Empty everywhere Win32 is not available, which every caller reads as "no
    other window here" -- the same answer as a machine running one workshop.
    """
    if _USER32 is None:
        return []
    out = []
    proc_type = ctypes.WINFUNCTYPE(_W.BOOL, _W.HWND, _W.LPARAM)

    def _each(hwnd, _lparam):
        if not _USER32.IsWindowVisible(hwnd):
            return True
        box = _rect_of(hwnd)
        if not box or box[2] <= box[0] or box[3] <= box[1]:
            return True
        pid = _W.DWORD(0)
        _USER32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        out.append((hwnd, int(pid.value), box))
        return True

    try:
        _USER32.EnumWindows(proc_type(_each), 0)
    except Exception:
        return []
    return out


def _root_pid_at(x, y):
    """The pid owning the top-most window at (x, y), or 0."""
    if _USER32 is None:
        return 0
    try:
        hwnd = _USER32.WindowFromPoint(_W.POINT(int(x), int(y)))
        if not hwnd:
            return 0
        root = _USER32.GetAncestor(hwnd, 2)     # GA_ROOT
        pid = _W.DWORD(0)
        _USER32.GetWindowThreadProcessId(root or hwnd, ctypes.byref(pid))
        return int(pid.value)
    except Exception:
        return 0


def instance_at(x, y, dpr=1.0, ports=None):
    """The OTHER instance whose window holds the point, or None.

    Two passes, and the order matters: Win32 hit testing gets overlapping
    windows right (it knows what is drawn on top), but it wants physical pixels
    and the page only knows CSS pixels.  When the scaled point finds nothing,
    the raw rectangle pass answers -- a few pixels of error never moves a point
    out of the window it is inside.
    """
    pool = [i for i in live() if not ports or i.get("port") in ports]
    if not pool:
        return None
    by_pid = {}
    for inst in pool:
        for key in ("parent", "pid"):
            if inst.get(key):
                by_pid.setdefault(int(inst[key]), inst)
    scales = [1.0] if dpr in (None, 1, 1.0) else [dpr, 1.0]
    for scale in scales:
        pid = _root_pid_at(int(round(float(x) * float(scale))),
                           int(round(float(y) * float(scale))))
        if pid in by_pid:
            return by_pid[pid]
    for scale in scales:
        sx = int(round(float(x) * float(scale)))
        sy = int(round(float(y) * float(scale)))
        for hwnd, pid, box in windows():
            if pid in by_pid and box[0] <= sx < box[2] and box[1] <= sy < box[3]:
                return by_pid[pid]
    return None

def cursor():
    """Where the mouse is, in PHYSICAL screen pixels, or None.

    Asked instead of trusting the page: a pointer event carries CSS pixels
    relative to the viewport, so the page would have to add its own screenX and
    then guess the display scale.  Win32 already knows, in the units the window
    rectangles are measured in, which is what `instance_at` compares against.
    """
    if _USER32 is None:
        return None
    try:
        p = _W.POINT()
        if not _USER32.GetCursorPos(ctypes.byref(p)):
            return None
        return (int(p.x), int(p.y))
    except Exception:
        return None

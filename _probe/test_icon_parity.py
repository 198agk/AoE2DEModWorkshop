# -*- coding: utf-8 -*-
"""Compare /api/icon output against the Python icon path, pixel for pixel.

Bytes cannot be compared (two zlib levels produce different PNGs of identical
pixels), so both sides are decoded back to RGBA. Three sizes are checked because
the resize path only runs above `max`: 0 (no resize), 64 (4x box filter), and 100
(factor 2, an uneven divisor of 256).
"""
import json
import os
import struct
import sys
import urllib.request
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import aoe2mod.api as A                      # noqa: E402
from aoe2mod.game import ddstex as D         # noqa: E402

def free_port(start=7970):
    import socket
    for p in range(start, start + 40):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", p))
            return p
        except OSError:
            continue
        finally:
            s.close()
    raise RuntimeError("no free port")


def spawn_server():
    """Start the engine this probe measures, instead of assuming one is running.

    The first version used a hardcoded port and silently produced eighteen
    `REQUEST FAILED` lines when nothing was listening; the verdict then read
    `ICON: -18/0 pixel-identical` -- a negative count, which is not a
    measurement of anything.  A gate that cannot run its subject must say so
    rather than count the absence as disagreement.
    Returns (proc, base_url).
    """
    import subprocess
    import time
    import urllib.request

    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, "-X", "utf8", "-u",
         os.path.join(os.path.dirname(HERE), "tools", "run_ui.py"),
         "--port", str(port), "--serve-only"],
        cwd=os.path.dirname(HERE),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = "http://127.0.0.1:%d" % port
    deadline = time.time() + 240
    while time.time() < deadline:
        if proc.poll() is not None:
            raise SystemExit("the engine exited: %s" % proc.returncode)
        try:
            with urllib.request.urlopen(base + "/api/progress", timeout=3) as r:
                p = json.loads(r.read().decode("utf-8")).get("progress") or {}
            if p.get("ready"):
                return proc, base
            if p.get("error"):
                raise SystemExit("the engine failed: %s" % p["error"])
        except SystemExit:
            raise
        except Exception:
            pass
        time.sleep(0.5)
    raise SystemExit("the engine never became ready")


def rgba(blob):
    if blob[:4] == b"\x89PNG":
        pass
    else:
        raise ValueError(blob[:200])
    i = 8
    idat = b""
    w = h = None
    while i < len(blob):
        ln = struct.unpack_from(">I", blob, i)[0]
        k = blob[i + 4:i + 8]
        d = blob[i + 8:i + 8 + ln]
        if k == b"IHDR":
            w, h = struct.unpack_from(">II", d, 0)
        elif k == b"IDAT":
            idat += d
        elif k == b"IEND":
            break
        i += 12 + ln
    raw = zlib.decompress(idat)
    stride = w * 4
    out = bytearray()
    pos = 0
    for _y in range(h):
        pos += 1
        out += raw[pos:pos + stride]
        pos += stride
    return w, h, bytes(out)


def main():
    proc, base = spawn_server()
    try:
        return _main(base)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except Exception:
            proc.kill()


def _main(base):
    tk = A.open_toolkit()
    tk._ensure()
    bad = 0
    total = 0
    skipped = []
    for sid in (1, 15, 30, 60, 100, 200):
        # The ROUTE takes a UNIT id and resolves it to a (section, icon id) pair
        # through `App.icon` -> `Toolkit.icon_for`; the icon tables are keyed by
        # ICON id, not by unit id.  The first version of this probe looked unit 1
        # up as icon 1, which is a different picture in a different folder, and it
        # asked for every id in one table ("Units") even for the unit whose icon
        # lives in "Buildings" (unit 30 is the monastery).  Both mistakes produce
        # a MISMATCH that says nothing about the decoder.
        mapped = tk.icon_for("unit", sid)
        if not mapped.get("ok"):
            # A unit with no icon id is a real answer, not a failure: the route
            # says so in words ("this record has no icon id").  Counting it as a
            # mismatch is how the verdict once read -6/12.
            skipped.append((sid, mapped.get("why")))
            continue
        section = mapped.get("section") or "Units"
        icon_id = mapped["icon_id"]
        got = tk.icons.picture(section, icon_id)
        if not got.get("ok"):
            skipped.append((sid, got.get("why")))
            continue
        for max_side in (0, 64, 100):
            # The query key is `size`, not `max` (server.py `/api/icon`:
            # `max_side=q.get("size", [0])[0]`).  The first version sent `max=`,
            # which the route silently ignored, so all three sizes came back
            # 256x256 and the two resized cases were compared against a full-size
            # picture -- a MISMATCH that was the probe's own wrong parameter.
            url = "%s/api/icon?kind=unit&id=%d&size=%d" % (base, sid, max_side)
            try:
                b = urllib.request.urlopen(url, timeout=60).read()
            except Exception as exc:
                print("unit %-4d max=%-4d REQUEST FAILED %s" % (sid, max_side, exc))
                bad += 1
                continue
            try:
                rw, rh, rpx = rgba(b)
            except Exception as exc:
                print("unit %-4d max=%-4d UNREADABLE %s" % (sid, max_side, exc))
                bad += 1
                continue
            py = D.to_png(got["path"], max_side=max_side)
            pw, ph, ppx = rgba(py)
            total += 1
            same = (rw, rh, rpx) == (pw, ph, ppx)
            print("unit %-4d icon %-4d %-10s max=%-4d %dx%d %s"
                  % (sid, icon_id, section, max_side, rw, rh,
                     "ok" if same else "MISMATCH"))
            if not same:
                bad += 1
    for sid, why in skipped:
        print("unit %-4d skipped: %s" % (sid, why))
    print()
    print("ICON: %d/%d pixel-identical" % (total - bad, total))
    if total == 0:
        print("REFUSING: nothing was compared, so this proves nothing")
        return 1
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

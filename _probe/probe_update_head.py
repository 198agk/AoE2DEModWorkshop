"""Can the guard read the version string without inflating 93 MB?

`probe_update_guard.py` measured the candidates on the real file:
  sha256 of the compressed file            0.009 s
  load_dat (full inflate to raw)           0.118 s
  sha256 of the raw stream                 0.036 s
  Parser().parse() (for the version enum)  4.564 s   <- far too slow for a guard

The version lives in the first bytes of the RAW stream ("VER 8.9\0"), which is raw
deflate -- so a streaming decompress of one small read should be enough.  Measure
that, and confirm it agrees with what a full parse reports, because a cheaper check
that answers a different question is worse than no check.
"""
import io
import os
import sys
import time
import zlib

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace")
except Exception:
    pass

from aoe2mod import api as A                      # noqa: E402
from aoe2mod.dat import parser as P              # noqa: E402
from aoe2mod.game import locations as G          # noqa: E402


def head_bytes(path, want=64):
    """Inflate only as far as `want` bytes, then stop."""
    d = zlib.decompressobj(-15)
    with open(path, "rb") as fh:
        out = b""
        while len(out) < want:
            chunk = fh.read(1 << 14)
            if not chunk:
                break
            out += d.decompress(chunk, want - len(out))
            if d.eof:
                break
    return out


def main():
    tk = A.open_toolkit()
    dat = tk.dat_path

    t = time.time()
    head = head_bytes(dat, 64)
    dt = time.time() - t
    print("streaming head  : %r  (%.4f s)" % (head, dt))

    # The container is `VER 8.9\0` and the whole string is what the file carries.
    ver = head.split(b"\x00")[0].decode("ascii", "replace")
    print("version string  : %r" % ver)
    print("GV from string  : %r" % (P.gv_from_version_string(ver),))
    print("GV toolkit says : %r" % (tk.version,))

    # --- agreement with the full path, on every .dat we can reach ----------
    print()
    print("--- does the cheap read agree with the full parse? ---")
    rows = [(dat, "base game")]
    prof = G.find_profile_root()
    for m in G.list_mods(prof):
        p = os.path.join(m.get("path") or "", G.DAT_REL)
        if os.path.isfile(p):
            rows.append((p, m.get("name")))
    for path, label in rows[:8]:
        h = head_bytes(path, 64)
        v = h.split(b"\x00")[0].decode("ascii", "replace")
        t = time.time()
        entire = zlib.decompress(open(path, "rb").read(), -15)
        full = entire.split(b"\x00")[0].decode("ascii", "replace")
        print("%-40s head=%-9r full=%-9r same=%s  (full read %.3f s)"
              % (str(label)[:40], v, full, v == full, time.time() - t))

    # --- and how expensive is "the whole raw sha" versus the file sha ------
    print()
    print("--- sha comparisons on one installed mod ---")
    for path, label in rows[1:3]:
        t = time.time()
        fs = G.sha256_file(path)
        tf = time.time() - t
        t = time.time()
        raw = zlib.decompress(open(path, "rb").read(), -15)
        rs = __import__("hashlib").sha256(raw).hexdigest()
        tr = time.time() - t
        print("%-40s file=%.3f s raw=%.3f s  file_sha=%s raw_sha=%s"
              % (str(label)[:40], tf, tr, fs[:10], rs[:10]))


if __name__ == "__main__":
    main()

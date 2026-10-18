# -*- coding: utf-8 -*-
"""Exploration for claim 2: build the archer edit, diff the decompressed bytes.

Read-only against the game install.  Writes only under the scratch dir.
Prints enough about the byte layout around each changed offset that the real
claim-2 probe can bind offsets to records without the product's parser.
"""
import json
import os
import sys
import time
import zlib

sys.path.insert(0, r"D:\Software\AI\帝国项目")
import aoe2mod.api as A  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
HERE = os.path.dirname(os.path.abspath(__file__))
SCRATCH = os.path.join(HERE, "scratch")
OUT = os.path.join(SCRATCH, "archer_atk_plus2")

INTENT = {"intent": "unit.stat", "unit": "步弓手",
          "stat": "displayed_attack", "delta": 2}


def inflate(path):
    raw = open(path, "rb").read()
    d = zlib.decompressobj(-15)
    out = d.decompress(raw) + d.flush()
    return out, raw, d


def main():
    os.makedirs(SCRATCH, exist_ok=True)
    tk = A.open_toolkit(GAME)
    t0 = time.time()
    man = tk.build(INTENT, OUT, title="kv archer atk +2", author="kv",
                   overwrite=True)
    print("build took %.1fs" % (time.time() - t0))
    print("manifest keys:", list(man.keys()))
    print("manifest (short):", json.dumps(
        {k: man[k] for k in ("dat", "dat_raw_bytes", "dat_file_bytes",
                             "changes_dat", "edit_count", "civs_edited",
                             "reparse_ok", "reparse_leftover", "resolved",
                             "verification") if k in man},
        ensure_ascii=False)[:1500])

    base, braw, _ = inflate(DAT)
    new, nraw, d = inflate(man["dat"])
    print("base raw %d  new raw %d  delta %+d  inflate_eof=%s unused=%d"
          % (len(base), len(new), len(new) - len(base), d.eof, len(d.unused_data)))

    diffs = [i for i in range(min(len(base), len(new))) if base[i] != new[i]]
    print("differing byte positions: %d" % len(diffs))
    runs = []
    for i in diffs:
        if runs and i - runs[-1][-1] <= 2:
            runs[-1].append(i)
        else:
            runs.append([i])
    print("contiguous runs: %d" % len(runs))
    for r in runs[:6]:
        off = r[0]
        old = base[off - 4:off + 8]
        newb = new[off - 4:off + 8]
        print("  run @%d len%d  old=%s new=%s" %
              (off, len(r), old.hex(), newb.hex()))

    # what else is around?  printable strings within +/-260 bytes of run starts
    def strings(blob, lo, hi):
        out, cur, start = [], "", None
        for i in range(lo, hi):
            c = blob[i]
            if 32 <= c < 127:
                if start is None:
                    start = i
                cur += chr(c)
            else:
                if start is not None and len(cur) >= 4:
                    out.append((start - lo, cur))
                cur, start = "", None
        if start is not None and len(cur) >= 4:
            out.append((start - lo, cur))
        return out

    for r in runs[:8]:
        off = r[0]
        print("  run @%d  ctx_strings(base) %s" % (off, strings(base, off - 260, off + 260)))
    return runs, base, new, man


if __name__ == "__main__":
    main()

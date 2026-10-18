# -*- coding: utf-8 -*-
"""Every generator that writes JSON must write LF, or it re-introduces CRLF.

`sync_engine.py` now keeps the source's line endings (newline=""), which means
whatever the generators produce is what lands in the vendored tree.  Those
generators write with `open(..., "w", encoding="utf-8")`, so on Windows they
produce CRLF, and the 13 vendored artifacts come back as whole-file diffs.

Two honest options: normalise on copy, or make the generators write LF.  The
second is better -- the CRLF was never intended, and a source file carrying
CRLF makes every future byte comparison disagree about something that is not
being compared.

This adds `newline="\\n"` to JSON writes in the generator scripts.
"""
import io
import glob
import os
import re

ROOT = r"D:\Software\AI\帝国项目"
WRITE_OPEN = re.compile(r'open\(([^()]*?),\s*(["\'])w\2([^()]*?)\)')


def patch(path):
    text = io.open(path, encoding="utf-8").read()
    n = 0

    def sub(m):
        nonlocal n
        args = m.group(1)
        quote = m.group(2)
        rest = m.group(3)
        if "newline" in rest:
            return m.group(0)
        n += 1
        return 'open(%s, %sw%s, newline=%s\\n%s)' % (
            args, quote, quote, quote, quote)

    new = WRITE_OPEN.sub(sub, text)
    if not n:
        return 0
    compile(new, path, "exec")
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(new)
    return n


def main():
    total = 0
    files = 0
    for pat in ("_probe/schema/build_*.py", "_probe/semantic/*.py",
                "_probe/tools_*.py"):
        for p in sorted(glob.glob(os.path.join(ROOT, pat))):
            name = os.path.basename(p)
            if name.startswith("tools_"):
                continue
            n = patch(p)
            if n:
                files += 1
                total += n
                print("  %-46s %d write(s)" % (name, n))
    print()
    print("patched %d write(s) across %d generator(s)" % (total, files))


if __name__ == "__main__":
    main()

"""Extract entries from the Electron asar holding the DSH checkout.

This build stores each entry's ``offset`` as a STRING, not a number -- a
``isinstance(off, int)`` guard therefore classifies every entry as unpacked
and extracts nothing.  Convert, don't type-check.

Usage:
    python asar_get.py <substring> [outdir]
    python asar_get.py --grep <regex> [outdir]
"""
import json
import os
import re
import struct
import sys

ASAR = r"D:\Software\DeepSeek Harness\resources\app.asar"


def load_index():
    with open(ASAR, "rb") as f:
        f.seek(12)
        n = struct.unpack("<I", f.read(4))[0]
        hdr = json.loads(f.read(n).decode("utf-8"))
    return hdr, 12 + 4 + n


def entries(node, path=""):
    out = []
    for name, val in node.get("files", {}).items():
        p = path + "/" + name
        if "files" in val:
            out += entries(val, p)
        else:
            out.append((p, val.get("offset"), val.get("size")))
    return out


def read_entry(base, off, size):
    with open(ASAR, "rb") as f:
        f.seek(base + int(off))
        return f.read(int(size))


def main():
    hdr, base = load_index()
    allf = entries(hdr)
    mode = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else None

    if mode == "--grep":
        pat = re.compile(sys.argv[2])
        outdir = sys.argv[3] if len(sys.argv) > 3 else None
        sel = [(p, o, s) for p, o, s in allf
               if o is not None and pat.search(p)]
    else:
        sel = [(p, o, s) for p, o, s in allf
               if o is not None and mode in p]

    for p, o, s in sel:
        if outdir:
            dest = os.path.join(outdir, p.strip("/").replace("/", os.sep))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as g:
                g.write(read_entry(base, o, s))
            print("wrote %-95s %8s" % (p, s))
        else:
            print("%-100s %10s %9s" % (p, o, s))


if __name__ == "__main__":
    main()

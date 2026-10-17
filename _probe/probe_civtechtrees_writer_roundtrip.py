# -*- coding: utf-8 -*-
"""Can the CivTechTrees JSON layer be written back BYTE-EXACTLY?

Before a writer is allowed to touch a file, it must prove it can reproduce that
file untouched.  This is the same discipline the `.dat` writer follows (its
round-trip is byte-exact across 5 datasets) and it matters more here, not less:
the layer is JSON, so a well-meaning `json.dump` silently rewrites every line
ending, adds a trailing newline and reflows the indentation -- producing a file
that differs on thousands of bytes while the *parsed* content is identical.  That
diff would be blamed on the change the user made.

So measure the exact serialisation first:
  * indentation width,
  * line ending,
  * BOM presence,
  * trailing newline,
  * and whether re-serialising a PARSED file reproduces the original bytes.

Only a writer that passes all 62 files may be used to emit a mod.
"""
import json
import os
import sys

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
CT = os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees")


def fingerprint(path):
    b = open(path, "rb").read()
    crlf = b.count(b"\r\n")
    lf = b.count(b"\n")
    return {
        "bytes": len(b),
        "bom": b[:3] == b"\xef\xbb\xbf",
        "crlf": crlf,
        "lf": lf,
        "lone_lf": lf - crlf,
        "trailing_nl": b.endswith(b"\n"),
        "indent2": b'\n  "' in b.replace(b"\r\n", b"\n"),
        "tabs": b"\t" in b,
    }


def main():
    files = sorted(f for f in os.listdir(CT) if f.lower().endswith(".json"))
    print("files: %d" % len(files))
    print()

    # ---- 1. is the format uniform? --------------------------------------
    props = {}
    for fn in files:
        props[fn] = fingerprint(os.path.join(CT, fn))
    uniform = {}
    for k in ("bom", "trailing_nl", "lone_lf", "tabs"):
        vals = {p[k] for p in props.values()}
        uniform[k] = vals
        print("%-12s distinct values across files: %s" % (k, vals))
    print()

    # ---- 2. the round-trip itself ---------------------------------------
    ok = 0
    bad = []
    for fn in files:
        raw = open(os.path.join(CT, fn), "rb").read()
        obj = json.loads(raw.decode("utf-8"))
        # 2-space indent, CRLF, no trailing newline, no BOM.
        out = json.dumps(obj, ensure_ascii=False, indent=2)
        out = out.replace("\n", "\r\n").encode("utf-8")
        if out == raw:
            ok += 1
        else:
            bad.append((fn, len(raw), len(out)))
    print("BYTE-EXACT JSON ROUND-TRIP: %d / %d" % (ok, len(files)))
    if bad:
        print("  mismatches (name, on-disk bytes, re-serialised bytes):")
        for t in bad[:10]:
            print("    %s" % (t,))
        print("  -> a writer MUST NOT be used until this is 62/62; find the")
        print("     difference (indent width, line ending, key order, float")
        print("     formatting) instead of accepting a near-match.")
        return 1

    print()
    print("The exact contract a writer must honour:")
    print("  1. json.dumps(obj, ensure_ascii=False, indent=2)")
    print("  2. replace '\\n' with '\\r\\n'   (every newline, uniformly)")
    print("  3. encode UTF-8, NO BOM, NO trailing newline")
    print("  4. key ORDER is the parsed dict's order -- never re-sort")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""Inventory the structure of every resources\\_common\\dat\\*.json semantic source.

For each file: top-level type, key sample, depth, and whether the numeric keys
join to dat ids.  Prints a compact structural sketch, never the whole file.
"""
import json
import _gamepaths as GP
import os
import sys
import collections

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = (GP.DAT_DIR)


def sketch(v, depth=0, max_depth=3):
    """Return a short type sketch of a JSON value."""
    if depth > max_depth:
        return "..."
    if isinstance(v, dict):
        if not v:
            return "{}"
        keys = list(v.keys())
        first = keys[0]
        return "{%d keys: %s ...} -> %s" % (
            len(keys), ", ".join(repr(k) for k in keys[:4]),
            sketch(v[first], depth + 1, max_depth))
    if isinstance(v, list):
        if not v:
            return "[]"
        return "[%d items] -> %s" % (len(v), sketch(v[0], depth + 1, max_depth))
    return "%s(%r)" % (type(v).__name__, v if not isinstance(v, str) or len(v) < 40 else v[:40] + "...")


def int_keys(d):
    if not isinstance(d, dict):
        return 0, 0
    n = sum(1 for k in d if isinstance(k, str) and k.lstrip("-").isdigit())
    return n, len(d)


for name in sorted(os.listdir(BASE)):
    if not name.endswith(".json"):
        continue
    path = os.path.join(BASE, name)
    size = os.path.getsize(path)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("%-32s %10s  LOAD ERROR %s" % (name, size, e))
        continue
    print("=" * 78)
    print("%s  (%s bytes)" % (name, format(size, ",")))
    print("  top: %s" % sketch(data))
    if isinstance(data, dict):
        ik, tot = int_keys(data)
        print("  numeric-key entries: %d / %d" % (ik, tot))
        if ik:
            ks = sorted(int(k) for k in data if k.lstrip("-").isdigit())
            print("  numeric key range: %d .. %d" % (ks[0], ks[-1]))
        # one concrete sample entry
        k0 = list(data.keys())[0]
        print("  sample [%r]: %s" % (k0, json.dumps(data[k0], ensure_ascii=False)[:420]))

# CivTechTrees: one representative file
ctdir = os.path.join(BASE, "CivTechTrees")
if os.path.isdir(ctdir):
    files = sorted(os.listdir(ctdir))
    print("=" * 78)
    print("CivTechTrees/: %d files" % len(files))
    print("  names: %s" % ", ".join(files))
    rep = os.path.join(ctdir, files[0])
    with open(rep, encoding="utf-8") as f:
        d = json.load(f)
    print("  sample file %s:" % files[0])
    print("  top keys: %s" % list(d.keys()))
    print("  sketch: %s" % sketch(d, max_depth=2))
    # print full first building + first unit and the numeric id fields
    for k in d:
        v = d[k]
        if isinstance(v, list) and v:
            print("  %s[0] = %s" % (k, json.dumps(v[0], ensure_ascii=False)[:600]))

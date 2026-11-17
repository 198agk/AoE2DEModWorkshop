import os as _os, sys as _sys
_p = _os.path.dirname(_os.path.abspath(__file__))
while _p and not _os.path.isfile(_os.path.join(_p, "_gamepaths.py")):
    _p = _os.path.dirname(_p)
if _p and _p not in _sys.path:
    _sys.path.insert(0, _p)
import _gamepaths as GP
# -*- coding: utf-8 -*-
"""Resolve AoE2DE string IDs from the key-value text files.

Format (verified):  <id><TAB or space>"<value>"  , CRLF line endings,
UTF-8 without BOM, '//' comments, blank lines allowed.
"""
import os, re, sys, json

G = GP.GAME

# key-value files that together form the localisation database for a language.
# order matters: later files OVERRIDE earlier ones (campaign/DLC packs add ids,
# and key-value-modded-strings overrides mod strings).
KV_FILES = [
    "key-value-strings-utf8.txt",
    "key-value-paphos-strings-utf8.txt",
    "key-value-modded-strings-utf8.txt",
    "paphos-campaign-key-value-strings-utf8.txt",
    "paris-campaign-key-value-strings-utf8.txt",
    "PDLC2-campaign-key-value-strings-utf8.txt",
    "PDLC3-campaign-key-value-strings-utf8.txt",
    "PDLC4-campaign-key-value-strings-utf8.txt",
    "PDLC6-campaign-key-value-strings-utf8.txt",
    "peru-campaign-key-value-strings-utf8.txt",
    "portland-campaign-key-value-strings-utf8.txt",
    "providence-campaign-key-value-strings-utf8.txt",
    "tournament-key-value-strings-utf8.txt",
]

# line regex: id, whitespace, then a double-quoted value (value may contain ").
LINE_RE = re.compile(r'^\s*(\d+)\s+"(.*)"\s*$')


def parse_kv_file(path):
    """Return (dict of id->value, stats dict)."""
    out = {}
    stats = {"lines": 0, "comments": 0, "blank": 0, "parsed": 0,
             "unparsed": 0, "unparsed_examples": []}
    with open(path, "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8")
    for ln in text.split("\n"):
        stats["lines"] += 1
        s = ln.strip()
        if not s:
            stats["blank"] += 1
            continue
        if s.startswith("//"):
            stats["comments"] += 1
            continue
        m = LINE_RE.match(ln)
        if m:
            out[int(m.group(1))] = m.group(2)
            stats["parsed"] += 1
        else:
            stats["unparsed"] += 1
            if len(stats["unparsed_examples"]) < 8:
                stats["unparsed_examples"].append(ln.rstrip("\r"))
    return out, stats


def load_language(loc):
    """Load and merge every key-value file for language `loc`."""
    base = os.path.join(G, "resources", loc, "strings", "key-value")
    merged = {}
    per_file = []
    for name in KV_FILES:
        p = os.path.join(base, name)
        if not os.path.exists(p):
            per_file.append({"file": name, "exists": False})
            continue
        d, st = parse_kv_file(p)
        added = len([k for k in d if k not in merged])
        overridden = len(d) - added
        merged.update(d)
        per_file.append({"file": name, "exists": True, "size": os.path.getsize(p),
                         "entries": len(d), "new_ids": added,
                         "overridden": overridden, **{k: v for k, v in st.items()
                                                      if k != "lines"}})
    return merged, per_file


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    for loc in ("en", "zh"):
        d, pf = load_language(loc)
        print("=" * 78)
        print("%s: %d unique ids" % (loc, len(d)))
        for f in pf:
            print("   ", f)
        print("  id range:", min(d), "..", max(d))
        for probe in (4, 38, 74, 83, 5504):
            print("   id %-6s -> %r" % (probe, d.get(probe)))

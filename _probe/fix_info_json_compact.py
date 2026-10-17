# -*- coding: utf-8 -*-
r"""Rewrite the installed test mod's `info.json` in the compact form the game reads.

The user's mod list showed `作者: Unpublished` / `No Description` for `dsh test v6`.
Measured: every one of the 8 third-party mods on this machine writes
`{"Author":"x","CacheStatus":0,...}` with NO space after the colon; the emitter wrote
`indent=2`, and that is the only file the mod manager's validation pass fails to read
(`Unpublished` / `No Description` are the engine's own fallbacks, sitting next to
`info.json` and `Validating '%s'` in the exe's string pool).

The emitter is fixed (`aoe2mod/mod/emitter.py`).  This rewrites the already-installed
copy so the running game reads it without a rebuild, and asserts every payload file is
byte-identical afterwards -- only `info.json` changes, and its CONTENT changes only in
whitespace.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

ACC = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391"
LOCAL = os.path.join(ACC, "mods", "local")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


if "AoE2DE_s.exe" in subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq AoE2DE_s.exe"],
        capture_output=True, text=True).stdout:
    print("REFUSING: close the game first.")
    sys.exit(1)
print("game running: False")

dirs = [d for d in sorted(os.listdir(LOCAL))
        if os.path.isdir(os.path.join(LOCAL, d)) and d.startswith("dsh test")]
if not dirs:
    print("no `dsh test` mod is installed")
    sys.exit(1)
mod = os.path.join(LOCAL, dirs[-1])
print("mod:", dirs[-1])

info_path = os.path.join(mod, "info.json")
raw = open(info_path, "rb").read()
info = json.loads(raw.decode("utf-8-sig"), strict=False)
print()
print("A  before")
print("     %d bytes, %d newline(s), space-after-colon: %s"
      % (len(raw), raw.count(b"\n"),
         b'"Author": ' in raw or b'"Title": ' in raw))

# hash every OTHER file first, so we can prove nothing else moved
before = {}
for root, _d, fs in os.walk(mod):
    for f in fs:
        p = os.path.join(root, f)
        rel = os.path.relpath(p, mod)
        if rel != "info.json":
            before[rel] = sha(p)
print("     payload files to preserve: %d" % len(before))

print()
print("B  rewrite compactly")
compact = json.dumps(info, ensure_ascii=False,
                     separators=(",", ":")).encode("utf-8")
shutil.copy2(info_path, info_path + ".pretty-backup")
with open(info_path, "wb") as fh:
    fh.write(compact)
back = json.loads(open(info_path, "rb").read().decode("utf-8"),
                  strict=False)
print("     %d -> %d bytes" % (len(raw), len(compact)))
print("     keys equal:", set(back) == set(info))
for k in sorted(info):
    if back.get(k) != info.get(k):
        print("     !! %r changed" % k)
        sys.exit(1)
print("     every key's VALUE is unchanged (whitespace only)")

print()
print("C  and nothing else moved")
bad = []
for rel, h in before.items():
    p = os.path.join(mod, rel)
    if not os.path.exists(p) or sha(p) != h:
        bad.append(rel)
print("     payload files re-verified: %d/%d  problems: %s"
      % (len(before) - len(bad), len(before), bad or "none"))
assert not bad
print()
print("     note: the game's mod LIST shows the folder name, which is why the title")
print("     looked right even while the detail panel said Unpublished.")
print()
print("REWRITTEN.  Reopen the mod list in game; the panel should now show")
print("  author: dsh  and the Description text.")

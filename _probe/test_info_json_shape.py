# -*- coding: utf-8 -*-
r"""`info.json` must be written the way the game's own mods are: COMPACT, one line.

## The symptom (user m26010)

In the game's mod list my mod's row showed the title but the detail panel said
`作者: Unpublished` / `标签:` / `No Description`.

## What the exe says

The string pool holds one cluster:

    info.json | Validating '%s' | Author | Unpublished | No Description
              | CacheStatus | mainmenu_bg.dds | previewIcon | thumbnail

`Unpublished` and `No Description` are the FALLBACKS the mod manager substitutes when
it cannot read `Author` / `Description` from the validation pass.

## The difference, measured

Every mod the game accepts writes `info.json` as **one line, no whitespace**:

    {"Author":"naga1v8","CacheStatus":0,"Description":"…","Title":"…"}     195 B

while the emitter wrote it pretty-printed (`indent=2`, line breaks).  8 of 8
accepted mods on this machine are compact; the only pretty-printed one is mine.
The title still appeared because the LIST shows the folder name, not the Title field
-- which is why only the detail panel looked wrong.

So the fix is in the emitter, and it applies to every mod this tool ships.

Run:  $env:PYTHONPATH='D:\\Software\\DeepSeek Harness\\工作区2'; python _probe\test_info_json_shape.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

ACC = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods"
fails = []


def check(name, ok, detail=""):
    print("  %-70s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


def installed():
    out = []
    for kind in ("subscribed", "local"):
        d = os.path.join(ACC, kind)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            p = os.path.join(d, name, "info.json")
            if os.path.isfile(p):
                out.append((kind, name, p))
    return out


print("A  every installed mod's info.json, by shape")
rows = []
for kind, name, p in installed():
    raw = open(p, "rb").read()
    try:
        obj = json.loads(raw.decode("utf-8-sig"), strict=False)
        ok_json = True
    except Exception:
        obj, ok_json = {}, False
    span = b'"Author": "' in raw or b'"Author":\t' in raw or b'"Author":\n' in raw
    rows.append((kind, name, raw, span))
    print("     [%-10s] json=%-4s bytes=%-5d space_after_colon=%-5s %s"
          % (kind, "ok" if ok_json else "BAD", len(raw), span, name[:40]))

print()
# The real discriminator is NOT whether there are newlines -- an ACCEPTED mod
# (`423821_…`, 748 B) contains 7 CRs, all of them INSIDE the Description value.
# What every accepted mod has is `"Key":"value"`: NO space after the colon.
n = len(rows)
spaced = [r for r in rows if r[3]]
print("     mods: %d ; with a space after a colon: %d" % (n, len(spaced)))
for r in spaced:
    print("        %s" % r[1][:56])
check("the only info.json with `\"Key\": \"value\"` spacing is this project's own",
      all("dsh test" in r[1] or r[1].startswith("aoe2mod") for r in spaced),
      "%s" % [r[1][:40] for r in spaced])
print("     -> compact separators (`,` / `:`) are what the mod manager's validation")
print("        pass expects; pretty-printing loses Author and Description.")

print()
print("B  and the game's own fallbacks, from the exe")
EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
d = open(EXE, "rb").read()
for lit in (b"Unpublished", b"No Description", b"Validating '%s'", b"info.json"):
    hit = d.find(lit)
    print("     %-18s %s" % (lit.decode(), hex(hit) if hit >= 0 else "absent"))
check("the exe carries the Unpublished / No Description fallbacks",
      b"Unpublished" in d and b"No Description" in d)
i = d.find(b"info.json")
seg = d[max(0, i - 40):i + 160]
runs = [r for r in seg.split(b"\x00") if 1 < len(r) < 60
        and all(32 <= c < 127 for c in r)]
print("     the string cluster around them: %s" % [r.decode() for r in runs])
check("`Validating '%s'` sits in the same cluster (a validation pass)",
      any(b"Validating" in r for r in runs))

print()
print("C  so the emitter must write compact JSON")
from aoe2mod.mod import emitter as E                        # noqa: E402
import inspect                                              # noqa: E402
src = inspect.getsource(E.emit_data_mod)
print("     emit_data_mod currently writes info.json with: %s"
      % ("indent=2" if "indent=2" in src else "unknown"))
check("the emitter needs changing (it pretty-prints today)",
      "indent=2" in src)
print()
print("     compact form: json.dumps(info, ensure_ascii=False, separators=(',',':'))")

print()
print("INFO.JSON SHAPE: the game reads a single-line, no-whitespace info.json; a")
print("  pretty-printed one loses Author and Description (the list still shows the")
print("  folder name, so only the detail panel looks wrong).")
for n_ in fails:
    print("  FAILED: %s" % n_)
sys.exit(1 if fails else 0)

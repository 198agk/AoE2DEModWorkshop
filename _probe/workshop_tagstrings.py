"""Resolve IDS_MODMGR_TAG_* to the game's own localized display names.

The exe stores canonical English in a string table; the game's user-facing
wording lives in resources/<lang>/strings/key-value/key-value-strings-utf8.txt.

This gives the tool the *game's own* tag wording in every shipped language
(the project rule: never invent field names; show the game's own words).

Read-only.
"""
import os
import re

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
KEYS = ["IDS_MODMGR_TAG_ANY", "IDS_MODMGR_TAG_AI", "IDS_MODMGR_TAG_CAMPAIGN",
        "IDS_MODMGR_TAG_DATA", "IDS_MODMGR_TAG_GRAPHIC", "IDS_MODMGR_TAG_MOVIE",
        "IDS_MODMGR_TAG_MUSIC", "IDS_MODMGR_TAG_RANDOM", "IDS_MODMGR_TAG_SCENARIO",
        "IDS_MODMGR_TAG_SOUND", "IDS_MODMGR_TAG_SPEECH", "IDS_MODMGR_TAG_TAUNT",
        "IDS_MODMGR_TAG_TERRAIN", "IDS_MODMGR_TAG_MENUBACKGROUND", "IDS_MODMGR_TAG_UI",
        "IDS_MODMGR_TAG_TEXT", "IDS_MODMGR_TAG_OFFICIAL", "IDS_MODMGR_TAG_EVENT",
        "IDS_MODMGR_TAG_GAME_VARIANT_RETURN_OF_ROME", "IDS_MODMAN_TAGS"]


def load_kv(path):
    """id<tab>"value"  with // comments."""
    out = {}
    with open(path, "rb") as f:
        txt = f.read().decode("utf-8-sig", "replace")
    for line in txt.splitlines():
        s = line.strip()
        if not s or s.startswith("//"):
            continue
        m = re.match(r'^(\d+)\s+"(.*)"\s*$', s)
        if m:
            out[m.group(1)] = m.group(2)
    return out


# 1) canonical English names straight from the exe string table
EXE = os.path.join(GAME, "AoE2DE_s.exe")
raw = open(EXE, "rb").read()
print("=== exe string-table neighbourhood (canonical keys) ===")
start = raw.find(b"IDS_MODMGR_TAG_ANY")
if start > 0:
    chunk = raw[start - 40:start + 900]
    for s in re.findall(rb"[\x20-\x7e]{3,}", chunk):
        print("   %s" % s.decode("ascii"))

# 2) look up the keys in every language's string files
print()
print("=== IDS_MODMGR_TAG_* found in shipped localization files ===")
langdir = os.path.join(GAME, "resources")
langs = sorted(d for d in os.listdir(langdir)
               if os.path.isdir(os.path.join(langdir, d, "strings", "key-value")))
print("   language dirs: %s" % langs)
per_lang_hits = {}
for lang in langs:
    d = os.path.join(langdir, lang, "strings", "key-value")
    if not os.path.isdir(d):
        continue
    for fn in os.listdir(d):
        if not fn.endswith(".txt"):
            continue
        kv = load_kv(os.path.join(d, fn))
        # search by VALUE == key text (the .txt files are numeric-id keyed)
        hits = {k: v for k, v in kv.items() if v in KEYS}
        if hits:
            per_lang_hits.setdefault(lang, {}).update(hits)

if not per_lang_hits:
    print("   (no direct key-name matches -- the txt files are numeric-keyed;")
    print("    the exe maps IDS_* -> numeric id, so search by that id instead)")
else:
    for lang, hits in sorted(per_lang_hits.items()):
        print("   %s: %d hits" % (lang, len(hits)))

# 3) the numeric id sits right after each IDS_* key in the exe; dump it
print()
print("=== numeric string ids adjacent to each IDS_MODMGR_TAG_* key ===")
for k in KEYS:
    i = raw.find(k.encode())
    if i < 0:
        print("   %-46s NOT FOUND" % k)
        continue
    nb = raw[i + len(k): i + len(k) + 48]
    nums = re.findall(rb"\d{3,7}", nb)
    # also read a little-endian u32 in the next 32 bytes
    import struct
    cand = []
    for off in range(0, 24, 4):
        try:
            v = struct.unpack_from("<I", raw, i + len(k) + off)[0]
        except Exception:
            continue
        if 1000 <= v <= 200000:
            cand.append((off, v))
    print("   %-46s ascii-nums=%-12s u32-cands=%s"
          % (k, [n.decode() for n in nums[:3]], cand[:3]))

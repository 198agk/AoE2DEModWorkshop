#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a29_class_namespace.py -- decide the atlas namespace per entity CLASS, empirically.

WHY:  a26/a27 showed ingameunits[028] = TREBUCHET while ingamebuildings[028] =
      TOWN CENTER.  Unit 42 'Trebuchet' and unit 71 'Town Center' BOTH carry
      IconID 28, so "Type==80 -> ingamebuildings" misassigns the Trebuchet.
      a28 showed Class==3 alone is also wrong (gates/walls/towers are Class
      39/27/52 yet clearly are buildings).

INSTRUMENT (independent of any internal token): the ingamebuildings atlas is the
only name-bearing one -- its RefName is 'BuildingIcons<NNN><CamelName>' and its
loose file is '<NNN>_<snake_name>.DDS'  (e.g. 035_farm.DDS / BuildingIcons035Farm).
So for an entity whose IconID is NNN, ask: does the building atlas entry for NNN
describe THIS entity?  Compare entity English name tokens against the CamelName.
Group the answer by entity Class.  A class that genuinely lives in the building
namespace should score high; a class that is really unit-space should score ~0.

CONTROLS
  * Type==70 units  -> expect LOW building-name plausibility (they are not buildings)
  * Type==80 Class 3 (Barracks, Castle, ...) -> expect HIGH
If the discriminator works, the two controls straddle the Type==80 classes and the
outlier classes fall on the unit side.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import json, os, re, struct

HERE = os.path.dirname(os.path.abspath(__file__))
WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
GRA = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"
J = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
ATLS = {e.get("AtlasDef", e)["Name"]: e.get("AtlasDef", e) for e in J["AtlasTextures"]}
UA = "ingameunits"
C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))
SEM = json.load(open(_HERE_PATH("_probe", "semantic", "unit_names.json"),
                     encoding="utf-8"))

STOP = {"age", "the", "and", "of", "icon", "sprite", "de"}

def toks(s):
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s or "")
    s = re.sub(r"([A-Za-z])([0-9])", r"\1 \2", s)
    s = re.sub(r"([0-9])([A-Za-z])", r"\1 \2", s)
    return set(x for x in re.split(r"[^A-Za-z0-9]+", s.lower())
               if len(x) > 2 and not x.isdigit() and x not in STOP)

def emb_of(name):
    """IconID -> atlas entry, keyed by the embedded numeric stem."""
    out = {}
    for t in ATLS[name]["Textures"]:
        stem = t["FileName"].rsplit("/", 1)[-1].rsplit(".", 1)[0]
        h = stem.split("_")[0]
        if h.isdigit():
            out[int(h)] = t
    return out

U = emb_of("ingameunits")
B = emb_of("ingamebuildings")
T = emb_of("ingametechs")
print("atlas entry counts keyed by numeric stem: ingameunits %d ingamebuildings %d ingametechs %d"
      % (len(U), len(B), len(T)))

# loose descriptive name for a building entry, from its file name
def bdesc(n):
    stem = B[n]["FileName"].rsplit("/", 1)[-1].rsplit(".", 1)[0]
    return re.sub(r"^[0-9]+_", "", stem)

def bplaus(en, n):
    return len(toks(en) & toks(bdesc(n))) > 0

byid = {}
for civ in C:
    for u in civ["units"]:
        byid.setdefault(u["id"], u)

print("\n=== Type 70 (unit space): building-name plausibility of its IconID ===")
t70 = [u for u in byid.values() if u.get("type") == 70 and u.get("icon_id", -1) > 0]
hit = [u for u in t70 if u["icon_id"] in B and bplaus((SEM.get(str(u["id"])) or {}).get("en") or "", u["icon_id"])]
print("Type70 with IconID>0 : %d ; whose BUILDING entry name matches : %d (%.1f%%)"
      % (len(t70), len(hit), 100.0 * len(hit) / max(1, len(t70))))
print("   matches: %s" % [(u["id"], (SEM.get(str(u['id'])) or {}).get('en'), bdesc(u['icon_id']))
                          for u in hit][:12])
print("   -> so a unit's IconID usually has NO building entry, or an unrelated one")

print("\n=== Type 80, broken down by Class ===")
print("%-6s %5s %6s %6s %6s %8s  %s" % ("class", "n", "inB", "inU", "nameOK", "OK/B%", "sample"))
rows80 = {}
for u in byid.values():
    if u.get("type") != 80 or u.get("icon_id", -1) <= 0:
        continue
    rows80.setdefault(u.get("class"), []).append(u)
for cl in sorted(rows80, key=lambda c: -len(rows80[c])):
    us = rows80[cl]
    nb = sum(1 for u in us if u["icon_id"] in B)
    nu = sum(1 for u in us if u["icon_id"] in U)
    ok = [u for u in us if u["icon_id"] in B
          and bplaus((SEM.get(str(u["id"])) or {}).get("en") or "", u["icon_id"])]
    samp = "; ".join("%s->%s" % (((SEM.get(str(u["id"])) or {}).get("en") or "?")[:16],
                                 bdesc(u["icon_id"]) if u["icon_id"] in B else "--")
                     for u in us[:3])
    print("%-6s %5d %6d %6d %6d %7.1f%%  %s"
          % (cl, len(us), nb, nu, len(ok), 100.0 * len(ok) / max(1, nb), samp))

print("\n=== The 3 candidate rules, applied to the 4 decisive entities ===")
DEC = [42, 71, 12, 79, 235, 50, 72, 117, 444, 331]
for uid in DEC:
    u = byid[uid]
    en = (SEM.get(str(uid)) or {}).get("en") or "?"
    n = u["icon_id"]
    print("  id %-5s %-26s type=%-3s class=%-3s icon=%-4s | B:%-34s | U:%s"
          % (uid, en[:26], u.get("type"), u.get("class"), n,
             ("%s ok=%s" % (bdesc(n), bplaus(en, n))) if n in B else "ABSENT",
             U[n]["RefName"] if n in U else "ABSENT"))

# ---- pixel proof that the two atlases really hold DIFFERENT images for shared N ----
def hdr(p):
    b = open(p, "rb").read(160)
    return {"w": struct.unpack_from("<I", b, 16)[0], "h": struct.unpack_from("<I", b, 12)[0],
            "fourcc": b[84:88].decode("latin1").strip("\x00"),
            "off": 148 if b[84:88] == b"DX10" else 128}

def _c565(c0, c1, d1):
    def ex(c):
        r = (c >> 11) & 31; g = (c >> 5) & 63; bl = c & 31
        return ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (bl << 3) | (bl >> 2))
    a, b2 = ex(c0), ex(c1)
    if not d1 or c0 > c1:
        return [a, b2, tuple((2 * a[k] + b2[k]) // 3 for k in range(3)),
                tuple((a[k] + 2 * b2[k]) // 3 for k in range(3))]
    return [a, b2, tuple((a[k] + b2[k]) // 2 for k in range(3)), (0, 0, 0)]

def _a5(blk, i):
    a0, a1 = blk[0], blk[1]
    if a0 > a1:
        tab = [a0, a1] + [((7 - k) * a0 + k * a1) // 7 for k in range(1, 7)]
    else:
        tab = [a0, a1] + [((5 - k) * a0 + k * a1) // 5 for k in range(1, 5)] + [0, 255]
    return tab[(int.from_bytes(blk[2:8], "little") >> (3 * i)) & 7]

def dec(p, lx, ly, w, h):
    d = hdr(p)
    mode = d["fourcc"]
    raw = open(p, "rb").read()[d["off"]:]
    W = d["w"]
    out = bytearray(w * h * 4)
    bs = 8 if mode == "DXT1" else 16
    bw = (W + 3) // 4
    for by in range(ly // 4, (ly + h - 1) // 4 + 1):
        for bx in range(lx // 4, (lx + w - 1) // 4 + 1):
            o = (by * bw + bx) * bs
            blk = raw[o:o + bs]
            if len(blk) < bs:
                continue
            if mode == "DXT1":
                c0, c1, bits = struct.unpack_from("<HHI", blk, 0)
                cols = _c565(c0, c1, True)
            else:
                c0, c1 = struct.unpack_from("<HH", blk, 8)
                bits = struct.unpack_from("<I", blk, 12)[0]
                cols = _c565(c0, c1, False)
            for py in range(4):
                y = by * 4 + py
                if y < ly or y >= ly + h:
                    continue
                for px in range(4):
                    x = bx * 4 + px
                    if x < lx or x >= lx + w:
                        continue
                    i = py * 4 + px
                    idx = (bits >> (2 * i)) & 3
                    r, g, bl = cols[idx]
                    a = 0 if (mode == "DXT1" and idx == 3 and c0 <= c1) else (
                        255 if mode == "DXT1" else (_a5(blk, i) if mode == "DXT5" else
                                                   (blk[i // 2] >> (4 * (i % 2)) & 0xF) * 17))
                    o2 = ((y - ly) * w + x - lx) * 4
                    out[o2:o2 + 4] = bytes((r, g, bl, a))
    return w, h, bytes(out)

def uv(t, W, H):
    lx = int(round(float(t["imageTLX"]) * W + 0.5)); ly = int(round(float(t["imageTLY"]) * H + 0.5))
    hx = int(round(float(t["imageBRX"]) * W - 0.5)); hy = int(round(float(t["imageBRY"]) * H - 0.5))
    return lx, ly, hx - lx + 1, hy - ly + 1

SU = os.path.join(WID, ATLS[UA]["DefaultSource"].replace("/", os.sep))
SB = os.path.join(WID, ATLS["ingamebuildings"]["DefaultSource"].replace("/", os.sep))
hu, hb = hdr(SU), hdr(SB)
print("\n=== shared numeric stems: are the two atlases the SAME image? ===")
shared = sorted(set(U) & set(B))
print("shared stems: %d ; units-only %d ; buildings-only %d"
      % (len(shared), len(set(U) - set(B)), len(set(B) - set(U))))
diffs = []
for n in shared:
    lx, ly, w, h = uv(U[n], hu["w"], hu["h"])
    _, _, ap = dec(SU, lx, ly, w, h)
    lx2, ly2, w2, h2 = uv(B[n], hb["w"], hb["h"])
    _, _, bp = dec(SB, lx2, ly2, w2, h2)
    if len(ap) != len(bp):
        diffs.append((n, -1.0)); continue
    m = sum(abs(ap[i] - bp[i]) for i in range(len(ap))) / float(len(ap))
    diffs.append((n, m))
same = [d for d in diffs if d[1] >= 0 and d[1] < 12]
diff = [d for d in diffs if d[1] >= 12 or d[1] < 0]
print("identical (MAD<12): %d ; DIFFERENT: %d" % (len(same), len(diff)))
print("   identical stems sample: %s" % [d[0] for d in same][:20])
print("   differing stems sample : %s" % [(d[0], round(d[1], 1)) for d in diff][:20])
print("   -> a shared stem does NOT imply a shared image, so namespace choice is load-bearing")

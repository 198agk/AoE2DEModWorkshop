# -*- coding: utf-8 -*-
"""Find the widget that actually owns the chibi's screen position, and get the
alignment math right.

Two things were shaky:
 1. cp_emblem_pos.py treated the Collection's yorigin as an absolute TOP
    coordinate, which is wrong for BottomLeft alignment.
 2. The resulting box was partly hand-patched, so "which widget owns this pixel"
    was never actually answered.

Correct model (validated against two known-good files):
   resourcepanel.json Collection: xorigin 0, yorigin 0, w 1935, h 228, TopLeft
      -> spans ref (0..1935, 0..228) = the top resource bar.  [matches screenshots]
   scorepanel.json   Collection: xorigin 3840, yorigin 2160, w 3840, h 2160, BottomRight
      -> spans ref (0..3840, 0..2160) = full screen.        [matches]
   So: Top*  -> origin is the TOP edge, box extends DOWN by height.
       Bottom*-> origin is the BOTTOM edge, box extends UP by height.

Here we compute boxes for BOTH models, then report every widget (across all
widgetui jsons) whose box contains the chibi's measured screen centre, so the
owner is identified by containment rather than by assuming.

Chibi centre measured in f1 (red-dress centroid, region offset 380,1080):
   absolute screenshot approx (750, 1390).  Reference coords = /0.7109.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import json
import numpy as np
from PIL import Image, ImageDraw

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WID = os.path.join(GAME, "widgetui")
OUT = _HERE_PATH("_shots", "ui")
SHOTS = r"C:\Users\26913\.dsh\attachments\v1\objects"

REF_W, REF_H = 3840, 2160
SHOT_W, SHOT_H = 2730, 1535
S = SHOT_W / REF_W

CHIBI_SHOT = (750.0, 1390.0)
CHIBI_REF = (CHIBI_SHOT[0] / S, CHIBI_SHOT[1] / S)
print("chibi screenshot centre %s -> ref %s" % (CHIBI_SHOT, CHIBI_REF))

def box_from_vp(vp, is_collection=False):
    """Return (x0,y0,x1,y1) in ref coords, or None."""
    if not vp:
        return None
    x = vp.get("xorigin", 0)
    y = vp.get("yorigin", 0)
    w = vp.get("width", 0)
    h = vp.get("height", 0)
    if not w or not h:
        return None
    al = (vp.get("alignment") or "TopLeft").lower()
    if al.startswith("top"):
        y0, y1 = y, y + h
    elif al.startswith("bottom"):
        y0, y1 = y - h, y
    elif al.startswith("centre") or al.startswith("center"):
        y0, y1 = y - h / 2.0, y + h / 2.0
    else:
        y0, y1 = y, y + h
    if al.endswith("left"):
        x0, x1 = x, x + w
    elif al.endswith("right"):
        x0, x1 = x - w, x
    elif al.endswith("centre") or al.endswith("center"):
        x0, x1 = x - w / 2.0, x + w / 2.0
    else:
        x0, x1 = x, x + w
    return (x0, y0, x1, y1)

def offset_child(al, w, h, pw, ph):
    """Child's top-left offset within a parent box of size pw x ph."""
    a = (al or "TopLeft").lower()
    if a.startswith("top"):
        dy = 0
    elif a.startswith("bottom"):
        dy = ph - h
    else:
        dy = (ph - h) / 2.0
    if a.endswith("left"):
        dx = 0
    elif a.endswith("right"):
        dx = pw - w
    else:
        dx = (pw - w) / 2.0
    return dx, dy

hits = []

def walk(w, px, py, pw, ph, path, fname):
    vp = w.get("ViewPort") or {}
    cw = vp.get("width", 0) or pw
    chh = vp.get("height", 0) or ph
    dx, dy = offset_child(vp.get("alignment"), cw, chh, pw, ph)
    ax = px + vp.get("xorigin", 0) + dx
    ay = py + vp.get("yorigin", 0) + dy
    p = path + "/" + str(w.get("Name", "?"))
    if cw and chh:
        if ax <= CHIBI_REF[0] <= ax + cw and ay <= CHIBI_REF[1] <= ay + chh:
            hits.append((fname, p, ax, ay, cw, chh, w.get("Type")))
    for c in w.get("ChildWidgets") or []:
        if "Widget" in c:
            walk(c["Widget"], ax, ay, cw, chh, p, fname)

files = [f for f in sorted(os.listdir(WID)) if f.endswith(".json")]
print("scanning %d widgetui json files..." % len(files))
for f in files:
    try:
        d = json.load(open(os.path.join(WID, f), "r", encoding="utf-8"))
    except Exception:
        continue
    if not isinstance(d, dict):
        continue
    col = d.get("Collection")
    if not isinstance(col, dict):
        continue
    b = box_from_vp(col.get("ViewPort"), True)
    if not b:
        continue
    x0, y0, x1, y1 = b
    pw, ph = x1 - x0, y1 - y0
    for item in col.get("Widgets") or []:
        if "Widget" in item:
            walk(item["Widget"], x0, y0, pw, ph, "", f)

print()
print("=== widgets whose box CONTAINS the chibi (ref %s) ===" % (tuple(round(v) for v in CHIBI_REF),))
if not hits:
    print("   none — alignment model still wrong")
for fname, p, ax, ay, cw, chh, t in sorted(hits, key=lambda z: z[4] * z[5]):
    print("   %-22s %-46s ref(%5.0f,%5.0f) %4.0fx%3.0f type=%s"
          % (fname, p[:46], ax, ay, cw, chh, t))
    print("        -> screenshot x %d..%d  y %d..%d"
          % (ax * S, (ax + cw) * S, ay * S, (ay + chh) * S))

# visual: draw the two candidate CivEmblem boxes on a big bottom-left crop
f1 = Image.open(os.path.join(SHOTS, "02",
    "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82")).convert("RGB")
CROP = (0, 1200, 1400, 1535)
c = f1.crop(CROP)
Z = 1.6
c = c.resize((int(c.width * Z), int(c.height * Z)), Image.LANCZOS)
d = ImageDraw.Draw(c)

def rect(box, colr, label):
    x0, y0, x1, y1 = box
    X0 = (x0 * S - CROP[0]) * Z
    Y0 = (y0 * S - CROP[1]) * Z
    X1 = (x1 * S - CROP[0]) * Z
    Y1 = (y1 * S - CROP[1]) * Z
    d.rectangle([X0, Y0, X1, Y1], outline=colr, width=2)
    d.text((X0 + 4, Y0 + 3), label, fill=colr)

rect((403, 1839, 853, 2119), (255, 0, 0), "model A: x=403 y=1746+93")
rect((761, 1839, 1211, 2119), (0, 255, 255), "model B: abs x=761 (hand-patched)")
d.line([CHIBI_SHOT[0] * 1 - CROP[0] * 1, 0, CHIBI_SHOT[0] - CROP[0], c.height], fill=(0, 255, 0), width=1)
c.save(os.path.join(OUT, "cp_box_overlay.png"))
print()
print("wrote cp_box_overlay.png", c.size)

# -*- coding: utf-8 -*-
"""Broad visual verification: render one frame from many different sprite
families and assemble a labelled contact sheet.  Read-only.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sldlib import read_sld, render_frame
from PIL import Image, ImageDraw

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
OUT = _HERE_PATH("_shots", "sld_render")
os.makedirs(OUT, exist_ok=True)

PICK = [
    "u_arc_archer_idlea_x1.sld",
    "u_arc_archer_attackA_x1.sld",
    "u_arc_skirmisher_idlea_x1.sld",
    "u_inf_militia_idlea_x1.sld",
    "u_inf_spearman_idlea_x1.sld",
    "u_inf_champion_idlea_x1.sld",
    "u_cav_knight_idlea_x1.sld",
    "u_cav_scout_idlea_x1.sld",
    "u_monk_west_idlea_x1.sld",
    "u_sie_ram_idlea_x1.sld",
    "u_sie_mangonel_idlea_x1.sld",
    "a_herd_sheep_idleA_x1.sld",
    "a_hunt_deer_idleA_x1.sld",
    "a_herd_goose_idleA_x1.sld",
    "t_tree_oak_x1.sld",
    "t_gold_x1.sld",
    "b_afri_stable_age2_x1.sld",
    "b_afri_house_age2_x1.sld",
    "b_afri_barracks_age2_x1.sld",
]

# resolve real filenames (some guesses may not exist)
present = set(os.listdir(GP))
for p in list(PICK):
    if p not in present:
        stem = p.replace("_x1.sld", "")
        alts = [f for f in present if f.startswith(stem) and f.endswith("_x1.sld")]
        print("(substituting) %-40s -> %s" % (p, alts[:1]))
        PICK[PICK.index(p)] = alts[0] if alts else p

rows = []
for fn in PICK:
    p = os.path.join(GP, fn)
    if not os.path.exists(p):
        print("(missing)", fn)
        continue
    s = read_sld(p)
    if not s.frames:
        continue
    fr = s.frames[0]
    canvas, w, h, info = render_frame(fr)
    im = Image.frombytes("RGBA", (w, h), bytes(canvas))
    rect = info.get("main_rect")
    if rect:
        x1, y1, x2, y2 = rect
        im = im.crop((max(0, x1 - 8), max(0, y1 - 8), x2 + 8, y2 + 8))
    else:
        bb = im.getbbox()
        im = im.crop(bb) if bb else im
    sc = max(1, min(4, 160 // max(1, im.height)))
    im = im.resize((im.width * sc, im.height * sc), Image.NEAREST)
    rows.append((fn, im, s, info, sc))
    print("%-38s n=%-5d walked=%-5d fo=%d ft=0x%02x rect=%s layers=%s"
          % (fn, s.num_frames, len(s.frames), s.frame_offset, fr.frame_type,
             rect, "+".join(sorted(fr.layers))))

if rows:
    COLS = 5
    cw = max(r[1].width for r in rows) + 14
    ch = max(r[1].height for r in rows) + 30
    nrows = (len(rows) + COLS - 1) // COLS
    sheet = Image.new("RGBA", (cw * COLS, ch * nrows), (18, 18, 22, 255))
    d = ImageDraw.Draw(sheet)
    for i, (fn, im, s, info, sc) in enumerate(rows):
        cx, cy = (i % COLS) * cw, (i // COLS) * ch
        d.text((cx + 4, cy + 3), fn[:34], fill=(230, 230, 230))
        d.text((cx + 4, cy + 14), "%dx%d sld  x%d" % (im.width, im.height, sc),
               fill=(150, 150, 150))
        sheet.alpha_composite(im, (cx + 6, cy + 28))
    p = os.path.join(OUT, "sld_broad_verify.png")
    sheet.save(p)
    print("\n->", p, sheet.size)

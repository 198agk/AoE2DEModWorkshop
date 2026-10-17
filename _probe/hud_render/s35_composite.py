# -*- coding: utf-8 -*-
"""Target 3: composite overlay of BOTH panels onto a plausible backdrop.

The backdrop is taken from a REAL screenshot's terrain (the ground below the HUD bar
in shot0, tiled), so the composite shows the renderer's output in a realistic context
without pretending to be a screenshot. Deliberately NOT a fake screenshot: the panels
are drawn at the measured HUD scale 0.5980 over a 2730x1535 canvas.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import numpy as np
from PIL import Image, ImageDraw

O = _HERE_PATH("_probe", "hud_render")
AT = r"C:\Users\26913\.dsh\attachments\v1\objects"
SHOT0 = os.path.join(AT, "02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82")
SC = 0.5980
W, H = 2730, 1535
rep = []

# backdrop: a big patch of real terrain from the lower-left of the screenshot (no HUD)
src = Image.open(SHOT0).convert("RGB")
ground = src.crop((0, 200, 1400, 900)).resize((W, H), Image.LANCZOS)
canvas = ground.copy()

# resource panel: ref rect (0,0,1750,276) TopLeft
rp = Image.open(os.path.join(O, "out", "resourcepanel_mod_4k.png")).convert("RGBA")
rpc = rp.crop((0, 0, 1750, 276))
rp_s = rpc.resize((int(round(1750 * SC)), int(round(276 * SC))), Image.LANCZOS)
canvas.alpha_composite if False else None
base = canvas.convert("RGBA")
base.alpha_composite(rp_s, (0, 0))
rep.append("resourcepanel.json -> screen (0,0) %dx%d" % rp_s.size)

# score panel: ref rect (3440,1400,400,400)
sp = Image.open(os.path.join(O, "out", "scorepanel_mod_4k.png")).convert("RGBA")
spc = sp.crop((3440, 1400, 3840, 1800))
sp_s = spc.resize((int(round(400 * SC)), int(round(400 * SC))), Image.LANCZOS)
px, py = int(round(3440 * SC)), int(round(1400 * SC))
base.alpha_composite(sp_s, (px, py))
rep.append("scorepanel.json   -> screen (%d,%d) %dx%d" % (px, py, sp_s.size[0], sp_s.size[1]))

out = base.convert("RGB")
d = ImageDraw.Draw(out)
d.text((8, H - 22), "COMPOSITE (not a screenshot): rendered resourcepanel.json + scorepanel.json "
                    "at measured HUD scale %.4f over real terrain from shot0" % SC, fill=(255, 240, 140))
out.save(os.path.join(O, "HUD_COMPOSITE.png"))
rep.append("")
rep.append("wrote HUD_COMPOSITE.png %dx%d" % out.size)
rep.append("NOTE: the score panel is placed at its layout-defined position even though the")
rep.append("real screenshots do not show it (it is a toggled overlay) - this composite")
rep.append("demonstrates geometry, NOT agreement with a real capture.")
print("\n".join(rep))
open(os.path.join(O, "composite.txt"), "w", encoding="utf-8").write("\n".join(rep))

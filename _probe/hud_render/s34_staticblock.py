# -*- coding: utf-8 -*-
"""What IS the most static 239x239 block at (2400,1280)? Verify before claiming it is the minimap."""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import numpy as np
from PIL import Image, ImageDraw
AT = r"C:\Users\26913\.dsh\attachments\v1\objects"
SHOTS = [os.path.join(AT, d, s) for d, s in [
    ("02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82"),
    ("2f", "2fe5282335f5d309abf86f9cd8afee0fb3d2407ce8296985b65d0f71d21da974"),
    ("16", "16175bb0620c40734d7a57b380781a09c713e7ff4c0f0c7be6726c59eea614be"),
    ("8e", "8eeadcf84b38696ac0ede7aedaf08ee6eff1812468c8d43fa667e2376c877850"),
    ("89", "89bdabdd26b4c0ada57121bc0851f93ee52aa18080e51a9274406c1dee0bd9f9"),
]]
O = _HERE_PATH("_probe", "hud_render")
im = Image.open(SHOTS[0]).convert("RGB")
W, H = im.size
# bottom-right quadrant, 2x
q = im.crop((W - 900, H - 500, W, H))
sheet = Image.new("RGB", (900 * 2, 500 * 2 + 24), (14, 14, 16))
d = ImageDraw.Draw(sheet)
d.text((8, 6), "REAL screenshot bottom-right 900x500 at 2x  (cyan box = most-static 239x239 window at 2400,1280)", fill=(255, 226, 110))
sheet.paste(q.resize((1800, 1000), Image.LANCZOS), (0, 24))
d2 = ImageDraw.Draw(sheet)
bx, by = (2400 - (W - 900)) * 2, (1280 - (H - 500)) * 2 + 24
d2.rectangle([bx, by, bx + 239 * 2, by + 239 * 2], outline=(0, 255, 255), width=3)
sheet.save(os.path.join(O, "chk_staticblock.png"))
print("screenshot", im.size, "-> wrote chk_staticblock.png", sheet.size)
print("most-static window screen rect (2400,1280)-(2639,1519); image is %dx%d so it is %s the right/bottom edge"
      % (W, H, "at" if 2639 <= W and 1519 <= H else "CLIPPED by"))
print("  x 2400..2639 of %d -> %.1f%%..%.1f%% across" % (W, 100 * 2400 / W, 100 * 2639 / W))
print("  y 1280..1519 of %d -> %.1f%%..%.1f%% down" % (H, 100 * 1280 / H, 100 * 1519 / H))

# -*- coding: utf-8 -*-
"""Look at the exact screen region where the BOTTOM command-panel CivEmblem renders.

Alignment interpretation validated by resourcepanel.json (TopLeft origin 0,0 =
top bar). For Bottom* alignment, yorigin measures upward from the screen bottom,
so the Collection with yorigin=2159 height=413 spans ref y 1746..2159, i.e. the
bottom HUD strip. Its child CivEmblem (rel 403,93, 450x280, TopLeft) lands at
ref (761..1211, 1839..2119) -> screenshot (541..861, 1307..1506).

Crop that generously from every frame and magnify; also crop a wide bottom strip
so the whole command panel is visible at once.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
from PIL import Image, ImageDraw

SHOTS = r"C:\Users\26913\.dsh\attachments\v1\objects"
OUT = _HERE_PATH("_shots", "ui")

F = [
    ("f1_29s", "02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82"),
    ("f2_37s", "2f", "2fe5282335f5d309abf86f9cd8afee0fb3d2407ce8296985b65d0f71d21da974"),
    ("f3_43s", "16", "16175bb0620c40734d7a57b380781a09c713e7ff4c0f0c7be6726c59eea614be"),
    ("f4_49s", "8e", "8eeadcf84b38696ac0ede7aedaf08ee6eff1812468c8d43fa667e2376c877850"),
    ("f5_55s", "89", "89bdabdd26b4c0ada57121bc0851f93ee52aa18080e51a9274406c1dee0bd9f9"),
]

BOX = (480, 1240, 940, 1520)          # generous around the computed emblem box
box_w = BOX[2] - BOX[0]
box_h = BOX[3] - BOX[1]
Z = 3

sheet = Image.new("RGB", (box_w * Z, box_h * Z * len(F)), (10, 10, 10))
d = ImageDraw.Draw(sheet)
for i, (k, dd, n) in enumerate(F):
    im = Image.open(os.path.join(SHOTS, dd, n)).convert("RGB")
    c = im.crop(BOX)
    c = c.resize((c.width * Z, c.height * Z), Image.LANCZOS)
    sheet.paste(c, (0, i * box_h * Z))
    d.text((8, i * box_h * Z + 6), k, fill=(255, 0, 0))
sheet.save(os.path.join(OUT, "cp_emblem_box.png"))
print("wrote cp_emblem_box.png", sheet.size, "box", BOX)

# exact box only, no margin, for the tightest possible read
EX = (541, 1307, 861, 1506)
ew, eh = EX[2] - EX[0], EX[3] - EX[1]
tight = Image.new("RGB", (ew * 3, eh * 3 * len(F)), (10, 10, 10))
for i, (k, dd, n) in enumerate(F):
    im = Image.open(os.path.join(SHOTS, dd, n)).convert("RGB")
    c = im.crop(EX).resize((ew * 3, eh * 3), Image.LANCZOS)
    tight.paste(c, (0, i * eh * 3))
tight.save(os.path.join(OUT, "cp_emblem_tight.png"))
print("wrote cp_emblem_tight.png", tight.size, "exact", EX)

# wide bottom strip, one frame, so the whole command panel is legible
im = Image.open(os.path.join(SHOTS, F[0][1], F[0][2])).convert("RGB")
big = im.crop((0, 1280, 1400, 1535))
big = big.resize((big.width * 2, big.height * 2), Image.LANCZOS)
big.save(os.path.join(OUT, "cp_wide_f1.png"))
print("wrote cp_wide_f1.png", big.size)

# does the computed emblem box differ from frame to frame? (it is a UI widget: it should NOT)
import numpy as np
prev = None
for k, dd, n in F:
    im = Image.open(os.path.join(SHOTS, dd, n)).convert("RGB")
    a = np.asarray(im.crop(EX), dtype=np.int16)
    if prev is not None:
        dd2 = np.abs(a - prev)
        print("  %-8s meanAbsDiff vs previous = %6.2f  frac>12 = %.3f  meanRGB=(%.1f,%.1f,%.1f)"
              % (k, dd2.mean(), (dd2 > 12).mean(), a[:, :, 0].mean(), a[:, :, 1].mean(), a[:, :, 2].mean()))
    else:
        print("  %-8s meanRGB=(%.1f,%.1f,%.1f)" % (k, a[:, :, 0].mean(), a[:, :, 1].mean(), a[:, :, 2].mean()))
    prev = a

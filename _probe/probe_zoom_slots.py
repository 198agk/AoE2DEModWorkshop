# -*- coding: utf-8 -*-
r"""Zoom the two decisive slot regions to settle tree-only vs union.

GAME 2 (Sicilians) already proved the menu is NOT fed by the panel alone: the siege
workshop offered the Onager -> Siege Onager upgrade while the panel file is silent
about both 588 and 320.

GAME 1 decides tree-only versus union: Poles' tree says 691 Elite Cannon Galleon
`NotAvailable` while the panel LISTS it.  If the dock offers that upgrade, the menu
unions both layers; if it does not, the tree alone is authoritative.

In AoE2 DE an upgradeable unit button carries a small gold chevron on its corner, and
the button's tooltip names the upgrade.  Crop the cannon/onager slots large enough to
see the chevron.
"""
import os

from PIL import Image

A = r"C:\Users\26913\.dsh\attachments\v1\objects"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_crops")
os.makedirs(OUT, exist_ok=True)

POLES = os.path.join(A, "5a",
    "5a77a828c64b351be52e2dc4d402e8b76798db6bf8f16a41e86ec13ab98ee9e6")
SIC3 = os.path.join(A, "2b",
    "2be84e564bfc25de5481338f98a153563641d463c1a8241015cfd0701ea86b01")

# Poles: the whole lower grid, 6x, so each slot and any chevron is legible.
im = Image.open(POLES).convert("RGB")
print("poles %s" % (im.size,))
for name, box in (("poles_grid6x", (20, 490, 400, 660)),
                  ("poles_tooltip", (0, 0, 1030, 400))):
    c = im.crop(box)
    s = 6 if "grid" in name else 2
    c.resize((c.size[0] * s, c.size[1] * s), Image.LANCZOS).save(
        os.path.join(OUT, name + ".png"))
    print("  %-16s box=%s x%d" % (name, box, s))

# Sicilians upgrade tooltip state: same grid, for a side-by-side of what an
# AVAILABLE upgrade looks like (the user's shot 3).
im3 = Image.open(SIC3).convert("RGB")
print("sic    %s" % (im3.size,))
c = im3.crop((20, 260, 420, 480))
c.resize((c.size[0] * 5, c.size[1] * 5), Image.LANCZOS).save(
    os.path.join(OUT, "sic_grid5x.png"))
print("  sic_grid5x       box=(20, 260, 420, 480) x5")

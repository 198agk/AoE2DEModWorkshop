# -*- coding: utf-8 -*-
"""Restore the game's own dataset files from the vanilla backup in _cache/vanilla_dat."""
import os, sys, shutil, hashlib, json

import _gamepaths as GP

# Where the game is, and where this repo keeps its copy of the untouched files,
# are both discovered: neither is the same on any two machines.
GD = GP.DAT_DIR
BAK = os.path.join(GP.REPO, "_cache", "vanilla_dat")
names = ['empires2_x2_p1.dat','futuravailableunits.json','paphosfutureavailableunits.json']
def sha(p):
    h = hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda: f.read(1<<20), b''): h.update(b)
    return h.hexdigest()[:16]
out = {}
for n in names:
    g = os.path.join(GD, n); b = os.path.join(BAK, n)
    if not os.path.exists(b):
        out[n] = 'no backup'; continue
    tmp = g + '.dshbak'
    shutil.copy2(b, tmp); os.replace(tmp, g)
    out[n] = {'bytes': os.path.getsize(g), 'sha': sha(g)}
print(json.dumps(out, ensure_ascii=False, indent=1))
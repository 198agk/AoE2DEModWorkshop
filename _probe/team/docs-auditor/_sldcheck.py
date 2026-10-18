# -*- coding: utf-8 -*-
import sys, os, io, struct, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
GFX = r"d:\games\steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"
names = sorted(n for n in os.listdir(GFX) if n.lower().endswith('.sld'))
ns = set(names)
x1 = [n for n in names if n.endswith('_x1.sld')]
x2 = [n for n in names if n.endswith('_x2.sld')]
print("x1:", len(x1), "x2:", len(x2))
o1 = [n for n in x1 if n[:-7] + '_x2.sld' not in ns]
o2 = [n for n in x2 if n[:-7] + '_x1.sld' not in ns]
print("orphan x1:", len(o1), o1[:10])
print("orphan x2:", len(o2), o2[:10])
print("neither x1 nor x2:", len([n for n in names if not (n.endswith('_x1.sld') or n.endswith('_x2.sld'))]))
bad = []
for n in names:
    with open(os.path.join(GFX, n), 'rb') as fh:
        b = fh.read(16)
    if len(b) < 16 or b[:4] != b'SLDX':
        bad.append((n, b[:8].hex(), os.path.getsize(os.path.join(GFX,n))))
print("non-SLDX / short header:", len(bad))
for t in bad: print("   ", t)
u1 = collections.Counter()
for n in names:
    with open(os.path.join(GFX, n), 'rb') as fh:
        b = fh.read(14)
    if len(b) >= 14 and b[:4]==b'SLDX':
        u1[struct.unpack('<H', b[8:10])[0]] += 1
print("u1 hist:", dict(u1))

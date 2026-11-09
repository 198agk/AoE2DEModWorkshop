# -*- coding: utf-8 -*-
"""L3 补充：单位图标字段 / 成本模型 / make-avail tech 的存在性。"""
import sys, io, json, struct, contextlib
sys.path.insert(0, '.')
import aoe2mod.dat.parser as P
from aoe2mod.dat import locate as L, newunit as NU

M1 = '_probe/_tmp/m1.dat'
m1 = open(M1, 'rb').read()
p = P.Parser(m1)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
st = p.stats
civs, civs_start, gv, tail = L.locate(m1, parser=p)
KI = 28

# make-avail tech
for i in (6665, 6666, 6667):
    if i < len(st['techs']):
        t = st['techs'][i]
        print('tech %d: %s civ=%s eff=%s locs=%s' % (
            i, t.get('name'), t.get('civ'), t.get('effect_id'), t.get('research_locations')))
print('avail effect 1501 =', st['effects'][1501].get('commands'))

# unit icon at record offset 51 (ICON_OFF)
spans = NU.unit_spans(m1, gv, civs_start, KI)
s, e = spans[6666]
img = m1[s:e]
print('unit6666 icon_id@51 =', struct.unpack_from('<h', img, 51)[0])
print('unit6666 hp bytes =', struct.unpack_from('<h', img, 8)[0])

# locate 的 unit record 里有没有 costs
u = [r for r in civs[KI]['units'] if r.get('id') == 6666][0]
print('locate rec keys =', sorted(u.keys()))
print('locate rec costs/icon =', u.get('costs'), u.get('icon_id'))

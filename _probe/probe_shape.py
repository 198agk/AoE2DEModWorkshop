# -*- coding: utf-8 -*-
"""看 shipped make-avail tech 的原始形状，以及 Khmer 城堡/TC 的 5x5 槽位图。"""
import sys, io, json, contextlib
sys.path.insert(0, '.')
import aoe2mod.dat.parser as P
from aoe2mod.dat import locate as L
from aoe2mod.game import civtechtrees as CT

BASE = r'D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat'
raw, how = P.load_dat(BASE)
p = P.Parser(raw)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
st = p.stats
civs, civs_start, gv, tail = L.locate(raw, parser=p)
techs = L.locate_techs(raw, tail, gv)

for tid in (151, 166, 87, 654):
    t = techs[tid]
    print('tech %d %-28s req=%s costs=%s locs=%s eff=%s icon=%s type=%s' % (
        tid, t.get('name'), t.get('required_techs'), t.get('costs'),
        t.get('research_locations'), t.get('effect_id'), t.get('icon_id'), t.get('type')))

print()
# Khmer 面板：按 button 排 5x5
trees = CT.load_trees(r'D:\Games\Steam\steamapps\common\AoE2DE')
tree = trees['Khmer'] if 'Khmer' in trees else trees[list(trees)[0]]
print('tree keys', list(trees)[:5], len(trees))

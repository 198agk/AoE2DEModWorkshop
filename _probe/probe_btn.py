# -*- coding: utf-8 -*-
"""train location 的键名核对 + button 与面板格子的对照。"""
import sys, io, contextlib, json
sys.path.insert(0, '.')
import aoe2mod.dat.parser as P
from aoe2mod.dat import locate as L
from aoe2mod.game import civtechtrees as CT

BASE = r'D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat'
raw, how = P.load_dat(BASE)
p = P.Parser(raw)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
civs, civs_start, gv, tail = L.locate(raw, parser=p)
KI = 28
u = [r for r in civs[KI]['units'] if r['id'] == 83][0]
print('train_locations sample:', json.dumps(u['train_locations'], ensure_ascii=False))
print('rec keys:', sorted(u.keys()))

# 建立 (building -> [(button, unit)]) 用 train_locations 的 location
avail = {}
for r in civs[KI]['units']:
    for tl in (r.get('train_locations') or []):
        loc = tl.get('location_id', tl.get('building_id'))
        if loc is None or loc < 0:
            continue
        avail.setdefault(loc, []).append((tl.get('button_id'), r['id'], r['name']))

trees = CT.load_trees(r'D:\Games\Steam\steamapps\common\AoE2DE')
tree = trees['KHMER']
for bid in (82, 109, 87, 101, 12, 45):
    rows = [(r['Node ID'], r['Name']) for r in tree['civ_techs_units']
            if r.get('Building ID') == bid and r.get('Use Type') == 'Unit']
    lst = sorted(avail.get(bid, []))
    print('=== building %d' % bid)
    print('  tree:', [n for _, n in rows])
    print('  btn :', lst)

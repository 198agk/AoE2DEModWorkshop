# -*- coding: utf-8 -*-
"""L0/L1/L3 验证 m1.dat —— 直接 parse（绕开 toolkit 的 datstamp 与缓存）。"""
import sys, io, json, struct, hashlib, contextlib, time
sys.path.insert(0, '.')
import aoe2mod.dat.parser as P
from aoe2mod.dat import locate as L, newunit as NU

BASE = r'D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat'
M1 = '_probe/_tmp/m1.dat'
TECH_ID, UNIT_ID = 6665, 6666

raw_base, how = P.load_dat(BASE)
m1 = open(M1, 'rb').read()
print('base %d  m1 %d  delta %+d  (%s)' % (len(raw_base), len(m1), len(m1) - len(raw_base), how))
print('sha base %s  m1 %s' % (hashlib.sha256(raw_base).hexdigest()[:16],
                              hashlib.sha256(m1).hexdigest()[:16]))


def first_last_diff(a, b):
    n = min(len(a), len(b)); i = 0
    while i < n and a[i] == b[i]: i += 1
    j = 0
    while j < n and a[len(a) - 1 - j] == b[len(b) - 1 - j]: j += 1
    return i, len(a) - j, len(b) - j

f, la, lb = first_last_diff(raw_base, m1)
print('[L2] common prefix %d | base tail %d | m1 tail %d' % (f, la, lb))

# ---------------- L0 重解析
t0 = time.time()
p = P.Parser(m1)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
st = p.stats
print('[L0] parse %.2fs  techs=%d effects=%d civs=%d' % (
    time.time() - t0, len(st['techs']), len(st['effects']), len(st['civs'])))

civs, civs_start, gv, tail = L.locate(m1, parser=p)
names = [c['name'] for c in st['civs']]
KI = names.index('Khmer')
print('[L0] khmer=%d  ptr_total=%d  units=%d' % (
    KI, st['civs'][KI]['unit_pointers_total'], len(st['civs'][KI]['units'])))

# ---------------- L3 字段回读
t = st['techs'][TECH_ID]
print('[L3 tech %d] name=%s civ=%s eff=%s icon=%s locs=%s' % (
    TECH_ID, t.get('name'), t.get('civ'), t.get('effect_id'), t.get('icon_id'),
    t.get('research_locations')))
e = st['effects'][t['effect_id']]
print('[L3 effect %s] name=%s cmds=%s' % (t['effect_id'], e.get('name'), e.get('commands')))

u = None
for r in st['civs'][KI]['units']:
    if r.get('id') == UNIT_ID:
        u = r; break
print('[L3 unit %d] %s' % (UNIT_ID, {k: u.get(k) for k in
      ('id', 'type', 'hit_points', 'name', 'class', 'icon_id', 'costs')}))

# ---------------- 字节级独立读回（不依赖 parse 的模型）
techs_raw = L.locate_techs(m1, tail, gv)
print('[BYTE] techs count=%d' % len(techs_raw))
print('[BYTE] tech %d = %s' % (TECH_ID, json.dumps(techs_raw[TECH_ID], ensure_ascii=False)[:600]))

spans = NU.unit_spans(m1, gv, civs_start, KI)
print('[BYTE] unit %d span=%s len=%d' % (UNIT_ID, spans.get(UNIT_ID),
      (spans[UNIT_ID][1] - spans[UNIT_ID][0]) if UNIT_ID in spans else -1))
if UNIT_ID in spans:
    s, en = spans[UNIT_ID]
    img = m1[s:en]
    print('[BYTE] cost @730 = %s' % (struct.unpack_from('<hhhhhhhhh', img, 730),))
    print('[BYTE] head = %s  id=%d' % (img[:3].hex(), struct.unpack_from('<h', img, 1)[0]))

print('OK')

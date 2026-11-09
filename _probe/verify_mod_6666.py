# -*- coding: utf-8 -*-
"""L4 三表对账：装好的 mod 里 dat / CivTechTrees / futuravailableunits / 字符串 / 材质
五处必须说的是同一件事。任何一处不一致都打印 FAIL 并给出期望值与实际值。

不开游戏。判据全部是字节与字段，不是"看起来对"。
"""
import io
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aoe2mod.dat import locate as L
from aoe2mod.dat import parser as P
from aoe2mod.game import ddstex as D

G = r'D:\Games\Steam\steamapps\common\AoE2DE'
MOD = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '_out', 'mod_6666_yg'))
UI = MOD + '_ui'
DAT = os.path.join(MOD, 'resources', '_common', 'dat', 'empires2_x2_p1.dat')
TREE = os.path.join(MOD, 'resources', '_common', 'dat', 'CivTechTrees', 'KHMER.json')
PANEL = os.path.join(MOD, 'resources', '_common', 'dat', 'futuravailableunits.json')
MATS = os.path.join(UI, 'widgetui', 'materials.json')

KI = 28          # Khmer
UID = 6666       # 新单位
TID = 6665       # 前置科技
AID = 6666       # make-avail 科技（自己占掉了 6666 这个 tech 下标）
E_DROP = 1500    # (1,33,0,-1,50.0) 高棉免磨坊
E_AVAIL = 1501   # (2,6666,1,-1,0.0)
S_UNIT, S_TECH, S_UNIT_HELP, S_TECH_DESC, S_TECH_HELP = 30030002, 30030003, 30030004, 30030005, 30030006

fails = []
oks = []


def check(tag, cond, detail=''):
    if cond:
        oks.append(tag)
    else:
        fails.append('%s  %s' % (tag, detail))
    print('%s %-46s %s' % ('PASS' if cond else 'FAIL', tag, detail))


# ── 1. dat ────────────────────────────────────────────────────────────────
blob = open(DAT, 'rb').read()
print('[dat] %s  %d B' % (os.path.basename(DAT), len(blob)))
# mod 目录里的 .dat 是 bare deflate（wbits=-15）；Parser 要未压缩流
if not blob[:1].isdigit():
    import zlib
    blob = zlib.decompressobj(-15).decompress(blob)
    print('[dat] inflated -> %d B' % len(blob))
    rawpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_tmp', 'mod_inflated.dat')
    os.makedirs(os.path.dirname(rawpath), exist_ok=True)
    open(rawpath, 'wb').write(blob)
    PATH_FOR_PARSER = rawpath
else:
    PATH_FOR_PARSER = DAT
p = P.Parser(blob)
st = p.parse()
print('[dat] parse ok  techs=%d effects=%d civs=%d' % (len(st['techs']), len(st['effects']), len(st['civs'])))

civs_l, civs_start, gv, tail = L.locate(blob)
print('[dat] gv=%s tail=%s' % (gv, tail))
recs = L.locate_techs(blob, tail, gv)
check('dat.techs>=6667', len(recs) >= 6667, 'len=%d' % len(recs))

t = recs[TID]
check('tech6665.required_techs==[101]', [x for x in t['required_techs'] if x] == [101],
      str(t['required_techs']))
costs = [(c['type'], c['amount']) for c in t['costs'] if c['type'] >= 0]
check('tech6665.costs', sorted(costs) == [(0, 500), (1, 500), (3, 500)], str(costs))
locs = t['research_locations']
check('tech6665.research@TC109/btn2', any(l['location_id'] == 109 and l['button_id'] == 2 for l in locs),
      str([(l['location_id'], l['button_id']) for l in locs]))
check('tech6665.effect_id==%d' % E_DROP, t['effect_id'] == E_DROP, str(t['effect_id']))
check('tech6665.icon_id==150', t['icon_id'] == 150, str(t['icon_id']))
check('tech6665.civ==28', t['civ'] == KI, str(t['civ']))
check('tech6665.name', t['name'] == 'NEWTECH6665', t['name'])

eff = st['effects'][E_DROP]
check('effect1500.cmds==[(1,33,0,-1,50.0)]', list(eff['commands']) == [(1, 33, 0, -1, 50.0)],
      str(list(eff['commands'])))

a = recs[AID]
check('tech6666.required_techs', sorted(x for x in a['required_techs'] if x) == [102, TID],
      str(a['required_techs']))
check('tech6666.no_research_location', len([l for l in a['research_locations'] if l['location_id'] >= 0]) == 0,
      str([(l['location_id'], l['button_id']) for l in a['research_locations']]))
check('tech6666.effect_id==%d' % E_AVAIL, a['effect_id'] == E_AVAIL, str(a['effect_id']))
check('effect1501.cmds==[(2,6666,1,-1,0.0)]',
      list(st['effects'][E_AVAIL]['commands']) == [(2, 6666, 1, -1, 0.0)],
      str(list(st['effects'][E_AVAIL]['commands'])))

u = None
for r in st['civs'][KI]['units']:
    if r['id'] == UID:
        u = r
check('dat.civ28.units has 6666', u is not None)
if u:
    from aoe2mod.dat import newunit as NU
    spans = NU.unit_spans(blob, gv, civs_start, KI)
    check('dat.unit6666 byte-span', UID in spans, 'span=%s' % (spans.get(UID),))

wrecs = None
civs, civs_start, gv, tail = L.locate(blob, parser=p)
for r in civs[KI]['units']:
    if r['id'] == UID:
        wrecs = r
check('unit6666.found_by_locate', wrecs is not None)
if wrecs:
    uc = [(c['type'], c['amount'], c['flag']) for c in wrecs['costs']]
    check('unit6666.costs==100f/100g/1pop', uc == [(0, 100, 1), (3, 100, 1), (4, 1, 0)], str(uc))
    check('unit6666.icon_id==174', wrecs['icon_id'] == 174, str(wrecs['icon_id']))
    tl = [(x['unit_id'], x['button_id']) for x in wrecs['train_locations']]
    check('unit6666.train@Castle82/btn4', (82, 4) in tl, str(tl))
    check('unit6666.train exactly one entry', len(tl) == 1, str(tl))
    check('unit6666.help string == 30030004', wrecs.get('_dll_help') == 30030004, str(wrecs.get('_dll_help')))
    check('unit6666.name string == 30030002', wrecs.get('_dll_name') == 30030002, str(wrecs.get('_dll_name')))
    check('unit6666.hp==200', wrecs['hit_points'] == 200, str(wrecs['hit_points']))

# ── 2. CivTechTrees/KHMER.json ────────────────────────────────────────────
tree = json.loads(open(TREE, encoding='utf-8').read())
rows = tree['civ_techs_units']

def row(nid, ut):
    return [r for r in rows if r.get('Node ID') == nid and r.get('Use Type') == ut]

ru = row(UID, 'Unit')
rt = row(TID, 'Tech')
check('tree.6666 Unit row', len(ru) == 1, str(len(ru)))
check('tree.6665 Tech row', len(rt) == 1, str(len(rt)))
if ru:
    r = ru[0]
    check('tree.6666 Building/Age', (r['Building ID'], r['Age ID']) == (82, 3),
          '%s/%s' % (r['Building ID'], r['Age ID']))
    check('tree.6666 Name String ID', r['Name String ID'] == S_UNIT, str(r['Name String ID']))
if rt:
    r = rt[0]
    check('tree.6665 Building/Age', (r['Building ID'], r['Age ID']) == (109, 1),
          '%s/%s' % (r['Building ID'], r['Age ID']))
    check('tree.6665 Name String ID', r['Name String ID'] == S_TECH, str(r['Name String ID']))

# ── 3. futuravailableunits.json ───────────────────────────────────────────
panel = json.loads(open(PANEL, encoding='utf-8').read())
blk = None
for b in panel['Khmer']['Buildings']:
    if b['ID'] == 82:
        blk = b
cu = [x for x in blk['Units'] if x['ID'] == UID]
check('panel.Castle(82).Units has 6666', len(cu) == 1, str(len(cu)))
if cu:
    check('panel.6666 RequiredAge==3', cu[0]['RequiredAge'] == 3, str(cu[0]))
    check('panel.6666 Name', cu[0]['Name'] == '高棉禁卫', cu[0]['Name'])
    check('panel.6666 is last-ish (idx>=4)', blk['Units'].index(cu[0]) >= 4, str(blk['Units'].index(cu[0])))
tc = [b for b in panel['Khmer']['Buildings'] if b['ID'] == 109][0]
ct = [x for x in tc['Techs'] if x['ID'] == TID]
check('panel.TC(109).Techs has 6665', len(ct) == 1, str(len(ct)))
if ct:
    check('panel.6665 RequiredAge==1', ct[0]['RequiredAge'] == 1, str(ct[0]))

# ── 4. 字符串 ─────────────────────────────────────────────────────────────
for loc in ('zh', 'en'):
    path = os.path.join(MOD, 'resources', loc, 'strings', 'key-value', 'key-value-modded-strings-utf8.txt')
    txt = open(path, encoding='utf-8').read()
    for sid, want in ((S_UNIT, '高棉禁卫'), (S_TECH, '高棉粮仓传统')):
        line = [l for l in txt.splitlines() if l.startswith('%d ' % sid)]
        check('str.%s.%d' % (loc, sid), len(line) == 1 and want in line[0],
              line[0][:60] if line else 'missing')

# ── 5. 材质与贴图 ─────────────────────────────────────────────────────────
mats = json.loads(open(MATS, encoding='utf-8').read())
mt = {m['MaterialDef']['Name']: m['MaterialDef'] for m in mats['Materials']}
gt = {g['TextureDef']['Name']: g['TextureDef'] for g in mats['GlobalTextures']}
for name, want_file, side in (('UnitIcons17450730', 'textures/ingame/units/yg_unit_6666.dds', 256),
                              ('TechIconsT150ArchaicAge', 'textures/ingame/tech/yg_tech_6665.dds', 256)):
    check('mat.%s exists' % name, name in mt)
    if name in mt:
        check('mat.%s Type==Texture' % name, mt[name]['Type'] == 'Texture', mt[name]['Type'])
        check('mat.%s no AtlasRef' % name, 'AtlasRef' not in mt[name], str(mt[name].get('AtlasRef')))
    check('gt.%s FileName' % name, name in gt and gt[name]['FileName'] == want_file,
          gt[name]['FileName'] if name in gt else 'missing')
    fp = os.path.join(UI, 'widgetui', want_file)
    check('file.%s exists' % os.path.basename(want_file), os.path.isfile(fp))

for rel, want_rgb in (('textures/ingame/units/yg_unit_6666.dds', (200, 32, 32)),
                      ('textures/ingame/tech/yg_tech_6665.dds', (32, 72, 200))):
    fp = os.path.join(UI, 'widgetui', rel)
    if not os.path.isfile(fp):
        check('pixel.%s' % os.path.basename(rel), False, 'missing file')
        continue
    hdr = D.header(fp)
    b, g_, r, _a = struct.unpack('<BBBB', open(fp, 'rb').read()[128:132])
    check('pixel.%s %dx%d %s' % (os.path.basename(rel), hdr.get('width', 0), hdr.get('height', 0), want_rgb),
          (hdr.get('width'), hdr.get('height')) == (256, 256) and (r, g_, b) == want_rgb,
          'first pixel rgb=(%d,%d,%d) hdr=%s' % (r, g_, b, hdr.get('format')))

# ── 结论 ─────────────────────────────────────────────────────────────────
print('')
print('=' * 68)
print('PASS %d / FAIL %d' % (len(oks), len(fails)))
for f in fails:
    print('  ! ' + f)
print('VERDICT: %s' % ('ALL GREEN' if not fails else 'MISMATCH'))
sys.exit(0 if not fails else 1)

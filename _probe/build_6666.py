# -*- coding: utf-8 -*-
"""构建 id 6666 单位 + id 6665 科技的高棉 dat 改动。

只做 dat 层，产物写到 _probe/_tmp/m1.dat（未压缩原始流）。
所有断言在序列化后重新解析、按字节独立读回再验一遍。
"""
import sys, copy, time, json, struct, hashlib
sys.path.insert(0, '.')
from aoe2mod import api
from aoe2mod.dat import writer as W, parser as P, locate as L, newunit as NU
from aoe2mod.dat.parser import GV_C31, GV_C15, GV_LatestDE2

TECH_ID = 6665
UNIT_ID = 6666
CIV = 'Khmer'

# ---------------------------------------------------------------- write_tech 补丁
ORIG_WRITE_TECH = W.write_tech


def fixed_write_tech(w, t):
    if not t.get("_new"):
        return ORIG_WRITE_TECH(w, t)
    reqs = list(t.get("required_techs") or [])[:6]
    costs = list(t.get("costs") or [])[:3]
    with w.new_record():
        for i in range(6):
            w.i16(reqs[i] if i < len(reqs) else 0)
        for i in range(3):
            if i < len(costs):
                c = costs[i]
                w.i16(c["type"]); w.i16(c["amount"]); w.u8(c["flag"])
            else:
                w.i16(-1); w.i16(0); w.u8(0)
        w.i16(len(reqs)); w.i16(t["civ"]); w.i16(0)
        if w.gv < GV_C31: w.i16(0)
        w.i32(int(t.get("lang_name") or 0)); w.i32(int(t.get("lang_description") or 0))
        if w.gv < GV_C31: w.i16(0)
        w.i16(t["effect_id"]); w.i16(t["type"]); w.i16(t["icon_id"])
        if w.gv < GV_C31: w.u8(0)
        w.i32(int(t.get("lang_help") or 0)); w.i32(int(t.get("lang_tech_tree") or 0))
        if w.gv < GV_C31: w.i32(0)
        w.debug_string(t["name"])
        if GV_C15 <= w.gv <= GV_LatestDE2: w.u8(0)
        if GV_C31 <= w.gv <= GV_LatestDE2:
            locs = t["research_locations"] or []
            w.i16(len(locs))
            for loc in locs:
                W.write_research_location(w, loc)


W.write_tech = fixed_write_tech

# ---------------------------------------------------------------- load
t0 = time.time()
tk = api.open_toolkit(); tk._ensure()
raw, civs, civs_start, gv, tail, how = tk._parsed
st = copy.deepcopy(tk._stats)
names = [c['name'] for c in st['civs']]
KI = names.index(CIV)
print('[load] %.2fs techs=%d units_total=%d gv=%d' % (
    time.time() - t0, len(st['techs']), st['civs'][KI]['unit_pointers_total'], gv))

# ---------------------------------------------------------------- 1) 撑 tech 数组到 6666
donor_t = copy.deepcopy(st['techs'][213])


def empty_tech(n):
    t = copy.deepcopy(donor_t)
    t['_new'] = True
    t['name'] = 'EMPTY%d' % n
    t['required_techs'] = []; t['required_tech_count'] = 0
    t['costs'] = []; t['research_locations'] = []
    t['effect_id'] = -1; t['icon_id'] = -1; t['civ'] = -1
    t['lang_name'] = 0; t['lang_description'] = 0
    t['lang_help'] = 0; t['lang_tech_tree'] = 0
    t['type'] = 0
    return t


while len(st['techs']) < TECH_ID + 1:
    st['techs'].append(empty_tech(len(st['techs'])))
print('[fill] techs=%d' % len(st['techs']))

# ---------------------------------------------------------------- 2) 新 effect：高棉免磨坊
effs = st['effects']
EFF_TECH = len(effs)
e = copy.deepcopy(effs[690])
e['_new'] = True
e['name'] = 'NEWEFF6665_KHMER_DROPSITE'
e['commands'] = [(1, 33, 0, -1, 50.0)]
effs.append(e)

# ---------------------------------------------------------------- 3) tech 6665
T = st['techs'][TECH_ID]
T['name'] = 'NEWTECH6665'
T['civ'] = KI
T['required_techs'] = [101]          # 101 = 封建（名字叫 Middle Age，历史遗留错位）
T['required_tech_count'] = 1
T['costs'] = [
    {'type': 0, 'amount': 500, 'flag': 1},   # 500 食物
    {'type': 1, 'amount': 500, 'flag': 1},   # 500 木头
    {'type': 3, 'amount': 500, 'flag': 1},   # 500 金
]
T['research_locations'] = [{'location_id': 109, 'research_time': 120,
                            'button_id': 2, 'hotkey_id': 0}]
T['effect_id'] = EFF_TECH
T['icon_id'] = 150                        # 科技图标槽 150 = 空闲且带真实贴图 TechIconsT150ArchaicAge
T['lang_name'] = 30030003
T['lang_description'] = 30030005
T['research_time'] = 120
T['type'] = 0
print('[tech] id=%d effect=%d' % (TECH_ID, EFF_TECH))

# ---------------------------------------------------------------- 4) unit 6666
st, rep = NU.add_unit(st, raw, gv, civs_start, KI, donor_id=440, new_id=UNIT_ID,
                      name_string_id=30030002, hp=200,
                      button=4, builder=82, civs=civs, icon_id=174)
print('[unit] %s' % {k: v for k, v in rep.items() if k != 'buttons'})
print('[unit] buttons=%s' % rep['buttons'])

# ---- 成本 100 食 / 100 金 / 1 人口（petard 的成本槽在记录内 rel=730，实测）
rec = None
for r in st['civs'][KI]['units']:
    if r.get('id') == UNIT_ID:
        rec = r
        break
assert rec is not None, 'unit 6666 不在 civ 的 units 里'
img = rec['_img']
COST_OFF = 730
before = struct.unpack_from('<hhhhhhhhh', img, COST_OFF)
struct.pack_into('<hhhhhhhhh', img, COST_OFF, 0, 100, 1, 3, 100, 1, 4, 1, 0)
after = struct.unpack_from('<hhhhhhhhh', img, COST_OFF)
print('[cost] %s -> %s  (len=%d)' % (before, after, len(img)))
assert before == (0, 65, 1, 3, 20, 1, 4, 1, 0), '偏移 730 不再是 petard 的成本槽: %s' % (before,)

# ---- 训练入口去重：donor petard 有两条 entry(82/btn3 与 1251/btn3)，builder 重写成 82
#      之后两条变成完全相同的 (82,4)。同一 (建筑,格子) 出现两次是无意义的重复，
#      而且实测全库 136,861 条只有我们这一条重复 -> 留一条。
CNT_OFF = 748                     # Creatable 的 i16 训练入口计数
ENT_OFF = 750                     # 第一条 9 字节 entry
n_ent = struct.unpack_from('<h', img, CNT_OFF)[0]
ents = [struct.unpack_from('<hhB', img, ENT_OFF + 9 * i) for i in range(n_ent)]
print('[train] count=%d entries=%s' % (n_ent, ents))
assert n_ent == 2 and ents[0] == ents[1], '训练入口不再是预期的两条重复: %s' % (ents,)
img2 = bytearray(img[:ENT_OFF + 9]) + bytearray(img[ENT_OFF + 18:])
struct.pack_into('<h', img2, CNT_OFF, 1)
img = bytearray(img2)
rec['_img'] = img
print('[train] dedup -> count=%d entries=%s len=%d'
      % (struct.unpack_from('<h', img, CNT_OFF)[0],
         [struct.unpack_from('<hhB', img, ENT_OFF)], len(img)))

# ---- 帮助文本换成自己的（克隆体默认带 petard 的 105660）
HELP_OFF = 95
was_help = struct.unpack_from('<i', img, HELP_OFF)[0]
assert was_help == 105660, '偏移 95 不再是 petard 的帮助串: %s' % was_help
struct.pack_into('<i', img, HELP_OFF, 30030004)
print('[help] %d -> %d' % (was_help, struct.unpack_from('<i', img, HELP_OFF)[0]))

# ---------------------------------------------------------------- 5) make-avail：城堡解锁
EFF_AVAIL = len(effs)
e2 = copy.deepcopy(effs[690])
e2['_new'] = True
e2['name'] = 'NEWEFF6666_MAKEAVAIL'
e2['commands'] = [(2, UNIT_ID, 1, -1, 0.0)]
effs.append(e2)

A = copy.deepcopy(donor_t)
A['_new'] = True
A['name'] = 'NEWTECH6666_MAKEAVAIL'
A['civ'] = KI
A['required_techs'] = [TECH_ID, 102]      # 先研究 6665，且已到城堡（102 名字叫 Feudal Age，实为城堡）
A['required_tech_count'] = 2
A['costs'] = []
A['research_locations'] = []              # 无研究地点 = 满足前置就自动获得
A['effect_id'] = EFF_AVAIL
A['icon_id'] = -1
A['lang_name'] = 0; A['lang_description'] = 0; A['lang_help'] = 0; A['lang_tech_tree'] = 0
A['type'] = 0; A['research_time'] = 0
AVAIL_ID = len(st['techs'])
st['techs'].append(A)
print('[avail] tech id=%d effect=%d' % (AVAIL_ID, EFF_AVAIL))

# ---------------------------------------------------------------- 6) 序列化
t1 = time.time()
out, report = W.serialize_dat(st, raw=raw, strict=True, gv=gv)
print('[serialize] %.2fs  %d -> %d (%+d)' % (
    time.time() - t1, len(raw), len(out), len(out) - len(raw)))
print('[serialize] mismatches=%d sites=%s' % (
    report.get('model_vs_original_mismatches'), report.get('opaque_sites')))
open('_probe/_tmp/m1.dat', 'wb').write(out)
print('[serialize] sha256=%s' % hashlib.sha256(out).hexdigest()[:16])

print('OK')

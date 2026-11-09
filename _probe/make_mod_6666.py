# -*- coding: utf-8 -*-
"""把 m1.dat 组装成一个可安装的 mod（数据 + 图标 + 字符串 + 面板/科技树）。

产物：_out/mod_6666_yg/ 与 _out/mod_6666_yg_ui/（widgetui 层必须拆开）
"""
import sys, os, json, copy, shutil, struct, hashlib
sys.path.insert(0, '.')

from aoe2mod.mod import emitter as E
from aoe2mod.mod import strings as S
from aoe2mod.game import ddstex as D
from aoe2mod.game import civtechtrees as CT
from aoe2mod.game import buildpanel as BP

G = r'D:\Games\Steam\steamapps\common\AoE2DE'
DAT = '_probe/_tmp/m1.dat'
OUT = '_out/mod_6666_yg'
TITLE = 'YG 高棉禁卫 6666 与 6665'

UNIT_ID, TECH_ID, CIV = 6666, 6665, 'Khmer'
CIV_STEM = 'KHMER'

# ---- 字符串 id（第一个空闲是 30030002）
S_UNIT_NAME = 30030002
S_UNIT_HELP = 30030004
S_TECH_NAME = 30030003
S_TECH_DESC = 30030005
S_TECH_HELP = 30030006

UNIT_ZH = '高棉禁卫'
UNIT_DESC = '高棉独有的重装步兵，城堡时代解锁。'
TECH_ZH = '高棉粮仓传统'
TECH_DESC = '农民无需磨坊或城镇中心即可存放食物。'

ICON_UNIT = 174     # 空闲且有贴图：UnitIcons17450730
ICON_TECH = 150     # 空闲且有贴图：TechIconsT150ArchaicAge


# ------------------------------------------------------------------ 1) 两张纯色图
def solid_rgba(side, rgb, alpha=255):
    r, g, b = rgb
    return bytes((r, g, b, alpha)) * (side * side)


RED = solid_rgba(256, (200, 32, 32))
BLUE = solid_rgba(256, (32, 72, 200))

UNIT_TEX_REL = 'textures/ingame/units/174_50730.dds'          # 覆盖 atlas 指向的源文件
UNIT_TEX2_REL = 'textures/ingame/units/yg_unit_6666.dds'      # 备用：自有文件
TECH_TEX_REL = 'textures/ingame/tech/150_archaic_age.dds'     # 覆盖 atlas 指向的源文件
TECH_TEX2_REL = 'textures/ingame/tech/yg_tech_6665.dds'

ui_files = {}
ui_files['widgetui/' + UNIT_TEX_REL] = D.encode_bgra(256, 256, RED)
ui_files['widgetui/' + UNIT_TEX2_REL] = D.encode_bgra(256, 256, RED)
ui_files['widgetui/' + TECH_TEX_REL] = D.encode_bgra(256, 256, BLUE)
ui_files['widgetui/' + TECH_TEX2_REL] = D.encode_bgra(256, 256, BLUE)
print('[tex] unit %d B  tech %d B' % (
    len(ui_files['widgetui/' + UNIT_TEX_REL]), len(ui_files['widgetui/' + TECH_TEX_REL])))

# ------------------------------------------------------------------ 2) materials.json
mat_path = os.path.join(G, 'widgetui', 'materials.json')
mats = json.load(open(mat_path, encoding='utf-8-sig'))

UNIT_MAT = 'UnitIcons%03d50730' % ICON_UNIT
TECH_MAT = 'TechIconsT%03dArchaicAge' % ICON_TECH

converted = []
gt = {x['TextureDef']['Name']: x['TextureDef'] for x in mats['GlobalTextures']}
for m in mats['Materials']:
    d = m['MaterialDef']
    if d['Name'] == UNIT_MAT:
        d.clear()
        d.update({'Name': UNIT_MAT, 'Type': 'Texture', 'Blend': 'AlphaPlayerColor',
                  'TextureRef': UNIT_MAT})
        converted.append(UNIT_MAT)
    elif d['Name'] == TECH_MAT:
        d.clear()
        d.update({'Name': TECH_MAT, 'Type': 'Texture', 'Blend': 'AlphaPlayerColor',
                  'TextureRef': TECH_MAT})
        converted.append(TECH_MAT)

# TextureDef 必须存在且指向我们的文件
for name, rel in ((UNIT_MAT, UNIT_TEX2_REL), (TECH_MAT, TECH_TEX2_REL)):
    td = gt.get(name)
    if td is None:
        mats['GlobalTextures'].append({'TextureDef': {
            'Name': name, 'FileName': rel, 'Cached': 'none'}})
    else:
        td['FileName'] = rel
        td.pop('Cached', None)

# atlas 条目也改指向自有文件，保证两条渲染路径都是红/蓝
for a in mats['AtlasTextures']:
    ad = a['AtlasDef']
    for t in ad.get('Textures') or []:
        if t['RefName'] == UNIT_MAT:
            t['FileName'] = UNIT_TEX2_REL
        elif t['RefName'] == TECH_MAT:
            t['FileName'] = TECH_TEX2_REL

ui_files['widgetui/materials.json'] = json.dumps(
    mats, ensure_ascii=False, indent='\t').encode('utf-8')
print('[materials] converted %s ; Materials=%d GlobalTextures=%d'
      % (converted, len(mats['Materials']), len(mats['GlobalTextures'])))

# ------------------------------------------------------------------ 3) 字符串
entries = [
    (S_UNIT_NAME, UNIT_ZH),
    (S_UNIT_HELP, UNIT_DESC),
    (S_TECH_NAME, TECH_ZH),
    (S_TECH_DESC, TECH_DESC),
    (S_TECH_HELP, TECH_DESC),
]
str_files = S.build_files(G, entries, locales=['zh', 'en'])
for k in sorted(str_files):
    print('[str] %s  %d B' % (k, len(str_files[k])))

# ------------------------------------------------------------------ 4) 科技树
trees = CT.load_trees(G)
tree = trees[CIV_STEM]
petard = [r for r in tree['civ_techs_units'] if r.get('Node ID') == 440][0]
feudal = [r for r in tree['civ_techs_units'] if r.get('Node ID') == 101][0]


def row_from(tpl, **kw):
    r = copy.deepcopy(tpl)
    r.update(kw)
    return r


unit_row = row_from(petard, **{
    'Name': UNIT_ZH, 'Node ID': UNIT_ID, 'Name String ID': S_UNIT_NAME,
    'Help String ID': S_UNIT_HELP, 'Picture Index': ICON_UNIT,
    'Age ID': 3, 'Building ID': 82, 'Use Type': 'Unit',
    'Node Type': 'Unit', 'Node Status': 'ResearchedCompleted'})
tech_row = row_from(feudal, **{
    'Name': TECH_ZH, 'Node ID': TECH_ID, 'Name String ID': S_TECH_NAME,
    'Help String ID': S_TECH_HELP, 'Picture Index': ICON_TECH,
    'Age ID': 1, 'Building ID': 109, 'Use Type': 'Tech',
    'Node Type': 'Research', 'Node Status': 'ResearchedCompleted'})
# 插入位置：紧跟 Petard / Feudal Age 之后，保证面板第 N 格语义
i_pet = tree['civ_techs_units'].index(petard)
tree['civ_techs_units'].insert(i_pet + 1, unit_row)
i_feu = tree['civ_techs_units'].index(feudal)
tree['civ_techs_units'].insert(i_feu + 1, tech_row)
tree_bytes = CT.serialize(tree)
back = json.loads(tree_bytes.decode('utf-8'))
ids = [r.get('Node ID') for r in back['civ_techs_units']]
assert UNIT_ID in ids and TECH_ID in ids
u = back['civ_techs_units'][ids.index(UNIT_ID)]
t = back['civ_techs_units'][ids.index(TECH_ID)]
assert (u['Building ID'], u['Age ID'], u['Use Type']) == (82, 3, 'Unit'), u
assert (t['Building ID'], t['Age ID'], t['Use Type']) == (109, 1, 'Tech'), t
assert 'path' not in back
print('[tree] rows %d -> %d  roundtrip=ok  bytes=%d'
      % (144, len(back['civ_techs_units']), len(tree_bytes)))

# ------------------------------------------------------------------ 5) 面板
panel_path, panel_key = BP.panel_path_for(G, CIV)
text, obj = BP.load_panel(panel_path)
t1 = BP.insert_entry(text, panel_key, 82,
                     {'ID': UNIT_ID, 'Name': UNIT_ZH, 'RequiredAge': 3},
                     space=BP.UNITS_KEY)
t2 = BP.insert_entry(t1, panel_key, 109,
                     {'ID': TECH_ID, 'Name': TECH_ZH, 'RequiredAge': 1},
                     space=BP.TECHS_KEY)
ok1, rep1 = BP.verify_surgical(text, t1)
ok2, rep2 = BP.verify_surgical(t1, t2)
print('[panel] insert1 ok=%s %s' % (ok1, {k: rep1.get(k) for k in ('inserted', 'kind', 'outside_is_untouched')}))
print('[panel] insert2 ok=%s %s' % (ok2, {k: rep2.get(k) for k in ('inserted', 'kind', 'outside_is_untouched')}))
assert ok1 and ok2, 'panel 外科插入不是单点插入'
panel_bytes = t2.encode('utf-8')

json_files = {
    'resources/_common/dat/CivTechTrees/%s.json' % CIV_STEM: tree_bytes,
    'resources/_common/dat/futuravailableunits.json': panel_bytes,
}
json_files.update(str_files)

# ------------------------------------------------------------------ 6) emit
dat_bytes = open(DAT, 'rb').read()
print('[dat] %d B sha=%s' % (len(dat_bytes), hashlib.sha256(dat_bytes).hexdigest()[:16]))
info = E.make_info(TITLE, author='YG', description='id 6666 单位 + id 6665 科技（高棉）')
probs = E.validate_info(info)
print('[info] %s  title_bytes=%d' % (probs or 'ok', E.title_bytes(TITLE)))
if probs:
    raise SystemExit('info.json 不合规: %s' % probs)

mod_dir = os.path.abspath(OUT)
manifest = E.emit_data_mod(mod_dir, dat_bytes, info, base_dir=G,
                            overwrite=True, json_files=json_files)
print('[emit] %s' % json.dumps({k: v for k, v in manifest.items()
                                if k in ('changes_dat', 'dat_is_carrier', 'json_overrides')},
                               ensure_ascii=False)[:400])
for rel, blob in ui_files.items():
    p = os.path.join(mod_dir, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(blob)
print('[emit] ui files %d' % len(ui_files))
ui_dir = E.split_ui_layer(mod_dir, info=info)
print('[split] %s' % ui_dir)
print('OK')

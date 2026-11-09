# -*- coding: utf-8 -*-
"""优先级冲突体检：我们的 UI 半（materials.json）会不会被更高优先级的 mod 覆盖。"""
import json
import os
import sys

sys.path.insert(0, '.')
from aoe2mod.game import locations as LOC

PR = r'C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391'
doc, acc, _ = LOC.read_status_doc(PR)

rows = []
for m in doc['Mods']:
    if not m.get('Enabled'):
        continue
    rel = m['Path'].replace('//', '/')
    p = os.path.join(acc, 'mods', rel.replace('/', os.sep))
    mats = os.path.join(p, 'widgetui', 'materials.json')
    icons = os.path.join(p, 'widgetui', 'icons.json')
    dats = os.path.join(p, 'resources', '_common', 'dat', 'empires2_x2_p1.dat')
    rows.append((int(m['Priority']), m['Title'], os.path.isfile(mats),
                 os.path.getsize(mats) if os.path.isfile(mats) else 0,
                 os.path.isfile(icons), os.path.isfile(dats), p))

for r in sorted(rows):
    print('P%-3d mats=%-8s icons=%-5s dat=%-5s  %s'
          % (r[0], r[3] or '-', r[4], r[5], r[1][:46]))

print('')
ours = [r for r in rows if r[1].startswith('YG ') and r[3]]
print('我们的 materials.json 条目：')
for r in ours:
    print('  P%d  %s  %d B' % (r[0], r[1], r[3]))

hi = [r for r in rows if r[3] and (not ours or r[0] < ours[0][0])]
print('优先级更高、也带 materials.json 的 mod：%d 个' % len(hi))
for r in hi:
    print('  P%d %s' % (r[0], r[1]))

# 高优先级的 materials.json 里是否已经写了我们这两条材质
key_u, key_t = 'UnitIcons17450730', 'TechIconsT150ArchaicAge'
for r in hi:
    d = json.loads(open(os.path.join(r[6], 'widgetui', 'materials.json'),
                        encoding='utf-8-sig').read())
    mt = {m['MaterialDef']['Name']: m['MaterialDef'] for m in d['Materials']}
    print('  %s -> %s / %s' % (r[1][:34],
                               mt.get(key_u, {}).get('Type'),
                               mt.get(key_t, {}).get('Type')))

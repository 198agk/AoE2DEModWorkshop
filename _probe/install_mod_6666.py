# -*- coding: utf-8 -*-
"""把 _out 下两个 mod 目录装进玩家档案，并回读 mod-status.json 证明两条都 enabled。

装完立刻做一次"落地复检"：装好的 dat 的 sha256 必须等于构建产物的 sha256 ——
否则玩家开的是旧字节，前面所有验证都白做。
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aoe2mod.game import locations as LOC

PR = r'C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, '..', '_out'))

MAIN = os.path.join(OUT, 'mod_6666_yg')
UI = os.path.join(OUT, 'mod_6666_yg_ui')


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


built = sha(os.path.join(MAIN, 'resources', '_common', 'dat', 'empires2_x2_p1.dat'))
print('[build] dat sha256 = %s' % built[:24])

man = {}
for d in (MAIN, UI):
    m = LOC.install_mod(d, PR, kind='local', enabled=True, overwrite=True, backup=True)
    man[d] = m
    print('[inst] %-22s -> %s' % (os.path.basename(d), m['mod_dir']))
    print('       enabled=%s priority=%s path=%r' % (m['enabled'], m['priority'], m['path_field']))

# 落地复检
inst_dat = man[MAIN]['dat']
print('[inst] installed dat %s' % inst_dat)
got = sha(inst_dat)
print('[inst] installed sha256 = %s' % got[:24])
assert got == built, '装进去的字节与构建产物不一致'

doc, acc, sp = LOC.read_status_doc(PR)
print('[status] %s  entries=%d' % (sp, len(doc.get('Mods', []))))
names = []
for e in doc.get('Mods', []):
    if 'yg' in str(e.get('Path', '')).lower() or '高棉禁卫' in str(e.get('Title', '')):
        names.append(e)
        print('  %s' % json.dumps({k: e.get(k) for k in ('Path', 'Title', 'Enabled', 'Priority')},
                                  ensure_ascii=False))
print('[status] our entries = %d' % len(names))
assert len(names) == 2, '应写入 2 条（数据 + 界面）'
assert all(e['Enabled'] for e in names), '有条目没被启用'
print('OK 两个 mod 已装并启用；字节一致')

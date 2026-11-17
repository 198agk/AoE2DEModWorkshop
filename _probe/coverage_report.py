# -*- coding: utf-8 -*-
"""量一遍：这个工具到底覆盖了 .dat 的多少，以及 AGE3 有而我们没有的到底是什么。

数字全部现场算，不抄文档。跑法：
  C:/Users/26913/AppData/Local/Python/bin/python.exe -X utf8 -u _probe/coverage_report.py
"""
import sys, io, contextlib, os, json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aoe2mod.ui.server import App
import aoe2mod.dat.tablefields as TF

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_tmp', 'coverage.md')

app = App()
raw = app.session_raw()
with contextlib.redirect_stdout(io.StringIO()):
    bounds, stats = TF.stage_offsets(raw, '7 ', quiet=True)
gv = stats.get('game_version')

TABLES = ('graphic', 'sound', 'effect', 'terrain', 'restriction', 'colour', 'task', 'map', 'tail', 'techtree')
rows = []
tot_rec = tot_fld = tot_ro = 0
for t in TABLES:
    with contextlib.redirect_stdout(io.StringIO()):
        recs, _ = TF.scan(raw, t)
    nf = nz = nh = ro = 0
    names = set()
    for rec in recs:
        with contextlib.redirect_stdout(io.StringIO()):
            fs = TF.fields_at(raw, gv, rec, t)
        for name in fs:
            nf += 1
            names.add(name)
            m = TF.meta_for(t, name)
            if not m.get('zh'): nz += 1
            if not m.get('hint'): nh += 1
            if m.get('ro'): ro += 1
    rows.append(dict(table=t, zh=TF.TABLE_ZH.get(t, t), recs=len(recs),
                     fields=nf, names=len(names), ro=ro, nozh=nz, nohint=nh))
    tot_rec += len(recs); tot_fld += nf; tot_ro += ro

# 单位与文明走公开接口那条路，跟 UI 拿到的一模一样
u = app.unit_fields(83)
u_n = len(u.get('fields') or [])
c = app.table_fields('civ', 0)
c_n = len(c.get('fields') or [])

lines = []
lines.append('# 覆盖度报告（现场算的数字）')
lines.append('')
lines.append('游戏版本 gv = %s' % gv)
lines.append('')
lines.append('## 十张全局表')
lines.append('')
lines.append('| 页签 | 记录数 | 字段总计 | 不同字段名 | 只读 | 缺中文名 | 缺解释 |')
lines.append('|---|---|---|---|---|---|---|')
for r in rows:
    lines.append('| %s | %d | %d | %d | %d | %d | %d |' % (
        r['zh'], r['recs'], r['fields'], r['names'], r['ro'], r['nozh'], r['nohint']))
lines.append('')
lines.append('合计：%d 条记录 / %d 个字段 / %d 只读' % (tot_rec, tot_fld, tot_ro))
lines.append('')
lines.append('单位 83 一条记录 %d 个字段；文明 0 号一条记录 %d 个字段。' % (u_n, c_n))
lines.append('')
open(OUT, 'w', encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines))

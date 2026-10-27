# coding: utf-8
"""Dump Python's /api/parse rows for every sentence the Rust reader understands.

The point is the PLAN shape: Rust must print the same numbers for the same
sentence, or the page shows a preview that the build will not honour.
"""
import json, os, sys, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from aoe2mod.ui import server as S

SENTS = [
    '村民血量改成100',
    '不列颠兵营攻击力加5',
    '织布术研究时间减少5秒',
    '织布术花费减少10食物',
    '把织布术的第0条效果改成5',
    '把织布机和铸币术做成只能选一个',
    '把民兵放在第5格',
    '把民兵的攻击类别改成步兵',
    '把民兵的贴图换成剑士',
]

app = S.App()
for s in SENTS:
    r = app.parse(s)
    for c in r['clauses']:
        p = c.get('preview') or {}
        plan = p.get('plan') or {}
        keep = {}
        for k in ('description','entity_id','entity_name','kind','stat','op','amount',
                  'writes','civ_count','edit_count','editable','changes_dat',
                  'button','builder_names','member_count','shape','warnings','reason',
                  'notes','buildable'):
            if k in plan or k in c:
                v = plan.get(k, c.get(k))
                if isinstance(v, list) and len(v) > 6:
                    v = v[:3] + ['...%d' % len(v)]
                keep[k] = v
        keep['_intent'] = (c.get('intent') or {}).get('intent')
        keep['_preview_ok'] = p.get('ok')
        keep['_preview_err'] = p.get('error')
        print(json.dumps(keep, ensure_ascii=False))

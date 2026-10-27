import json, sys
sys.path.insert(0, "D:/Software/AI/帝国项目")
from aoe2mod.ui.server import App
app = App()
for s in ["让弓兵的样子换成长弓兵", "让村民的样子换成绵羊"]:
    got = app.parse(s)
    cl = (got.get("clauses") or [{}])[0]
    p = (cl.get("preview") or {}).get("plan") or {}
    print("=== %s" % s)
    for k in ("description","shape","edit_count","civ_count","civs","records","changes_dat","target_stems","donor_stems","file_count"):
        print("  %-12s %s" % (k, json.dumps(p.get(k), ensure_ascii=False)))

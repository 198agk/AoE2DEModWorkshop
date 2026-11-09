import json, sys
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..")))
from aoe2mod.ui.server import App
import os
app = App()
for s in ["让弓兵的样子换成长弓兵", "织布机第1条效果改成100", "把织布机和铸币术做成只能选一个"]:
    got = app.parse(s)
    cl = (got.get("clauses") or [{}])[0]
    print("=== %s" % s)
    print(json.dumps(cl.get("preview"), ensure_ascii=False, indent=1)[:1500])

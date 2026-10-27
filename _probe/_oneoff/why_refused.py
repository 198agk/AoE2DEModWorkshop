"""Why does the reader resolve a unit whose type50 has no attacks?

The earlier refusal ("步弓手 没有「基础攻击」这项可以改") and the target resolver
agreeing unit 4 DOES have a class-3 entry cannot both be right.  Find out which
id the sentence actually names.
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import aoe2mod.ui.server as S

app = S.App()
for s in ["步弓手对骑兵攻击加2", "民兵对弓箭手护甲加3", "城堡基础攻击加5"]:
    j = app.parse(s)
    c = (j.get("clauses") or [{}])[0]
    it = (c.get("intent") or {})
    print(s)
    print("  intent", it.get("intent"), "unit", it.get("unit"), "entity", c.get("entity"), c.get("entity_id"))
    print("  class_id", it.get("class_id"), "class_label", it.get("class_label"), "kind", it.get("kind"))
    p = (c.get("preview") or {}).get("plan") or {}
    print("  plan stat", p.get("stat"), "editable", p.get("editable"), "reason", p.get("reason"))
    print()

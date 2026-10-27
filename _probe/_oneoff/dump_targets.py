"""Dump the exact byte targets Python writes for the two intents Rust is missing.

The point is not to re-derive the rule but to have a number Rust must land on:
`edit_count` alone can agree while the offsets differ.
"""
import io, json, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import aoe2mod.ui.server as S

GAME = r"d:\games\steam\steamapps\common\AoE2DE"
app = S.App()
SENTENCES = [
    "民兵人口成本设为0",
    "民兵木材成本减少10",
    "步弓手对骑兵攻击加2",
    "民兵对弓箭手护甲加3",
    "城堡基础攻击加5",
]
for s in SENTENCES:
    j = app.parse(s)
    c = (j.get("clauses") or [{}])[0]
    p = (c.get("preview") or {}).get("plan") or {}
    keep = {k: p.get(k) for k in
            ("kind", "stat", "shape", "edit_count", "editable", "civ_count",
             "description", "reason", "resource", "class_id", "class_label",
             "op", "amount", "delta", "writes")}
    print("SENTENCE", s)
    print("  preview", json.dumps(keep, ensure_ascii=False, sort_keys=True))
    offs = p.get("offsets") or p.get("targets") or []
    print("  offset keys", [k for k in p if "off" in k or "targ" in k])
    print()

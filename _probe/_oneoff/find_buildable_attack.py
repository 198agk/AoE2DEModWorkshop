"""Which `unit.attack_class` sentences does the reader itself consider buildable?

The gate needs a case that Python both reads AND can build.  Class 12 (骑兵) has
zero attack entries in the whole .dat, so `对骑兵攻击加2` can never build -- my
gate case was wrong, not the reader.
"""
import os, sys, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import aoe2mod.ui.server as S

app = S.App()
CASES = [
    "城堡攻击加5",
    "民兵攻击加2",
    "步弓手攻击加2",
    "投石车攻击加5",
    "骑士攻击加2",
    "长枪兵攻击加2",
    "精锐掷矛手攻击加1",
    "民兵护甲加3",
    "步弓手护甲加1",
    "骑士护甲加1",
    "城堡护甲加2",
    "民兵对弓箭手攻击加2",
]
for s in CASES:
    j = app.parse(s)
    c = (j.get("clauses") or [{}])[0]
    it = c.get("intent") or {}
    p = (c.get("preview") or {}).get("plan") or {}
    ok = p.get("editable")
    print("%-20s %-22s class=%-4s editable=%-5s edits=%-6s %s"
          % (s, it.get("intent"), it.get("class_id"), ok,
             p.get("edit_count"), (p.get("reason") or "")[:46]))

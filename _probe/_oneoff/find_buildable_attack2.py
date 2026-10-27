"""Does `unit.attack_class` ever build when the class named IS one the unit carries?"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import aoe2mod.ui.server as S

app = S.App()
CASES = [
    # 民兵 74 attacks classes: 29, 21, 4, 8, 30, 15
    "民兵对平民攻击加2",
    "民兵对建筑攻击加2",
    "民兵对家畜攻击加2",
    # 民兵 74 armors classes: 1, 4, 3, 31
    "民兵对平民护甲加3",
    "民兵对建筑护甲加3",
    "民兵对神器护甲加3",
    # 城堡 82
    "城堡对建筑攻击加5",
    # 步弓手 4 attacks classes: class 3 present (from earlier dump: atk 含 (3,4))
    "步弓手对建筑攻击加2",
]
for s in CASES:
    j = app.parse(s)
    c = (j.get("clauses") or [{}])[0]
    it = c.get("intent") or {}
    p = (c.get("preview") or {}).get("plan") or {}
    print("%-22s %-20s class=%-4s %-14s edits=%-5s %s"
          % (s, it.get("intent"), it.get("class_id"), it.get("kind"),
             p.get("edit_count"), (p.get("reason") or "")[:44]))

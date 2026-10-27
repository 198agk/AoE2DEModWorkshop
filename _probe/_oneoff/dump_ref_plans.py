import sys, json
sys.path.insert(0, '.')
from aoe2mod.ui.server import App
a = App()
SENTS = [
 "村民血量改成100", "不列颠村民血量改成100",
 "民兵黄金成本减少5", "民兵人口成本设为0",
 "织布机研究时间 -5", "织布机黄金成本 -10",
 "织布机第1条效果改成100", "织布机第2条效果加5", "织布机效果加5", "织布机第0条效果加5",
 "把织布机和铸币术做成只能选一个",
 "民兵对平民攻击加2", "民兵对建筑攻击加2", "民兵对骑兵攻击加2", "城堡对建筑攻击加5",
 "让村民长得像绵羊", "让弓兵长得像长弓兵",
 "把民兵放在第5格", "把民兵挪到兵营的第5格",
]
for s in SENTS:
    j = a.parse(s)
    c = (j.get("clauses") or [{}])[0]
    pl = (c.get("preview") or {}).get("plan") or {}
    print("==", s)
    print("  intents:", json.dumps(j.get("intents"), ensure_ascii=False))
    if c.get("why"): print("  why:", c["why"])
    print("  plan:", json.dumps(pl, ensure_ascii=False, sort_keys=True))

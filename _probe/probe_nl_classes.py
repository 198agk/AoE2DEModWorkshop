# -*- coding: utf-8 -*-
"""Can a Chinese sentence name a damage class without naming a unit or a tech?

`unit.attack_class` addresses a (kind, class_id) pair, and the only words a
player has for a class are the game's own class names (弓箭手, 骑兵, 步兵,
建筑 ...).  Some of those words are ALSO shipped entity names, and the parser
resolves entity names first -- so before writing the rule this measures which
class names collide and with what.

Also measures what a tech.effect sentence has to say: the command index, and
whether "第N条效果" is unambiguous for the techs people actually edit.
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from aoe2mod import api as A
from aoe2mod.intent import compiler as C
from aoe2mod.semantic import index as SI
from aoe2mod.ui import nl

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
tk = A.open_toolkit(game_root=GAME)
ix = SI.index()
vocab = nl.Vocabulary(ix.units, ix.techs)

tables = C.load_effect_tables()
zh = (tables.get("zh") or {}).get("classes") or {}
en = (tables.get("classes") or {}).get("classes") or {}

print("=== class names that collide with a shipped entity name or a common word")
unit_names = {}
tech_names = {}
for e in ix.units.values():
    for f in (e.zh, e.en):
        if f:
            unit_names.setdefault(nl._norm(f), []).append(e.id)
for e in ix.techs.values():
    for f in (e.zh, e.en):
        if f:
            tech_names.setdefault(nl._norm(f), []).append(e.id)

by_zh = {}
for k, name in zh.items():
    if not name:
        continue
    by_zh.setdefault(name, []).append(int(k))

for name in sorted(by_zh, key=lambda n: by_zh[n][0]):
    key = nl._norm(name)
    u = unit_names.get(key)
    t = tech_names.get(key)
    spans = vocab.spans(name)
    flag = "UNIT" if u else ("TECH" if t else "")
    if flag or spans:
        print("   %-12s ids=%-10s %-5s spans=%s"
              % (name, by_zh[name][:6],
                 flag, [(s[1], s[2], s[0].id) for s in spans][:3]))

print()
print("=== how many class names are clean one-word spans")
clean = [n for n in by_zh if not vocab.spans(n)]
print("   clean class words: %d of %d" % (len(clean), len(by_zh)))
print("   sample:", sorted(clean, key=lambda n: by_zh[n][0])[:14])

print()
print("=== 对-class sentences today")
for s in ("步弓手对骑兵攻击加2", "步弓手对骑兵防御加2", "步弓手对弓箭手攻击加1",
          "步弓手对建筑攻击加10", "村民对骑兵攻击加2"):
    cl = nl.read_clause(s, vocab, civ_names=tk.civ_names, civ_zh=nl.CIV_ZH)
    print("   %-24s -> %s" % (s, cl.intent or ("NO: " + cl.why)))

print()
print("=== tech.effect: how many commands do editable techs have?")
hist = {}
for tid in range(len(tk._tech_records())):
    try:
        eff = tk.effects(tid, fanout=False)
    except Exception:
        continue
    n = eff.get("command_count") or 0
    hist[n] = hist.get(n, 0) + 1
print("   command count -> techs:", dict(sorted(hist.items())))
print("   techs with exactly 1 command: %d" % hist.get(1, 0))
print("   techs with 0: %d, 2 or more: %d"
      % (hist.get(0, 0), sum(v for k, v in hist.items() if k >= 2)))

print()
print("=== what a one-command tech's only command reads like")
shown = 0
for tid in range(len(tk._tech_records())):
    eff = tk.effects(tid, fanout=False)
    if eff.get("command_count") == 1 and shown < 6:
        row = eff["rows"][0]
        print("   tech %-4s %-18s #0 %s %s %s"
              % (tid, (eff.get("name") or "")[:18], row.get("type_label"),
                 row.get("attribute_label"), row.get("target_label")))
        shown += 1

print()
print("=== 织布机-style sentences today")
for s in ("织布机第2条效果加5", "织布机第2条加5", "织布机的效果加5",
          "织布机第二条效果改成10"):
    cl = nl.read_clause(s, vocab, civ_names=tk.civ_names, civ_zh=nl.CIV_ZH)
    print("   %-24s -> %s" % (s, cl.intent or ("NO: " + cl.why)))

print()
print("=== availability words: which verb does a tech sentence use?")
for s in ("印加不能研究织布机", "印加不能造织布机", "给不列颠解锁织布机",
          "印加禁用织布机"):
    cl = nl.read_clause(s, vocab, civ_names=tk.civ_names, civ_zh=nl.CIV_ZH)
    print("   %-24s -> %s" % (s, cl.intent or ("NO: " + cl.why)))

print()
print("=== sprite sentences today")
for s in ("把村民的样子换成步弓手", "村民的样子改成步弓手", "村民换成步弓手的造型",
          "给村民换张图 D:\\Software\\AI\\帝国项目\\_shots\\live_unit83.png"):
    cl = nl.read_clause(s, vocab, civ_names=tk.civ_names, civ_zh=nl.CIV_ZH)
    print("   %-34s -> %s" % (s[:34], cl.intent or ("NO: " + cl.why)))

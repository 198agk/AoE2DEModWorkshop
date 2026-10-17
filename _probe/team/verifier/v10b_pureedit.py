"""v10b: CORRECT pure-edit test for the two JSON files.
Hypothesis H: the mod file differs from the game file by ONE contiguous
insertion (tree) or ONE contiguous deletion (panel), with no other byte touched.
Test: pre = common prefix length; d = len(mod)-len(game).
  insertion (d>0):  game[pre:] == mod[pre+d:]   AND  mod[pre:pre+d] is the inserted text
  deletion  (d<0):  game[pre-d:] == mod[pre:]   AND  game[pre:pre-d] is the deleted text
Also report the truly-different byte count under that aligned model (== |d|),
and re-derive pre WITHOUT assuming anything. Raw bytes only."""
import hashlib
import os

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\local\aoe2mod Smoke5 TreeVsPanel"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

out = []


def p(s=""):
    out.append(s)
    print(s)


def common_prefix(a, b):
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def analyse(tag, gpath, mpath):
    with open(gpath, "rb") as f:
        g = f.read()
    with open(mpath, "rb") as f:
        m = f.read()
    p("-- %s --" % tag)
    p("   game %d B sha256 %s" % (len(g), hashlib.sha256(g).hexdigest()))
    p("   mod  %d B sha256 %s" % (len(m), hashlib.sha256(m).hexdigest()))
    d = len(m) - len(g)
    pre = common_prefix(g, m)
    p("   length delta (mod-game) = %+d ; common prefix = %d bytes ; first diff at %d"
      % (d, pre, pre))
    if d > 0:
        inserted = m[pre:pre + d]
        tail_ok = g[pre:] == m[pre + d:]
        p("   PURE INSERTION: game[%d:] == mod[%d:] ? %s" % (pre, pre + d, tail_ok))
        p("   inserted bytes: %d ; text: %r" % (len(inserted), inserted))
        p("   differing byte COUNT under the aligned model: %d (== length delta)" % d)
        p("   inserted text is valid JSON on its own: %s" % _isjson(inserted))
        return {"kind": "insert", "pre": pre, "n": d, "tail_ok": tail_ok, "text": inserted}
    else:
        deleted = g[pre:pre - d]
        tail_ok = g[pre - d:] == m[pre:]
        p("   PURE DELETION: game[%d:] == mod[%d:] ? %s" % (pre - d, pre, tail_ok))
        p("   deleted bytes: %d ; text: %r" % (len(deleted), deleted))
        p("   differing byte COUNT under the aligned model: %d (== length delta)" % -d)
        return {"kind": "delete", "pre": pre, "n": -d, "tail_ok": tail_ok, "text": deleted}


def _isjson(b):
    import json
    try:
        json.loads(b.decode("utf-8-sig"))
        return True
    except Exception:
        try:
            json.loads(("[" + b.decode("utf-8-sig") + "]").replace(",\r\n    {", ",\r\n    {", 1))
        except Exception:
            return "not-standalone (expected: a list element, needs surrounding [ ])"
        return "parses once wrapped as a list element"


r1 = analyse("BRITONS.json",
             os.path.join(GAME, r"resources\_common\dat\CivTechTrees\BRITONS.json"),
             os.path.join(MOD, r"resources\_common\dat\CivTechTrees\BRITONS.json"))
p("")
r2 = analyse("futuravailableunits.json",
             os.path.join(GAME, r"resources\_common\dat\futuravailableunits.json"),
             os.path.join(MOD, r"resources\_common\dat\futuravailableunits.json"))

p("")
p("### stronger: mod == game with the single edit applied, byte for byte")
def apply_insert(g, pre, text):
    return g[:pre] + text + g[pre:]


def apply_delete(g, pre, n):
    return g[:pre] + g[pre + n:]


with open(os.path.join(GAME, r"resources\_common\dat\CivTechTrees\BRITONS.json"), "rb") as f:
    gt = f.read()
with open(os.path.join(MOD, r"resources\_common\dat\CivTechTrees\BRITONS.json"), "rb") as f:
    mt = f.read()
with open(os.path.join(GAME, r"resources\_common\dat\futuravailableunits.json"), "rb") as f:
    gp = f.read()
with open(os.path.join(MOD, r"resources\_common\dat\futuravailableunits.json"), "rb") as f:
    mp = f.read()
sh = apply_insert(gt, r1["pre"], r1["text"])
p("  tree  : game + inserted-block == mod : %s" % (sh == mt))
p("          sha256 recomputed  %s" % hashlib.sha256(sh).hexdigest())
p("          sha256 mod on disk %s" % hashlib.sha256(mt).hexdigest())
sp = apply_delete(gp, r2["pre"], r2["n"])
p("  panel : game - deleted-block  == mod : %s" % (sp == mp))
p("          sha256 recomputed  %s" % hashlib.sha256(sp).hexdigest())
p("          sha256 mod on disk %s" % hashlib.sha256(mp).hexdigest())

with open(os.path.join(HERE, "v10b_out.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(out))

# -*- coding: utf-8 -*-
"""What does the screen do with a sentence it READ but cannot DO?

The parser answers one question ("which entity and which field?").  A clause
having an intent therefore does NOT mean the edit is possible: the plan can
still refuse it (never had it / already has it / nothing would change / no such
field).

`index.html` counts `good` by `c.intent is not None`, and `doBuild()` sends
every clause that has an intent.  If a refused clause is counted as good then:

  * "生成并安装" is offered for work that cannot be done, and
  * the whole bundle fails, taking the sentences that WERE possible with it.

This probe measures both halves without a browser: it calls the same App the
server calls and reports what the screen would show and what build would get.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from aoe2mod.ui import server as S  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

#: sentences whose READING is fine but whose EDIT is not.  Every one of these
#: must reach the screen as "understood, but refused", not as "will build".
REFUSED = [
    "给不列颠解锁村民",              # villagers are in no tech tree at all
    "织布机研究时间加0",             # nothing would change
    "村民木材成本加10",              # villagers have no wood cost slot
    "取消不列颠的蔷琵侦察兵",        # British never had it, so nothing to remove
]

#: a sentence that IS possible, so a bundle mixing it with a refusal shows
#: whether the refusal takes the good edit down with it.
GOOD = "村民血量改成1000"


def main():
    app = S.App(game_root=GAME)
    meta = app.meta()
    print("meta ok=%s intents=%d" % (meta.get("ok"), len(meta.get("intents") or [])))

    bad = 0
    print("\n=== refused clauses: what the screen would offer ===")
    for text in REFUSED:
        cl = app.parse(text)["clauses"][0]
        has_intent = cl.get("intent") is not None
        can = bool(cl.get("buildable"))
        prev = cl.get("preview") or {}
        plan = (prev.get("plan") or {}) if prev.get("ok") else {}
        print("  %-24s intent=%-5s preview_ok=%-5s editable=%-5s -> buildable=%s"
              % (text, has_intent, prev.get("ok"), plan.get("editable"), can))
        if can:
            bad += 1
        said = plan.get("description") or prev.get("error") or cl.get("why")
        print("      it would say: %s" % said)

    print("\n=== a bundle of one possible + one refused ===")
    mix = app.parse("%s，%s" % (GOOD, REFUSED[1]))
    all_intents = [c["intent"] for c in mix["clauses"] if c.get("intent")]
    intents = [c["intent"] for c in mix["clauses"] if c.get("buildable")]
    print("  clauses=%d, understood=%d, buildable=%d"
          % (len(mix["clauses"]), len(all_intents), len(intents)))
    # The screen now sends only the buildable ones, so THAT is the path that
    # must work.  emit_data_mod refuses an empty author, so pass one.
    sunk = None
    try:
        r = app.build(intents, author="dsh")
        print("  build of the buildable ones: ok, mod_dir=%s"
              % os.path.relpath(r["manifest"]["mod_dir"], ROOT))
    except Exception as exc:
        print("  build of the buildable ones: RAISED %s: %s"
              % (type(exc).__name__, exc))
        sunk = True
    # A caller that ignores `buildable` still gets an error -- that is correct
    # (silently dropping an edit would be worse).  What is NOT acceptable is an
    # error that does not say which sentence was refused.
    if sunk is None:
        try:
            app.build(all_intents, author="dsh")
            print("  build of ALL understood: ok -- a refusal does not sink it")
        except Exception as exc:
            named = "sentence 2" in str(exc) or "第 2" in str(exc)
            print("  build of ALL understood: refused, %s: %s"
                  % ("and it NAMES the sentence" if named else
                     "and it does NOT say which sentence", exc))
            if not named:
                sunk = True

    print()
    if bad:
        print("SCREEN OFFERS BUILD FOR %d REFUSED SENTENCE(S)" % bad)
    else:
        print("every refused sentence is shown as refused")
    if sunk:
        print("AND ONE REFUSAL SINKS THE WHOLE BUNDLE")
    return 1 if (bad or sunk) else 0


if __name__ == "__main__":
    sys.exit(main())

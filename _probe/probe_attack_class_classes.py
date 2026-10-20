# -*- coding: utf-8 -*-
"""Which attack/armour classes does a unit actually carry, and does the class id
mean the same thing to `plan()` and to `build()`?

`probe_attack_class_disagreement.py` measured a disagreement that matters for
every sentence the Chinese reader understands: `步弓手对骑兵攻击加2` previews
"126 edits, editable", then the build refuses with "没有「基础攻击」这项可以改".
Two readings, and they need opposite fixes:

  A. plan() ignores the intent's `class_id` while compile_edits() honours it, so
     the preview is looking at a different field than the write.  Then plan is
     the liar and the fix is to make one binding decision for both.
  B. the class id in the sentence does not name an attack entry the unit has,
     and the build is right -- then the preview must say so too, and the reader
     needs a class id that some unit really carries.

This prints the entry table of a few units plus plan-vs-build on the same
intent, so the answer is measured rather than argued.
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import aoe2mod.api as A
from aoe2mod.dat import locate as L
from aoe2mod.ui import nl as NL

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def main():
    tk = A.open_toolkit(game_root=GAME)
    tk._ensure()
    print("class id -> chinese name, for the ids that appear below")
    names = NL.class_names()
    print("  ", {k: v for k, v in sorted(names.items(), key=lambda kv: int(kv[0]))})
    print()

    for uid, label in ((4, "步弓手"), (93, "长矛兵"), (358, "长枪兵"), (12, "兵营")):
        hits = L.find_units(tk._civs, uid)
        if not hits:
            print("unit %d %s: no record" % (uid, label))
            continue
        unit = hits[0][2]
        t50 = unit.get("type50") or {}
        print("unit %d %s  attacks=%s  armors=%s"
              % (uid, label,
                 [(a["class"], a["amount"]) for a in (t50.get("attacks") or [])],
                 [(a["class"], a["amount"]) for a in (t50.get("armors") or [])]))
        for cls in (3, 4, 12, 8):
            intent = {"intent": "unit.attack_class", "unit": uid,
                      "class_id": cls, "kind": "attack", "delta": 2}
            try:
                pl = tk.plan(intent)
                pv = "editable=%s edits=%s「%s」" % (
                    pl.get("editable"), pl.get("edit_count"), pl.get("description"))
            except Exception as exc:               # noqa: BLE001
                pv = "%s: %s" % (type(exc).__name__, exc)
            try:
                out = os.path.join(os.environ.get("TEMP", "."), "dsh_cls_probe")
                man = tk.build(intent, out, title="p", author="dsh", overwrite=True)
                bv = "ok edits=%s" % man.get("edit_count")
            except Exception as exc:               # noqa: BLE001
                bv = "%s: %s" % (type(exc).__name__, exc)
            print("   class %-2d plan %-52s build %s" % (cls, pv, bv))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

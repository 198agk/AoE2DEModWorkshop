"""A preview must say what lands on disk, and the page must show it.

Measured 2026-10-25: `unit.stat`, `unit.cost`, `tech.research_time` and `tech.effect`
returned plans with NO `writes` key, while `unit.sprite`, `unit.create`,
`tech.availability`, `tech.toggle_group` and `tech.create` all had one.  Those four
are the most common sentences in the tool, and every one of them rewrites the whole
93 MB `.dat` inside a new mod folder -- so the screen said "this works, 1,701 edits"
and never said it would replace the game's data file.

Two separate failures are pinned here, because fixing one does not fix the other:

  A. the plan does not carry the fact  (fixed in aoe2mod/api.py)
  B. the page does not print it        (fixed in aoe2mod/ui/static/index.html)

A nail that only swept plans would have been green for B forever: `writes` existed on
five intents since 2026-10-22 and no screen ever showed it.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402
from aoe2mod.game import locations as G  # noqa: E402

FAILED = []
CHECKS = [0]


def check(name, cond, detail=""):
    CHECKS[0] += 1
    if cond:
        print("  ok   %s" % name)
    else:
        print("  FAIL %s :: %s" % (name, detail))
        FAILED.append(name)


# One sentence-shaped intent per compile strategy.  The four at the top are the ones
# that were missing `writes`; the rest are the controls that always had it, so a
# broken sweep cannot pass by accident.
_CASES = (
    ("unit.stat (in_place_patch)", {"intent": "unit.stat", "unit": 83, "stat": "hit_points", "value": 60}),
    ("unit.cost (in_place_patch)", {"intent": "unit.cost", "unit": 83, "resource": "food", "delta": 5}),
    ("tech.research_time (in_place_patch)", {"intent": "tech.research_time", "tech": 22, "delta": -5}),
    ("tech.effect (in_place_patch)", {"intent": "tech.effect", "tech": 22, "command": 0, "delta": 1}),
    ("unit.availability (civtechtrees_json)", {"intent": "unit.availability", "unit": 2550, "civ": "Incas", "action": "revoke"}),
    ("tech.availability (civtechtrees_json)", {"intent": "tech.availability", "tech": 22, "civ": "Britons", "action": "grant"}),
    ("unit.sprite (loose_files)", {"intent": "unit.sprite", "unit": 83, "donor": 4}),
    ("unit.create (new_unit)", {"intent": "unit.create", "donor": 83, "civ": "British", "name": "writes nail"}),
    ("tech.toggle_group (linked_techs_json)", {"intent": "tech.toggle_group", "techs": [22, 24]}),
    ("tech.create (new_tech)", {"intent": "tech.create", "donor": 22, "civ": "British", "name": "writes nail tech"}),
)


def main():
    tk = A.open_toolkit()
    tk._ensure()
    dat_rel = "resources/_common/dat/empires2_x2_p1.dat"

    print("=== A. every editable plan names its file")
    editable = 0
    missing = []
    for label, intent in _CASES:
        try:
            p = tk.plan(intent)
        except Exception as exc:                      # noqa: BLE001 - a refusal is a result
            print("  --   %-42s refused: %s" % (label, exc))
            continue
        if not p.get("editable"):
            print("  --   %-42s not editable: %s" % (label, p.get("reason")))
            continue
        editable += 1
        w = p.get("writes")
        check("%s says what it writes" % label, bool(w), "writes=%r keys=%s" % (w, sorted(p)))
        if not w:
            missing.append(label)

    check("the sweep actually reached some editable plans", editable >= 8,
          "editable plans: %d of %d" % (editable, len(_CASES)))
    check("no editable plan is silent about its file", not missing, "silent: %s" % missing)

    print("=== B. the four that were silent all name the same .dat")
    for label, intent in _CASES[:4]:
        p = tk.plan(intent)
        check("%s -> %s" % (label.split(" (")[0], dat_rel),
              p.get("writes") == dat_rel, "got %r" % p.get("writes"))

    print("=== C. the path is a relative path the mod folder really uses")
    p = tk.plan(_CASES[0][1])
    w = p.get("writes") or ""
    check("it is relative, not absolute", not os.path.isabs(w), w)
    check("it uses forward slashes", "\\" not in w, w)
    check("it is the emitter's own DAT_REL", w == A.E.DAT_REL.replace(os.sep, "/"),
          "plan=%r emitter=%r" % (w, A.E.DAT_REL))
    check("that file exists in the install", os.path.isfile(os.path.join(tk.game_root, *w.split("/"))),
          os.path.join(tk.game_root, *w.split("/")))

    print("=== D. the page prints the field (a plan key nobody renders is half a fix)")
    page = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
    with open(page, "r", encoding="utf-8") as fh:
        html = fh.read()
    check("the page reads plan.writes", "p.writes" in html,
          "grep plan.writes in index.html: absent")
    check("and it says the Chinese word for it", "写入" in html, "no 写入 文案")
    # The edit_count label is the one this must sit next to: "N edits" alone is the
    # sentence this nail exists to stop.
    check("it sits next to the edit count", html.index("p.writes") > html.index("处改动"),
          "p.writes appears before the edit count")
    check("the comment no longer claims a renderer that did not exist",
          "The page prints `plan.writes`" not in open(
              os.path.join(ROOT, "aoe2mod", "api.py"), "r", encoding="utf-8").read(),
          "aoe2mod/api.py still says the page prints it")

    print()
    if FAILED:
        print("PLAN WRITES: %d CHECK(S) FAILED -> %s" % (len(FAILED), FAILED))
        return 1
    print("PLAN WRITES: EVERY EDITABLE PLAN NAMES THE FILE IT REWRITES, AND THE SCREEN SHOWS IT "
          "(%d checks)" % CHECKS[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

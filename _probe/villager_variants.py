"""Why does a villager show 2500 HP until it is given a task, then 25?

The in-game panel showed `村民 2500/2500` for an idle villager, but
`建筑者 (Builder) 25/25` once construction started.  A different *display name*
means a different unit record with a different LanguageDLLName -- so the engine
is switching the object to a different unit id.

Find every unit record the game could swap a villager into, and check whether
our edit reached it.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

from aoe2mod import api as A  # noqa: E402

tk = A.open_toolkit()
tk._ensure()

WORDS = ["villager", "builder", "repair", "farmer", "forager", "hunter",
         "lumberjack", "miner", "shepherd", "fisher"]
ZH = ["村民", "建筑", "修理", "农", "采集", "猎", "伐木", "矿", "牧", "渔"]

seen = {}
for w in WORDS:
    try:
        for r in tk.search(w, "unit", limit=60):
            seen[r["id"]] = r
    except Exception as exc:                     # noqa: BLE001
        print("search %r failed: %s" % (w, exc))

print("=== name matches (%d) ===" % len(seen))
for uid in sorted(seen):
    r = seen[uid]
    nm = r.get("name") or ""
    en = r.get("en") or ""
    if any(w in (nm + " " + en).lower() for w in WORDS) or any(z in nm for z in ZH):
        print("  id %-5d %-28s %s" % (uid, nm, en))

print()
print("=== describe the interesting ones ===")
for uid in (83, 293, 118, 212, 156, 592, 596, 597, 598, 599, 600, 601, 602, 603, 604, 605):
    try:
        d = tk.describe(uid, "unit")
    except Exception as exc:                     # noqa: BLE001
        print("  id %-5d <error %s>" % (uid, exc))
        continue
    s = d["stats"]
    print("  id %-5d %-22s hp=%-8s los=%-6s speed=%-8s class=%s"
          % (uid, d["name"], s.get("hit_points"), s.get("line_of_sight"),
             s.get("movement_speed"), s.get("class")))

# -*- coding: utf-8 -*-
"""Do the unit.* intents work on BUILDINGS?

Buildings are ordinary unit records of type 80, so the same machinery should
apply.  This probe checks what actually works and, more importantly, what the
toolkit currently DOES when a field does not exist on the record (a building has
no attack, a tree has no speed).  A mark that was never recorded must not turn
into a silent no-op or an offset-0 write.
"""
import io
import json
import os
import sys
import contextlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod import api as A          # noqa: E402

tk = A.open_toolkit()
print("game:", tk.game_root)

TRIES = [
    # (label, intent dict)
    ("House hp +100",        {"intent": "unit.stat", "unit": "House", "stat": "hit_points", "delta": 100}),
    ("House wood cost -5",   {"intent": "unit.cost", "unit": "House", "resource": "wood", "delta": -5}),
    ("House build time +5",  {"intent": "unit.stat", "unit": "House", "stat": "creation_time", "delta": 5}),
    ("House LOS +1",         {"intent": "unit.stat", "unit": "House", "stat": "line_of_sight", "delta": 1}),
    ("House speed +1",       {"intent": "unit.stat", "unit": "House", "stat": "movement_speed", "delta": 1}),
    ("House attack +1",      {"intent": "unit.stat", "unit": "House", "stat": "displayed_attack", "delta": 1}),
    ("Barracks hp +100",     {"intent": "unit.stat", "unit": "Barracks", "stat": "hit_points", "delta": 100}),
    ("Castle attack +5",     {"intent": "unit.stat", "unit": "Castle", "stat": "displayed_attack", "delta": 5}),
    ("Castle class-3 +5",    {"intent": "unit.attack_class", "unit": "Castle", "kind": 3, "delta": 5}),
    ("Town Center hp +100",  {"intent": "unit.stat", "unit": "Town Center", "stat": "hit_points", "delta": 100}),
]

print()
print("=== plan() on buildings ===")
for label, it in TRIES:
    try:
        p = tk.plan(it)
        print("  OK   %-22s -> %-46s | kind %s edits %s civs %s"
              % (label, p.get("description"), p.get("kind"),
                 p.get("edit_count"), p.get("civ_count")))
    except Exception as e:
        print("  %-4s %-22s -> %s: %s"
              % (type(e).__name__[:4].upper(), label, type(e).__name__, e))

print()
print("=== describe() on buildings ===")
for name in ("House", "Barracks", "Castle", "Town Center"):
    hits = tk.search(name, kind="unit")
    if not hits:
        print("  %-12s -> NO HIT" % name)
        continue
    d = tk.describe(hits[0]["id"], "unit")
    print("  id %-5s %-14s en=%-16s hp=%-5s atk=%-5s los=%-5s costs=%s"
          % (d["id"], d["name"], d.get("en"), d["stats"].get("hit_points"),
             d["stats"].get("displayed_attack"), d["stats"].get("line_of_sight"),
             d["stats"].get("costs")))

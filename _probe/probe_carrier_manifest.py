r"""What does the manifest of a unit.availability grant look like now?

The pin `test_dat_carrier.py` section E was written when the availability path
wrote only JSON, so the `.dat` was a CARRIER (byte-identical copy).  After the
`.dat` half was wired in (m27131), the grant really modifies the `.dat`, so
`dat_is_carrier` must be False and there must be no "carried UNMODIFIED"
warning.  This probe prints the truth so the pin can be rewritten to assert it.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import aoe2mod.api as A                                     # noqa: E402
from aoe2mod.mod import emitter as E                        # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
out = os.path.join(HERE, "out_carrier_probe")

tk = A.open_toolkit(game_root=GAME)
m = tk.build({"intent": "unit.availability", "unit": 2550, "civ": "British",
              "action": "grant"}, out, title="carrier probe", author="aoe2mod probe",
             overwrite=True)

print("manifest keys of interest:")
for k in sorted(m):
    if k in ("edits", "per_intent_edits"):
        print("  %-28s %d entries" % (k, len(m[k] or [])))
    elif k in ("warnings", "notes"):
        print("  %-28s %r" % (k, m[k]))
    elif "dat" in k or "json" in k or k in ("changes_dat", "edit_count", "strategy"):
        print("  %-28s %r" % (k, m[k]))
print()
print("full manifest (json):")
print(json.dumps({k: v for k, v in m.items() if k != "edits"},
                 ensure_ascii=False, indent=2, default=str)[:4000])
print()
dat = os.path.join(out, E.DAT_REL)
print("dat on disk      :", os.path.exists(dat))
base = os.path.join(GAME, E.DAT_REL)
if os.path.exists(dat) and os.path.exists(base):
    with open(dat, "rb") as fh:
        a = fh.read()
    with open(base, "rb") as fh:
        b = fh.read()
    print("dat size mod/base:", len(a), len(b))
    print("dat differs      :", a != b)

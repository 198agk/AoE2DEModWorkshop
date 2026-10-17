"""Find the authority for the villager task-variant set.

Observation to explain: an IDLE villager showed 2500/2500 in the in-game panel,
but the SAME villager, once told to build, showed `建筑者 25/25`.  A different
display name means a different unit record, and 25 means our edit did not reach
it.

Candidates for the link:
  - the exe (a hardcoded villager task table)
  - unit_headers / unit lines in the dat
  - resources/_common/dat/*.json
"""
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

from aoe2mod import api as A  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
EXE = os.path.join(GAME, "AoE2DE_s.exe")

print("=== 1. internal villager names in the exe ===")
with open(EXE, "rb") as fh:
    blob = fh.read()
for tok in (b"VMBAS", b"VMBLD", b"VMLUM", b"VMREP", b"VMFOR", b"VMFAR"):
    hits = [m.start() for m in re.finditer(re.escape(tok), blob)]
    print("   %-8s count=%d  offsets=%s" % (tok.decode(), len(hits),
                                            [hex(h) for h in hits[:6]]))

print()
print("=== 2. what sits around VMBAS / VMBLD in the exe ===")
for tok in (b"VMBAS", b"VMBLD"):
    for m in re.finditer(re.escape(tok), blob):
        s = max(0, m.start() - 200)
        e = min(len(blob), m.start() + 400)
        chunk = blob[s:e]
        strs = re.findall(rb"[ -~]{4,}", chunk)
        print("   @%s: %s" % (hex(m.start()), [x.decode() for x in strs]))
        break

print()
print("=== 3. dat dir JSON inventory ===")
dd = os.path.join(GAME, "resources", "_common", "dat")
for n in sorted(os.listdir(dd)):
    p = os.path.join(dd, n)
    print("   %-46s %s" % (n, os.path.getsize(p) if os.path.isfile(p) else "<dir>"))

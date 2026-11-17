import os as _os, sys as _sys
_p = _os.path.dirname(_os.path.abspath(__file__))
while _p and not _os.path.isfile(_os.path.join(_p, "_gamepaths.py")):
    _p = _os.path.dirname(_p)
if _p and _p not in _sys.path:
    _sys.path.insert(0, _p)
import _gamepaths as GP
"""Decisive question for the data-mod product:
Can we implement 'add a new gameplay tech' by REPURPOSING existing unused
tech/effect slots, instead of growing the dat (which would need a re-serializer)?

Surveys BASE for:
  - effects referenced by zero techs
  - techs with empty name / no research locations / not referenced by anything
"""
import os, sys, io, json, contextlib, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_dat as P

BASE = GP.DAT

data, _ = P.load_dat(BASE)
p = P.Parser(data)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
s = p.stats
techs, effects = s["techs"], s["effects"]
print("BASE techs=%d effects=%d" % (len(techs), len(effects)))

# ---- which effects are referenced by techs?
refd = collections.Counter()
for t in techs:
    e = t.get("effect_id", -1)
    if e is not None and e >= 0:
        refd[e] += 1
print("distinct effects referenced: %d / %d" % (len(refd), len(effects)))
free_eff = [i for i in range(len(effects)) if refd[i] == 0]
print("effects referenced by ZERO techs: %d" % len(free_eff))

# effect "usefulness": does it carry real commands?
def cmds(i):
    return effects[i].get("commands") or []
nonempty_free = [i for i in free_eff if len(cmds(i)) > 0]
empty_free = [i for i in free_eff if len(cmds(i)) == 0]
print("   of which NON-EMPTY (real logic): %d" % len(nonempty_free))
print("   of which EMPTY (pure placeholder): %d" % len(empty_free))

print("\n== sample non-empty unused effects (repurpose candidates) ==")
for i in nonempty_free[:15]:
    print("   eff[%d] %-40r cmds=%d" % (i, effects[i].get("name", "")[:40], len(cmds(i))))
print("\n== sample empty unused effects ==")
for i in empty_free[:5]:
    print("   eff[%d] %r" % (i, effects[i].get("name", "")))

# ---- techs: which are "internal / invisible"?
def tname(t):
    return (t.get("name") or "")
def nloc(t):
    return len(t.get("research_locations") or [])
civm1 = [t for t in techs if t.get("civ", -2) == -1]
empty_name = [t for t in techs if not tname(t).strip()]
no_loc = [t for t in techs if nloc(t) == 0]
print("\nBASE techs: total=%d  civ==-1=%d  empty-name=%d  no-research-location=%d"
      % (len(techs), len(civm1), len(empty_name), len(no_loc)))
cand = [t for t in techs if not tname(t).strip() and nloc(t) == 0 and t.get("civ", -2) == -1]
print("techs that are civ==-1 AND empty-name AND no-location: %d" % len(cand))
for t in cand[:12]:
    print("   tech[?] civ=%s eff=%s type=%s icon=%s name=%r"
          % (t.get("civ"), t.get("effect_id"), t.get("type"), t.get("icon_id"), tname(t)[:30]))

# ---- how many effects does the FULL playable set actually use?
print("\n== effect type histogram of ALL BASE effects ==")
h = collections.Counter()
for e in effects:
    for c in cmds_of if False else (e.get("commands") or []):
        h[c[0]] += 1
print("  ", dict(sorted(h.items(), key=lambda kv: -kv[1])[:12]))

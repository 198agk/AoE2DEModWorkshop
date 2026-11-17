import _gamepaths as GP
"""Trace the civ -> TechTreeID / TeamBonusID -> tech -> effect chain, and survey
'repurposable' slots (techs whose names are empty / that nothing references)."""
import os, sys, io, contextlib, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_dat as P

BASE = GP.DAT
data, _ = P.load_dat(BASE)
p = P.Parser(data)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
s = p.stats
techs, effects, civs = s["techs"], s["effects"], s["civs"]
print("civs=%d techs=%d effects=%d" % (len(civs), len(techs), len(effects)))

print("\n== civ keys ==")
print(sorted(civs[1].keys())[:30])

print("\n== first 5 civs: name / TechTreeID / TeamBonusID ==")
for c in civs[:5]:
    print("  %-12s ttid=%s tbid=%s nres=%d nunits=%d"
          % (c.get("name"), c.get("techtree_id"), c.get("team_bonus_id"),
             len(c.get("resources") or []), len(c.get("units") or [])))

# any civ key that looks like an id?
sample = civs[1]
for k, v in sample.items():
    if isinstance(v, int) and not isinstance(v, bool):
        print("  int field: %s = %s" % (k, v))

# effects referenced by techs vs by civs
refd = collections.Counter()
for t in techs:
    e = t.get("effect_id", -1)
    if e is not None and e >= 0:
        refd[e] += 1
civref = collections.Counter()
for c in civs:
    for k in ("techtree_id", "team_bonus_id"):
        v = c.get(k)
        if isinstance(v, int) and 0 <= v < len(techs):
            e = techs[v].get("effect_id", -1)
            if e >= 0:
                civref[e] += 1
print("\neffects referenced by techs: %d ; effects reachable via civ ttid/tbid: %d"
      % (len(refd), len(civref)))
print("effects referenced by NEITHER: %d"
      % len([i for i in range(len(effects)) if refd[i] == 0 and civref[i] == 0]))
neither = [i for i in range(len(effects)) if refd[i] == 0 and civref[i] == 0]
print("  sample:", [(i, (effects[i].get('name') or '')[:28]) for i in neither[:10]])

# how are civ tech tree effects wired? show a couple of tech-tree techs
print("\n== techs whose effect name contains 'Tech Tree' ==")
n = 0
for i, t in enumerate(techs):
    e = t.get("effect_id", -1)
    if e is not None and 0 <= e < len(effects):
        nm = effects[e].get("name") or ""
        if "Tech Tree" in nm:
            print("  tech[%d] civ=%-3s type=%-3s loc=%s eff=%d %r"
                  % (i, t.get("civ"), t.get("type"), t.get("research_locations"), e, nm[:32]))
            n += 1
            if n >= 6:
                break

# repurposable tech slots: empty name
print("\n== empty-name techs (%d total) ==" % len([t for t in techs if not (t.get('name') or '').strip()]))
by = collections.Counter()
for t in techs:
    if not (t.get("name") or "").strip():
        by[(t.get("civ"), t.get("type"), len(t.get("research_locations") or []))] += 1
print("  (civ, type, n_locations) -> count:", dict(by.most_common(12)))

# Are there techs nothing else references (tech ids referenced by research_locations)?
locref = set()
for t in techs:
    for loc in (t.get("research_locations") or []):
        if isinstance(loc, (list, tuple)) and len(loc) >= 4:
            if loc[3] > 0:
                locref.add(loc[3])
print("\ntech ids referenced as a research_location target: %d" % len(locref))

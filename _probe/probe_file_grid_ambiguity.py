"""Two questions the frame-grid warning depends on.

1. When several graphics records name the SAME file, do they agree on
   (frame_count, angle_count)?  If they disagree, a grid is a property of the
   RECORD, not of the file, and comparing "the target's grid" with "the donor's
   grid" is ambiguous the moment either side has more than one claimant.

2. Do the two int16 arrays inside one unit record agree with the graphics
   records about which animation each file is?  (Sanity only.)
"""
import collections
import os
import aoe2mod.api as A

tk = A.open_toolkit()
tk._ensure()
graphics = tk._stats["graphics"]
gdir = os.path.join(tk.game_root, "resources", "_common", "drs", "graphics")
on_disk = set(n[:-4] for n in os.listdir(gdir) if n.lower().endswith(".sld"))

per_file = collections.defaultdict(set)
for g in graphics:
    f = (g.get("file") or "").strip()
    if not f or f not in on_disk:
        continue
    per_file[f].add((g.get("frame_count"), g.get("angle_count")))

multi = {f: v for f, v in per_file.items() if len(v) > 1}
print("distinct files named by shipped records : %d" % len(per_file))
print("  files whose claimants DISAGREE on grid : %d" % len(multi))
for f, v in sorted(multi.items())[:8]:
    print("    %-34s %s" % (f, sorted(v)))

# Is the disagreement ever between two records that a single unit's art would
# pick up -- i.e. two records in the same stem group?
idx = A.__dict__  # not used; keep the probe honest about what it reads
stems = collections.defaultdict(lambda: collections.defaultdict(set))
for g in graphics:
    f, n = (g.get("file") or "").strip(), (g.get("name") or "").strip()
    if not f or not n or f not in on_disk:
        continue
    s = n.split(" (")[0].strip()
    stems[s][f].add((g.get("frame_count"), g.get("angle_count")))
bad_in_stem = {s: {f: v for f, v in fs.items() if len(v) > 1}
               for s, fs in stems.items()}
bad_in_stem = {s: v for s, v in bad_in_stem.items() if v}
print()
print("stems where one of their files has disagreeing claimants: %d" % len(bad_in_stem))
for s, v in sorted(bad_in_stem.items())[:8]:
    print("    %-28s %s" % (s, {k: sorted(x) for k, x in list(v.items())[:2]}))

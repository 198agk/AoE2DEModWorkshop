import os as _os, sys as _sys
_p = _os.path.dirname(_os.path.abspath(__file__))
while _p and not _os.path.isfile(_os.path.join(_p, "_gamepaths.py")):
    _p = _os.path.dirname(_p)
if _p and _p not in _sys.path:
    _sys.path.insert(0, _p)
import _gamepaths as GP
"""Verify the EMITTED MOD ARTIFACT as a black box.

Everything so far verified in-memory byte arrays.  A user never ships those --
they ship a compressed .dat inside a mod folder.  This closes the loop by
treating `out_modtest/ArcherAttackPlus2_probe/` as the shipped product and
checking it the way the game would:

  1. read the file from disk exactly as delivered
  2. inflate it with the same raw-deflate the game container uses
  3. parse it with the UNMODIFIED parser -> must reach exact EOF
  4. assert the intent is present (archer attack 6) in ALL 63 civs
  5. assert nothing else moved (hit points, unit count, effect count, tech count)

Any failure here means the deliverable is broken even though the in-memory
experiment passed.
"""
import os, sys, io, json, zlib, struct, hashlib, contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parse_dat as P
import intent_patch as IP

MODROOT = os.path.join(HERE, "out_modtest", "ArcherAttackPlus2_probe")
DAT = os.path.join(MODROOT, "resources", "_common", "dat", "empires2_x2_p1.dat")
BASE = GP.DAT

fail = []


def check(label, ok, detail=""):
    print("  [%s] %-58s %s" % ("PASS" if ok else "FAIL", label, detail))
    if not ok:
        fail.append(label)


print("=" * 78)
print("BLACK-BOX VERIFICATION OF THE SHIPPED MOD ARTIFACT")
print("=" * 78)
print("artifact: %s" % os.path.relpath(DAT, HERE))

# ---- 1. the folder shape the game requires -------------------------------
check("info.json exists at mod root", os.path.isfile(os.path.join(MODROOT, "info.json")))
check("thumbnail.png exists", os.path.isfile(os.path.join(MODROOT, "thumbnail.png")))
check("dat is at resources/_common/dat/ (game-mirroring path)",
      os.path.isfile(DAT))
with open(os.path.join(MODROOT, "info.json"), "rb") as f:
    raw_info = f.read()
try:
    info = json.loads(raw_info.decode("utf-8"))
    check("info.json is valid UTF-8 JSON", True, json.dumps(info, ensure_ascii=False)[:60])
except Exception as e:
    check("info.json is valid UTF-8 JSON", False, str(e))
    info = {}
check("info.json has the 4 required keys",
      set(info) >= {"Author", "CacheStatus", "Description", "Title"}, str(sorted(info)))
check("no stray top-level 'resources' nesting", os.path.isdir(os.path.join(MODROOT, "resources")))

# ---- 2. inflate the delivered blob ---------------------------------------
with open(DAT, "rb") as f:
    blob = f.read()
print("\n  delivered file  : %d bytes" % len(blob))
with open(BASE, "rb") as f:
    base_blob = f.read()
print("  game original   : %d bytes (%+d)" % (len(base_blob), len(blob) - len(base_blob)))

d = zlib.decompressobj(-15)
patched = d.decompress(blob) + d.flush()
check("inflates with raw deflate (window_bits=-15)", True, "%d bytes" % len(patched))
check("no trailing data after stream", len(d.unused_data) == 0,
      "%d stray byte(s)" % len(d.unused_data))
check("inflated size unchanged (geometry)", len(patched) == 93_268_152,
      "%d vs 93,268,152" % len(patched))

# ---- 3. the unmodified parser must accept it -----------------------------
p = P.Parser(patched)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
check("unmodified parser reaches exact EOF", p.r.pos == len(patched),
      "EOF %d, leftover %d" % (p.r.pos, len(patched) - p.r.pos))

# ---- 4. the intent is actually present ----------------------------------
stage8 = next(t for t in p.stage_offsets if t[0].startswith("8 Civs"))
nCiv = struct.unpack_from("<h", patched, stage8[1])[0]
r = IP.Orec(patched, stage8[1] + 2)
civs = [IP.walk_civ(r, ci) for ci in range(nCiv)]
hits = [u for c in civs for u in c["units"] if u["id"] == 4]
disp = sorted({u["type50"]["displayed_attack"] for u in hits})
raw3 = sorted({a["amount"] for u in hits for a in u["type50"]["attacks"]
               if a["class"] == 3})
check("archer record count per civ unchanged", len(hits) == 63, "%d records" % len(hits))
check("displayed_attack == 6 in every civ", disp == [6], str(disp))
check("raw class-3 attack == 6 in every civ", raw3 == [6], str(raw3))

# ---- 5. nothing else moved ----------------------------------------------
check("hit_points still 30 everywhere",
      {u["hit_points"] for u in hits} == {30},
      str({u["hit_points"] for u in hits}))
check("civ count unchanged", nCiv == 63, str(nCiv))
check("eff""ects count unchanged", len(p.stats["effects"]) == 1500,
      str(len(p.stats["effects"])))
check("techs count unchanged", len(p.stats["techs"]) == 1510,
      str(len(p.stats["techs"])))
check("total unit objects unchanged",
      sum(len(c["units"]) for c in civs) == 136861,
      str(sum(len(c["units"]) for c in civs)))

# ---- 6. the change is exactly what we asked for -------------------------
with open(BASE, "rb") as f:
    base_raw = zlib.decompressobj(-15)
    b0 = base_raw.decompress(f.read()) + base_raw.flush()
diffs = sum(1 for a, b in zip(b0, patched) if a != b)
check("exactly 126 bytes changed (63 civs x 2 fields)", diffs == 126, "%d bytes" % diffs)

print("\n" + "=" * 78)
print("VERDICT: %s" % ("SHIPPABLE ARTIFACT VALID" if not fail
                       else "%d CHECK(S) FAILED: %s" % (len(fail), fail)))
print("=" * 78)
print("""
What this proves and what it does not:
  PROVEN   the artifact on disk is structurally valid, the game's own inflate
           path reconstructs it, an independent parser accepts it to the last
           byte, the intended values are present in all 63 civilisations, and
           nothing else changed.
  NOT PROVEN  that the running game renders attack 6.  File-level validity is
           not runtime validity; that needs one in-game load.""")
sys.exit(1 if fail else 0)

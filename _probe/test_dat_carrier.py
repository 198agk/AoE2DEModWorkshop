# -*- coding: utf-8 -*-
r"""PIN: a mod that writes INSIDE the DAT storage point must carry the `.dat`.

## The reported defect

The user hit this in game, twice:

    m21855  「你的mod里没有empires2_x2_p1.dat，所以连开局都开不了」
    m21927  「能开局，村民血量1000，靶场没有火枪手」     <- same intent, `.dat` added

`unit.availability` naturally produces the failing shape: its whole point is to
change `CivTechTrees/<CIV>.json` (and the panel file) without touching one `.dat`
byte, so the first version emitted a mod with NO `.dat` at all.

## The corpus evidence

Every third-party mod on this machine that writes under `resources/_common/dat/`
ALSO carries `empires2_x2_p1.dat` -- 5 of 5 -- and the only copy without one is
this project's own JSON-only test that the user reported as unstartable
(`_probe/probe_dat_only_defect.py`).  The DAT storage point is also the only one
flagged `use_modes_path_for_mods: true` in `modes/Pompeii/Pompeii.json`, which
suggests the engine resolves that directory as a unit rather than per file.

Correlation, not proof of mechanism -- but the cost of being wrong is asymmetric:
carrying a 12 MB file that turns out to be unnecessary is harmless, while omitting
it produces a mod that stops the game from launching.

## The fix

`emit_data_mod` now copies the base `.dat` in as a CARRIER when `json_files`
reaches into the DAT storage point and no `.dat` was supplied.  Passing `base_dir`
is what makes that possible, so without it the call is REFUSED rather than silently
producing an unstartable mod.  The manifest reports `dat_is_carrier` and a warning
in place of the usual "byte-identical to base, so this mod changes nothing".

Run:  $env:PYTHONPATH='D:\\Software\\AI\\帝国项目'; python _probe\test_dat_carrier.py
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.mod import emitter as E                       # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
fails = []


def check(name, ok, detail=""):
    print("  %-72s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


print("A  the prefix test classifies mod-relative paths correctly")
CASES = [
    (os.path.join("resources", "_common", "dat", "CivTechTrees", "BRITONS.json"),
     True),
    (os.path.join("resources", "_common", "dat", "futuravailableunits.json"), True),
    ("resources/_common/dat/empires2_x2_p1.dat", True),
    (os.path.join("widgetui", "textures", "x.png"), False),
    (os.path.join("resources", "_common", "dat2", "x.json"), False),
    (os.path.join("resources", "_common", "dat"), True),
]
for rel, want in CASES:
    got = E._rel_is_under_dat_storage(rel)
    check("classified %-62s as %s" % (rel[-62:], want), got == want,
          "got %s" % got)
check("the DAT_STORAGE_REL prefix is the folder that holds empires2_x2_p1.dat",
      E.DAT_STORAGE_REL.replace("/", os.sep) ==
      os.path.join("resources", "_common", "dat"))

print()
print("B  a JSON file OUTSIDE that folder needs no carrier")
with tempfile.TemporaryDirectory() as td:
    m = E.emit_json_mod(
        os.path.join(td, "m1"),
        {os.path.join("widgetui", "x.json"): b'{"a":1}'},
        E.make_info("no carrier", author="aoe2mod probe"), base_dir=GAME)
    check("no .dat was written", m.get("dat") is None)
    check("and it is not marked as a carrier", not m.get("dat_is_carrier"))

print()
print("C  a JSON file INSIDE that folder gets the base .dat carried")
with tempfile.TemporaryDirectory() as td:
    dest = os.path.join(td, "m2")
    m = E.emit_json_mod(
        dest,
        {os.path.join("resources", "_common", "dat", "CivTechTrees",
                      "BRITONS.json"): b'{"civ_id":"BRITONS"}'},
        E.make_info("carrier", author="aoe2mod probe"), base_dir=GAME)
    check("a .dat IS written", m.get("dat") is not None and
          os.path.exists(m["dat"]))
    check("it is flagged as a carrier", m.get("dat_is_carrier") is True)
    check("the manifest names the JSON file that caused it",
          m.get("dat_storage_point_json") ==
          ["resources/_common/dat/CivTechTrees/BRITONS.json"],
          "got %r" % (m.get("dat_storage_point_json"),))
    check("it is byte-identical to the base .dat (unmodified)",
          m.get("dat_identical_to_base") is True)
    _w = " ".join(m.get("warnings") or [])
    check("the warning explains the carrier instead of saying 'changes nothing'",
          "原样带了一份" in _w and "开局就失败" in _w, "warnings=%r" % _w)
    check("the warning does NOT claim the mod changes nothing",
          "什么都没改" not in _w)
    _bytes = os.path.getsize(os.path.join(dest, E.DAT_REL))
    check("the carried file is on disk at the DAT path", _bytes > 1_000_000,
          "%d bytes" % _bytes)

print()
print("D  without base_dir the emitter REFUSES instead of emitting a broken mod")
with tempfile.TemporaryDirectory() as td:
    try:
        E.emit_json_mod(
            os.path.join(td, "m3"),
            {os.path.join("resources", "_common", "dat", "CivTechTrees",
                          "BRITONS.json"): b"{}"},
            E.make_info("no base_dir", author="aoe2mod probe"))
        check("refused when base_dir is missing", False, "it did not raise")
    except E.ModError as exc:
        check("refused when base_dir is missing", True)
        print("        %s" % str(exc)[:150])

print()
print("E  a GRANT now carries a MODIFIED .dat, not a carrier")
# This section used to assert `dat_is_carrier is True` for a grant, which was true
# until the `.dat` recipe was wired in.  A grant now writes the layer the user
# confirmed in game, so the honest assertion is the opposite one: the `.dat` on
# disk is NOT byte-identical to the base, and the carrier warning must NOT appear.
# `carried UNMODIFIED` on a mod that really changed the `.dat` is exactly the kind
# of quiet lie this project keeps paying for.
tk = A.open_toolkit(game_root=GAME)
out = os.path.join(HERE, "out_carrier_pin")
m = tk.build({"intent": "unit.availability", "unit": 2550, "civ": "British",
              "action": "grant"}, out, title="carrier pin", author="aoe2mod probe",
             overwrite=True)
_has = os.path.exists(os.path.join(out, E.DAT_REL))
check("the emitted mod contains empires2_x2_p1.dat", _has)
check("mod_contains_dat reports it truthfully", m.get("mod_contains_dat") is True,
      "got %r" % m.get("mod_contains_dat"))
check("dat_is_carrier is False -- this `.dat` is genuinely edited",
      m.get("dat_is_carrier") is False, "got %r" % m.get("dat_is_carrier"))
check("changes_dat is True", m.get("changes_dat") is True,
      "got %r" % m.get("changes_dat"))
check("the `.dat` on disk differs from the shipped one",
      m.get("dat_identical_to_base") is not True,
      "got %r" % m.get("dat_identical_to_base"))
_w = " ".join(m.get("warnings") or [])
check("the row warnings are present", ("照抄" in _w and "名字" in _w),
      "warnings=%r" % (m.get("warnings"),))
check("but the carrier warning is NOT (it would deny the edit)",
      "原样带了一份" not in _w, "warnings=%r" % (m.get("warnings"),))
check("the mod still changes the JSON layers it promised",
      os.path.exists(os.path.join(out, "resources", "_common", "dat",
                                  "CivTechTrees", "BRITONS.json")))

print()
print("F  a REVOKE now edits the `.dat` too -- since 2026-10-19 (`dsh test v17`)")
# This section used to assert the OPPOSITE: that a revoke shipped a byte-identical
# carrier because no recipe for taking a unit away had ever been confirmed in game.
# `dsh test v17` confirmed one -- and confirmed the ordering rule with it (the same
# disable won in the Castle Age and lost in the Dark Age, because the last command
# to fire wins).  So the asymmetry is gone and what must stay observable is the
# composition: the `.dat` IS edited, it is NOT a carrier, and the manifest reports
# the work rather than a refusal.
out2 = os.path.join(HERE, "out_carrier_pin_revoke")
m2 = tk.build({"intent": "unit.availability", "unit": 692, "civ": "Vikings",
               "action": "revoke"}, out2, title="revoke pin",
              author="aoe2mod probe", overwrite=True)
check("it still emits a mod", os.path.isdir(out2))
check("the `.dat` here is NOT a carrier", m2.get("dat_is_carrier") is False,
      "got %r" % m2.get("dat_is_carrier"))
check("changes_dat is True", m2.get("changes_dat") is True,
      "got %r" % m2.get("changes_dat"))
_dh = m2.get("dat_half") or {}
check("the manifest reports the `.dat` operations that ran",
      bool(_dh.get("ok")) and len(_dh.get("edits") or ()) > 0,
      "dat_half=%r" % ({k: _dh.get(k) for k in ("ok", "tech", "edits")},))
check("and it names which technology carried the disable",
      isinstance(_dh.get("tech"), int), "dat_half.tech=%r" % (_dh.get("tech"),))

print()
print("DAT CARRIER: a mod writing under the DAT storage point now carries the .dat,")
print("  because the game fails to start without it -- as the user reported twice.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)

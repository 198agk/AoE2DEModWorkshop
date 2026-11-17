# -*- coding: utf-8 -*-
r"""PIN: the test-validity verdict, on synthetic logs.

`_probe/check_test_validity.py` answers the question that made seven in-game tests
meaningless: was the mod under test loaded EARLY ENOUGH for the dat-adjacent JSON
layers to be read?  A tool like that is dangerous if it is wrong -- it would certify
an invalid test -- so its judgement is pinned here against hand-built logs where the
answer is known by construction.

The rule it implements:

    "Setup mod manager"  ... "Setup post mod manager"   <- the STARTUP enable block
    "Opening resource packages"                          <- dat storage point read
    a mod enabled INSIDE the startup block   -> VALID
    a mod enabled AFTER resource packages    -> INVALID (the .dat half still renders,
                                                the JSON half is read too early)
    no resource-packages marker              -> UNCLEAR (not evidence either way)

Run:  python _probe\test_test_validity.py
"""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

fails = []


def check(name, ok, detail=""):
    print("  %-72s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


spec = importlib.util.spec_from_file_location(
    "ctv", os.path.join(HERE, "check_test_validity.py"))
ctv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ctv)


def verdict(text, needle="aoe2mod"):
    """Run the analyser over hand-written log text and return its judgement."""
    fd, path = tempfile.mkstemp(suffix=".txt", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        r = ctv.analyse(path, needle)
        first = r["enabled"][0][0] if r["enabled"] else None
        blk = r["startup_block"]
        res = r["phase"].get("Opening resource packages")
        if first is None:
            return "absent", r
        if blk and blk[0] < first < blk[1]:
            return "VALID", r
        if res is not None and first > res:
            return "INVALID", r
        return "UNCLEAR", r
    finally:
        os.unlink(path)


BOOT = ("Initializing Mod Manager\n"
        "Setup mod manager\n"
        "{startup}"
        "Setup post mod manager\n"
        "Opening resource packages\n"
        "Running Game\n"
        "Closing video\n")

print("A  a mod inside the startup enable block is VALID")
log = BOOT.format(startup="Enabling mod #0 (aoe2mod Smoke6)\n")
v, r = verdict(log)
check("verdict is VALID", v == "VALID", "got %s" % v)
# BOOT's "Setup mod manager" is line 2 and "Setup post mod manager" is line 4 when
# the startup slot is empty of a marker line; with the mod line present it is 5.
# Assert the RELATIONSHIP (the mod sits strictly between them), not a literal pair.
_blk = r["startup_block"]
_mod = r["enabled"][0][0]
check("the mod line sits strictly inside the startup block",
      _blk is not None and _blk[0] < _mod < _blk[1],
      "block=%s mod=%s" % (_blk, _mod))

print()
print("B  a mod enabled AFTER resource packages is INVALID")
log = BOOT.format(startup="") + "Enabling mod #0 (aoe2mod Smoke6)\n"
v, r = verdict(log)
check("verdict is INVALID", v == "INVALID", "got %s" % v)
check("and it is reported later than the resource marker",
      r["enabled"][0][0] > r["phase"]["Opening resource packages"])

print()
print("C  exactly what the seven real sessions look like")
log = ("Initializing Mod Manager\n"
       "Setup mod manager\n"
       "Enabling mod #0 (Age of Anime (Chibi Edition))\n"
       "Setup post mod manager\n"
       "Opening resource packages\n"
       "Running Game\n"
       "Closing video\n"
       "Enabling mod #0 (aoe2mod Smoke6 Champi Scout)\n"
       "Terminating Mod Manager\n")
v, _r = verdict(log)
check("the real shape is judged INVALID", v == "INVALID", "got %s" % v)
v2, _r2 = verdict(log, needle="Age of Anime")
check("and a mod in the STARTUP block in the same log is VALID",
      v2 == "VALID", "got %s" % v2)

print()
print("D  the two honest non-answers")
v, _r = verdict("Setup mod manager\nSetup post mod manager\n")
check("a mod that never appears is 'absent'", v == "absent", "got %s" % v)
v, _r = verdict("Setup mod manager\nEnabling mod #0 (aoe2mod X)\n"
                "Setup post mod manager\n")
# A mod line inside the startup block WITHOUT a resource-packages marker is VALID:
# it was plainly in the startup enable list, which is the whole criterion.  (The
# earlier version of this test expected UNCLEAR and was wrong -- "no marker" only
# makes a LATE mod unclear, because then there is nothing to compare against.)
check("a startup-block mod with no resource marker is still VALID",
      v == "VALID", "got %s" % v)
v, _r = verdict("Setup mod manager\nOpening resource packages\n"
                "Enabling mod #0 (aoe2mod X)\n")
check("a late mod WITH a resource marker is INVALID", v == "INVALID",
      "got %s" % v)
v, _r = verdict("Setup mod manager\nEnabling mod #0 (aoe2mod X)\n")
check("a mod line with NEITHER a startup block NOR a resource marker is UNCLEAR",
      v == "UNCLEAR", "got %s" % v)
print("     -> the rule is: inside the startup block = VALID (that IS the")
print("        criterion); after the resource marker = INVALID; with neither")
print("        marker we cannot tell, and must NOT answer VALID.")

print()
print("E  the phase scan records the FIRST occurrence of each marker")
log = ("Setup mod manager\n"
       "Opening resource packages\n"
       "Opening resource packages\n"
       "Running Game\n")
_r = None
fd, path = tempfile.mkstemp(suffix=".txt", text=True)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(log)
    _r = ctv.analyse(path, "aoe2mod")
finally:
    os.unlink(path)
check("the first 'Opening resource packages' wins",
      _r["phase"].get("Opening resource packages") == 2,
      "phase=%s" % _r["phase"])
print("     -> the engine reads resources once; a later duplicate must not move")
print("        the deadline later and make an invalid test look valid.")

print()
print("TEST VALIDITY: the checker distinguishes VALID / INVALID / UNCLEAR / absent,")
print("  and refuses to call a missing marker valid.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)

# -*- coding: utf-8 -*-
"""A toggle must not INVENT the mod it is asked to toggle.

Found by accident on 2026-10-20: a probe POSTed ``/api/mod`` with a name that
cannot exist, expecting a refusal, and ``set_mod_enabled`` answered ``ok: true``
after inserting ``__no_such_mod__`` at Priority 1 of the player's REAL list -- a
phantom entry pointing at a folder that is not there.  It was cleaned up in the
same probe (and the ``.bak`` that got written from the contaminated state was
rewritten from the clean one), but the defect underneath is the product's:

    ``resolve_mod_name`` returns ``(name, "bare")`` for a name that matches
    nothing, and its docstring promises "the caller's own 'not installed' error
    still reads naturally" -- except ``set_mod_enabled`` had no such error.  It
    called ``upsert_mod_entry``, whose job is to create.

The fix has to keep one real-world behaviour alive: a mod folder the player
drops into ``mods/local`` by hand is registered by the game itself, so it is
NOT in ``mod-status.json`` yet.  Those must still be toggleable -- the folder on
disk is the second half of "does this mod exist".  That is the shape of every
check below: refuse when BOTH halves are missing, keep working when either is
present.

Runs against a throwaway account directory; the player's real mod list is never
written.
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from aoe2mod.game import locations as G  # noqa: E402
from aoe2mod.ui import server as S  # noqa: E402

FAILS = []


def check(label, cond, detail=""):
    print("  [%s] %s%s" % ("OK " if cond else "FAIL", label,
                           ("  -- " + detail) if detail and not cond else ""))
    if not cond:
        FAILS.append(label)


def _raw(acc):
    """The status file's bytes, or ``b""`` when it does not exist yet.

    Bytes, not the parsed doc: a refusal must leave the file EXACTLY alone, and
    a parse-and-compare would pass while ``Priority`` order got rewritten.
    """
    p = G.status_path(acc)
    if not os.path.exists(p):
        return b""
    with open(p, "rb") as fh:
        return fh.read()


def _write_status(acc, paths):
    doc = {"Mods": []}
    for i, rel in enumerate(paths):
        doc["Mods"].append(G.make_status_entry(
            rel.partition("//")[2], kind=rel.partition("//")[0],
            title="模组 %d" % (i + 1), priority=i + 1))
    os.makedirs(acc, exist_ok=True)
    with open(G.status_path(acc), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)


def main():
    tmp = tempfile.mkdtemp(prefix="dsh_toggle_unknown_")
    try:
        acc = os.path.join(tmp, "0")
        prof = os.path.join(tmp, "")
        os.makedirs(os.path.join(acc, "mods", "local"))
        _write_status(acc, ["local//真的模组"])
        os.makedirs(os.path.join(acc, "mods", "local", "真的模组"))

        print("=== a name that is in neither half is refused ===")
        before = _raw(acc)
        raised = None
        try:
            G.set_mod_enabled(prof, "__no_such_mod__", False, account=acc)
        except Exception as exc:                       # noqa: BLE001
            raised = exc
        check("it refuses instead of answering ok", raised is not None,
              "returned normally")
        check("the status file is byte-for-byte unchanged",
              _raw(acc) == before)
        doc, _, _ = G.read_status_doc(prof, account=acc)
        check("no phantom entry was created",
              [e["Path"] for e in doc["Mods"]] == ["local//真的模组"],
              repr([e["Path"] for e in doc["Mods"]]))
        check("it is not a bare KeyError/IndexError (the player reads this)",
              isinstance(raised, (FileNotFoundError, ValueError)),
              type(raised).__name__)

        print("=== the sentence is one a player can act on ===")
        text = S._sentence(raised)
        check("it names the name that was not found", "__no_such_mod__" in text,
              text)
        check("it does not lead with an English exception class",
              not text.startswith("FileNotFoundError"), text)
        import re
        # The name the caller asked for is DATA, not wording: a mod folder may be
        # called anything, and this test deliberately uses an ASCII one.  Drop
        # the quoted name first -- the same rule `_probe/test_prose_language.py`
        # applies to file names -- so real English in the sentence is still
        # caught while the player's own string does not look like a leak.
        prose = text.replace("__no_such_mod__", " ")
        check("no English words in it", not re.search(r"[A-Za-z]{2,}", prose),
              prose)
        check("it says what to do next",
              ("刷新" in text) or ("再试" in text), text)

        print("=== a folder the player dropped in by hand still toggles ===")
        hand = os.path.join(acc, "mods", "local", "手放的模组")
        os.makedirs(hand)
        got = G.set_mod_enabled(prof, "手放的模组", False, account=acc)
        check("it answers with the entry it wrote",
              got.get("path_field") == "local//手放的模组", repr(got))
        doc, _, _ = G.read_status_doc(prof, account=acc)
        check("the entry now exists in the status file",
              any(e["Path"] == "local//手放的模组" for e in doc["Mods"]),
              repr([e["Path"] for e in doc["Mods"]]))
        check("and it is disabled, as asked",
              [e["Enabled"] for e in doc["Mods"]
               if e["Path"] == "local//手放的模组"] == [False])

        print("=== and the ordinary case is untouched ===")
        before = _raw(acc)
        got = G.set_mod_enabled(prof, "模组 1", False, account=acc)   # by Title
        doc, _, _ = G.read_status_doc(prof, account=acc)
        entry = [e for e in doc["Mods"] if e["Path"] == "local//真的模组"]
        check("a Title still resolves to its folder", len(entry) == 1, repr(got))
        check("Enabled flipped", entry and entry[0]["Enabled"] is False)
        check("the file really changed (so the check above was not vacuous)",
              _raw(acc) != before)
        check("no entry was added", len(doc["Mods"]) == 2,
              repr([e["Path"] for e in doc["Mods"]]))

        print("=== uninstalling a name that is not there still reports zero ===")
        before = _raw(acc)
        res = G.uninstall_mod(prof, "__no_such_mod__", account=acc)
        check("entries_removed is 0", res["entries_removed"] == 0, repr(res))
        check("nothing was written", _raw(acc) == before)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILS:
        print("FAILED %d CHECK(S):" % len(FAILS))
        for f in FAILS:
            print("  - " + f)
        return 1
    print("MOD TOGGLE: A NAME THAT EXISTS NOWHERE IS REFUSED, NOT INVENTED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

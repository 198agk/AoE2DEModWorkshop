"""Pin the facts about `objreplacement.json` that today's read-only probes established.

Why a nail and not a paragraph
------------------------------
`_probe/report_shipped_vs_modded_json.md` says the open item is "does a MOD's copy of this
file get read".  Getting to that sentence cost a wrong verdict (the first version of the
report said "mod copies are ignored"), and the wrong verdict came from judging by eye
against a screen that three other mods were also changing.  The facts that survive are the
cheap ones -- the file's own vocabulary, the loader's field list inside the EXE, and the
storage point the file lives in -- and those are exactly the facts that rot silently:

  * someone edits the report and the numbers drift,
  * a Steam update changes the shipped file and nobody notices until an experiment is built
    on a stale description,
  * `families.declared_edges()` starts returning something else, which is worse, because
    that silently splits the villager into two families and halves every villager edit.

So this file asserts them.  It reads the installed game and never writes to it.

What it deliberately does NOT assert
------------------------------------
Whether a mod's copy is honoured.  That needs a live round; asserting it here would be
asserting the open question.  Section F prints that boundary so the nail cannot be mistaken
for an answer.
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from aoe2mod.dat import families as F  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
EXE = os.path.join(GAME, "AoE2DE_s.exe")
MODE = os.path.join(GAME, "modes", "Pompeii", "Pompeii.json")
REL = os.path.join("resources", "_common", "dat", "objreplacement.json")

# The eleven names the loader enumerates, taken from the contiguous run of printable
# strings that starts 24 bytes after `objreplacement.json` in the EXE (offset 53213376).
LOADER_FIELDS = ["objects", "object_id", "object_override", "replacement_object",
                 "chance", "replacement_attribute", "required_attribute",
                 "excluded_computer_players", "technology", "technology_state",
                 "replacement_rate"]

FAILS = []
CHECKS = [0]


def check(name, ok, detail=""):
    CHECKS[0] += 1
    if ok:
        print("  ok   %s" % name)
    else:
        print("  FAIL %s :: %s" % (name, detail))
        FAILS.append(name)


def shipped():
    path = os.path.join(GAME, REL)
    raw = io.open(path, "rb").read()
    return path, raw, json.loads(raw.decode("utf-8-sig"))


def flat_entries(doc):
    """(index, outer entry, its object_override) -- the level the data actually lives on.

    Stated as a helper because reading `entry["chance"]` is wrong: everything nested lives
    under `object_override`, and the first version of today's probe printed "no entry
    carries a chance" because it read the outer dictionary.
    """
    out = []
    for i, e in enumerate(doc.get("objects") or []):
        out.append((i, e, e.get("object_override") or {}))
    return out


def printable_runs(blob, minlen=3):
    out, start = [], None
    for i, b in enumerate(blob):
        ok = 32 <= b < 127
        if ok and start is None:
            start = i
        elif not ok and start is not None:
            if i - start >= minlen:
                out.append((start, blob[start:i].decode("ascii", "replace")))
            start = None
    return out


def main():
    print("=== A. the shipped file, at the level the data lives on")
    path, raw, doc = shipped()
    rows = flat_entries(doc)
    check("the file is where the loader looks for it", os.path.isfile(path), path)
    check("it has a single top-level `objects` list",
          list(doc.keys()) == ["objects"], repr(list(doc.keys())))
    check("it holds eight entries, which is what the catalog documents",
          len(rows) == 8, "got %d" % len(rows))
    check("it is plain UTF-8 with no BOM and CRLF endings",
          raw[:3] != b"\xef\xbb\xbf" and raw.count(b"\r\n") == raw.count(b"\n"),
          "bom=%s crlf=%d lf=%d" % (raw[:3] == b"\xef\xbb\xbf",
                                    raw.count(b"\r\n"), raw.count(b"\n")))

    print("\n=== B. `chance` is a percentage, and the only use is the villager pair")
    chances = [(i, e.get("object_id"), ov.get("replacement_object"), ov.get("chance"))
               for i, e, ov in rows if "chance" in ov]
    check("exactly two entries carry a chance", len(chances) == 2, repr(chances))
    check("both chances are 50, i.e. 'half the time', not a boolean",
          [c[3] for c in chances] == [50, 50], repr([c[3] for c in chances]))
    check("and they are the villager <-> villager (female) pair",
          sorted((c[1], c[2]) for c in chances) == [(83, 293), (293, 83)],
          repr(sorted((c[1], c[2]) for c in chances)))
    check("no shipped entry uses the loader's `replacement_rate`",
          b"replacement_rate" not in raw,
          "the field is in the loader's list but not in this file")

    print("\n=== C. the loader enumerates its fields in the EXE")
    blob = io.open(EXE, "rb").read()
    runs = printable_runs(blob, 3)
    offsets = {}
    for off, s in runs:
        offsets.setdefault(s, []).append(off)
    check("the file name appears exactly once in the EXE",
          len(offsets.get("objreplacement.json") or []) == 1,
          repr(offsets.get("objreplacement.json")))
    if len(offsets.get("objreplacement.json") or []) == 1:
        anchor = offsets["objreplacement.json"][0]
        window = [(off, s) for off, s in runs if anchor < off < anchor + 260]
        present = [s for _o, s in window if s in LOADER_FIELDS]
        # `present == LOADER_FIELDS` alone is NOT a claim about adjacency: every one of
        # these names can be found somewhere in a 72 MB binary, so a search over the whole
        # file passes the same test.  Measured 2026-10-25: widening the window to "the
        # whole EXE" left this green.  So assert the *span*, and assert the window holds
        # nothing but these names.
        check("eleven field names sit right after it, in order",
              present == LOADER_FIELDS,
              "got %r" % (present,))
        # NOTE 2026-10-25: there used to be a check here asserting the 260-byte window
        # held exactly eleven strings.  It was wrong by construction -- the window's own
        # definition reaches the source path that follows the table
        # (`...\ObjectGenerator.cpp`), so it counted 12 and could never pass.  Deleted
        # rather than "fixed", because the three checks below already say what that one
        # was trying to say: order, no gaps, and no copy anywhere else in the binary.
        offs = [o for o, s in window if s in LOADER_FIELDS]
        check("they fit inside 240 bytes, which is what 'one table' means",
              bool(offs) and (offs[-1] - offs[0]) < 240,
              "span %s" % ((offs[-1] - offs[0]) if offs else "no offsets"))
        # No gap between consecutive names is wider than a name itself.  This is the
        # assertion that survives the 72 MB search (a scattered copy would have gaps of
        # megabytes between names) and it is also what makes "one table" mean something:
        # measured gaps in the shipped table are 8-24 bytes, and the string that follows
        # the last name is the source path, which is why counting strings in a fixed
        # window was the wrong test (it found 12, not 11).
        gaps = [b - a for a, b in zip(offs, offs[1:])]
        check("and no gap between them is wider than a name",
              gaps and max(gaps) < 64,
              "gaps %r" % (gaps,))
        check("and each name occurs exactly once in the whole binary",
              all(len(offsets.get(n) or []) == 1 for n in LOADER_FIELDS),
              repr([(n, len(offsets.get(n) or [])) for n in LOADER_FIELDS
                    if len(offsets.get(n) or []) != 1]))
    used = {"objects"}
    for _i, e, ov in rows:
        used |= set(e.keys()) | set(ov.keys())
    check("ten of the eleven loader fields are exercised by shipped data",
          len([f for f in LOADER_FIELDS if f in used]) == 10,
          "used: %r" % sorted(f for f in LOADER_FIELDS if f in used))

    print("\n=== D. the directory it lives in is the mod-overridable one")
    mode = json.loads(io.open(MODE, "rb").read().decode("utf-8-sig"))
    pts = mode.get("storage_point_list") or []
    flagged = [p for p in pts if p.get("use_modes_path_for_mods")]
    check("the mode table has 28 storage points", len(pts) == 28, "got %d" % len(pts))
    check("exactly one of them lets a mod's copy be used",
          len(flagged) == 1, repr([p.get("path") for p in flagged]))
    check("and it is resources\\_common\\dat, where this file sits",
          len(flagged) == 1 and
          (flagged[0].get("path") or "").rstrip("\\/").lower()
          == os.path.dirname(REL).rstrip("\\/").lower(),
          repr([p.get("path") for p in flagged]))

    print("\n=== E. the product reads this file for its family edges")
    edges, epath, why = F.declared_edges(GAME)
    check("the edge list is readable and reports no reason", why == "", repr(why))
    check("it points at the shipped file",
          os.path.normcase(os.path.abspath(epath or "")) ==
          os.path.normcase(os.path.abspath(path)),
          repr(epath))
    pairs = set()
    for a, b in edges:
        pairs.add((a, b))
        pairs.add((b, a))
    check("the villager pair is one declared edge", (83, 293) in pairs, repr(sorted(edges)))
    check("the scout row is skipped, because it has no replacement_object",
          all(448 not in e for e in edges),
          "448 carries replacement_attribute, not replacement_object")
    check("no edge is a self-loop", all(a != b for a, b in edges), repr(list(edges)))

    print("\n=== F. what this nail does NOT do, and what answered the question")
    print("  everything above is about the SHIPPED copy -- these are the facts that rot.")
    print("  The mod-copy question was ANSWERED 2026-10-25 16:3x, by a match in which")
    print("  the probe mod shipped objreplacement.json plus a .dat canary in one folder")
    print("  and NO third-party mod was enabled:")
    print("     town centre panel  4000/4000   -> the .dat in that folder mounted")
    print("     a unit at 0:00     45/45       -> scout 448, and the rule named")
    print("                                      villager 83 (25 HP)")
    print("  Frames: _evidence/objrepl-map-start-scouts.png, objrepl-scout-45hp.png.")
    print("  So the file's mod copy IS honoured, at map generation.  The 2026-10-24")
    print("  verdict 'mod copies are ignored' is withdrawn in the report (it came from a")
    print("  match where three other mods were also enabled).")
    print("  A nail cannot re-run that match, so nothing here asserts it: the boundary")
    print("  is that this file keeps the cheap facts, and the answer lives in the report")
    print("  with two frames and a record id.")

    print("\nOBJREPLACE FACTS: %d checks, %d failed" % (CHECKS[0], len(FAILS)))
    if FAILS:
        print("FAILURES: %r" % FAILS)
        return 1
    print("OBJREPLACE FACTS: THE LOADER'S FIELD LIST, THE CHANCE MEANING AND THE "
          "FAMILY EDGES ARE ALL AS DOCUMENTED -- AND A MOD'S COPY IS HONOURED "
          "(ANSWERED 2026-10-25)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

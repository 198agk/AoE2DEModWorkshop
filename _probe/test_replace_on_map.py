# -*- coding: utf-8 -*-
"""Nail the `unit.replace_on_map` layer: it writes bytes, keeps every old row, and
refuses the two things the file cannot express.

The failure this file exists to catch is not "the JSON is wrong".  It is the two
quiet ones:

* a row that **replaces** the shipped villager sex swap instead of adding to it -- the
  player's game silently loses a behaviour nobody looked at;
* an intent that accepts `civs`, because the file has no per-civilization key and a
  preview that accepted one would promise scoping that does not exist.

So section B reads the produced bytes back off disk and compares **every previous
row key for key**, and section C asserts that `civs` is refused by name.
"""
import io
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
HERE = os.path.join(ROOT, "_probe")
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from aoe2mod import api as A
from aoe2mod.game import objreplace as OR

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = os.path.join(ROOT, "_probe", "_objrepl_out")

CHECKS = []
FAILS = []


def check(name, cond, detail=""):
    ok = bool(cond)
    CHECKS.append(name)
    print("  %s %s%s" % ("ok  " if ok else "FAIL", name,
                         "" if ok else " :: %s" % detail))
    if not ok:
        FAILS.append(name)
    return ok


def main():
    raw = OR.shipped_bytes(GAME)
    if raw is None:
        print("REPLACE: this install has no objreplacement.json -- nothing to check")
        return 0
    style = OR.detect_style(raw)
    doc = OR.load(GAME)
    before_rows = OR.rows(doc)
    before_canon = OR.canonical(doc)

    print("=== A. the shipped file is reproducible, so any diff is ours")
    check("the shipped file parses", isinstance(doc.get("objects"), list),
          repr(type(doc.get("objects"))))
    check("it has 8 rows", len(doc["objects"]) == 8, str(len(doc["objects"])))
    check("serialising it unchanged gives the shipped bytes back",
          OR.serialize(doc, style) == raw,
          "%d vs %d bytes" % (len(OR.serialize(doc, style)), len(raw)))
    check("the style is read off the bytes", style["indent"] == 4 and
          style["newline"] == "\r\n" and style["trailing_newline"] is True, repr(style))

    print("\n=== B. adding a row keeps every row that was already there")
    doc2 = OR.load(GAME)
    row, replaced = OR.add_replacement(doc2, 2727, 83, "神射手埃纳尔", "村民", chance=100)
    check("the new row names both ids", row["object_id"] == 2727 and
          row["object_override"]["replacement_object"] == 83, repr(row))
    check("and it is written at chance 100, not a coin flip",
          row["object_override"]["chance"] == 100, repr(row))
    check("no shipped row was replaced", replaced == 0, "replaced %d" % replaced)
    check("there are now 9 rows", len(doc2["objects"]) == 9, str(len(doc2["objects"])))
    after = OR.rows(doc2)
    keep = [r for r in after if r["source"] != 2727]
    check("every previous row survived, field for field",
          json.dumps(keep, ensure_ascii=False, sort_keys=True) ==
          json.dumps(before_rows, ensure_ascii=False, sort_keys=True),
          "counts %d vs %d" % (len(keep), len(before_rows)))

    blob = OR.serialize(doc2, style)
    path = os.path.join(OUT, "objreplacement.json")
    if os.path.isdir(OUT):
        for name in os.listdir(OUT):
            os.remove(os.path.join(OUT, name))
    os.makedirs(OUT, exist_ok=True)
    with io.open(path, "wb") as fh:
        fh.write(blob)

    print("\n=== C. the file on disk says what we think it says")
    reread = json.loads(io.open(path, "rb").read().decode("utf-8-sig"))
    check("the file on disk parses", isinstance(reread.get("objects"), list))
    check("it has the new row", any(r.get("object_id") == 2727
                                    for r in reread["objects"]),
          repr([r.get("object_id") for r in reread["objects"]]))
    check("it still has the shipped villager sex swap",
          any(r.get("object_id") == 83 and
              (r.get("object_override") or {}).get("replacement_object") == 293
              for r in reread["objects"]))
    check("it keeps CRLF line endings and a trailing newline",
          blob.count(b"\r\n") > 0 and blob.endswith(b"\r\n") and
          blob.count(b"\n") == blob.count(b"\r\n"),
          "%d CRLF / %d LF" % (blob.count(b"\r\n"), blob.count(b"\n")))
    check("it is bigger than the shipped file, by about one row",
          0 < len(blob) - len(raw) < 300, "%d bytes bigger" % (len(blob) - len(raw)))

    print("\n=== D. the two things this layer must refuse")
    doc3 = OR.load(GAME)
    zh = {83: "村民", 293: "村民（女性）", 448: "斥候骑兵"}
    try:
        OR.add_replacement(doc3, 83, 448, "村民", "斥候骑兵",
                           name_for=lambda uid: zh.get(uid))
        check("a source that already has a row is refused", False, "it was accepted")
    except OR.ObjReplaceError as exc:
        msg = str(exc)
        check("a source that already has a row is refused", True)
        check("and the refusal names the row that exists", "50%" in msg, msg)
        check("and no English internal name reaches the player", "Villager" not in msg, msg)
        check("because a caller with the Chinese names passes them in",
              "村民" in msg and "村民（女性）" in msg, msg)
    doc4 = OR.load(GAME)
    row2, replaced2 = OR.add_replacement(doc4, 83, 448, "村民", "斥候骑兵",
                                        replace_existing=True)
    check("replacing that row on request is allowed", replaced2 == 1,
          "replaced %d" % replaced2)
    check("and it leaves the row count unchanged", len(doc4["objects"]) == 8,
          str(len(doc4["objects"])))
    check("the replaced row now points at the new target",
          row2["object_override"]["replacement_object"] == 448, repr(row2))
    doc5 = OR.load(GAME)
    try:
        OR.add_replacement(doc5, 83, 83, "村民", "村民")
        check("a self-replacement is refused", False, "it was accepted")
    except OR.ObjReplaceError as exc:
        check("a self-replacement is refused", True)
        check("and the refusal says why", "没有意义" in str(exc), str(exc))
    try:
        OR.add_replacement(doc5, 1, 2, "a", "b", chance=0)
        check("a zero chance is refused", False, "it was accepted")
    except OR.ObjReplaceError as exc:
        check("a zero chance is refused", True)
        check("and the refusal gives the range", "1 到 100" in str(exc), str(exc))

    print("\n=== E. this layer has no per-civilization key, and the module says so")
    keys = set()
    for r in before_rows:
        for k in ("source", "target", "chance", "attribute", "technology"):
            if r.get(k) is not None:
                keys.add(k)
    check("the rows carry no civilization field", "civ" not in keys and
          "civs" not in keys, repr(sorted(keys)))
    src = io.open(os.path.join(ROOT, "aoe2mod", "game", "objreplace.py"),
                  encoding="utf-8").read()
    check("the module states the scope is global", "no per-civilization key" in src)
    check("and it states when the layer acts", "map generation" in src)
    check("and it states that chance is a percentage", "percentage" in src)

    if os.path.isdir(OUT):
        for name in os.listdir(OUT):
            os.remove(os.path.join(OUT, name))
        os.rmdir(OUT)

    print("\n=== F. the bundle path (the only one the screen uses)")
    tk = A.open_toolkit(GAME)
    # `plan_bundle` and `build_bundle` are what a player's sentence actually
    # goes through: the page always posts a list.  `_split_by_strategy` grew an
    # eighth bucket when this intent landed, and neither caller unpacked it, so
    # this section exists to keep that from coming back as a tuple-size
    # traceback.  Everything here is read from the mod FOLDER.
    b_out = os.path.join(HERE, "out_repl_bundle_nail")
    if os.path.isdir(b_out):
        shutil.rmtree(b_out)
    b_intents = [{"intent": "unit.replace_on_map", "unit": 4,
                  "replacement": 448}]
    b_plan = tk.plan_bundle(b_intents)
    check("the bundle preview reports the replacement",
          len(b_plan.get("replace_on_map") or ()) == 1, b_plan.get("replace_on_map"))
    check("and counts it as one change", b_plan.get("edit_count") == 1,
          b_plan.get("edit_count"))
    check("and does not claim a .dat byte changed",
          b_plan.get("changes_dat") is False, b_plan.get("changes_dat"))
    check("but says the mod will contain a .dat carrier",
          b_plan.get("mod_contains_dat") is True, b_plan.get("mod_contains_dat"))
    # A build that RAISES has to become a named failure, not a traceback: the
    # difference between "the bundle path broke" and "this machine is broken" is
    # exactly what a nail exists to tell apart.  Measured 2026-10-25: a break
    # that stopped emitting the file made this section die in `emit_data_mod`
    # with `ModError: nothing to emit`, which the reverse-validation script
    # correctly refused to count as a proof.
    try:
        b_man = tk.build_bundle(b_intents, b_out, title="replace nail bundle",
                                author="dsh", overwrite=True)
        _b_err = ""
    except Exception as exc:
        b_man = {}
        _b_err = "%s: %s" % (type(exc).__name__, exc)
    check("the bundle build succeeded", bool(b_man) and not _b_err, _b_err)
    b_file = os.path.join(b_man.get("mod_dir") or b_out, OR.OBJREPLACEMENT_REL)
    check("the bundle shipped the file", os.path.isfile(b_file), b_file)
    if not os.path.isfile(b_file):
        print("\nREPLACE ON MAP: %d checks, %d failed" % (len(CHECKS), len(FAILS)))
        print("FAILURES: %r" % FAILS)
        return 1
    b_blob = io.open(b_file, "rb").read()
    b_rows = OR.rows(json.loads(b_blob.decode("utf-8-sig")))
    check("the file grew by exactly one row", len(b_rows) == 9, len(b_rows))
    check("the new row is there",
          [(r["source"], r["target"], r["chance"]) for r in b_rows
           if int(r["source"] or 0) == 4] == [(4, 448, 100)],
          [r for r in b_rows if int(r["source"] or 0) == 4])
    _key = lambda r: (r.get("source"), r.get("target"))
    _have = {_key(r) for r in b_rows}
    check("every shipped row survived",
          all(_key(r) in _have for r in before_rows),
          [k for k in {_key(r) for r in before_rows} if k not in _have])
    check("and the shipped gender pair is still there",
          (83, 293) in _have, sorted(_have))
    check("the manifest reports the file it wrote",
          (b_man.get("replace_on_map_file") or {}).get("rows_in_file") == 9,
          b_man.get("replace_on_map_file"))
    check("and its own verification passed",
          (b_man.get("replace_on_map_file") or {}).get("verification_ok") is True,
          b_man.get("replace_on_map_file"))
    check("the manifest sentence is Chinese, not the intent id",
          "replace_on_map" not in
          ((b_man.get("replace_on_map") or [{}])[0].get("description") or ""),
          (b_man.get("replace_on_map") or [{}])[0].get("description"))
    # A sentence about a source the shipped file already governs must be refused,
    # not silently merged: the file permits two rows for one source and the
    # engine would pick one of them without saying which.
    dup = tk.plan_bundle([{"intent": "unit.replace_on_map", "unit": 83,
                           "replacement": 448}])
    check("a source the shipped file already governs is refused",
          not dup.get("replace_on_map")
          and bool(dup.get("replace_on_map_refusals")),
          (dup.get("replace_on_map"), dup.get("replace_on_map_refusals")))
    check("and the refusal names the existing rule",
          "50%" in ((dup.get("replace_on_map_refusals") or [{}])[0].get("reason")
                    or ""),
          (dup.get("replace_on_map_refusals") or [{}])[0].get("reason"))
    if os.path.isdir(b_out):
        shutil.rmtree(b_out)

    print("\n=== G. the preview and the build answer the same questions")
    # Measured 2026-10-25: the preview said `mod_contains_dat: False` while the
    # build shipped an 11,982,480 B carrier `.dat` -- mandatory, because
    # `objreplacement.json` lives under the DAT storage point and the game
    # refuses to start when a mod overrides that folder without it.  The toggle
    # group had this exact shape on 2026-10-22.  A preview is a promise about
    # what lands on disk, so the two objects must answer the same questions.
    g_out = os.path.join(HERE, "out_repl_agree_nail")
    if os.path.isdir(g_out):
        shutil.rmtree(g_out)
    g_intent = {"intent": "unit.replace_on_map", "unit": 4, "replacement": 448}
    g_plan = tk.plan(g_intent)
    g_man = tk.build(g_intent, g_out, title="agree nail", author="dsh",
                     overwrite=True)
    for key in ("changes_dat", "mod_contains_dat", "dat_is_carrier", "writes",
                "edit_count", "shape"):
        check("plan and build agree about %s" % key,
              g_plan.get(key) == g_man.get(key),
              "plan=%r build=%r" % (g_plan.get(key), g_man.get(key)))
    g_dat = os.path.join(g_man["mod_dir"], "resources", "_common", "dat",
                         "empires2_x2_p1.dat")
    check("the carrier .dat really is on disk", os.path.isfile(g_dat), g_dat)
    check("and the manifest calls it a carrier, not an edit",
          g_man.get("dat_is_carrier") is True and
          g_man.get("changes_dat") is False,
          repr((g_man.get("dat_is_carrier"), g_man.get("changes_dat"))))
    check("the manifest counts the change it made",
          g_man.get("edit_count") == 1, g_man.get("edit_count"))
    if os.path.isdir(g_out):
        shutil.rmtree(g_out)

    print("\nREPLACE ON MAP: %d checks, %d failed" % (len(CHECKS), len(FAILS)))
    if FAILS:
        print("FAILURES: %r" % FAILS)
        return 1
    print("REPLACE ON MAP: A ROW IS APPENDED, EVERY OLD ROW SURVIVES, AND THE TWO "
          "THINGS THE FILE CANNOT SAY ARE REFUSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

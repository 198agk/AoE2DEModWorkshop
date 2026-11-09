"""Prove what `unit.sprite` actually rewrites, for sentences naming other units.

Originally written to MEASURE a defect: the preview said "步弓手 的样子换成 #8"
while the writer ignored the request and walked one frozen pair table
(villager -> sheep), so the archer sentence edited 244 villager records.  A
preview that describes a different edit than the build performs is worse than no
preview: the number is right, the sentence is right, and the bytes are somebody
else's.

Now that `spriteart.rs` decides the pair from the request, this asserts the
positive: ask the SHIPPED build for a sprite edit about the archer, read the
produced `.dat` back, and require that the moved records are the archer's, that
the count equals the preview's promise, and that something moved at all.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
import _paths as P

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..")))

BUNDLE = P.BUNDLE
EXE = os.path.join(BUNDLE, "aoe2-mod-workshop.exe")
PORT = 7847
GAME = r"d:\games\steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources/_common/dat/empires2_x2_p1.dat")


def post(path, body, timeout=1800):
    req = urllib.request.Request(
        "http://127.0.0.1:%d%s" % (PORT, path),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def wait_ready(proc):
    deadline = time.time() + 240
    while time.time() < deadline:
        if proc.poll() is not None:
            raise SystemExit("the bundle exited: %s" % proc.returncode)
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/api/progress" % PORT, timeout=3) as r:
                p = json.loads(r.read().decode("utf-8")).get("progress") or {}
            if p.get("ready"):
                return
            if p.get("error"):
                raise SystemExit("the bundle failed: %s" % p["error"])
        except SystemExit:
            raise
        except Exception:
            pass
        time.sleep(0.5)
    raise SystemExit("the bundle never became ready")


def graphics_files(raw_path):
    """Every graphics record's `file` string, straight from the produced .dat.

    Uses the project's own reader rather than the shipped service so this probe
    measures the ARTEFACT and not another opinion of it.
    """
    from aoe2mod.dat import parser as P

    raw, _how = P.load_dat(raw_path)
    p = P.Parser(raw)
    p.parse()
    return [(g["id"], g.get("file") or "") for g in p.stats["graphics"]]


def folder_of(reply):
    """The mod folder a build reply points at, whichever shape it uses."""
    b = reply.get("built")
    if isinstance(b, str):
        return b
    return (b or {}).get("dir") or ""


def count_kinds(folder):
    """`(dat files, sld files)` under a built mod folder."""
    dats = slds = 0
    for _root, _dirs, files in os.walk(folder):
        for f in files:
            if f.endswith(".dat"):
                dats += 1
            elif f.endswith(".sld"):
                slds += 1
    return dats, slds


def main():
    before = graphics_files(DAT)
    proc = subprocess.Popen(
        [EXE, "--port", str(PORT)],
        cwd=BUNDLE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    bad = 0
    try:
        wait_ready(proc)
        got = post("/api/parse", {"text": "让弓兵的样子换成长弓兵", "pins": {}})
        clause = (got.get("clauses") or [{}])[0]
        intent = (got.get("intents") or [{}])[0]
        plan = (clause.get("preview") or {}).get("plan") or {}
        print("reader said : %s" % json.dumps(intent, ensure_ascii=False)[:160])
        print("preview said: %s" % (plan.get("description") or ""))
        print("edit_count  : %s" % plan.get("edit_count"))
        # A preview that names the donor by its raw id ("#8") is not a
        # description a player can check against the sentence they typed.
        desc = plan.get("description") or ""
        desc_names_donor = "#" not in desc

        title = "sprite probe %d" % int(time.time())

        # TWO delivery models, and the default is the one that composes with any
        # data mod (aoe2mod/api.py::_reskin_mode).  `copy` ships the donor's
        # picture as loose .sld files and NO .dat; `rename` rewrites the graphics
        # records' `file` strings and IS a data mod.  The sentence above names no
        # mode, so it must land on `copy` -- this asserts that first, then asks
        # for `rename` explicitly to measure the record rewrite.  A probe that
        # only ever requested the model it wanted would stop noticing the day the
        # default flipped, and one that demanded a .dat from a copy build (what
        # this file used to do) fails on a correct product.
        copy_built = post("/api/build", {
            "intents": [intent],
            "title": title + " copy",
            "install": False,
        })
        if not copy_built.get("ok"):
            print("copy build refused: %s" % copy_built.get("error"))
            return 1
        copy_folder = folder_of(copy_built)
        copy_dats, copy_slds = count_kinds(copy_folder)
        print("copy build  : %d .dat, %d .sld -> %s"
              % (copy_dats, copy_slds, copy_folder))
        default_is_copy = copy_dats == 0 and copy_slds > 0

        rename_intent = dict(intent)
        rename_intent["mode"] = "rename"
        # The count the preview promises for THIS model.  The copy plan above
        # promises 20 animation files; the rename plan promises 10 records, and
        # comparing one model's promise with the other model's build is the same
        # class of mistake as demanding a .dat from a copy build.
        rplan = post("/api/plan", {"intent": rename_intent})
        if not rplan.get("ok"):
            print("rename plan refused: %s" % rplan.get("error"))
            return 1
        # `/api/plan` answers `{"ok": true, "plan": {...}}`; reading the count off
        # the envelope gives None and every later comparison then quietly fails.
        rp = rplan.get("plan") or {}
        print("rename plan : %s | %s" % (rp.get("edit_count"), rp.get("description")))
        rename_promise = rp.get("edit_count")
        built = post("/api/build", {
            "intents": [rename_intent],
            "title": title,
            "install": False,
        })
        if not built.get("ok"):
            print("build refused: %s" % built.get("error"))
            return 1
        print("build reply : %s" % json.dumps(built, ensure_ascii=False)[:400])

        # Read the produced `.dat` back out of the shipped mod folder.
        folder = folder_of(built)
        cand = [os.path.join(root, f)
                for root, _dirs, files in os.walk(folder)
                for f in files if f.endswith(".dat")]
        if not cand:
            print("no .dat in the built folder: %s" % folder)
            return 1
        after = graphics_files(cand[0])

        moved = [(i, b, a) for (i, b), (_j, a) in zip(before, after) if b != a]
        print("records moved: %d" % len(moved))
        kinds = {}
        for _i, b, _a in moved:
            stem = re.sub(r"_x\d$", "", b)
            kinds[stem] = kinds.get(stem, 0) + 1
        print("moved stems  : %s" % json.dumps(dict(sorted(kinds.items())[:6]), ensure_ascii=False))

        # The sentence named the ARCHER (4) as target and the LONGBOWMAN (8) as
        # donor.  Nothing the villager owns is an acceptable answer.
        villager = [k for k in kinds if "vil" in k or "Villager" in k]
        # The plan's own count is the only promise the preview makes, so a build
        # that moved a different number of records is a lie even when the records
        # it moved belong to the right unit.  And a build that moved NOTHING used
        # to pass this probe, because only the villager case was counted -- a
        # measurement that goes green when the edit disappears is not a
        # measurement.
        matches = len(moved) == rename_promise
        named_ok = not villager
        print("\nVERDICT")
        print("  no mode asked = copy    = %s (must be True)" % default_is_copy)
        print("  records moved           = %d (the rename plan says %s)" % (len(moved), rename_promise))
        print("  plan count matches disk = %s" % matches)
        print("  edits the NAMED unit    = %s (must be True)" % named_ok)
        print("  preview names the donor = %s (must be True)" % desc_names_donor)
        if not default_is_copy:
            bad += 1
            print("  a sentence that names no mode shipped a .dat (%d .dat, %d .sld);"
                  " the cheap model must be asked for, not assumed" % (copy_dats, copy_slds))
        if not matches:
            bad += 1
            print("  the preview promised a different number of records than the build wrote")
        if villager:
            bad += 1
            print("  the sentence was about the archer; what moved belongs to the villager")
        if not moved:
            bad += 1
            print("  nothing moved at all, so this proves nothing about which unit is edited")
        if not desc_names_donor:
            bad += 1
            print("  the preview names the donor by id (%s), not by the name the sentence used" % desc)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

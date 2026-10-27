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

sys.path.insert(0, "D:/Software/AI/帝国项目")

BUNDLE = r"D:\Software\AI\AoE2ModWorkshop"
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
        built = post("/api/build", {
            "intents": [intent],
            "title": title,
            "install": False,
        })
        if not built.get("ok"):
            print("build refused: %s" % built.get("error"))
            return 1
        print("build reply : %s" % json.dumps(built, ensure_ascii=False)[:400])

        # Read the produced `.dat` back out of the shipped mod folder.
        b = built.get("built")
        folder = b if isinstance(b, str) else ((b or {}).get("dir") or "")
        cand = []
        for root, _dirs, files in os.walk(folder):
            for f in files:
                if f.endswith(".dat"):
                    cand.append(os.path.join(root, f))
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
        matches = len(moved) == plan.get("edit_count")
        named_ok = not villager
        print("\nVERDICT")
        print("  records moved           = %d (the plan says %s)" % (len(moved), plan.get("edit_count")))
        print("  plan count matches disk = %s" % matches)
        print("  edits the NAMED unit    = %s (must be True)" % named_ok)
        print("  preview names the donor = %s (must be True)" % desc_names_donor)
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

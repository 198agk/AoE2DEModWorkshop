# -*- coding: utf-8 -*-
r"""The v10 experiment record: what it changes, what each outcome means, and the
evidence that decides it.

Run this before the in-game test (it writes the record) and again after (it
appends whatever the logs and screenshots now show).

The point of writing this down BEFORE the result is that the interpretation
cannot be adjusted afterwards.  Ten in-game tests in this project were wasted by
deciding what a result meant after seeing it.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

MOD_TITLE = "dsh test v10 村民变成绵羊"
ACC = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391"
MOD = os.path.join(ACC, "mods", "local", MOD_TITLE)
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DRS = os.path.join(GAME, "resources", "_common", "drs", "graphics")
RECORD = os.path.join(ROOT, "_probe", "v10_record.json")

# Decided in advance.  Every row is a distinct observable outcome.
OUTCOMES = {
    "sheep": "the loose .sld overrides the packed sprite -> the sprite layer is "
             "proven end to end (first time in this project)",
    "human": "the loose file did NOT override -> the sprite layer is refuted on "
             "this build; the next step is the storage-point path/timing, not "
             "more models",
    "garbled": "the engine loaded the file but the grid does not fit -> the swap "
               "needed the frame-grid guard, and the guard's `attack` warning "
               "predicted exactly this",
    "absent": "the game did not enable the mod at all -> check Title bytes and "
              "the mod manager tick; this says nothing about the sprite layer",
}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def inventory():
    out = {"title": MOD_TITLE, "mod_dir": MOD, "exists": os.path.isdir(MOD),
           "files": [], "total_bytes": 0}
    if not out["exists"]:
        return out
    for root, _d, fs in os.walk(MOD):
        for f in sorted(fs):
            p = os.path.join(root, f)
            rel = os.path.relpath(p, MOD).replace("\\", "/")
            out["files"].append({"rel": rel, "bytes": os.path.getsize(p),
                                 "sha256_16": sha(p)[:16]})
            out["total_bytes"] += os.path.getsize(p)
    out["file_count"] = len(out["files"])
    out["has_dat"] = any(f["rel"].endswith(".dat") for f in out["files"])
    out["sld_count"] = sum(1 for f in out["files"] if f["rel"].endswith(".sld"))
    # Every shipped .sld must differ from the game's own copy, otherwise it is a
    # silent no-op that would look like a working swap in a file listing.
    changed = same = 0
    for f in out["files"]:
        if not f["rel"].endswith(".sld"):
            continue
        gp = os.path.join(GAME, f["rel"].replace("/", os.sep))
        if not os.path.exists(gp):
            same += 1
            continue
        if sha(gp)[:16] == f["sha256_16"]:
            same += 1
        else:
            changed += 1
    out["sld_replaced"] = changed
    out["sld_identical_to_game"] = same
    return out


def status():
    p = os.path.join(ACC, "mods", "mod-status.json")
    if not os.path.exists(p):
        return {"error": "no mod-status.json"}
    d = json.loads(open(p, encoding="utf-8-sig").read(), strict=False)
    mine = [m for m in d["Mods"] if (m.get("Title") or "") == MOD_TITLE]
    return {"entries": len(d["Mods"]),
            "mine": mine[0] if mine else None}


def main(argv):
    inv = inventory()
    st = status()

    print("=== THE SUBJECT ===")
    print("mod        : %s" % MOD_TITLE)
    print("exists     : %r" % inv.get("exists"))
    print("files      : %d (%d .sld, %d total bytes = %.1f MB)"
          % (inv.get("file_count", 0), inv.get("sld_count", 0),
             inv.get("total_bytes", 0), inv.get("total_bytes", 0) / 1e6))
    print("contains .dat        : %r" % inv.get("has_dat"))
    print("shipped .sld that differ from the game's copy : %d"
          % inv.get("sld_replaced", 0))
    print("shipped .sld identical to the game's copy     : %d"
          % inv.get("sld_identical_to_game", 0))
    print()
    print("=== THE GAME'S OWN VIEW ===")
    print("mod-status entries: %r" % st.get("entries"))
    m = st.get("mine")
    if m:
        print("this mod          : Enabled=%r Priority=%r"
              % (m.get("Enabled"), m.get("Priority")))
    else:
        print("this mod          : NOT REGISTERED YET")
    print()
    print("=== WHAT CHANGES ON SCREEN ===")
    print("unit 83 'Villager (Male)' -> the art of unit 594 'Sheep'")
    print("  standing (idle).sld  : u_vil_male_villager_idleA_x1 <- a_herd_sheep_idleA_x1")
    print("  walking  (walk).sld  : u_vil_male_villager_walkA_x1 <- a_herd_sheep_walkA_x1")
    print("  attacking            : u_vil_male_villager_attackA_x1 <- a_herd_sheep_idleA_x1")
    print("  dying / decay        : deathA / decayA <- a_herd_sheep_deathA / _decayA")
    print("The same art is shared by units 224 / 1810 / 1875, so every villager")
    print("sprite should change, not just one.")
    print()
    print("=== DECIDED IN ADVANCE ===")
    for k, v in OUTCOMES.items():
        print("  %-8s %s" % (k, v))
    print()
    print("NOT decided by the visual alone: whether the .dat-rendered numbers")
    print("(villager HP etc.) are unaffected -- this mod ships no .dat at all, so")
    print("they CANNOT be affected.  That is the control.")

    rec = {"inventory": inv, "status": st, "outcomes": OUTCOMES,
           "checked_at": __import__("datetime").datetime.now().isoformat()}
    if os.path.exists(RECORD):
        old = json.loads(open(RECORD, encoding="utf-8").read())
        old.update(rec)
        rec = old
    if len(argv) > 1:
        rec.setdefault("observed", {})[argv[1]] = argv[2] if len(argv) > 2 else True
    with open(RECORD, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    print()
    print("record written: %s" % RECORD)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

import _gamepaths as GP
"""Emit a COMPLETE, installable data-mod directory from an intent.

This is the last link in the chain and the one the user actually cares about:
not a .dat lying in a probe folder, but a folder you can drop into
`...\\Age of Empires 2 DE\\<id>\\mods\\local\\` and see in-game.

Layout produced (mirrors the game root, per the official mod docs):

    out_modtest/
      <Mod Name>/
        info.json                        <- {"Author","CacheStatus","Description","Title"}
        thumbnail.png                    <- optional; must be present if referenced
        resources/_common/dat/empires2_x2_p1.dat    <- the patched data

Two rules learned from the real installed mods on this machine, both enforced
here because violating either silently breaks the mod:

  * the mod root is the folder that CONTAINS info.json; the game tree is mirrored
    directly beneath it (NOT wrapped in an extra `resources/` level)
  * strings written to disk are UTF-8 -- several subscribed mods on this machine
    have mojibake titles because their author wrote GBK into info.json

Nothing outside `out_modtest/` is written.
"""
import os, sys, io, json, zlib, struct, shutil, contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parse_dat as P

BASE = GP.DAT
OUT = os.path.join(HERE, "out_modtest")

INTENT = {
    "say":         "弓箭手攻击力 +2",
    "unit_id":     4,
    "field":       "attack",
    "delta":       +2,
    "mod_title":   "Archer Attack +2 (probe)",
    "mod_author":  "DSH intent-compiler probe",
    "mod_desc":    ("Generated automatically from the intent 'archer attack +2'. "
                    "Demonstrates intent -> dat bytes -> installable data mod."),
}

MOD_DIR_NAME = "ArcherAttackPlus2_probe"


def main():
    import intent_patch as IP                      # reuse the verified compiler

    data, _ = P.load_dat(BASE)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    stage8 = next(t for t in p.stage_offsets if t[0].startswith("8 Civs"))
    nCiv = struct.unpack_from("<h", data, stage8[1])[0]
    CIVS_START = stage8[1] + 2

    r = IP.Orec(data, CIVS_START)
    civs = [IP.walk_civ(r, ci) for ci in range(nCiv)]

    uid = INTENT["unit_id"]
    hits = [u for c in civs for u in c["units"] if u["id"] == uid]
    print("intent %r -> %d physical records (one per civ)" % (INTENT["say"], len(hits)))

    buf = bytearray(data)
    per = []
    for u in hits:
        t = u["type50"]
        base_cls = next((c for c in (3, 4)
                         if any(a["class"] == c and a["amount"] for a in t["attacks"])), None)
        if base_cls is None:
            continue
        n_raw = n_disp = 0
        for a in t["attacks"]:
            if a["class"] == base_cls:
                struct.pack_into("<h", buf, a["_off_amount"], a["amount"] + INTENT["delta"])
                n_raw += 1
        off = u["_offs"]["displayed_attack"]
        struct.pack_into("<h", buf, off, t["displayed_attack"] + INTENT["delta"])
        n_disp += 1
        per.append((u["civ"], base_cls, n_raw, n_disp))
    print("patched %d civs (%d raw-list + %d displayed per civ)"
          % (len(per), per[0][2], per[0][3]))

    # --- independent re-verification ---------------------------------------
    patched = bytes(buf)
    p2 = P.Parser(patched)
    with contextlib.redirect_stdout(io.StringIO()):
        p2.parse()
    assert p2.r.pos == len(patched), "geometry broken!"
    r2 = IP.Orec(patched, CIVS_START)
    civs2 = [IP.walk_civ(r2, ci) for ci in range(nCiv)]
    hits2 = [u for c in civs2 for u in c["units"] if u["id"] == uid]
    vals = {u["type50"]["displayed_attack"] for u in hits2}
    raws = {[a["amount"] for a in u["type50"]["attacks"] if a["class"] == 3][0]
            for u in hits2 if u["type50"]["attacks"]}
    hps = {u["hit_points"] for u in hits2}
    print("re-verify: EOF ok, displayed_attack=%s raw_class3=%s hit_points=%s"
          % (vals, raws, hps))

    # --- assemble the mod directory ----------------------------------------
    root = os.path.join(OUT, MOD_DIR_NAME)
    datdir = os.path.join(root, "resources", "_common", "dat")
    os.makedirs(datdir, exist_ok=True)

    comp = zlib.compressobj(6, zlib.DEFLATED, -15)
    blob = comp.compress(patched) + comp.flush()
    datpath = os.path.join(datdir, "empires2_x2_p1.dat")
    with open(datpath, "wb") as f:
        f.write(blob)

    info = {
        "Author": INTENT["mod_author"],
        "CacheStatus": 0,
        "Description": INTENT["mod_desc"],
        "Title": INTENT["mod_title"],
    }
    with open(os.path.join(root, "info.json"), "w", encoding="utf-8", newline="") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    # a thumbnail is expected by the mod manager; generate a tiny valid PNG
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (256, 256), (24, 32, 56, 255))
        d = ImageDraw.Draw(img)
        d.ellipse((64, 64, 192, 192), outline=(240, 200, 90, 255), width=6)
        d.line((128, 88, 128, 168), fill=(240, 200, 90, 255), width=6)
        d.line((128, 168, 168, 128), fill=(240, 200, 90, 255), width=6)
        img.save(os.path.join(root, "thumbnail.png"))
        thumb = "yes"
    except Exception as e:
        thumb = "no (%s)" % e

    print("\n=== MOD DIRECTORY EMITTED ===")
    for dirpath, _, files in os.walk(root):
        for fn in sorted(files):
            fp = os.path.join(dirpath, fn)
            print("  %-58s %8d B" % (os.path.relpath(fp, OUT), os.path.getsize(fp)))
    print("  thumbnail.png: %s" % thumb)
    print("\ninfo.json:")
    print("  " + json.dumps(info, ensure_ascii=False))
    print("\ndat: %d bytes compressed (original 12,023,754)" % len(blob))
    print("target: copy '%s' into ...\\Age of Empires 2 DE\\<id>\\mods\\local\\"
          % MOD_DIR_NAME)
    print("\nThe game directory was not touched; nothing outside out_modtest/ was written.")


if __name__ == "__main__":
    main()

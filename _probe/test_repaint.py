# -*- coding: utf-8 -*-
"""End-to-end: a user picture -> repainted .sld files -> a mod folder.

Parts:
  A  load a real PNG and paint one unit; check the file count, that x1 and x2
     are both present, and that nothing else changed
  B  the repainted art actually differs from the original
  C  a picture whose aspect ratio is wrong still lands inside the canvas
  D  a unit with no loose art is refused with a sentence, not a traceback
  E  emit the files as a mod and confirm the emitter accepts a graphics path
  F  render a montage so the result can be looked at
"""
import os
import _gamepaths as GP
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from aoe2mod.intent import repaint as RP
from aoe2mod.game import sld as S
from aoe2mod.game import sldencode as E
from aoe2mod.game import sprites as SP
from aoe2mod.mod import emitter as EM

GAME = GP.GAME
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
OUT = os.path.join(ROOT, "_probe", "out_repaint")
SHOTS = os.path.join(ROOT, "_shots", "artpipe")


def make_picture(path):
    """A picture that is obviously not the original art, with its own shape."""
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (256, 320), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((28, 40, 228, 240), fill=(70, 130, 200, 255))
    d.rectangle((88, 200, 168, 300), fill=(230, 200, 40, 255))
    d.ellipse((100, 90, 150, 140), fill=(20, 20, 20, 255))
    d.ellipse((110, 100, 140, 130), fill=(255, 255, 255, 255))
    im.save(path)
    return path


def main():
    fails = []
    fails += part_a()
    fails += part_e()
    part_f()
    print()
    if fails:
        print("REPAINT: %d PROBLEM(S) -> %s" % (len(fails), fails))
        return 1
    print("REPAINT: a picture goes in at canvas coordinates and comes out as "
          "playable .sld files, with no unknown byte invented.")
    return 0


def _stats():
    from aoe2mod import api
    tk = api.Toolkit(GAME)
    tk._ensure()
    return tk


def part_a():
    fails = []
    tk = _stats()
    pic = make_picture(os.path.join(OUT, "picture.png")) \
        if os.path.isdir(OUT) else None
    os.makedirs(OUT, exist_ok=True)
    pic = make_picture(os.path.join(OUT, "picture.png"))
    img, PW, PH = RP.load_picture(pic)
    print("A. picture %dx%d" % (PW, PH))

    rep = RP.paint_unit(GAME, tk._stats["graphics"], tk._parsed[1], 83,
                        img, PW, PH, animations=None)
    print("   unit 83: editable %s  files %d  civs %d  animations %s"
          % (rep["editable"], rep["file_count"], rep["civ_count"],
             rep["animations"]))
    if not rep["editable"]:
        fails.append("unit 83 was not paintable")
        return fails
    names = sorted(os.path.basename(p) for p in rep["files"])
    x1 = [n for n in names if n.endswith("_x1.sld")]
    x2 = [n for n in names if n.endswith("_x2.sld")]
    print("   x1 %d / x2 %d  (both needed: the engine derives x2 from x1)"
          % (len(x1), len(x2)))
    if len(x1) != len(x2):
        fails.append("x1 and x2 counts differ: %d vs %d" % (len(x1), len(x2)))
    pairs_ok = all(n[:-7] + "_x2.sld" in names for n in x1)
    print("   every x1 has an x2 twin: %s" % pairs_ok)
    if not pairs_ok:
        fails.append("an x1 file has no x2 twin")

    # same length, and the art really changed
    changed, same_len = 0, True
    for rel, data in rep["files"].items():
        src = os.path.join(GAME, *rel.split("/"))
        orig = open(src, "rb").read()
        if len(data) != len(orig):
            same_len = False
        if data != orig:
            changed += 1
    print("   every file keeps its length: %s   files whose bytes changed: "
          "%d of %d" % (same_len, changed, len(rep["files"])))
    if not same_len:
        fails.append("a repainted file changed length")
    if changed != len(rep["files"]):
        fails.append("some files were written back unchanged")

    # non-main layers untouched, for one file
    rel = sorted(rep["files"])[0]
    orig = S.Sld(rel, open(os.path.join(GAME, *rel.split("/")), "rb").read())
    new = S.Sld(rel, rep["files"][rel])
    others = all(new.frames[i].layers[k].data == orig.frames[i].layers[k].data
                 for i in range(len(orig.frames))
                 for k in orig.frames[i].layers if k != "main")
    print("   non-main layers byte-identical in %s: %s"
          % (os.path.basename(rel), others))
    if not others:
        fails.append("a repaint disturbed a non-main layer")

    # a picture with the wrong aspect ratio still lands inside the canvas
    wide = bytearray(400 * 60 * 4)
    for i in range(400 * 60):
        wide[i * 4:i * 4 + 4] = bytes((10, 200, 10, 255))
    rep2 = RP.paint_unit(GAME, tk._stats["graphics"], tk._parsed[1], 83,
                         wide, 400, 60, animations=None)
    inside = all(r["drawn_size"][0] <= r["bbox"][2] - r["bbox"][0] and
                 r["drawn_size"][1] <= r["bbox"][3] - r["bbox"][1]
                 for r in rep2["per_file"])
    print("   a 400x60 picture keeps its aspect and stays inside the union "
          "bbox: %s" % inside)
    if not inside:
        fails.append("a wide picture overflowed the union bbox")

    # a unit with no loose art
    try:
        RP.paint_unit(GAME, tk._stats["graphics"], tk._parsed[1], 9,
                      img, PW, PH)
        print("   unit 9 (legacy art) was NOT refused -- BAD")
        fails.append("a unit with no loose art was accepted")
    except RP.PaintError as e:
        print("   unit 9 refused: %s" % e)

    # civilisations the change reaches: unit 83 exists in all 63, and every one
    # of them uses a file being shipped, so the count must not be 2.
    print("   civ_count %d (the change reaches every civilisation that uses "
          "these files, not only those that contributed a new one)"
          % rep["civ_count"])
    if rep["civ_count"] < 60:
        fails.append("civ_count %d undercounts the civilisations reached"
                     % rep["civ_count"])
    return fails


def part_e():
    fails = []
    tk = _stats()
    pic = make_picture(os.path.join(OUT, "picture2.png"))
    img, PW, PH = RP.load_picture(pic)
    rep = RP.paint_unit(GAME, tk._stats["graphics"], tk._parsed[1], 4,
                        img, PW, PH)
    mod = os.path.join(OUT, "repaint_mod")
    import shutil
    shutil.rmtree(mod, ignore_errors=True)
    info = EM.make_info("dsh test repaint", author="aoe2mod",
                        description="a picture painted onto the archer")
    man = EM.emit_json_mod(mod, rep["files"], info, base_dir=GAME,
                           overwrite=True)
    on_disk = sum(1 for r in rep["files"]
                  if os.path.exists(os.path.join(mod, *r.split("/"))))
    has_dat = os.path.exists(os.path.join(
        mod, "resources", "_common", "dat", "empires2_x2_p1.dat"))
    print("E. emitted %d file(s), %d on disk, %d B manifest, ships a .dat: %s"
          % (len(rep["files"]), on_disk, man["files"][0].get("bytes", 0)
             if man.get("files") else 0, has_dat))
    print("   storage points: %s"
          % __import__("aoe2mod.game.locations", fromlist=["x"])
          .storage_points_touched(mod))
    if on_disk != len(rep["files"]):
        fails.append("emitter did not write every file")
    if has_dat:
        fails.append("a repaint mod must not carry a .dat")
    return fails


def part_f():
    from PIL import Image
    tk = _stats()
    pic = make_picture(os.path.join(OUT, "picture3.png"))
    img, PW, PH = RP.load_picture(pic)
    rep = RP.paint_unit(GAME, tk._stats["graphics"], tk._parsed[1], 4,
                        img, PW, PH)
    rel = [r for r in rep["files"] if r.endswith("idleA_x1.sld")]
    if not rel:
        print("F. no idleA file to render")
        return
    s = S.Sld(rel[0], rep["files"][rel[0]])
    tiles = []
    for i in (0, 15, 120, 400):
        canvas, w, h, _info = S.render_frame(s.frames[i])
        im = Image.frombytes("RGBA", (w, h), bytes(canvas))
        bb = im.getbbox()
        tiles.append(im.crop(bb) if bb else im)
    tw = max(t.width for t in tiles)
    th = max(t.height for t in tiles)
    sheet = Image.new("RGBA", (tw * len(tiles), th), (24, 24, 28, 255))
    for i, t in enumerate(tiles):
        sheet.paste(t, (i * tw + (tw - t.width) // 2,
                        (th - t.height) // 2), t)
    os.makedirs(SHOTS, exist_ok=True)
    p = os.path.join(SHOTS, "repaint_archer_montage.png")
    sheet.convert("RGB").save(p)
    print("F. montage -> %s (%dx%d)" % (p, sheet.width, sheet.height))


if __name__ == "__main__":
    sys.exit(main())

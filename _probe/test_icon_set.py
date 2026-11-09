# -*- coding: utf-8 -*-
"""Nail: 「换图标」-- one picture, four things that must agree, two folders.

What is being pinned, and why each part could be false:

1. `IconID` alone is a lie.  The record carries a NUMBER; the picture lives in a
   texture file, a material row, a texture row and a key in `icons.json`.  A slot
   with no key draws an EMPTY BOX (measured eleven times on 2026-10-24, all of
   them inside one folder -- and the split build drew).  So the checks below are
   about all five places moving together, never about the number.
2. Two pictures in one session must land in two slots.  The first draft planned
   every slot from the shipped tables, so the second picture got the same number
   as the first and the second `icons.json` quietly dropped the first key.
3. `emit_many` must merge EVERY item each time.  Calling `emit` once per picture
   rebuilds the table from scratch each call, so only the last picture survives.
   That is the same defect one layer down and it is why `_icon_items` exists.
4. One picture on one record, twice, must be a REPLACEMENT.  The record does not
   move (same slot), the bytes behind it do.  `set_unit_field` correctly refuses
   a same-value write, so the branch that says "the record did not need to
   change" is load-bearing -- without it the tool reports failure AFTER the
   merge table has already swapped the image.
5. A save that makes TWO folders must say so.  The engine ignores `widgetui/`
   next to a `.dat`; the emitter moves it to `<title>_ui` and puts that in the
   manifest; `save_session` used to answer with five keys, none of them that, so
   the player enabled the data half, launched, and saw the empty box again.
6. The page's wire key must be readable by the contract checker.  It matches
   keys with `[A-Za-z_]+`, so `data_b64` parsed as `data_b` and the route read
   as ignoring a key the page sends.  The pattern is fixed, not the key, because
   the next key with a digit would hit the same wall.
"""
import base64
import io
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
SERVER = os.path.join(ROOT, "aoe2mod", "ui", "server.py")
ART = os.path.join(ROOT, "aoe2mod", "game", "iconart.py")
CONTRACT = os.path.join(ROOT, "_probe", "test_page_route_contract.py")

CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, bool(ok), detail))
    print(("  ok   " if ok else "  FAIL ") + name
          + (("  " + str(detail)) if detail else ""))


def png_bytes(r, g, b, side=24):
    from aoe2mod.game import ddstex as D
    px = bytearray()
    for _y in range(side):
        for _x in range(side):
            px += bytes((r, g, b, 255))
    return D.encode_png(side, side, bytes(px))


def main():
    page = io.open(PAGE, encoding="utf-8").read()
    server = io.open(SERVER, encoding="utf-8").read()
    art = io.open(ART, encoding="utf-8").read()
    contract = io.open(CONTRACT, encoding="utf-8").read()

    from aoe2mod.game import iconart as IA
    from aoe2mod.ui import server as S

    # ---- 1. emit_many merges the WHOLE list in one write -------------------
    doc_i, doc_m = IA.shipped(_game_root())
    one = png_bytes(200, 40, 40)
    two = png_bytes(40, 200, 40)
    items = [
        {"label": "nail_a_1000", "rgba": bytes(256 * 256 * 4), "side": 256,
         "slot": 1000, "stem": "nail_a_1000", "kind": "unit"},
        {"label": "nail_b_1001", "rgba": bytes(256 * 256 * 4), "side": 256,
         "slot": 1001, "stem": "nail_b_1001", "kind": "unit"},
    ]
    files, metas = IA.emit_many(doc_i, doc_m, items)
    ic = json.loads(files[IA.ICONS_REL.replace(os.sep, "/")].decode("utf-8"))
    mt = json.loads(files[IA.MATERIALS_REL.replace(os.sep, "/")].decode("utf-8"))
    slots_here = [m["slot"] for m in metas]
    check("emit_many answers one meta per item", slots_here == [1000, 1001],
          slots_here)
    check("both keys survive ONE call",
          "1000" in ic["Units"] and "1001" in ic["Units"],
          sorted(k for k in ic["Units"] if k.startswith("100")))
    names = [e["MaterialDef"]["Name"] for e in mt["Materials"]]
    tex = [e["TextureDef"]["Name"] for e in mt["GlobalTextures"]]
    # `_clean_stem` prefixes the kind when the stem does not already carry it,
    # so the name in the table is not the stem that was passed in.
    check("both materials are in the merged table",
          all(m["material"] in names for m in metas),
          [n for n in names if "nail" in n])
    check("both texture rows are in the merged table",
          all(m["material"] in tex for m in metas),
          [n for n in tex if "nail" in n])
    check("each texture row points at a file under widgetui/",
          all(str(e["TextureDef"].get("FileName", "")).startswith(
              "textures/ingame/units/")
              for e in mt["GlobalTextures"]
              if str(e["TextureDef"].get("Name", "")).startswith("unit_nail")),
          "relative to widgetui/, which is why the mod path adds one level")
    first = [r for r in files if r.endswith(".dds")][0]
    check("the texture bytes are uncompressed BGRA DDS",
          files[first][:4] == b"DDS ", files[first][:4])
    check("the shipped tables are untouched",
          "nail_a_1000" not in json.dumps(doc_i) and
          "nail_a_1000" not in json.dumps(doc_m))

    # ---- 2. the App: dry is the same answer as the write -------------------
    app = S.App()
    app.session_raw()
    tmpdir = os.path.join(ROOT, "_probe", "_tmp")
    p1 = os.path.join(tmpdir, "nail_icon_red.png")
    p2 = os.path.join(tmpdir, "nail_icon_green.png")
    io.open(p1, "wb").write(one)
    io.open(p2, "wb").write(two)
    b64 = "data:image/png;base64," + base64.b64encode(one).decode("ascii")

    t0 = time.time()
    d_path = app.set_icon(kind="unit", record=74, civ="British", path=p1,
                          dry=True)
    dry_s = time.time() - t0
    d_b64 = app.set_icon(kind="unit", record=74, civ="British", data_b64=b64,
                         filename="x.png", dry=True)
    check("a preview writes nothing",
          d_path.get("ok") and d_path.get("dry") is True
          and not app._icons, "%.2f s" % dry_s)
    check("bytes and a path plan the same slot",
          d_path.get("slot") == d_b64.get("slot")
          and d_path.get("material") == d_b64.get("material"),
          "%r vs %r" % (d_path.get("slot"), d_b64.get("slot")))
    check("the preview names all four things",
          all(k in d_path for k in ("slot", "material", "file", "key")),
          sorted(d_path))
    check("it says what the record says now",
          d_path.get("was") is not None and d_path.get("becomes") == d_path["slot"],
          "%r -> %r" % (d_path.get("was"), d_path.get("becomes")))

    # ---- 3. two records, two slots ---------------------------------------
    a = app.set_icon(kind="unit", record=74, civ="British", path=p1, dry=False)
    b = app.set_icon(kind="unit", record=83, civ="British", path=p2, dry=False)
    check("two records get two slots",
          a.get("ok") and b.get("ok") and a["slot"] != b["slot"],
          (a.get("slot"), b.get("slot")))
    check("both records are remembered as owners",
          app._icon_owner.get(("unit", 74)) == a["slot"]
          and app._icon_owner.get(("unit", 83)) == b["slot"],
          dict(app._icon_owner))
    ic2 = json.loads(app._icons["widgetui/icons.json"].decode("utf-8"))
    check("both slots have a key in the merged table",
          str(a["slot"]) in ic2["Units"] and str(b["slot"]) in ic2["Units"],
          "%s / %s" % (a["slot"], b["slot"]))
    check("the record's IconID is the slot",
          _icon_id(app, 74) == a["slot"], _icon_id(app, 74))

    # ---- 4. same record, second picture: replace, do not refuse -----------
    first_tex = {k: v for k, v in app._icons.items() if k.endswith(".dds")}
    c = app.set_icon(kind="unit", record=74, civ="British", path=p2, dry=False)
    check("a second picture for the same record succeeds",
          c.get("ok") is True, c.get("error"))
    check("...in the SAME slot", c.get("slot") == a["slot"],
          (c.get("slot"), a["slot"]))
    check("...and says the record did not have to move",
          c.get("record_unchanged") is True, c.get("record_unchanged"))
    tex_now = {k: v for k, v in app._icons.items() if k.endswith(".dds")}
    check("...but the bytes behind it changed", tex_now != first_tex,
          sorted(tex_now))
    check("...and it did not grow a second entry",
          len([i for i in app._icon_items if i["slot"] == a["slot"]]) == 1,
          len(app._icon_items))

    # ---- 5. every refusal that must survive ------------------------------
    bad = [
        (app.set_icon(kind="unit", record=None, path=p1),
         "要给出这要换图标的记录编号"),
        (app.set_icon(kind="building", record=74, path=p1),
         "只有单位和科技有图标"),
        (app.set_icon(kind="unit", record=999999, civ="British", path=p1),
         "这个文明里没有第 999999 号单位"),
        (app.set_icon(kind="tech", record=999999, path=p1),
         "没有第 999999 号科技"),
        (app.set_icon(kind="unit", record=74, civ="British", slot=9, path=p1),
         "图标槽只能取"),
        (app.set_icon(kind="unit", record=74, civ="British"),
         "没有给出要用的图片"),
    ]
    for got, must in bad:
        check("refuses: %s" % must, got.get("ok") is False
              and must in str(got.get("error")), got.get("error"))
    check("a refused picture writes no icon state",
          len(app._icons) == 4, sorted(app._icons))

    # ---- 6. undo moves the LAST record write; the files stay --------------
    # The second picture on record 74 was `record_unchanged`, so the newest
    # FIELD write is record 83's.  Undoing therefore puts 83's `IconID` back and
    # leaves 74 alone -- which is the honest behaviour, but only if the nail
    # asks about 83 instead of assuming the last icon gesture was the last
    # write.
    before_undo = _icon_id(app, 83)
    u = app.undo()
    after_undo = _icon_id(app, 83)
    check("undo moves the record its step was about",
          u.get("ok") and after_undo != before_undo,
          "%r -> %r" % (before_undo, after_undo))
    check("...and leaves the record that did not move alone",
          _icon_id(app, 74) == a["slot"], _icon_id(app, 74))
    check("the pictures stay in memory: an orphan texture is cheaper than a "
          "record pointing at nothing", len(app._icons) == 4, sorted(app._icons))

    # ---- 7. a save says there are TWO folders ---------------------------
    outdir = os.path.join(ROOT, "_out", "_nailicon")
    os.environ["AOE2MOD_BUILD_OUT"] = outdir
    man = app.save_session(title="nail icon save")
    check("the save succeeds", man.get("ok") is True, man.get("error"))
    check("it reports the second folder", bool(man.get("ui_mod_dir")),
          man.get("ui_mod_dir"))
    check("it reports both titles",
          (man.get("info") or {}).get("Title") and
          (man.get("ui_info") or {}).get("Title"),
          ((man.get("info") or {}).get("Title"),
           (man.get("ui_info") or {}).get("Title")))
    ui_dir = man.get("ui_mod_dir") or ""
    landed = []
    for base, _dirs, fs in os.walk(ui_dir):
        landed += [os.path.relpath(os.path.join(base, f), ui_dir).replace(
            os.sep, "/") for f in fs]
    check("the second folder carries the texture and both tables",
          any(r.endswith(".dds") for r in landed)
          and "widgetui/icons.json" in landed
          and "widgetui/materials.json" in landed, sorted(landed))
    check("the second folder carries no .dat",
          not any(r.endswith(".dat") for r in landed), sorted(landed))
    dat_landed = []
    for base, _dirs, fs in os.walk(man.get("built") or ""):
        dat_landed += [os.path.relpath(os.path.join(base, f),
                                       man.get("built")).replace(os.sep, "/")
                       for f in fs]
    check("the data folder carries the .dat and no widgetui/",
          any(r.endswith(".dat") for r in dat_landed)
          and not any(r.startswith("widgetui/") for r in dat_landed),
          sorted(dat_landed))

    # ---- 8. the route is in do_POST and reads the page's keys ------------
    get_at = server.index("        def do_GET(self):")
    post_at = server.index("        def do_POST(self):")
    check("the icon route is a POST",
          server[post_at:].count('"/api/icon-set"') == 1
          and server[get_at:post_at].count('"/api/icon-set"') == 0,
          server[post_at:].count('"/api/icon-set"'))
    body = server[post_at:]
    for key in ("kind", "record", "civ", "data_b64", "filename", "slot", "dry"):
        reads = ('payload.get("%s"' % (key,)) in body
        check("the route reads %r" % (key,), reads, key)
    check("the page sends the same key the route reads",
          page.count("data_b64: ") >= 2 and 'payload.get("data_b64")' in server,
          page.count("data_b64: "))

    # ---- 9. the contract checker can SEE a key with a digit -------------
    check("the contract's key pattern admits digits",
          "A-Za-z0-9_" in contract, "was [A-Za-z_]+")

    # ---- 10. the page: box, picker, preview, write, pending bar ----------
    check("the pane grows the box", "drawIconBox(pane, d);" in page)
    check("the box has a file picker",
          'pick.type = "file"' in page and 'pick.id = "ed-icon-file"' in page)
    check("it accepts the three formats the reader can actually open",
          '".png,.bmp,.dds' in page, "picture.read is stdlib-only")
    check("the write button starts disabled",
          'go.id = "ed-icon-go";' in page and "go.disabled = true;" in page)
    check("the preview is the SERVER's answer, not a guess",
          'api("/api/icon-set", {kind: kind, record: id, civ: edCiv(),\n'
          '      data_b64: data, filename: filename, dry: true});' in page)
    check("the picture beside the summary is the chosen file",
          "shot.src = String(fr.result || \"\");" in page,
          "the new slot is not in icons.json until the save")
    check("the preview says the picture is padded, not cropped",
          "留白" in page and "不拉伸也不裁" in page)
    check("the preview warns about the split",
          "模组会拆成两个文件夹" in page)
    check("the same-record case is named, not reported as a new slot",
          "j.record_unchanged" in page)
    check("the pending bar is refilled from the server after a write",
          "edSyncPending(st.pending, st.edits, st);" in page
          and "edSyncPending();" not in page)
    check("the save toast names BOTH titles",
          "两个模组都要启用" in page and "(j.ui_info || {}).Title" in page)

    bad_checks = [c for c in CHECKS if not c[1]]
    print()
    if bad_checks:
        for name, _, detail in bad_checks:
            print("FAILED: %s :: %s" % (name, detail))
        print("ICON SET: %d CHECK(S) FAILED" % len(bad_checks))
        return 1
    print("ICON SET: A PICTURE IS NOT A NUMBER -- IT IS A TEXTURE, A MATERIAL "
          "ROW, A TEXTURE ROW AND A KEY THAT MUST ALL NAME THE SAME SLOT, TWO "
          "RECORDS NEVER SHARE ONE, A SECOND PICTURE REPLACES THE FIRST, AND "
          "THE SAVE SAYS THE BUILD IS TWO MODS BECAUSE IT IS")
    return 0


def _game_root():
    import aoe2mod.game.locations as L
    return L.find_game_root()


def _icon_id(app, unit):
    """The record's IconID, read the way the field table reports it.

    `unit_fields` answers `fields` as a LIST of `{name, label, kind, value,
    offset, hint, ro}` rows -- not a dict keyed by name -- so reading it as one
    is how a nail reports `'list' object has no attribute 'get'` instead of a
    number.
    """
    for row in (app.unit_fields(unit, civ="British").get("fields") or []):
        if row.get("name") == "IconID":
            return row.get("value")
    return None


sys.exit(main())

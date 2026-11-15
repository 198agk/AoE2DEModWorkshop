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
5. A save that makes TWO folders must say so -- and a picture does not have to
   make two.  The engine ignores `widgetui/` next to a `.dat`; the emitter moves
   it to `<title>_ui` and puts that in the manifest, and `save_session` used to
   answer with five keys, none of them that, so the player enabled the data
   half, launched, and saw the empty box again.  The other half of the same
   fact: a record that keeps its slot needs no `.dat` edit at all, so that
   build is ONE folder (section 7b).  The two shapes are pinned separately
   because they are the two answers the player is choosing between.
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
    # `inplace=False` throughout sections 2-7: those checks are about the
    # NEW-SLOT path (a record that has to be renumbered), which is still the
    # only way to change one unit on a shared slot.  The in-place path has its
    # own section below, because its whole point is the opposite answer.
    d_path = app.set_icon(kind="unit", record=74, civ="British", path=p1,
                          dry=True, inplace=False)
    dry_s = time.time() - t0
    d_b64 = app.set_icon(kind="unit", record=74, civ="British", data_b64=b64,
                         filename="x.png", dry=True, inplace=False)
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
    a = app.set_icon(kind="unit", record=74, civ="British", path=p1,
                     dry=False, inplace=False)
    b = app.set_icon(kind="unit", record=83, civ="British", path=p2,
                     dry=False, inplace=False)
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
    c = app.set_icon(kind="unit", record=74, civ="British", path=p2,
                     dry=False, inplace=False)
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
        # 999999 exists in NO civilization, so since _unit_missing was split
        # (server.py:5727, 2026-11-12) the sentence is the "nowhere at all"
        # one, not "not in this civilization".  Asserting the old wording sent
        # the reader looking for the right civilization when there is none --
        # which is exactly the confusion the split exists to remove.
        (app.set_icon(kind="unit", record=999999, civ="British", path=p1),
         "第 999999 号单位在 63 个文明里都没有记录"),
        (app.set_icon(kind="tech", record=999999, path=p1),
         "没有第 999999 号科技"),
        (app.set_icon(kind="unit", record=74, civ="British", slot=9, path=p1,
                      inplace=False),
         "图标槽只能取"),
        (app.set_icon(kind="unit", record=74, civ="British"),
         "没有给出要用的图片"),
    ]
    for got, must in bad:
        check("refuses: %s" % must, got.get("ok") is False
              and must in str(got.get("error")), got.get("error"))
    # ...and the "nowhere at all" refusal must NOT blame a civilization: that
    # wording is reserved for ids that exist somewhere else (see the docstring
    # of `_unit_missing`).  Two truths, two sentences.
    nowhere = app.set_icon(kind="unit", record=999999, civ="British", path=p1)
    check("an id that exists nowhere does not blame a civilization",
          "这个文明里没有" not in str(nowhere.get("error")),
          nowhere.get("error"))
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

    # ---- 7. a save that moved IconID says there are TWO folders ----------
    # Every write above was `inplace=False`, i.e. a real .dat edit, so this
    # save MUST still split and MUST still say so.  The one-folder case is a
    # different session and it gets its own section (7b): conflating them was
    # how the tool shipped a build nobody could enable correctly.
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

    # ---- 7b. a save that did NOT move IconID is ONE folder ---------------
    # This is the whole point of in-place: the record already names the slot,
    # so the picture is three files under widgetui/ and nothing else.  A save
    # that still carried a .dat would be split by the emitter and the player
    # would be back to enabling two mods for one picture -- the complaint this
    # mode exists to answer.
    one = S.App()
    one.session_raw()
    ip = one.set_icon(kind="unit", record=74, civ="British", path=p1,
                      dry=False)
    check("an icon swap defaults to in-place", ip.get("mode") == "inplace",
          (ip.get("mode"), ip.get("error")))
    check("...which leaves the record's IconID alone",
          ip.get("record_unchanged") is True and _icon_id(one, 74) == ip["slot"],
          (_icon_id(one, 74), ip.get("slot")))
    check("...and therefore has no pending .dat edit",
          one.pending_edits() == [], len(one.pending_edits()))
    check("the preview lists the other units on that slot",
          isinstance(ip.get("shares"), list) and
          any(s.get("record") == 33 for s in ip["shares"]),
          ip.get("shares"))
    check("a picture alone is enough to save",
          one.session_info().get("picture_count") == 1
          and one.session_info().get("pending") == 1,
          one.session_info().get("pending"))
    man1 = one.save_session(title="nail icon inplace")
    check("the one-folder save succeeds", man1.get("ok") is True,
          man1.get("error"))
    check("it carries no .dat", man1.get("carries_dat") is False,
          man1.get("carries_dat"))
    check("it reports NO second folder", man1.get("ui_mod_dir") is None,
          man1.get("ui_mod_dir"))
    only = []
    for base, _dirs, fs in os.walk(man1.get("built") or ""):
        only += [os.path.relpath(os.path.join(base, f), man1.get("built"))
                 .replace(os.sep, "/") for f in fs]
    check("one folder holds the picture and both tables",
          any(r.endswith(".dds") for r in only)
          and "widgetui/icons.json" in only
          and "widgetui/materials.json" in only, sorted(only))
    check("...and no .dat anywhere in it",
          not any(r.endswith(".dat") for r in only), sorted(only))
    check("...and no sibling folder was written",
          not os.path.isdir((man1.get("built") or "") + "_ui"),
          (man1.get("built") or "") + "_ui")
    merged = json.loads(one._icons["widgetui/icons.json"].decode("utf-8"))
    shipped_i, _shipped_m = IA.shipped(_game_root())
    moved = [k for k in shipped_i["Units"]
             if merged["Units"].get(k) != shipped_i["Units"][k]]
    check("re-pointing touches exactly the slot it repainted",
          moved == [str(ip["slot"]).zfill(3)],
          (moved, str(ip["slot"]).zfill(3)))

    # ---- 7c. "all civilizations" is STILL one folder ---------------------
    # The complaint this whole mode answers was heard while the write scope
    # said 全部文明, and the first draft of in-place gave up there: unit 74 has
    # 57 copies on slot 8 and 6 on slot 600 (the DLC civs), the slots did not
    # agree, so the write fell back to renumbering IconID -- a .dat, two
    # folders, the exact thing being fixed.  A record that names TWO slots is
    # still repaintable: two textures, two material rows, zero .dat bytes.
    allc = S.App()
    allc.session_raw()
    ipa = allc.set_icon(kind="unit", record=74, civ="*", path=p1, dry=False)
    check("an all-civ icon write stays in-place",
          ipa.get("mode") == "inplace",
          (ipa.get("mode"), ipa.get("why_not_inplace")))
    check("...and repaints every slot the record names, not just one",
          sorted(ipa.get("slots") or []) == [8, 600], ipa.get("slots"))
    check("...with a texture per slot",
          len(set(ipa.get("files_all") or [])) == 2, ipa.get("files_all"))
    check("...and it still has no pending .dat edit",
          allc.pending_edits() == [], len(allc.pending_edits()))
    mana = allc.save_session(title="nail icon all civs")
    check("the all-civ save is ONE folder too",
          mana.get("ok") is True and mana.get("carries_dat") is False
          and mana.get("ui_mod_dir") is None,
          (mana.get("carries_dat"), mana.get("ui_mod_dir")))
    onlya = []
    for base, _dirs, fs in os.walk(mana.get("built") or ""):
        onlya += [os.path.relpath(os.path.join(base, f), mana.get("built"))
                  .replace(os.sep, "/") for f in fs]
    check("...holding two textures and no .dat",
          len([r for r in onlya if r.endswith(".dds")]) == 2
          and not any(r.endswith(".dat") for r in onlya), sorted(onlya))

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
    check("the pane grows the box",
          "drawIconBox(t.body, d);" in page,
          "the strip owns the <details>, so the box fills a body")
    check("the box has a file picker",
          'pick.type = "file"' in page and 'pick.id = "ed-icon-file"' in page)
    check("it accepts the three formats the reader can actually open",
          '".png,.bmp,.dds' in page, "picture.read is stdlib-only")
    check("the write button starts disabled",
          'go.id = "ed-icon-go";' in page and "go.disabled = true;" in page)
    check("the preview is the SERVER's answer, not a guess",
          'api("/api/icon-set", {kind: kind, record: id, civ: edScopeCiv(),\n'
          '      inplace: !!inplace,\n'
          '      data_b64: data, filename: filename, dry: true});' in page)
    check("the write sends the same scope and the same switch",
          'api("/api/icon-set", {kind: kind, record: id, civ: edScopeCiv(),\n'
          '        inplace: !!inplaceBox.checked,' in page)
    check("the switch is a visible checkbox, not a hidden rule",
          'inplaceBox.id = "ed-icon-inplace";' in page
          and 'inplaceBox.type = "checkbox";' in page
          and "原地换" in page)
    check("the picture beside the summary is the chosen file",
          "shot.src = String(fr.result || \"\");" in page,
          "the new slot is not in icons.json until the save")
    check("the preview says the picture is padded, not cropped",
          "留白" in page and "不拉伸也不裁" in page)
    check("the preview says WHICH of the two shapes this build is",
          "一个文件夹" in page and "模组会拆成两个文件夹" in page,
          "one folder only when the record keeps its slot")
    check("the preview names every slot the write repaints",
          "(plan.slots || [plan.slot]).join" in page,
          "a record can name two slots across 63 civs")
    check("the preview names the units that share the slot",
          "plan.shares" in page and "也指在同一个号上" in page)
    check("a refused in-place says why, not just switches shape",
          "plan.why_not_inplace" in page and "没法原地换" in page)
    check("the same-record case is named, not reported as a new slot",
          "j.record_unchanged" in page)
    check("the pending bar is refilled from the server after a write",
          "edSyncPending(st.pending, st.edits, st);" in page
          and "edSyncPending();" not in page)
    check("the save toast names BOTH titles",
          "两个模组都要启用" in page and "(j.ui_info || {}).Title" in page)
    check("an icon-only save does not read as \"0 项改动\"",
          "function landedWhat(j)" in page and "j.pictures" in page
          and page.count("+ landedWhat(j) +") == 2,
          "a picture is pending work with no .dat edit")
    check("the write toast lists the slots it actually wrote",
          "(j.slots || [j.slot]).join" in page
          and page.count("(j.slots || [j.slot]).join") == 1,
          "one list, used by every sentence after a write")
    check("the status line under the button names the same slots",
          'was.textContent = "槽 " + slotText + " · 保存后生效"' in page
          and 'was.textContent = "槽 " + slotText + " · 还没写入"' in page)

    bad_checks = [c for c in CHECKS if not c[1]]
    print()
    if bad_checks:
        for name, _, detail in bad_checks:
            print("FAILED: %s :: %s" % (name, detail))
        print("ICON SET: %d CHECK(S) FAILED" % len(bad_checks))
        return 1
    print("ICON SET: A PICTURE IS NOT A NUMBER -- IT IS A TEXTURE, A MATERIAL "
          "ROW, A TEXTURE ROW AND A KEY THAT MUST ALL NAME THE SAME SLOT.  A "
          "PICTURE ALONE CAN KEEP THE NUMBER THE RECORD ALREADY HAS, AND THEN "
          "THE BUILD IS ONE FOLDER; MOVING THE NUMBER COSTS A .dat AND TWO.")
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

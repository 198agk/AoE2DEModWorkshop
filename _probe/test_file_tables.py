# -*- coding: utf-8 -*-
"""The three tables that are not record lists: 地图块 / 全局数值 / 科技树.

`.dat` has three stretches that are not families of records with their own
count field.  For twenty years AGE3 put them on a static box in General and on
four lists inside TechTrees, and this project had no address for any of them:

  map        the 25 scalars after the 200 terrain records (tile 96x48, the
             elevation step 24, the block rows and columns, fog flag)
  tail       the 7 counters between the last technology and the tech tree
             (time slice 30, kill rates 7/14 and 700/1400, razing 5/10)
  techtree   550 connections: 4 ages, 37 buildings, 269 units, 240 researches

What this pins, in order:

1. The walks land on the byte the parser lands on.  A pseudo table's whole
   claim is that it can name an address inside a block it does not own; if a
   leftover is not 0 the addresses are guesses and a write goes into the
   neighbouring record.
2. The 550 tech-tree connections are four different layouts behind one list.
   `fields_at` cannot pick a reader without the record's `kind`, so the index
   has to carry it -- and the failure mode without it is not an exception on
   record 0, it is an `EOFError` on record 549 after 545 correct records.
3. Every field has a Chinese name.  A row that reads `TileHalfHeight` is AGE3's
   screen, which is the screen this project exists to replace.
4. Read-only is where writing would corrupt: the two search-map pointers are
   memory addresses left in the file, and a group's count byte IS the record's
   own width.
5. The write path round-trips: plan -> apply -> put the old bytes back leaves
   the file byte-identical.
6. The page reaches all three: a tab each, the loader knows the kinds, and the
   search box only offers examples those tables actually have.
"""
import io
import json
import os
import re
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

from aoe2mod.dat import parser as P
from aoe2mod.dat import tablefields as TF

PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
FAILS = []


def ck(name, ok, detail=""):
    if ok:
        print("  ok   %s" % (name,))
    else:
        print("  FAIL %s%s" % (name, (" :: " + str(detail)) if detail else ""))
        FAILS.append(name)


def read(path):
    return io.open(path, encoding="utf-8").read()



def _first(recs, kind):
    return [r for r in recs if r.get("kind") == kind][0]


def _spread(recs):
    """One record of each kind, so a per-kind field is not called missing."""
    seen = set()
    out = []
    for r in recs:
        if r.get("kind") not in seen:
            seen.add(r.get("kind"))
            out.append(r)
    return out

def section(title):
    print("\n=== %s ===" % (title,))


def main():
    from aoe2mod.ui.server import App
    app = App()
    raw = app.session_raw()
    gv = app.tk._parsed[3]

    section("1. the three walks leave nothing behind")
    t = time.time()
    map_recs, map_left = TF.scan(raw, "map")
    tail_recs, tail_left = TF.scan(raw, "tail")
    tt_recs, tt_left = TF.scan(raw, "techtree")
    dt = time.time() - t
    print("        (%.2fs for all three, tail and techtree pay the 89 MB civ"
          " block)" % (dt,))
    ck("map leftover is 0", map_left == 0, map_left)
    ck("tail leftover is 0", tail_left == 0, tail_left)
    ck("techtree leftover is 0", tt_left == 0, tt_left)
    ck("one map record, 63 bytes",
       len(map_recs) == 1 and map_recs[0]["end"] - map_recs[0]["start"] == 63,
       map_recs[:1])
    ck("seven tail records, four bytes each",
       len(tail_recs) == 7 and
       [r["end"] - r["start"] for r in tail_recs] == [4] * 7,
       [r["end"] - r["start"] for r in tail_recs])
    kinds = {}
    for r in tt_recs:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    ck("550 tech-tree connections: 4 ages / 37 buildings / 269 units / "
       "240 researches",
       len(tt_recs) == 550 and
       kinds == {"age": 4, "building": 37, "unit": 269, "research": 240},
       (len(tt_recs), kinds))
    ck("the three blocks do not overlap",
       map_recs[0]["end"] < tail_recs[0]["start"] and
       tail_recs[-1]["end"] < tt_recs[0]["start"],
       (map_recs[0]["end"], tail_recs[0]["start"],
        tail_recs[-1]["end"], tt_recs[0]["start"]))

    section("2. the index carries what the four tech-tree layouts need")
    idx_tt = app._table_index("techtree")
    ck("the index row carries kind",
       all(r.get("kind") for r in idx_tt.values()),
       [k for k, r in idx_tt.items() if not r.get("kind")][:5])
    ck("the index row carries the record's own id",
       all(r.get("id") is not None for r in idx_tt.values()),
       [k for k, r in idx_tt.items() if r.get("id") is None][:5])
    # The last record is the one that proved the point: read as `unit` it needs
    # 114 bytes and the file has 112 left there; read as `research` it is 112.
    last = idx_tt[len(idx_tt) - 1]
    f_last = TF.fields_at(raw, gv, last, table="techtree")
    ck("the last record is a research and reads fine",
       last.get("kind") == "research" and len(f_last) >= 30,
       (last.get("kind"), len(f_last)))
    ck("fields_at without a kind would have read it as a unit",
       last["end"] - last["start"] < 114,
       (last["end"] - last["start"],))

    section("3. every field has a Chinese name")
    expect = {"map": 25, "tail": 1, "techtree": 30}
    for table, n in expect.items():
        rec = (map_recs if table == "map" else
               tail_recs if table == "tail" else tt_recs)[-1 if table == "techtree" else 0]
        flds = TF.fields_at(raw, gv, rec, table=table)
        ck("%s: %d fields" % (table, n), len(flds) == n, len(flds))
        missing = [k for k in flds if not TF.meta_for(table, k).get("zh")]
        ck("%s: every field has a Chinese name" % (table,), not missing,
           missing[:8])
    flds = TF.fields_at(raw, gv, map_recs[0], table="map")
    ck("the tile size is 96 x 48 and the elevation step is 24",
       (flds["TileWidth"]["value"], flds["TileHeight"]["value"],
        flds["ElevHeight"]["value"]) == (96, 48, 24),
       (flds["TileWidth"]["value"], flds["TileHeight"]["value"],
        flds["ElevHeight"]["value"]))
    ck("134 of the 200 terrain slots are used",
       flds["TerrainsUsed2"]["value"] == 134,
       flds["TerrainsUsed2"]["value"])
    ck("fog is on and the map block is not visible",
       (flds["FogFlag"]["value"], flds["MapVisibleFlag"]["value"]) == (1, 0),
       (flds["FogFlag"]["value"], flds["MapVisibleFlag"]["value"]))
    tail_vals = [TF.fields_at(raw, gv, r, table="tail") for r in tail_recs]
    got = [list(v.values())[0]["value"] for v in tail_vals]
    ck("the seven counters are 30 / 7 / 14 / 700 / 1400 / 5 / 10",
       got == [30, 7, 14, 700, 1400, 5, 10], got)
    age0 = TF.fields_at(raw, gv, tt_recs[0], table="techtree")
    ck("the first connection is age 1 with 11 buildings, 4 units, 2 techs",
       (age0["ID"]["value"], age0["BuildingsCount"]["value"],
        age0["UnitsCount"]["value"], age0["TechsCount"]["value"]) ==
       (1, 11, 4, 2),
       {k: age0[k]["value"] for k in
        ("ID", "BuildingsCount", "UnitsCount", "TechsCount")})
    ck("the age carries 21 Common integers",
       sum(1 for k in age0 if k.startswith(("CommonUnitResearch.",
                                           "CommonMode."))) == 20,
       sum(1 for k in age0 if k.startswith(("CommonUnitResearch.",
                                           "CommonMode."))))

    section("4. read-only is where writing would corrupt")
    for table, rec, name in (
            ("map", map_recs[0], "SearchMapPtr"),
            ("map", map_recs[0], "SearchMapRowsPtr"),
            ("techtree", tt_recs[0], "BuildingsCount"),
            ("techtree", tt_recs[0], "CommonSlotsUsed_free")):
        got = TF.plan(table, raw, gv, rec, name, 7)
        if name == "CommonSlotsUsed_free":
            # Not a real field: the point is that a name nobody can read is
            # refused rather than guessed at.
            ck("an unknown field is refused, in Chinese",
               not got.get("ok") and "没有叫" in got.get("error", ""),
               got.get("error"))
            continue
        ck("%s is read-only" % (name,),
           not got.get("ok") and "只读" in got.get("error", ""),
           got.get("error"))
    got = TF.plan("map", raw, gv, map_recs[0], "TerrainsUsed2", 99999)
    ck("a value wider than i16 is refused by byte width, not by clamp",
       not got.get("ok") and "装不下" in got.get("error", ""),
       got.get("error"))
    got = TF.plan("map", raw, gv, map_recs[0], "TileWidth", 96)
    ck("writing the value that is already there is refused as unchanged",
       not got.get("ok") and got.get("unchanged"), got)

    section("5. plan -> apply -> put it back leaves the file identical")
    buf = bytearray(raw)
    steps = [("map", map_recs[0], "TileWidth", 64, 96),
             ("tail", tail_recs[0], "TimeSlice", 31, 30),
             ("techtree", tt_recs[0], "Status", 3, 2),
             ("techtree", tt_recs[0], "Buildings.0", 13, 12),
             ("techtree", _first(tt_recs, "unit"), "UpperBuilding", 44, 45)]
    for table, rec, name, new, old in steps:
        got = TF.plan(table, raw, gv, rec, name, new)
        ck("%s %s -> %s plans" % (table, name, new), got.get("ok"),
           got.get("error"))
        if not got.get("ok"):
            continue
        back = TF.apply(buf, got["offset"], got["packed"])
        ck("   ...and changes one byte group", back["changed"] >= 1,
           back["changed"])
        again = TF.plan(table, bytes(buf), gv, rec, name, old)
        ck("   ...and reads back as %s" % (new,),
           again.get("ok"), again.get("error"))
        TF.apply(buf, again["offset"], again["packed"])
    ck("the buffer is byte-identical again", bytes(buf) == raw,
       sum(1 for a, b in zip(bytes(buf), raw) if a != b))

    section("6. a row says what it is")
    names = [TF.record_name(raw, gv, r, table="map") for r in map_recs]
    ck("the map record is named in Chinese", names == ["地图块标量"], names)
    names = [TF.record_name(raw, gv, r, table="tail") for r in tail_recs]
    ck("the seven counters are named after what they count",
       names[:3] == ["时间切片", "单位击杀率", "单位击杀总分"], names)
    names = [TF.record_name(raw, gv, r, table="techtree") for r in tt_recs]
    ck("a connection is named by kind and id",
       names[:3] == ["时代 1", "时代 2", "时代 3"] and
       names[-1].startswith("科技 "), names[:3] + names[-1:])

    section("7. the page reaches all three")
    page = read(PAGE)
    n_tabs = len(re.findall(r'data-edkind="', page))
    ck("a tab exists for each",
       all(('data-edkind="%s"' % t) in page for t in ("map", "tail", "techtree")),
       [t for t in ("map", "tail", "techtree")
        if ('data-edkind="%s"' % t) not in page])
    ck("the loader knows all three",
       re.search(r'ED_TABLES\s*=\s*\[[^\]]*"map"[^\]]*"tail"[^\]]*"techtree"',
                 page, re.S) is not None)
    m = re.search(r"([一二三四五六七八九十]+)个页签", page)
    ck("the page states a tab count", m is not None)
    ck("...and it is the number of buttons on the row",
       m is not None and _zh_num(m.group(1)) == n_tabs, (m and m.group(1), n_tabs))
    ck("the three file-block tabs are the last three",
       re.search(r'data-edkind="techtree">[^<]*</button>\s*<select id="ed-civ"',
                 page) is not None)

    section("8. the search box only offers fields these tables have")
    ph = {}
    cur = None
    for line in page.splitlines():
        m = re.search(r'd\.table === "([a-z]+)"', line)
        if m:
            cur = m.group(1)
            continue
        m = re.search(r'"搜字段名，例如 ([^"]+)"', line)
        if m and cur:
            ph[cur] = [w.strip() for w in m.group(1).split("/")]
            cur = None
    for table in ("map", "tail", "techtree"):
        ck("%s has its own examples" % (table,), table in ph, sorted(ph))
    for table, recs_ in (("map", map_recs), ("tail", tail_recs),
                         ("techtree", tt_recs)):
        vocab = []
        # Ages carry Buildings/Units/Techs, buildings carry UnitsTechsTotal,
        # units carry UpperBuilding and RequiredResearch, researches carry
        # nothing else -- sampling one kind would call the other three's
        # examples missing.  `test_field_search_hint.py` samples every record;
        # this is the cheap version of the same rule.
        for r in (_spread(recs_) if table == "techtree" else recs_):
            for f in app.table_fields(table, r["index"])["fields"]:
                vocab.append((str(f.get("label") or "") + " " +
                              str(f.get("name") or "")).lower())
        bad = [w for w in ph.get(table, [])
               if not any(w.lower() in v for v in vocab)]
        ck("%s: every example is a field the table has" % (table,), not bad,
           bad)
    ck("no two tables share the same examples",
       len({tuple(v) for v in ph.values()}) == len(ph), ph)

    section("9. the real page, at the real window size")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        ck("playwright is installed", False)
        sync_playwright = None
    if sync_playwright is not None:
        base = os.environ.get("AOE2MOD_BASE", "http://127.0.0.1:7811")
        try:
            with sync_playwright() as pw:
                b = pw.chromium.launch()
                pg = b.new_page(viewport={"width": 1264, "height": 821})
                errs = []
                pg.on("console", lambda m: errs.append(m.text)
                      if m.type == "error" else None)
                pg.goto(base + "/", wait_until="networkidle", timeout=120000)
                pg.click("#nav-editor")
                hdr = pg.evaluate("""() => {
                  const t = document.querySelector('.edtabs');
                  return {h: Math.round(t.getBoundingClientRect().height),
                          w: Math.round(t.getBoundingClientRect().width),
                          chips: [...t.querySelectorAll('[data-edkind]')]
                                    .map(c => c.textContent.trim())};
                }""")
                ck("13 chips on the row", len(hdr["chips"]) == 13,
                   hdr["chips"])
                ck("the row wraps to two lines instead of crushing a chip",
                   hdr["h"] > 60, hdr["h"])
                ck("no horizontal scroll",
                   pg.evaluate("() => document.documentElement.scrollWidth")
                   <= 1264)
                for kind, n in (("map", 25), ("tail", 1), ("techtree", 65)):
                    pg.click('[data-edkind="%s"]' % kind)
                    pg.wait_for_function(
                        "() => document.querySelectorAll('#fbody table.f tr')"
                        ".length > 1", timeout=60000)
                    st = pg.evaluate("""() => {
                      const rows = document.querySelectorAll(
                        '#fbody table.f tr:not(.fhint)');
                      const q = document.querySelector('#field-q');
                      return {rows: rows.length,
                              first: rows[1] ? rows[1].textContent.trim()
                                                .slice(0, 40) : null,
                              ph: q ? q.placeholder : null};
                    }""")
                    ck("%s: the pane renders its field table" % (kind,),
                       st["rows"] >= n, (st["rows"], n))
                    ck("%s: the search box says what this table has" % (kind,),
                       bool(st["ph"]) and "搜字段名" in st["ph"], st["ph"])
                ck("no console errors", not errs, errs[:3])
                b.close()
        except Exception as exc:                       # noqa: BLE001
            ck("the real page loads", False,
               "%s: %s" % (type(exc).__name__, exc))

    print()
    if FAILS:
        print("FILE TABLES: %d CHECK(S) FAILED -> %r" % (len(FAILS), FAILS))
        return 1
    print("FILE TABLES: THE THREE STRETCHES THAT ARE NOT RECORD LISTS HAVE "
          "ADDRESSES, CHINESE NAMES, READ-ONLY BOUNDARIES AND A WRITE PATH")
    return 0


_ZH_DIGITS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def _zh_num(word):
    """`十一` / `十` / `九` -> int.  Only the form the page actually writes."""
    if word == "十":
        return 10
    if word.startswith("十"):
        return 10 + _ZH_DIGITS.get(word[1:], 0)
    if "十" in word:
        head, _sep, tail = word.partition("十")
        return _ZH_DIGITS.get(head, 0) * 10 + (_ZH_DIGITS.get(tail, 0) if tail else 0)
    return _ZH_DIGITS.get(word, 0)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""In-place byte-patching experiment for the AoE2:DE .dat.

Strategy under test: because the verified parser (parse_dat.py) knows the exact
byte offset of every field, we never need to change the file's geometry -- we
only overwrite specific fields with new values of the SAME width.  No
re-serializer is involved.

This file does NOT modify parse_dat.py.  It reaches into it in two ways:

  1. It monkeypatches parse_dat.read_civ / parse_dat.read_tech with
     byte-identical *recording* variants that additionally note the byte offset
     of each unit start / each tech field.  The recording variants perform
     exactly the same reads in exactly the same order as the originals.

  2. It subclasses parse_dat.Parser only to observe the start offset of each
     top-level stage (so we learn where the numCivs / numTechs count fields
     live) without changing any parsing behaviour.

Everything is then cross-checked: for all 136,861 unit objects the recorded
offsets are re-read from the raw bytes and compared against the values the
parser returned.  A wrong offset table cannot survive that.

Usage:
    python patch_probe.py
"""

import collections
import _gamepaths as GP
import hashlib
import json
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_dat as P

DAT = GP.DAT
COMMON = os.path.dirname(DAT)
HERE = os.path.dirname(os.path.abspath(__file__))

OUT_CIV0 = os.path.join(HERE, "out_patched_civ0.dat")
OUT_ALLCIVS = os.path.join(HERE, "out_patched_allcivs.dat")
OUT_TECHONLY = os.path.join(HERE, "out_patched_techonly.dat")
OFFSETS_JSON = os.path.join(HERE, "patch_offsets.json")
RESULTS_JSON = os.path.join(HERE, "patch_results.json")

VILLAGER_ID = 83
VILLAGER_HP_OLD = 25
VILLAGER_HP_NEW = 99

# --- recording hooks -------------------------------------------------------
UNIT_RECORDS = []      # (civ_index, unit_start_offset, unit_dict)
CIV_RECORDS = []       # civ dicts, in file order
TECH_RECORDS = []      # tech dicts with _* offset keys
CUR_CIV_INDEX = [0]
_ORIG_READ_CIV = P.read_civ
_ORIG_READ_TECH = P.read_tech


def read_civ_recording(r, collect=None):
    """Byte-for-byte the same reads as parse_dat.read_civ, plus offsets."""
    c = {}
    c["player_type"] = r.u8()
    c["name"] = r.debug_string()[1]
    n = r.i16()
    c["tech_tree_id"] = r.i16()
    c["team_bonus_id"] = r.i16()
    c["resources"] = r.f32_array(n)
    c["icon_set"] = r.u8()
    m = r.i16()
    ptrs = r.i32_array(m)
    c["unit_pointers_total"] = m
    c["unit_pointers_nonzero"] = sum(1 for p in ptrs if p != 0)
    c["units"] = []
    idx = len(CIV_RECORDS)
    for i in range(m):
        if ptrs[i] != 0:
            start = r.pos
            u = P.read_unit(r, collect)
            UNIT_RECORDS.append((idx, start, u))
            c["units"].append(u)
    CIV_RECORDS.append(c)
    return c


def read_tech_recording(r):
    """Byte-for-byte the same reads as parse_dat.read_tech, plus offsets."""
    t = {}
    start = r.pos
    r.i16_array(6)                                        # RequiredTechs
    for _ in range(3):
        P.read_research_resource_cost(r)
    r.i16()                                               # RequiredTechCount
    t["_civ_off"] = r.pos
    t["civ"] = r.i16()
    r.i16()                                               # FullTechMode
    r.i32()                                               # LanguageDLLName
    r.i32()                                               # LanguageDLLDescription
    t["_eff_off"] = r.pos
    t["effect_id"] = r.i16()
    t["type"] = r.i16()
    t["_icon_off"] = r.pos
    t["icon_id"] = r.i16()
    r.i32()                                               # LanguageDLLHelp
    r.i32()                                               # LanguageDLLTechTree
    t["name"] = r.debug_string()[1]
    r.u8()                                                # Repeatable
    n = r.i16()
    t["research_locations"] = [P.read_research_location(r) for _ in range(n)]
    t["_start"] = start
    t["_end"] = r.pos
    TECH_RECORDS.append(t)
    return t


class RecordingParser(P.Parser):
    """Same parser; only remembers each top-level stage's start offset."""

    def __init__(self, data):
        P.Parser.__init__(self, data)
        self.stage_starts = {}
        self.stage_ends = {}

    def _stage(self, name, fn, stop_after=None):
        start = self.r.pos
        P.Parser._stage(self, name, fn, stop_after)
        self.stage_starts[name] = start
        self.stage_ends[name] = self.r.pos


# --- helpers ---------------------------------------------------------------
def find_diff_regions(a, b):
    """Return (total_diff_bytes, [(start, end_exclusive, length), ...]).

    Compares in blocks so identical regions are skipped at C speed.
    """
    assert len(a) == len(b), "length mismatch: %d vs %d" % (len(a), len(b))
    BLK = 4096
    n = len(a)
    regions = []
    total = 0
    cur = None
    for off in range(0, n, BLK):
        chunk_a = a[off:off + BLK]
        chunk_b = b[off:off + BLK]
        if chunk_a == chunk_b:
            continue
        for i in range(len(chunk_a)):
            if chunk_a[i] != chunk_b[i]:
                total += 1
                pos = off + i
                if cur is not None and pos == cur[1]:
                    cur = (cur[0], pos + 1)
                    regions[-1] = cur
                else:
                    cur = (pos, pos + 1)
                    regions.append(cur)
    return total, regions


def recompress(data, level=6):
    co = zlib.compressobj(level, zlib.DEFLATED, -15)
    return co.compress(bytes(data)) + co.flush()


VERIFY = {}


def verify_patched(path, label, expect_villager_new=(), tech_icon_expect=None):
    """End-to-end: read the WRITTEN file with the UNMODIFIED parser."""
    data, how = P.load_dat(path)
    out = {"label": label, "path": path, "how": how,
           "raw_size": len(data), "compressed_size": os.path.getsize(path)}
    p = P.Parser(data)
    st = p.parse()
    out["final_offset"] = p.r.pos
    out["leftover"] = len(data) - p.r.pos
    out["byte_exact"] = (p.r.pos == len(data))
    out["civ_count"] = st["civ_count"]
    out["tech_count"] = st["tech_count"]

    # (b) patched unit now reports the new hit points
    hp_rows = []
    for (ci, uid) in expect_villager_new:
        civ = st["civs"][ci]
        units = [u for u in civ["units"] if u["id"] == uid]
        hp_rows.append({"civ": ci, "civ_name": civ["name"], "unit_id": uid,
                        "n_copies": len(units),
                        "hit_points": [u["hit_points"] for u in units]})
    out["villager_check"] = hp_rows

    # (c) unpatched civs unchanged
    unpatched = [ci for ci in range(st["civ_count"])
                 if ci not in {c for c, _ in expect_villager_new}]
    other_hp = set()
    for ci in range(0, st["civ_count"], 7):
        if ci in {c for c, _ in expect_villager_new}:
            continue
        for u in st["civs"][ci]["units"]:
            if u["id"] == VILLAGER_ID:
                other_hp.add(u["hit_points"])
    out["sampled_other_civs_villager_hp"] = sorted(other_hp)

    # (c2) a structural digest so "unchanged" is measurable, not eyeballed
    h = hashlib.sha1()
    for c in st["civs"]:
        h.update(c["name"].encode("latin-1"))
        for u in c["units"]:
            h.update(struct.pack("<Bh", u["type"], u["id"]))
            h.update(struct.pack("<h", u["hit_points"]))
    out["civ_unit_stat_digest"] = h.hexdigest()

    # tech icon
    if tech_icon_expect is not None:
        matches = [(i, t["name"], t["icon_id"]) for i, t in enumerate(st["techs"])
                   if t["name"] == tech_icon_expect["name"]
                   and t["civ"] == tech_icon_expect["civ"]
                   and t["effect_id"] == tech_icon_expect["effect_id"]]
        out["tech_icon_check"] = matches
    return out, st


def main():
    report = {}

    # ------------------------------------------------------------------ load
    orig_blob = open(DAT, "rb").read()
    orig_compressed_size = len(orig_blob)
    orig, how = P.load_dat(DAT)
    print("original .dat      : %s" % DAT)
    print("  compressed       : %d bytes" % orig_compressed_size)
    print("  decompressed     : %d bytes  (%s)" % (len(orig), how))

    # ------------------------------------------------- parse with recording
    P.read_civ = read_civ_recording
    P.read_tech = read_tech_recording
    rp = RecordingParser(orig)
    st = rp.parse()
    consumed = rp.r.pos
    P.read_civ = _ORIG_READ_CIV
    P.read_tech = _ORIG_READ_TECH

    print("")
    print("recording parse    : consumed %d / %d  leftover=%d  exact=%s"
          % (consumed, len(orig), len(orig) - consumed, consumed == len(orig)))
    print("units recorded     : %d" % len(UNIT_RECORDS))
    print("civs recorded      : %d" % len(CIV_RECORDS))
    print("techs recorded     : %d" % len(TECH_RECORDS))

    stage8 = [k for k in rp.stage_starts if k.startswith("8 ")]
    stage9 = [k for k in rp.stage_starts if k.startswith("9 ")]
    NUM_CIVS_OFF = rp.stage_starts[stage8[0]]
    NUM_TECHS_OFF = rp.stage_starts[stage9[0]]
    stage5 = [k for k in rp.stage_starts if k.startswith("5 ")]
    NUM_EFFECTS_OFF = rp.stage_starts[stage5[0]]

    print("")
    print("offset of numCivs   (int16) : %d (0x%X)" % (NUM_CIVS_OFF, NUM_CIVS_OFF))
    print("offset of numTechs  (int16) : %d (0x%X)" % (NUM_TECHS_OFF, NUM_TECHS_OFF))
    print("offset of numEffects(int32) : %d (0x%X)" % (NUM_EFFECTS_OFF, NUM_EFFECTS_OFF))
    assert struct.unpack_from("<h", orig, NUM_CIVS_OFF)[0] == st["civ_count"]
    assert struct.unpack_from("<h", orig, NUM_TECHS_OFF)[0] == st["tech_count"]
    assert struct.unpack_from("<i", orig, NUM_EFFECTS_OFF)[0] == st["effect_count"]
    print("  count fields re-read from raw bytes: OK")

    # ------------------------------------------- build + PROVE offset table
    # read_unit layout is fixed up to HitPoints:
    #   +0 type u8, +1 id i16, +3 LangDLLName i32, +7 LangDLLCreation i32,
    #   +11 class i16, +13 StandingGraphic[2] i16, +17 DyingGraphic i16,
    #   +19 UndeadGraphic i16, +21 UndeadMode u8, +22 HitPoints i16
    HP_DELTA, ID_DELTA, TYPE_DELTA = 22, 1, 0
    UNIT_HP_OFF = {}
    bad_off = 0
    for (ci, start, u) in UNIT_RECORDS:
        hp_off = start + HP_DELTA
        if struct.unpack_from("<h", orig, hp_off)[0] != u["hit_points"]:
            bad_off += 1
            continue
        if struct.unpack_from("<h", orig, start + ID_DELTA)[0] != u["id"]:
            bad_off += 1
            continue
        if orig[start + TYPE_DELTA] != u["type"]:
            bad_off += 1
            continue
        UNIT_HP_OFF[(ci, u["id"])] = (hp_off, u["hit_points"], start, u["type"])
    print("")
    print("offset-table proof : %d/%d unit objects re-read from raw bytes match "
          "the parser's values (mismatches: %d)"
          % (len(UNIT_HP_OFF), len(UNIT_RECORDS), bad_off))
    assert bad_off == 0, "offset table is wrong"

    # tech offsets, same proof
    bad_tech = 0
    for t in TECH_RECORDS:
        if struct.unpack_from("<h", orig, t["_civ_off"])[0] != t["civ"]:
            bad_tech += 1
        if struct.unpack_from("<h", orig, t["_eff_off"])[0] != t["effect_id"]:
            bad_tech += 1
        if struct.unpack_from("<h", orig, t["_icon_off"])[0] != t["icon_id"]:
            bad_tech += 1
    print("offset-table proof : %d/%d tech objects (Civ/EffectID/IconID) re-read "
          "from raw bytes match (mismatches: %d)"
          % (len(TECH_RECORDS), len(TECH_RECORDS), bad_tech))
    assert bad_tech == 0

    # ------------------------------------------------------ auxiliary facts
    aux = {}
    aux["civ_names"] = [c["name"] for c in CIV_RECORDS]
    aux["civ_unit_counts"] = [len(c["units"]) for c in CIV_RECORDS]

    # independence of the per-civ Villager copies
    copies = []
    hp_values = collections.Counter()
    for ci, c in enumerate(CIV_RECORDS):
        us = [u for u in c["units"] if u["id"] == VILLAGER_ID]
        copies.append(len(us))
        for u in us:
            hp_values[u["hit_points"]] += 1
    aux["villager_copies_per_civ"] = copies
    aux["villager_total_copies"] = sum(copies)
    aux["villager_hp_histogram_before"] = {str(k): v for k, v in sorted(hp_values.items())}
    aux["civs_with_villager"] = sum(1 for n in copies if n)

    # identical unit-stat blocks (id, hp) per civ
    blocks = collections.defaultdict(list)
    for ci, c in enumerate(CIV_RECORDS):
        key = tuple(sorted((u["id"], u["hit_points"]) for u in c["units"]))
        blocks[hashlib.sha1(repr(key).encode()).hexdigest()[:16]].append(ci)
    aux["stat_block_groups"] = {
        "n_distinct": len(blocks),
        "groups": [{"sha1_16": h, "n_civs": len(v),
                    "civ_indices": v[:5] + (["..."] if len(v) > 5 else []),
                    "names": [CIV_RECORDS[i]["name"] for i in v[:5]]}
                   for h, v in sorted(blocks.items(), key=lambda kv: -len(kv[1]))]
    }

    # per-civ full sha1 of (id,hp,type) triples for the "unchanged" check
    aux["per_civ_digest"] = []
    for c in CIV_RECORDS:
        h = hashlib.sha1()
        for u in c["units"]:
            h.update(struct.pack("<Bh", u["type"], u["id"]))
            h.update(struct.pack("<h", u["hit_points"]))
        aux["per_civ_digest"].append(h.hexdigest()[:16])

    # unit id multiplicity across the whole file (the UX question)
    id_civ_count = collections.Counter()
    for c in CIV_RECORDS:
        for uid in {u["id"] for u in c["units"]}:
            id_civ_count[uid] += 1
    aux["distinct_unit_ids"] = len(id_civ_count)
    aux["ids_in_all_63_civs"] = sum(1 for v in id_civ_count.values() if v == 63)
    aux["id_civ_count_sample"] = {
        str(uid): id_civ_count[uid]
        for uid in (83, 4, 38, 93, 74, 448, 546, 751, 8, 7)
    }

    # external civ-key files for the 63-vs-58 reconciliation
    ext = {}
    fav = os.path.join(COMMON, "futuravailableunits.json")
    try:
        favj = json.load(open(fav, "r", encoding="utf-8"))
        ext["futuravailableunits_json"] = {
            "path": fav, "n_keys": len(favj),
            "keys_head": sorted(favj.keys())[:8],
        }
    except Exception as e:                                # pragma: no cover
        ext["futuravailableunits_json"] = {"path": fav, "error": repr(e)}
    ctt = os.path.join(COMMON, "CivTechTrees")
    try:
        files = sorted(os.listdir(ctt))
        ext["CivTechTrees"] = {"path": ctt, "n_files": len(files),
                               "extensions": sorted({os.path.splitext(f)[1] for f in files}),
                               "names_head": files[:8]}
    except Exception as e:                                # pragma: no cover
        ext["CivTechTrees"] = {"path": ctt, "error": repr(e)}
    aux["external"] = ext

    # ---- reconcile the 63 dat civs vs futuravailableunits.json vs CivTechTrees
    recon = {}
    try:
        civ_names = [c["name"] for c in CIV_RECORDS]
        recon["dat_civ_names_in_order"] = civ_names
        fav_keys = set(favj.keys())
        recon["fav_n_keys"] = len(fav_keys)
        recon["dat_civs_absent_from_fav"] = [n for n in civ_names if n not in fav_keys]
        recon["fav_keys_absent_from_dat"] = sorted(fav_keys - set(civ_names))
        # AoE2DE spells the dat civs "British"/"French"/"Byzantine"/"Mayan" while
        # the json/tech-tree files use "Britons"/"Franks"/"Byzantines"/"Mayans".
        ALIAS = {"British": "Britons", "French": "Franks",
                 "Byzantine": "Byzantines", "Mayan": "Mayans"}
        dat_alias = [ALIAS.get(n, n) for n in civ_names]
        recon["dat_civ_names_aliased"] = dat_alias
        recon["fav_missing_after_alias"] = [n for n in dat_alias if n not in fav_keys]
        tt_stems = {os.path.splitext(f)[0] for f in os.listdir(ctt)}
        recon["tt_n_stems"] = len(tt_stems)
        recon["dat_civs_without_tt_file"] = [n for n in dat_alias if n.upper() not in tt_stems]
        recon["tt_files_without_dat_civ"] = sorted(
            s for s in tt_stems if s not in {n.upper() for n in dat_alias})
        recon["fav_keys_without_tt_file"] = sorted(
            k for k in fav_keys if k.upper() not in tt_stems and k != "FullTechCiv")
        recon["is_gaia_in_fav"] = "Gaia" in fav_keys
        recon["is_fulltechciv_in_fav"] = "FullTechCiv" in fav_keys
        recon["fulltechciv_not_a_dat_civ"] = "FullTechCiv" not in set(civ_names)
    except Exception as e:                                # pragma: no cover
        recon["error"] = repr(e)
    aux["civ_reconciliation"] = recon

    # ------------------------------------------------------- choose a tech
    icon_values = [t["icon_id"] for t in TECH_RECORDS if t["icon_id"] >= 0]
    icon_hist = collections.Counter(icon_values)
    aux["tech_icon_id_range"] = [min(icon_values), max(icon_values)] if icon_values else None
    aux["tech_icon_ids_distinct"] = len(set(icon_values))

    # a recognizable, all-civ tech with a positive icon id and a real EffectID
    pick = None
    for want in ("Fletching", "Loom", "Wheelbarrow", "Feudal Age", "Bow Saw"):
        for i, t in enumerate(TECH_RECORDS):
            if t["name"] == want and t["icon_id"] >= 0 and t["effect_id"] >= 0:
                pick = (i, t, want)
                break
        if pick:
            break
    if pick is None:
        for i, t in enumerate(TECH_RECORDS):
            if t["name"] and t["icon_id"] >= 0 and t["effect_id"] >= 0:
                pick = (i, t, t["name"])
                break
    TECH_INDEX, TECH, TECH_NAME = pick
    # a clearly different but valid icon id: the most common icon id in the file
    # that is not the tech's current value (i.e. genuinely used by other techs)
    common_icon = next(v for v, _ in icon_hist.most_common()
                       if v != TECH["icon_id"])
    TECH_ICON_OLD = TECH["icon_id"]
    TECH_ICON_NEW = common_icon
    print("")
    print("tech chosen        : index=%d name=%r civ=%d effect_id=%d type=%d"
          % (TECH_INDEX, TECH_NAME, TECH["civ"], TECH["effect_id"], TECH["type"]))
    print("  IconID offset    : %d (0x%X)   %d -> %d"
          % (TECH["_icon_off"], TECH["_icon_off"], TECH_ICON_OLD, TECH_ICON_NEW))
    print("  (new value %d is an icon id already used by %d other techs)"
          % (TECH_ICON_NEW, icon_hist[TECH_ICON_NEW]))

    # ------------------------------------------------------------- offsets
    civ0 = CIV_RECORDS[0]
    v0 = [u for u in civ0["units"] if u["id"] == VILLAGER_ID]
    assert len(v0) == 1, "expected exactly one Villager in civ[0]"
    V0_HP_OFF = UNIT_HP_OFF[(0, VILLAGER_ID)][0]
    print("")
    print("civ[0]             : %r  units=%d" % (civ0["name"], len(civ0["units"])))
    print("civ[0] Villager 83 : HitPoints at %d (0x%X), value=%d"
          % (V0_HP_OFF, V0_HP_OFF, UNIT_HP_OFF[(0, VILLAGER_ID)][1]))

    all_villager_offsets = []
    for ci in range(len(CIV_RECORDS)):
        if (ci, VILLAGER_ID) in UNIT_HP_OFF:
            all_villager_offsets.append((ci, UNIT_HP_OFF[(ci, VILLAGER_ID)][0],
                                         UNIT_HP_OFF[(ci, VILLAGER_ID)][1]))
    print("Villager copies    : %d civs carry a unit id 83 (%d objects total)"
          % (len(all_villager_offsets), sum(1 for n in copies if n)))

    offsets_dump = {
        "num_civs": {"offset": NUM_CIVS_OFF, "width": 2, "value": st["civ_count"]},
        "num_techs": {"offset": NUM_TECHS_OFF, "width": 2, "value": st["tech_count"]},
        "num_effects": {"offset": NUM_EFFECTS_OFF, "width": 4, "value": st["effect_count"]},
        "unit_layout": {"type_delta": 0, "id_delta": 1, "hit_points_delta": 22},
        "civ0_villager_83": {"unit_start": UNIT_HP_OFF[(0, VILLAGER_ID)][2],
                             "hit_points_offset": V0_HP_OFF, "hit_points": 25},
        "villager_83_all_civs": [
            {"civ": ci, "unit_start": UNIT_HP_OFF[(ci, VILLAGER_ID)][2],
             "hit_points_offset": off, "hit_points": hp,
             "civ_name": CIV_RECORDS[ci]["name"]}
            for (ci, off, hp) in all_villager_offsets],
        "chosen_tech": {
            "index": TECH_INDEX, "name": TECH_NAME, "civ": TECH["civ"],
            "effect_id": TECH["effect_id"], "type": TECH["type"],
            "start": TECH["_start"], "civ_offset": TECH["_civ_off"],
            "effect_id_offset": TECH["_eff_off"], "icon_id_offset": TECH["_icon_off"],
            "icon_id_old": TECH_ICON_OLD, "icon_id_new": TECH_ICON_NEW},
    }
    with open(OFFSETS_JSON, "w", encoding="utf-8") as fh:
        json.dump(offsets_dump, fh, indent=1)

    # ------------------------------------------------------------- patching
    def patch(hp_targets, icon_new):
        """hp_targets: list of absolute offsets to write 99 into (int16)."""
        buf = bytearray(orig)
        for off in hp_targets:
            struct.pack_into("<h", buf, off, VILLAGER_HP_NEW)
        if icon_new is not None:
            struct.pack_into("<h", buf, TECH["_icon_off"], icon_new)
        return buf

    civ0_buf = patch([V0_HP_OFF], TECH_ICON_NEW)
    allcivs_buf = patch([off for (_c, off, _h) in all_villager_offsets], TECH_ICON_NEW)
    techonly_buf = patch([], TECH_ICON_NEW)

    writes = []
    for path, buf, label in ((OUT_CIV0, civ0_buf, "civ0 villager + tech icon"),
                             (OUT_ALLCIVS, allcivs_buf, "all-civs villager + tech icon"),
                             (OUT_TECHONLY, techonly_buf, "tech icon only")):
        blob = recompress(buf, 6)
        with open(path, "wb") as fh:
            fh.write(blob)
        writes.append({"path": path, "label": label,
                       "compressed_size": len(blob),
                       "delta_vs_original": len(blob) - orig_compressed_size})
        print("wrote %-42s %d bytes" % (os.path.basename(path), len(blob)))

    # control: recompress the UNMODIFIED data to isolate "recompress" cost
    control_blob = recompress(orig, 6)
    control_size = len(control_blob)
    print("control (unmodified recompress level 6): %d bytes" % control_size)

    # ------------------------------------------------------- diff analysis
    diffs = {}
    for key, buf in (("civ0", civ0_buf), ("allcivs", allcivs_buf),
                     ("techonly", techonly_buf)):
        total, regions = find_diff_regions(orig, bytes(buf))
        diffs[key] = {"total_diff_bytes": total,
                      "n_regions": len(regions),
                      "regions": [{"start": s, "end": e, "len": e - s}
                                  for (s, e) in regions]}
        print("")
        print("diff %-9s : %d bytes in %d region(s)" % (key, total, len(regions)))
        for rg in diffs[key]["regions"][:8]:
            print("    [%d,%d)  len=%d" % (rg["start"], rg["end"], rg["len"]))
        if len(regions) > 8:
            print("    ... %d more" % (len(regions) - 8))

    expected = {}
    for key, offsets in (("civ0", [V0_HP_OFF]),
                         ("allcivs", [off for (_c, off, _h) in all_villager_offsets]),
                         ("techonly", [])):
        exp = sorted(offsets + [TECH["_icon_off"]])
        expected[key] = exp
    diffs["civ0"]["expected_offsets"] = expected["civ0"]
    diffs["allcivs"]["expected_offsets"] = expected["allcivs"]
    diffs["techonly"]["expected_offsets"] = expected["techonly"]
    for key in ("civ0", "allcivs", "techonly"):
        got = [(rg["start"], rg["end"]) for rg in diffs[key]["regions"]]
        fields = sorted((off, off + 2) for off in expected[key])
        # A changed region is only emitted where a byte VALUE actually differs,
        # so a 2-byte field whose high byte is unchanged yields a 1-byte region.
        # Correct test is CONTAINMENT: every diff region must lie inside exactly
        # one intended 2-byte field, and no intended field may be untouched
        # unless its new value is byte-identical to the old one.
        def _field_of(lo, hi):
            hits = [f for f in fields if lo >= f[0] and hi <= f[1]]
            return hits[0] if len(hits) == 1 else None
        unexpected, missing = [], []
        for (lo, hi) in got:
            if _field_of(lo, hi) is None:
                unexpected.append((lo, hi))
        for (lo, hi) in fields:
            if not any(g_lo >= lo and g_hi <= hi for (g_lo, g_hi) in got):
                # no byte changed in this field => old and new value identical
                if orig[lo:hi] != bytes(buf)[lo:hi]:
                    missing.append((lo, hi))
        diffs[key]["expected_fields"] = fields
        diffs[key]["unexpected_regions"] = unexpected
        diffs[key]["missing_regions"] = missing
        diffs[key]["surgical"] = (not unexpected and not missing)
        print("diff %-9s : surgical=%s (%d changed byte(s) in %d region(s); "
              "all inside the %d intended 2-byte field(s)=%s; silent fields=%d)"
              % (key, diffs[key]["surgical"], diffs[key]["total_diff_bytes"],
                 len(got), len(fields), not unexpected,
                 len(fields) - len([1 for (lo, hi) in fields
                                    if any(g_lo >= lo and g_hi <= hi
                                           for (g_lo, g_hi) in got)])))

    # ----------------------------------------------------------- verification
    print("")
    print("=" * 72)
    print("VERIFICATION: re-parse each WRITTEN file with the UNMODIFIED parser")
    print("=" * 72)
    checks = []
    for path, label, expect in (
            (OUT_CIV0, "civ0", [(0, VILLAGER_ID)]),
            (OUT_ALLCIVS, "allcivs", [(ci, VILLAGER_ID) for ci in range(len(CIV_RECORDS))
                                      if (ci, VILLAGER_ID) in UNIT_HP_OFF]),
            (OUT_TECHONLY, "techonly", [])):
        out, _st = verify_patched(path, label,
                                  expect_villager_new=expect,
                                  tech_icon_expect=dict(
                                      name=TECH_NAME, civ=TECH["civ"],
                                      effect_id=TECH["effect_id"]))
        checks.append(out)
        print("%-9s %s" % (label, path))
        print("   raw=%d final=%d leftover=%d byte_exact=%s  (compressed %d)"
              % (out["raw_size"], out["final_offset"], out["leftover"],
                 out["byte_exact"], out["compressed_size"]))
        print("   civs=%d techs=%d" % (out["civ_count"], out["tech_count"]))
        if out["villager_check"]:
            print("   villager(id 83) checks: patched civs=%d, hp values=%s"
                  % (len(out["villager_check"]),
                     sorted({h for r in out["villager_check"] for h in r["hit_points"]})))
        print("   sampled non-patched civs villager hp: %s"
              % out["sampled_other_civs_villager_hp"])
        if out.get("tech_icon_check") is not None:
            print("   tech icon after patch: %s" % (out["tech_icon_check"],))
        print("   civ/unit stat digest: %s" % out["civ_unit_stat_digest"])
        assert out["byte_exact"], "patched file did not parse to exactly its size!"
        assert out["leftover"] == 0
        if out["villager_check"]:
            assert all(h == VILLAGER_HP_NEW
                       for r in out["villager_check"] for h in r["hit_points"]), \
                "patched villager did not report %d" % VILLAGER_HP_NEW
        if out["sampled_other_civs_villager_hp"]:
            assert out["sampled_other_civs_villager_hp"] == [VILLAGER_HP_OLD], \
                "an unpatched civ changed!"

    # ------------------------------------------------- semantic validator run
    print("")
    print("=" * 72)
    print("SEMANTIC VALIDATOR (unmodified validate_semantics.py) on patched files")
    print("=" * 72)
    import validate_semantics as VS
    val = {}
    for path, label in ((DAT, "original"),
                        (OUT_TECHONLY, "techonly"),
                        (OUT_CIV0, "civ0"),
                        (OUT_ALLCIVS, "allcivs")):
        VS.DAT = path
        print("\n--- validate: %s ---" % label)
        rc = VS.main()
        val[label] = {"path": path, "exit_code": rc}
        print("--- validate %s: exit %d ---" % (label, rc))
    VS.DAT = DAT

    # -------------------------------------------------------------- results
    results = {
        "original": {"path": DAT,
                     "compressed_size": orig_compressed_size,
                     "decompressed_size": len(orig),
                     "compression": how},
        "counts": {"civs": st["civ_count"], "techs": st["tech_count"],
                   "effects": st["effect_count"], "units_total": len(UNIT_RECORDS)},
        "stage_offsets": {k: [rp.stage_starts[k], rp.stage_ends[k]]
                          for k in sorted(rp.stage_starts)},
        "offset_proof": {"units_checked": len(UNIT_RECORDS),
                         "units_matched": len(UNIT_HP_OFF), "unit_mismatches": bad_off,
                         "techs_checked": len(TECH_RECORDS), "tech_mismatches": bad_tech},
        "offsets": offsets_dump,
        "auxiliary": aux,
        "patch": {
            "villager": {"id": VILLAGER_ID, "old_hp": VILLAGER_HP_OLD,
                         "new_hp": VILLAGER_HP_NEW,
                         "civ0_hp_offset": V0_HP_OFF,
                         "n_all_civ_offsets": len(all_villager_offsets)},
            "tech": {"index": TECH_INDEX, "name": TECH_NAME, "civ": TECH["civ"],
                     "effect_id": TECH["effect_id"], "type": TECH["type"],
                     "icon_id_offset": TECH["_icon_off"],
                     "icon_id_old": TECH_ICON_OLD, "icon_id_new": TECH_ICON_NEW,
                     "new_icon_used_by_n_other_techs": icon_hist[TECH_ICON_NEW]},
        },
        "writes": writes,
        "control_unmodified_recompress_size": control_size,
        "diffs": diffs,
        "verification": checks,
        "validator": val,
    }
    with open(RESULTS_JSON, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1)
    print("")
    print("results JSON: %s" % RESULTS_JSON)
    print("offset JSON : %s" % OFFSETS_JSON)
    return 0


if __name__ == "__main__":
    sys.exit(main())

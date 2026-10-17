# -*- coding: utf-8 -*-
"""Palette / player-color mechanism probe (read-only).

Question under test: is "make a unit red" a palette edit (as the graphics
survey claimed), and for WHICH units?

Sub-questions:
  P1 format         -- parse every .pal/.palx; JASC-PAL vs JASC-PALX, size,
                       alpha directive, comment syntax
  P2 registry       -- palettes.conf maps id -> file; which ids are real
                       colors vs placeholder black
  P3 SLD linkage    -- do .sld files carry a palette id anywhere? (dump the
                       16-byte file header and 12-byte frame header of several
                       real sprites and look for a palettes.conf id)
  P4 team colors    -- spritecolors.json / *.json variants: structure, and
                       whether the engine reads them (exe string check)
  P5 moddability    -- does any installed mod ship a palettes/ dir or
                       spritecolors.json already (official overlay precedent)?
"""
import json
import os
import re

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
USER = r"C:\Users\26913\Games\Age of Empires 2 DE"
PALDIR = os.path.join(GAME, "resources", "_common", "palettes")
EXE = os.path.join(GAME, "AoE2DE_s.exe")


def parse_pal(path):
    raw = open(path, "rb").read()
    txt = raw.decode("latin1")
    lines = [l.rstrip("\r") for l in txt.split("\n") if l.strip()]
    magic = lines[0]
    ver = lines[1] if len(lines) > 1 else ""
    n = int(lines[2]) if len(lines) > 2 and lines[2].strip().isdigit() else -1
    body = lines[3:]
    colours = []
    directives = []
    comments = 0
    for l in body:
        s = l.strip()
        if s.startswith("//") or s.startswith("#"):
            comments += 1
            continue
        if s.startswith("$"):
            directives.append(s)
            continue
        parts = s.split()
        if len(parts) >= 3 and all(p.lstrip("-").isdigit() for p in parts[:3]):
            colours.append(tuple(int(p) for p in parts[:4]))
    return dict(magic=magic, ver=ver, declared=n, got=len(colours),
                directives=directives, comments=comments,
                size=len(raw), colours=colours)


print("=" * 70)
print("P1  palette file formats")
print("=" * 70)
files = []
for b, s, fs in os.walk(PALDIR):
    for f in fs:
        if f.lower().endswith((".pal", ".palx")):
            files.append(os.path.join(b, f))
files.sort()
magics = {}
for p in files:
    try:
        r = parse_pal(p)
    except Exception as e:
        print("  PARSE FAIL", os.path.basename(p), e)
        continue
    magics[r["magic"]] = magics.get(r["magic"], 0) + 1
    rel = os.path.relpath(p, PALDIR)
    dirs = ("dirs:" + ",".join(r["directives"])) if r["directives"] else ""
    flag = "" if r["declared"] == r["got"] else "  <-- COUNT MISMATCH"
    if r["directives"] or flag or "PALX" in r["magic"]:
        print("  %-38s %-11s decl=%-5d got=%-5d %s%s"
              % (rel, r["magic"], r["declared"], r["got"], dirs, flag))
print()
print("  magic histogram:", magics)
print("  total palette files on disk:", len(files))

print()
print("=" * 70)
print("P2  palettes.conf registry")
print("=" * 70)
conf = open(os.path.join(PALDIR, "palettes.conf"), "rb").read().decode("latin1")
reg = {}
for l in conf.split("\n"):
    l = l.split("//")[0].strip()
    if not l:
        continue
    m = re.match(r"^(\d+)\s*,\s*(\S+)$", l)
    if m:
        reg[int(m.group(1))] = m.group(2)
print("  registered ids:", len(reg))
holders = {}
for i, f in sorted(reg.items()):
    holders.setdefault(f, []).append(i)
placeholder = [i for i, f in sorted(reg.items()) if "playercolor_black" in f]
print("  ids -> playercolor_black (PLACEHOLDER):", placeholder)
print("  distinct files referenced:", len(holders))
real = {i: f for i, f in sorted(reg.items()) if "playercolor_black" not in f}
print()
for i, f in sorted(real.items()):
    print("   id %-3d -> %s" % (i, f))

print()
print("=" * 70)
print("P3  do .sld sprites reference a palette id?")
print("=" * 70)
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
import struct
samples = ["u_arc_archer_idlea_x1.sld", "u_vil_male_villager_idlea_x1.sld",
           "b_west_town_center_age2_back_x1.sld", "u_cav_knight_idlea_x1.sld"]
import zlib
for s in samples:
    p = os.path.join(GP, s)
    if not os.path.exists(p):
        print("  missing", s)
        continue
    b = open(p, "rb").read()
    sig = b[0:4]
    hdr = struct.unpack_from("<4s 4H I", b, 0)
    print("  %-40s size=%-9d sig=%r header=%s" % (s, len(b), sig, hdr))
    # frame header right after the 16-byte file header
    ft, u1, fi, nlay, nl2 = struct.unpack_from("<4H 2B H", b, 16)[0:5] if False else (0, 0, 0, 0, 0)
    fh = struct.unpack_from("<HHHHBBH", b, 16)
    print("      frame0: frame_type=%d unknown1=%d frame_index=%d layer_count=%d unk=%d unk=%d cmd_len=%d"
          % (fh[0], fh[1], fh[2], fh[3], fh[4], fh[5], fh[6]))

print()
print("=" * 70)
print("P4  team-colour JSON + exe references")
print("=" * 70)
for f in sorted(os.listdir(PALDIR)):
    if f.endswith(".json"):
        p = os.path.join(PALDIR, f)
        d = json.load(open(p, encoding="utf-8-sig"))
        keys = list(d.keys())
        style = set()
        for grp in d.values():
            for ent in grp.values():
                style.update(ent.keys())
        n = {k: len(v) for k, v in d.items()}
        print("  %-34s groups=%s counts=%s value-style=%s"
              % (f, keys, n, sorted(style)))
b = open(EXE, "rb").read()
print()
for s in [b"spritecolors", b"TeamColors", b"OutlineColors", b"FloatRGBA",
          b"HexColor", b"JASC-PAL", b".palx", b"PALETTES", b"palettes"]:
    print("  exe contains %-14s : %d" % (s.decode(), b.count(s)))

print()
print("=" * 70)
print("P5  moddability: do installed mods ship palettes / spritecolors?")
print("=" * 70)
for root in (USER, os.path.join(GAME)):
    for b2, s2, fs2 in os.walk(root):
        if "mods" not in b2.lower() and "subscribed" not in b2.lower():
            continue
        for f2 in fs2:
            if f2.lower().endswith((".pal", ".palx")) or f2.lower().startswith("spritecolors") or f2 == "palettes.conf":
                print("   MOD FILE:", os.path.join(b2, f2).replace(root, "<root>"))
print("  (scan complete)")

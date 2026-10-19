# -*- coding: utf-8 -*-
"""probe_icon_render_route.py -- decide how an icon is actually turned into pixels.

`probe_icon_look.py` failed for the right reason: it assumed a material's
`imageTLX..imageBRY` UV rect indexes into the loose file.  It does not -- those
fractions index the big ATLAS (`textures/atlas/HD/ingameunits.dds`, DX10/BC7),
while `FileName` points at a per-icon file that is already the whole picture.

Evidence needed before writing a renderer, measured here:
  1. how the UV size compares to the loose file size (if the loose file IS the
     tile, its pixel size must equal uv * atlas size),
  2. what `FileName` prefixes the three icon atlases use (the renderer reads
     them relative to `widgetui/`),
  3. which DDS pixel formats those files use, so the decoder knows what to read.

Nothing is decoded here on purpose: this probe answers "where are the pixels".
"""
from __future__ import print_function

import codecs
import collections
import io
import json
import os
import struct
import sys

WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
ATLASES = ("ingameunits", "ingamebuildings", "ingametechs", "ingameicons", "ingamepanels")


def dds_head(path):
    with open(path, "rb") as fh:
        b = fh.read(148)
    return {
        "h": struct.unpack_from("<I", b, 12)[0],
        "w": struct.unpack_from("<I", b, 16)[0],
        "pitch": struct.unpack_from("<I", b, 20)[0],
        "fourcc": struct.unpack_from("<4s", b, 84)[0].decode("latin1").strip("\x00"),
        "dx10": struct.unpack_from("<I", b, 128)[0] if b[84:88] == b"DX10" else None,
        "pf_flags": struct.unpack_from("<I", b, 80)[0],
        "rgba_bits": struct.unpack_from("<II", b, 88)[0],
    }


def main():
    with io.open(os.path.join(WID, "materials.json"), encoding="utf-8-sig") as fh:
        J = json.load(fh)
    ATLS = {e.get("AtlasDef", e)["Name"]: e.get("AtlasDef", e) for e in J["AtlasTextures"]}

    for name in ATLASES:
        at = ATLS.get(name)
        if not at:
            print("%s: absent" % name)
            continue
        aw, ah = int(at.get("MaxWidth") or 0), int(at.get("MaxHeight") or 0)
        print("\n=== %s  atlas %dx%d  textures=%d ===" % (name, aw, ah, len(at["Textures"])))

        prefixes = collections.Counter()
        formats = collections.Counter()
        size_mismatch = 0
        checked = 0
        for t in at["Textures"]:
            fn = t.get("FileName") or ""
            prefixes[fn.rsplit("/", 1)[0]] += 1
            fp = os.path.join(WID, fn.replace("/", os.sep))
            if not os.path.exists(fp):
                formats["MISSING FILE"] += 1
                continue
            hd = dds_head(fp)
            uvw = (float(t["imageBRX"]) - float(t["imageTLX"])) * aw
            uvh = (float(t["imageBRY"]) - float(t["imageTLY"])) * ah
            if abs(uvw - hd["w"]) > 2 or abs(uvh - hd["h"]) > 2:
                size_mismatch += 1
                if size_mismatch <= 4:
                    print("  size differs: %s uv=%.1fx%.1f file=%dx%d"
                          % (fn, uvw, uvh, hd["w"], hd["h"]))
            checked += 1
            formats[(fn.rsplit(".", 1)[-1].upper(), hd["fourcc"] or "raw", hd["dx10"],
                     hd["w"], hd["h"])] += 1
        print("  FileName dirs: %s"
              % ", ".join("%s=%d" % kv for kv in sorted(prefixes.items())))
        print("  uv rect vs loose file size: %d checked, %d differ by >2px"
              % (checked, size_mismatch))
        print("  formats (ext, fourcc, dxgi, w, h):")
        for k in sorted(formats, key=str):
            print("     %-34s %d" % (str(k), formats[k]))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())

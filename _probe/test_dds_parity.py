# -*- coding: utf-8 -*-
"""Compare the Rust DDS decoder against the Python one, pixel for pixel.

Not "the PNG opens": a decoder that swaps two channels or drops alpha produces a
perfectly valid PNG. So this decodes the same file both ways and compares the
RGBA buffers, then checks the PNG the Rust side writes parses back to the same
pixels.
"""
import io
import os
import struct
import subprocess
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.game.ddstex as D          # noqa: E402

EXE = os.path.join(ROOT, "desktop", "aoe2mod-serve", "target", "release",
                   "aoe2mod-serve.exe")
GAME = r"d:\games\steam\steamapps\common\AoE2DE"
TEX = os.path.join(GAME, "widgetui", "textures", "ingame")


def sample_dds(limit=120):
    out = []
    for base, _dirs, files in os.walk(TEX):
        for f in files:
            if f.lower().endswith(".dds"):
                out.append(os.path.join(base, f))
                if len(out) >= limit:
                    return out
    return out


def png_to_rgba(blob):
    """Minimal PNG reader: IHDR + IDAT, 8-bit RGBA, filter 0 only."""
    assert blob[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    i = 8
    w = h = None
    idat = b""
    while i < len(blob):
        ln = struct.unpack_from(">I", blob, i)[0]
        kind = blob[i + 4:i + 8]
        data = blob[i + 8:i + 8 + ln]
        if kind == b"IHDR":
            w, h = struct.unpack_from(">II", data, 0)
            assert data[8] == 8 and data[9] == 6, "expected 8-bit RGBA"
        elif kind == b"IDAT":
            idat += data
        elif kind == b"IEND":
            break
        i += 12 + ln
    raw = zlib.decompress(idat)
    stride = w * 4
    out = bytearray()
    pos = 0
    for _y in range(h):
        f = raw[pos]
        pos += 1
        row = raw[pos:pos + stride]
        pos += stride
        # Only filter 0 is emitted by the Rust encoder; be strict so a different
        # filter cannot masquerade as a match.
        assert f == 0, "unexpected PNG filter %d" % f
        out += row
    return w, h, bytes(out)


def main():
    if not os.path.isfile(EXE):
        print("REFUSING: build the crate first")
        return 1
    files = sample_dds()
    if not files:
        print("REFUSING: no .dds under", TEX)
        return 1

    # Add a probe binary route? No: call the decoder through a tiny sidecar that
    # the crate already exposes via `--dds-dump`.
    bad = 0
    for path in files:
        rel = os.path.relpath(path, ROOT)
        try:
            pw, ph, prgba = D.decode(path)
        except Exception as exc:
            print("py decode failed %s: %s" % (os.path.basename(path), exc))
            continue
        r = subprocess.run([EXE, "--dds", path], capture_output=True, timeout=120)
        if r.returncode != 0:
            print("rust decode failed %s: %s" % (os.path.basename(path),
                                                 r.stderr[:120]))
            bad += 1
            continue
        blob = r.stdout
        try:
            rw, rh, rrgba = png_to_rgba(blob)
        except Exception as exc:
            print("rust png unreadable %s: %s" % (os.path.basename(path), exc))
            bad += 1
            continue
        ok = (rw == pw and rh == ph and rrgba == prgba)
        print("%-44s %dx%d py=%dx%d %s"
              % (os.path.basename(path)[:44], rw, rh, pw, ph,
                 "ok" if ok else "MISMATCH"))
        if not ok:
            bad += 1
            if rw == pw and rh == ph:
                diff = next((i for i in range(min(len(rrgba), len(prgba)))
                             if rrgba[i] != prgba[i]), None)
                print("   first differing byte:", diff)
    print()
    print("DDS: %d/%d match" % (len(files) - bad, len(files)))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

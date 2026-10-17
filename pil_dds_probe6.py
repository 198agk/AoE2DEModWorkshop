import struct, io
from PIL import Image

def blocks(d, b=4): return max(1, (d + b - 1) // b)

print("### uncompressed DDS round-trip (dds_rgb path)")
for mode, color in [("RGB", (200, 100, 50)), ("RGBA", (200, 100, 50, 128)), ("L", 200), ("LA", (200, 128))]:
    src = Image.new(mode, (7, 5), color)
    b = io.BytesIO(); src.save(b, format="DDS")
    raw = b.getvalue()
    try:
        back = Image.open(io.BytesIO(raw)); back.load()
        print(f"  mode={mode:4s} hdr={len(raw)-35} -> read OK mode={back.mode} size={back.size} px0={back.getpixel((0,0))}")
    except Exception as e:
        print(f"  mode={mode:4s} -> {type(e).__name__}: {e}")
print()

print("### writer: DDPF_ALPHAPIXELS on FOURCC formats")
for pf in ["DXT1", "DXT3", "DXT5", "BC2", "BC3"]:
    b = io.BytesIO(); Image.new("RGBA", (8, 8)).save(b, format="DDS", pixel_format=pf)
    raw = b.getvalue()
    pfflags, = struct.unpack_from("<I", raw, 80)
    print(f"  {pf:5s} pfflags=0x{pfflags:X}  FOURCC={bool(pfflags&4)} ALPHAPIXELS={bool(pfflags&1)}")
print("  -> BC2/BC3 explicit-alpha formats are NOT flagged ALPHAPIXELS in the legacy header")
print()

print("### writer declares DDSD_LINEARSIZE but writes (w+3)*4")
for w, h, pf, bb in [(2048, 1572, "DXT5", 16), (2048, 1572, "DXT1", 8), (8, 8, "DXT5", 16), (7, 7, "DXT5", 16)]:
    b = io.BytesIO(); Image.new("RGBA", (w, h)).save(b, format="DDS", pixel_format=pf)
    raw = b.getvalue()
    flags, = struct.unpack_from("<I", raw, 8)
    val, = struct.unpack_from("<I", raw, 20)
    true_row = blocks(w) * bb
    true_lin = blocks(w) * blocks(h) * bb
    print(f"  {w}x{h} {pf}: LINEARSIZE={bool(flags & 0x80000)} value={val} | true row pitch={true_row} true top-mip linear={true_lin}")
print("  -> (w+3)*4 is the number of BYTES per 4x4 block-row / 4  == 'dwPitch' in DWORDs;")
print("     it is NEITHER the row pitch in bytes NOR the top-mip linear size for DXT.")
print()

print("### total header bytes recap")
for pf in [None, "DXT1", "DXT5", "BC2", "BC3", "BC5"]:
    b = io.BytesIO(); im = Image.new("RGB" if pf == "BC5" else "RGBA", (8, 8))
    kw = {} if pf is None else {"pixel_format": pf}
    im.save(b, format="DDS", **kw)
    raw = b.getvalue()
    hdrlen = 148 if raw[84:88] == b"DX10" else 128
    print(f"  pf={str(pf):5s} main_header=124+4={128} DXT10={'yes(+20=148)' if hdrlen==148 else 'no'} -> pixel data @{hdrlen}")

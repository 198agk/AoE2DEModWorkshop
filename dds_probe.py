import struct, io, math, sys
from PIL import Image

FOURCC = {v: k for k, v in {
    "DXT1": b"DXT1", "DXT3": b"DXT3", "DXT5": b"DXT5", "DX10": b"DX10",
    "BC4U": b"BC4U", "BC4S": b"BC4S", "BC5U": b"BC5U", "BC5S": b"BC5S",
    "ATI1": b"ATI1", "ATI2": b"ATI2",
}.items()}

def parse(buf):
    assert buf[:4] == b"DDS "
    (hsize,) = struct.unpack_from("<I", buf, 4)
    (flags, h, w, pitch, depth, mips) = struct.unpack_from("<6I", buf, 8)
    (pfsize, pfflags, fourcc, bitcount) = struct.unpack_from("<4I", buf, 76)
    masks = struct.unpack_from("<4I", buf, 92)
    (caps, caps2, caps3, caps4, reserved2) = struct.unpack_from("<5I", buf, 108)
    d = dict(hsize=hsize, flags=hex(flags), height=h, width=w, pitch=pitch,
             depth=depth, mips=mips, pfsize=pfsize, pfflags=hex(pfflags),
             fourcc=fourcc, bitcount=bitcount, masks=tuple(hex(m) for m in masks),
             caps=hex(caps), caps2=hex(caps2), caps3=caps3, caps4=caps4)
    if fourcc == int.from_bytes(b"DX10", "little"):
        (dxgi, resdim, misc, arrsize, misc2) = struct.unpack_from("<5I", buf, 128)
        d.update(dxgi=dxgi, resdim=resdim, misc=misc, arrsize=arrsize, misc2=misc2)
    return d

def save_bytes(im, **kw):
    b = io.BytesIO()
    im.save(b, format="DDS", **kw)
    return b.getvalue()

def blocks(dim, bs):
    return max(1, (dim + bs - 1) // bs)

print("== Pillow", Image.__version__, "==")
print()

# --- 1. pixel_format matrix on 8x8
print("### pixel_format matrix, image 8x8 RGBA/RGB")
for pf in ["DXT1", "DXT3", "DXT5", "BC2", "BC3", "BC5", "BC7", "BC1", "BC4", "BC6H", None]:
    im = Image.new("RGBA" if pf != "BC5" else "RGB", (8, 8), (1, 2, 3, 4))
    try:
        kw = {} if pf is None else {"pixel_format": pf}
        b = save_bytes(im, **kw)
        d = parse(b)
        fc = FOURCC.get(struct.pack("<I", d["fourcc"]), struct.pack("<I", d["fourcc"]))
        line = f"  pf={str(pf):5s} len={len(b):6d} fourcc={fc!r:8s} flags={d['flags']} pitch={d['pitch']} mips={d['mips']} caps={d['caps']}"
        if "dxgi" in d:
            line += f" DX10@128 dxgi={d['dxgi']} resdim={d['resdim']} arr={d['arrsize']} misc2={d['misc2']}"
        print(line)
    except Exception as e:
        print(f"  pf={str(pf):5s} EXC {type(e).__name__}: {e}")
print()

# --- 2. exact byte layout of a BC3 (DX10) file
print("### BC3 8x8 raw hex, first 164 bytes")
b = save_bytes(Image.new("RGBA", (8, 8), (1, 2, 3, 4)), pixel_format="BC3")
print("  len =", len(b))
for off in range(0, 164, 16):
    chunk = b[off:off + 16]
    print(f"  {off:5d} 0x{off:04X}  {chunk.hex(' ')}")
d = parse(b)
print("  parsed:", d)
print()

# --- 3. Does the DX10 block ever exceed 20 bytes? check DX10 vs legacy DXT5 sizes same dims
print("### size delta: DX10 (BC3) vs legacy (DXT5), 8x8 and 1024x1024")
for size in [(8, 8), (1024, 1024)]:
    a = save_bytes(Image.new("RGBA", size), pixel_format="DX10" if False else "DXT5")
    c = save_bytes(Image.new("RGBA", size), pixel_format="BC3")
    print(f"  {size}: DXT5={len(a)} BC3(DX10)={len(c)} delta={len(c)-len(a)}")
print()

# --- 4. pitch / linear size correctness
print("### pitch (dwPitchOrLinearSize) vs correct DXT block linear size")
print(f"  {'WxH':>12} {'pf':>5} {'Pillow pitch':>13} {'ceil(w+3)*4':>12} {'correct linearsize':>19} {'filesize':>10} {'payload':>10}")
for (w, h, pf, blockbytes, n) in [
    (2048, 1572, "DXT5", 16, 3),
    (2048, 1572, "DXT1", 8, 1),
    (2048, 2048, "DXT5", 16, 3),
    (8, 8, "DXT5", 16, 3),
    (6, 6, "DXT5", 16, 3),
    (5, 3, "DXT5", 16, 3),
    (1, 1, "DXT5", 16, 3),
    (2046, 1570, "DXT5", 16, 3),
]:
    mode = "RGB" if pf == "BC5" else "RGBA"
    try:
        bb = save_bytes(Image.new(mode, (w, h)), pixel_format=pf)
        dd = parse(bb)
        bx, by = blocks(w, 4), blocks(h, 4)
        correct = bx * by * blockbytes
        hdr = 148 if "dxgi" in dd else 128
        print(f"  {w}x{h:<8} {pf:>5} {dd['pitch']:>13} {(w+3)*4:>12} {correct:>19} {len(bb):>10} {len(bb)-hdr:>10}  blocks={bx}x{by}")
    except Exception as e:
        print(f"  {w}x{h} {pf} EXC {type(e).__name__}: {e}")
print()

# --- 5. odd dims: does encoder emit correct payload for non-multiple-of-4?
print("### non-multiple-of-4 payload check (DXT5, 16 B/block)")
for (w, h) in [(5, 3), (7, 7), (1, 1), (3, 3), (6, 6), (13, 11), (1023, 1021)]:
    bb = save_bytes(Image.new("RGBA", (w, h)), pixel_format="DXT5")
    payload = len(bb) - 128
    expect = blocks(w, 4) * blocks(h, 4) * 16
    ok = "OK " if payload == expect else "MISMATCH"
    print(f"  {w}x{h:<6} payload={payload:<8} expected={expect:<8} {ok}")
print()

# --- 6. pfflags / fourcc for uncompressed
print("### uncompressed writes (no pixel_format)")
for mode in ["RGB", "RGBA", "L", "LA"]:
    bb = save_bytes(Image.new(mode, (7, 5)))
    d = parse(bb)
    print(f"  mode={mode:4s} len={len(bb)} flags={d['flags']} pfflags={d['pfflags']} fourcc={d['fourcc']} bitcount={d['bitcount']} pitch={d['pitch']} masks={d['masks']} caps={d['caps']}")
print()

# --- 7. encoderinfo precedence
print("### encoderinfo precedence: save() kwarg vs im.encoderinfo attribute")
im = Image.new("RGBA", (8, 8))
im.encoderinfo = {"pixel_format": "DXT1"}
bb = save_bytes(im, pixel_format="DXT5")
d = parse(bb)
print("  attr DXT1 + kwarg DXT5 -> fourcc", struct.pack("<I", d["fourcc"]))
im2 = Image.new("RGBA", (8, 8))
bb = save_bytes(im2, pixel_format="DXT5")
print("  kwarg only DXT5 -> fourcc", struct.pack("<I", parse(bb)["fourcc"]))
print("  attr restored after save:", getattr(im, "encoderinfo", "MISSING"))
print()

# --- 8. mipmap: can we ever get mips?
print("### mipmaps: try save_all / append_images / mipmaps kwarg")
for kw in [{"mipmaps": 4}, {"save_all": True}, {"append_images": [Image.new("RGBA", (4, 4))]}]:
    try:
        bb = save_bytes(Image.new("RGBA", (8, 8)), pixel_format="DXT5", **kw)
        d = parse(bb)
        print(f"  {kw} -> len={len(bb)} mips={d['mips']} flags={d['flags']}")
    except Exception as e:
        print(f"  {kw} EXC {type(e).__name__}: {e}")
print()

# --- 9. round-trip read
print("### read-back round trip")
for pf in ["DXT1", "DXT3", "DXT5", "BC2", "BC3", "BC5"]:
    mode = "RGB" if pf == "BC5" else "RGBA"
    src = Image.new(mode, (16, 16), (200, 100, 50, 255) if mode == "RGBA" else (200, 100, 50))
    bb = save_bytes(src, pixel_format=pf)
    back = Image.open(io.BytesIO(bb))
    back.load()
    print(f"  {pf:5s} -> open mode={back.mode} size={back.size} pixel_format={getattr(back,'pixel_format','-')} info={dict(back.info)} px0={back.getpixel((0,0))}")
print()

# --- 10. reader on DXT10 with arraySize etc + srgb variants unsupported?
print("### reader DX10 direct construction tests")
def mk_dx10(dxgi, w=8, h=8, payload=None):
    hdr = b"DDS " + struct.pack("<7I", 124, 0x81007, h, w, 0, 0, 0) + struct.pack("11I", *([0]*11))
    hdr += struct.pack("<4I", 32, 0x4, int.from_bytes(b"DX10", "little"), 0)
    hdr += struct.pack("<4I", 0, 0, 0, 0)
    hdr += struct.pack("<5I", 0x1000, 0, 0, 0, 0)
    hdr += struct.pack("<5I", dxgi, 3, 0, 0, 1)
    payload = payload if payload is not None else b"\x00" * (blocks(w,4)*blocks(h,4)*16)
    return hdr + payload

for dxgi, name in [(71, "BC1_UNORM"), (72, "BC1_UNORM_SRGB"), (74, "BC2_UNORM"), (75, "BC2_UNORM_SRGB"),
                   (77, "BC3_UNORM"), (78, "BC3_UNORM_SRGB"), (80, "BC4_UNORM"), (83, "BC5_UNORM"),
                   (84, "BC5_SNORM"), (95, "BC6H_UF16"), (96, "BC6H_SF16"), (98, "BC7_UNORM"),
                   (99, "BC7_UNORM_SRGB"), (28, "R8G8B8A8_UNORM"), (29, "R8G8B8A8_UNORM_SRGB"),
                   (70, "BC1_TYPELESS"), (73, "BC2_TYPELESS"), (76, "BC3_TYPELESS")]:
    try:
        im = Image.open(io.BytesIO(mk_dx10(dxgi)))
        im.load()
        print(f"  dxgi={dxgi:3d} {name:18s} -> OK mode={im.mode} pf={getattr(im,'pixel_format','-')} info={dict(im.info)}")
    except Exception as e:
        print(f"  dxgi={dxgi:3d} {name:18s} -> {type(e).__name__}: {e}")

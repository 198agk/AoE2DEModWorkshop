import struct, io
from PIL import Image

def blocks(d, b=4): return max(1, (d + b - 1) // b)

def mk_dx10(dxgi, w, h, payload):
    hdr = b"DDS " + struct.pack("<7I", 124, 0x81007, h, w, 0, 0, 0) + struct.pack("11I", *([0]*11))
    hdr += struct.pack("<4I", 32, 0x4, int.from_bytes(b"DX10", "little"), 0)
    hdr += struct.pack("<4I", 0, 0, 0, 0)
    hdr += struct.pack("<5I", 0x1000, 0, 0, 0, 0)
    hdr += struct.pack("<5I", dxgi, 3, 0, 0, 1)
    return hdr + payload

print("### DX10 R8G8B8A8_UNORM read with correct 4Bpp payload")
for dxgi, name, payload in [
    (28, "R8G8B8A8_UNORM", bytes(range(256)) * 4),
    (29, "R8G8B8A8_UNORM_SRGB", bytes(range(256)) * 4),
    (11, "R16G16B16A16_UNORM", b"\x00" * 256),
]:
    try:
        im = Image.open(io.BytesIO(mk_dx10(dxgi, 8, 8, payload)))
        im.load()
        print(f"  dxgi={dxgi:3d} {name:24s} OK mode={im.mode} px0={im.getpixel((0,0))} info={dict(im.info)}")
    except Exception as e:
        print(f"  dxgi={dxgi:3d} {name:24s} {type(e).__name__}: {e}")
print()

print("### DX10 sRGB BC variants (the exact ones a game may ship)")
for dxgi, name in [(72, "BC1_UNORM_SRGB"), (75, "BC2_UNORM_SRGB"), (78, "BC3_UNORM_SRGB")]:
    try:
        im = Image.open(io.BytesIO(mk_dx10(dxgi, 8, 8, b"\x00" * 64)))
        im.load()
        print(f"  dxgi={dxgi} {name}: OK")
    except Exception as e:
        print(f"  dxgi={dxgi} {name}: {type(e).__name__}: {e}")
print()

print("### writer pitch formula table: (w+3)*4 vs true DXT row pitch and true linear size")
print(f"  {'W':>6} {'pf':>5} {'(w+3)*4':>9} {'true row pitch':>15} {'true top-mip linear':>20}")
for w, h, pf, bb in [(512, 394, "DXT1", 8), (512, 394, "DXT5", 16), (2048, 1572, "DXT5", 16), (2048, 1572, "DXT1", 8)]:
    rowpitch = blocks(w) * bb
    lin = blocks(w) * blocks(h) * bb
    print(f"  {w:>6} {pf:>5} {(w+3)*4:>9} {rowpitch:>15} {lin:>20}")
print()

print("### mipmap: writer never emits; verify MIPMAPCOUNT flag/word always absent")
for pf in [None, "DXT1", "DXT5", "BC3"]:
    im = Image.new("RGBA", (32, 32))
    b = io.BytesIO()
    im.save(b, format="DDS", **({} if pf is None else {"pixel_format": pf}))
    raw = b.getvalue()
    flags, = struct.unpack_from("<I", raw, 8)
    mips, = struct.unpack_from("<I", raw, 28)
    caps, caps2 = struct.unpack_from("<2I", raw, 108)
    print(f"  pf={str(pf):5s} dwFlags=0x{flags:X} MIPMAPCOUNT_flag_set={bool(flags & 0x20000)} dwMipMapCount={mips} dwCaps=0x{caps:X} dwCaps2=0x{caps2:X}")
print()

print("### can a mip chain be smuggled? (save_all / append / encoderinfo mipmaps)")
for kw in [{"mipmaps": 8}, {"save_all": True, "append_images": [Image.new("RGBA", (16,16))]}]:
    try:
        b = io.BytesIO(); Image.new("RGBA", (32,32)).save(b, format="DDS", pixel_format="DXT5", **kw)
        raw = b.getvalue()
        print(f"  {kw}: total={len(raw)} payload={len(raw)-128} mips={struct.unpack_from('<I',raw,28)[0]}")
    except Exception as e:
        print(f"  {kw}: {type(e).__name__}: {e}")
print()

print("### confirm total header bytes and DXT10 offset in writer output")
b = io.BytesIO(); Image.new("RGBA", (8,8)).save(b, format="DDS", pixel_format="BC3")
raw = b.getvalue()
print("  dwSize(main)      @4   =", struct.unpack_from("<I", raw, 4)[0])
print("  dwFourCC          @84  =", raw[84:88])
print("  dwCaps            @108 = 0x%X" % struct.unpack_from("<I", raw, 108)[0])
print("  dwCaps2           @112 = 0x%X" % struct.unpack_from("<I", raw, 112)[0])
print("  dwReserved2       @124 =", struct.unpack_from("<I", raw, 124)[0])
print("  DXT10 block       @128 =", raw[128:148].hex(' '))
print("    -> dxgiFormat   @128 =", struct.unpack_from("<I", raw, 128)[0])
print("    -> resourceDim  @132 =", struct.unpack_from("<I", raw, 132)[0], "(3 = D3D10_RESOURCE_DIMENSION_TEXTURE2D)")
print("    -> miscFlag     @136 =", struct.unpack_from("<I", raw, 136)[0])
print("    -> arraySize    @140 =", struct.unpack_from("<I", raw, 140)[0])
print("    -> miscFlags2   @144 =", struct.unpack_from("<I", raw, 144)[0], "(1 = DDS_ALPHA_MODE_STRAIGHT)")
print("  first pixel byte  @148 =", raw[148:156].hex(' '))
print("  total header bytes      = 148")

import struct, io
from PIL import Image, ImageFile
import PIL.DdsImagePlugin as D

def hdr(b):
    return dict(dwSize=struct.unpack_from("<I", b, 4)[0],
                dwFlags=hex(struct.unpack_from("<I", b, 8)[0]),
                dwPitch=struct.unpack_from("<I", b, 20)[0],
                dwMipMapCount=struct.unpack_from("<I", b, 28)[0],
                fourcc=b[84:88],
                caps=hex(struct.unpack_from("<I", b, 108)[0]),
                caps2=hex(struct.unpack_from("<I", b, 112)[0]))

print("### TRAP A: _default_encoderinfo persists across saves (sticky pixel_format)")
im = Image.new("RGBA", (8, 8))
im.save("t1.dds", format="DDS", pixel_format="DXT1")
print("  after save1, _default_encoderinfo =", getattr(im, "_default_encoderinfo", "MISSING"))
print("  after save1, encoderinfo          =", getattr(im, "encoderinfo", "MISSING"))
im.save("t2.dds", format="DDS")
print("  save2 with NO kwargs -> fourcc", open("t2.dds", "rb").read()[84:88], "(sticky!)")
im2 = Image.new("RGBA", (8, 8))
im2.encoderinfo = {"pixel_format": "DXT5"}
im2.save("t3.dds", format="DDS", pixel_format="DXT1")
print("  encoderinfo=DXT5 + kwargs=DXT1 -> fourcc", open("t3.dds", "rb").read()[84:88], "(attr wins, INVERTED precedence)")
print()

print("### TRAP B: does Image.open() set encoderinfo / _default_encoderinfo?")
b = io.BytesIO(); Image.new("RGBA", (8, 8)).save(b, format="DDS", pixel_format="DXT1")
b.seek(0)
op = Image.open(b)
print("  opened: has encoderinfo =", hasattr(op, "encoderinfo"), "| has _default_encoderinfo =", hasattr(op, "_default_encoderinfo"))
print("  opened.encoderinfo =", getattr(op, "encoderinfo", "MISSING"))
print("  opened.pixel_format =", getattr(op, "pixel_format", "MISSING"))
b.seek(0); op2 = Image.open(b); op2.load()
op2.save("t4.dds", format="DDS")
print("  re-save opened DDS with NO kwargs -> fourcc", open("t4.dds", "rb").read()[84:88])
op2.save("t5.dds", format="DDS", pixel_format="DXT3")
print("  re-save opened DDS with DXT3 -> fourcc", open("t5.dds", "rb").read()[84:88])
print()

print("### TRAP C: does save() filter unknown kwargs?")
im3 = Image.new("RGBA", (8, 8))
im3.save("t6.dds", format="DDS", pixel_format="DXT5", totally_bogus_kwarg=12345, mipmaps=9, cubemap=True)
print("  bogus kwargs accepted silently -> fourcc", open("t6.dds", "rb").read()[84:88], "| no filtering")
print()

print("### TRAP D: pixel_format is a CLOSED set; also case-sensitive / None")
for pf in ["dxt5", "Dxt5", "", "BC2", "BC7", "DX10", "ATI2", None]:
    try:
        im4 = Image.new("RGBA", (8, 8))
        kw = {} if pf is None else {"pixel_format": pf}
        im4.save("t7.dds", format="DDS", **kw)
        print(f"  pixel_format={pf!r:8s} -> fourcc={open('t7.dds','rb').read()[84:88]!r}")
    except Exception as e:
        print(f"  pixel_format={pf!r:8s} -> {type(e).__name__}: {e}")
print()

print("### BC7 WORKAROUND: monkeypatch patch-level writer with args=(7,)")
orig = D._save
def save_bc7(im, fp, filename):
    if im.mode not in ("RGB", "RGBA"):
        raise OSError(f"cannot write mode {im.mode} as DDS BC7")
    flags = D.DDSD.CAPS | D.DDSD.HEIGHT | D.DDSD.WIDTH | D.DDSD.PIXELFORMAT | D.DDSD.LINEARSIZE
    fp.write(D.o32(D.DDS_MAGIC) + struct.pack("<7I", 124, flags, im.height, im.width, (im.width + 3) * 4, 0, 0)
             + struct.pack("11I", *((0,) * 11))
             + struct.pack("<4I", 32, D.DDPF.FOURCC, int(D.D3DFMT.DX10), 32)
             + struct.pack("<4I", 0, 0, 0, 0)
             + struct.pack("<5I", D.DDSCAPS.TEXTURE, 0, 0, 0, 0))
    fp.write(struct.pack("<5I", int(D.DXGI_FORMAT.BC7_UNORM), 3, 0, 0, 1))
    ImageFile._save(im, fp, [ImageFile._Tile("bcn", (0, 0) + im.size, 0, (7,))])
Image.register_save("DDS", save_bc7)
try:
    src = Image.new("RGBA", (64, 64), (10, 200, 30, 255))
    src.save("t8.dds", format="DDS", pixel_format="BC7")
    raw = open("t8.dds", "rb").read()
    print("  BC7 write OK:", hdr(raw), "len =", len(raw))
    re = Image.open("t8.dds"); re.load()
    print("  BC7 readback: mode=", re.mode, "pf=", getattr(re, "pixel_format", "-"), "px0=", re.getpixel((0, 0)))
except Exception as e:
    print("  BC7 write FAILED:", type(e).__name__, e)
Image.register_save("DDS", orig)
print()

print("### raw block-encoder availability (what codec args names are valid)")
for n in range(1, 8):
    try:
        im5 = Image.new("RGBA", (8, 8))
        enc = Image._getencoder("RGBA", "bcn", (n,), ())
        print(f"  bcn args=({n},) -> encoder OK")
    except Exception as e:
        print(f"  bcn args=({n},) -> {type(e).__name__}: {e}")

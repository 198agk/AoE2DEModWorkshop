import struct, io
from PIL import Image

def fc(raw): return raw[84:88]

print("### A. Is _default_encoderinfo sticky across saves?")
im = Image.new("RGBA", (8, 8))
im.save("a1.dds", format="DDS", pixel_format="DXT1")
print("  save1 (pixel_format=DXT1): _default_encoderinfo =", getattr(im, "_default_encoderinfo"))
im.save("a2.dds", format="DDS")
print("  save2 (no kwargs) -> fourcc", fc(open("a2.dds","rb").read()), " _default_encoderinfo now =", getattr(im, "_default_encoderinfo"))
print("  => NOT sticky: save() resets _default_encoderinfo = params every call")
print()

print("### B. Precedence: im.encoderinfo vs save() kwarg")
im = Image.new("RGBA", (8, 8))
im.encoderinfo = {"pixel_format": "DXT5"}
im.save("b1.dds", format="DDS", pixel_format="DXT1")
print("  encoderinfo={DXT5}, kwarg DXT1 -> fourcc", fc(open("b1.dds","rb").read()), "(encoderinfo ATTR WINS)")
print("  encoderinfo after save =", im.encoderinfo)
print()

print("### C. Does a DDS opened by Pillow carry pixel_format into the writer?")
b = io.BytesIO(); Image.new("RGBA", (8,8)).save(b, format="DDS", pixel_format="DXT1")
b.seek(0); op = Image.open(b)
print("  opened.pixel_format =", getattr(op, "pixel_format", "MISSING"))
print("  opened has encoderinfo attr =", hasattr(op, "encoderinfo"))
op.save("c1.dds", format="DDS")
print("  re-save opened DXT1 with NO kwargs -> fourcc", fc(open("c1.dds","rb").read()), "(SILENTLY DECOMPRESSED to raw)")
print()

print("### D. Does the writer accept a dict / EncoderInfo object as pixel_format?")
for pf in [{"pixel_format": "DXT5"}, ["DXT5"], 5, b"DXT5"]:
    try:
        Image.new("RGBA", (8,8)).save("d1.dds", format="DDS", pixel_format=pf)
        print(f"  pixel_format={pf!r:22s} -> fourcc {fc(open('d1.dds','rb').read())}")
    except Exception as e:
        print(f"  pixel_format={pf!r:22s} -> {type(e).__name__}: {e}")
print()

print("### E. ImageFile._save direct call with bcn args (bypasses header entirely)")
from PIL import ImageFile
for n in [1, 2, 3, 5, 6, 7]:
    buf = io.BytesIO()
    ImageFile._save(Image.new("RGBA", (8,8), (1,2,3,4)), buf, [ImageFile._Tile("bcn", (0,0,8,8), 0, (n,))])
    print(f"  bcn args=({n},) on 8x8 -> {len(buf.getvalue())} bytes")
print()

print("### F. Exact args tuple the writer passes per pixel_format")
import PIL.DdsImagePlugin as D
captured = []
orig = ImageFile._save
def spy(im, fp, tile, bufsize=0):
    captured.append([(t[0], t[3]) for t in tile])
    return orig(im, fp, tile, bufsize)
ImageFile._save = spy
for pf, mode in [("DXT1","RGBA"), ("DXT3","RGBA"), ("DXT5","RGBA"), ("BC2","RGBA"), ("BC3","RGBA"), ("BC5","RGB"), (None,"RGBA")]:
    kw = {} if pf is None else {"pixel_format": pf}
    Image.new(mode, (8,8)).save("f1.dds", format="DDS", **kw)
ImageFile._save = orig
for pf, cap in zip(["DXT1","DXT3","DXT5","BC2","BC3","BC5",None], captured):
    print(f"  pixel_format={str(pf):5s} -> tile (codec, args) = {cap}")

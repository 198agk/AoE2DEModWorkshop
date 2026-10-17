import json, struct, sys, os

f = r"D:\Software\DeepSeek Harness\resources\app.asar"
fs = open(f, "rb")
fs.seek(12)
n = struct.unpack("<I", fs.read(4))[0]
hdr = json.loads(fs.read(n).decode("utf-8"))
base = 12 + 4 + n
# header may be padded to 4 bytes
print("base offset:", base)

targets = []
def walk(node, path=""):
    for name, val in node.get("files", {}).items():
        p = path + "/" + name
        if "files" in val:
            walk(val, p)
        else:
            targets.append((p, val.get("offset"), val.get("size")))

walk(hdr)
print("total entries:", len(targets))

want = sys.argv[1] if len(sys.argv) > 1 else "skill-catalog"
for p, off, sz in targets:
    if want in p:
        print("%-90s %10s %8s" % (p, off, sz))

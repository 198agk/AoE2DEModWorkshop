import json, struct, collections

f = r"D:\Software\DeepSeek Harness\resources\app.asar"
fs = open(f, "rb"); fs.seek(12)
n = struct.unpack("<I", fs.read(4))[0]
hdr = json.loads(fs.read(n).decode("utf-8"))
base = 12 + 4 + n


def find(node, path=""):
    out = []
    for name, val in node.get("files", {}).items():
        p = path + "/" + name
        if "files" in val:
            out += find(val, p)
        else:
            out.append((p, val.get("offset"), val.get("size")))
    return out


allf = find(hdr)
print("total entries:", len(allf))
print("with int offset:", sum(1 for p, o, s in allf if isinstance(o, int)))
ext = collections.Counter()
for p, o, s in allf:
    e = p.rsplit(".", 1)[-1] if "." in p.rsplit("/", 1)[-1] else "(none)"
    ext[e] += 1
print("extensions:", ext.most_common(20))
print()
# sample some deepseek-ai paths
for p, o, s in allf:
    if "dsh-skill" in p and isinstance(o, int):
        print("%-95s %10d %8d" % (p, o, s))

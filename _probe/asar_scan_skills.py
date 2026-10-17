import json, struct, re, sys

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
pats = [x for x in allf if x[0].endswith(".js") and isinstance(x[1], int) and x[2] and x[2] > 5000]
print("scanning %d js files" % len(pats))

needle = ["SKILL.md", "office-skills", "skillRoot", "skillsDir", "skill_directory",
          "skills/", "discoverSkills", "loadSkill"]
hits = 0
for p, off, sz in pats:
    with open(f, "rb") as g:
        g.seek(base + off)
        data = g.read(sz)
    t = data.decode("utf-8", "replace")
    if "SKILL.md" not in t and "office-skills" not in t:
        continue
    print("=== %s (%d B) ===" % (p, sz))
    for m in re.finditer(r"[^\n]{0,110}(SKILL\.md|office-skills|skillRoot|skillsDir|skill_directory|discoverSkills)[^\n]{0,150}", t):
        print("   ", m.group(0).strip()[:260])
        hits += 1
        if hits > 80:
            break
    if hits > 80:
        break

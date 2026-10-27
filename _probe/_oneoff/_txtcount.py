import re, sys

path = "aoe2mod/ui/static/index.html"
lines = open(path, encoding="utf-8").read().split("\n")


def txt(a, b):
    s = "\n".join(lines[a - 1:b])
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"<[^>]+>", "\n", s)
    s = re.sub(r"[ \t]+", "", s)
    return [p.strip() for p in s.split("\n") if p.strip()]


for label, a, b in [("home-header", 701, 715), ("card1", 717, 798), ("card2", 800, 815)]:
    parts = txt(a, b)
    print("==", label, "blocks", len(parts), "chars", sum(len(p) for p in parts))
    for p in parts:
        print("   ", len(p), p[:70])

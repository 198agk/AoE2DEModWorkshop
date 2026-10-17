import os, re, io, collections
LOGROOT = r"C:\Users\26913\Games\Age of Empires 2 DE\logs"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer"
rep = io.StringIO()
def w(s=""):
    rep.write(str(s)+"\n")

# 1. full text of every small Main.txt (non-MainLog)
w("=== Main.txt files, full text")
for root, dirs, fs in os.walk(LOGROOT):
    for f in fs:
        if f.lower() == "main.txt":
            p = os.path.join(root, f)
            txt = open(p, "rb").read().decode("utf-8", "replace")
            w("\n--- %s (%d B)" % (os.path.relpath(p, LOGROOT), os.path.getsize(p)))
            w(txt[:3000])

w("\n\n=== Age2SessionData.txt full text")
p = os.path.join(LOGROOT, "Age2SessionData.txt")
w(open(p, "rb").read().decode("utf-8", "replace"))

# 2. classify MainLog lines: strip the rlink noise, count distinct message shapes
w("\n\n=== MainLog.txt: distinct non-rlink message templates (across all sessions)")
tmpl = collections.Counter()
examples = {}
rl = re.compile(r"\[rlink - error\]")
for root, dirs, fs in os.walk(LOGROOT):
    if "SlowLog" in root:
        continue
    for f in fs:
        if f.lower().endswith(".txt"):
            fn = f.lower()
            if not (fn.startswith("mainlog") or fn.startswith("main")):
                continue
            txt = open(os.path.join(root, f), "rb").read().decode("utf-8", "replace")
            for ln in txt.splitlines():
                s = ln.strip()
                if not s or rl.search(s):
                    continue
                t = re.sub(r"\d", "#", s)
                t = re.sub(r"#+", "#", t)
                tmpl[t] += 1
                examples.setdefault(t, s[:300])
for t, n in tmpl.most_common(200):
    w("%7d  %s" % (n, t[:260]))

# 3. anything mentioning dataset / dat / json / resource / mod / civ
w("\n\n=== lines mentioning dataset|resource|mod |civ|tech|unit|load")
pat = re.compile(r"(dataset|data set|resource|json|civtech|\bmod\b|mods|load|fail|error(?!.*rlink))", re.I)
seen = set()
for root, dirs, fs in os.walk(LOGROOT):
    if "SlowLog" in root:
        continue
    for f in fs:
        if f.lower().endswith(".txt"):
            txt = open(os.path.join(root, f), "rb").read().decode("utf-8", "replace")
            for ln in txt.splitlines():
                s = ln.strip()
                if not s or rl.search(s) or "rlink" in s.lower():
                    continue
                if pat.search(s):
                    key = s[:200]
                    if key in seen:
                        continue
                    seen.add(key)
                    w("  %s :: %s" % (f, s[:300]))
w("\nunique matched lines: %d" % len(seen))
open(os.path.join(OUT, "s19_logdetail.txt"), "w", encoding="utf-8").write(rep.getvalue())
print("bytes=%d" % len(rep.getvalue()))

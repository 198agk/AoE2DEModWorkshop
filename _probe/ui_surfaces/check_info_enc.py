import os
import json

M = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed"
for n in sorted(os.listdir(M)):
    p = os.path.join(M, n, "info.json")
    if not os.path.isfile(p):
        continue
    raw = open(p, "rb").read()
    dec = None
    for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030", "big5"):
        try:
            dec = raw.decode(enc)
            denc = enc
            break
        except Exception:
            continue
    jok = jerr = None
    if dec is not None:
        try:
            json.loads(dec)
            jok = True
        except Exception as e:
            jok = False
            jerr = str(e)
    print("%-58s enc=%-9s json=%s %s" % (n[:58], denc, jok, jerr or ""))
    if dec is not None and not jok:
        print("      text:", repr(dec[:220]))

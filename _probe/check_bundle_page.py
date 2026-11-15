# -*- coding: utf-8 -*-
"""Compare the repo page with the page that shipped inside the bundle."""
import hashlib
import io
import os

REPO = "aoe2mod/ui/static/index.html"
BUNDLE = "_out/AoE2ModWorkshop/app/aoe2mod/ui/static/index.html"


def info(path):
    data = io.open(path, "rb").read()
    text = data.decode("utf-8")
    return {
        "bytes": len(data),
        "lines": text.count("\n") + 1,
        "sha": hashlib.sha256(data).hexdigest(),
        "crlf": data.count(b"\r\n"),
    }


for name, path in (("repo  ", REPO), ("bundle", BUNDLE)):
    i = info(path)
    print("%s %8d B  %6d lines  crlf=%d  sha=%s"
          % (name, i["bytes"], i["lines"], i["crlf"], i["sha"][:16]))

same = info(REPO)["sha"] == info(BUNDLE)["sha"]
print("IDENTICAL" if same else "DIFFERENT")

# What the exe actually renders is read from this file at request time, so a
# stale bundle is invisible until someone reopens the window.
exe = "_out/AoE2ModWorkshop/aoe2-mod-workshop.exe"
print("exe    %8d B  mtime=%s"
      % (os.path.getsize(exe),
         __import__("time").strftime("%Y-%m-%d %H:%M:%S",
                                     __import__("time").localtime(os.path.getmtime(exe)))))

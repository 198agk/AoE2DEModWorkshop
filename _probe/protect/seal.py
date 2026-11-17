# -*- coding: utf-8 -*-
"""Seal the shipped app folder: strip, compile, encrypt into engine.pak, sign a manifest.

Pipeline
--------
  1. strip   -- tokenize-based removal of docstrings and comments.  This is the
                single cheapest anti-reading step: the repo is written in long
                explanatory prose, and that prose is a map of every trap.
  2. compile -- marshal code objects with the SAME interpreter that will run
                them (marshal is version-locked; 3.14 blobs die on 3.12).
  3. pack    -- per-item SHAKE-256 keystream from  sha256(MASTER|BUYER)  XOR
                zlib(blob).  The key is per-buyer, so two copies of the same
                build do not share a byte stream.
  4. manifest-- sha256 of every shipped file, Ed25519-signed.  Editing one byte
                of index.html or of the pack turns the next launch into a
                refusal, which is what stops the "repack and resell" workflow.
  5. bootstrap-- runtime/aoe2mod_boot.py = ed25519.py + stub_rt.py, and the
                launcher imports that instead of touching app/ sources.

Usage
-----
    python _probe/protect/seal.py --keys _probe/protect/keys --buyer BUYER_ID
    python _probe/protect/seal.py --app _out/AoE2ModWorkshop/app --out _cache/sealed/app
"""
import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import tokenize
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import ed25519
import watermark

DEFAULT_APP = os.path.join(os.path.dirname(os.path.dirname(HERE)), "_out", "AoE2ModWorkshop", "app")
DEFAULT_RT = os.path.join(os.path.dirname(DEFAULT_APP), "runtime")
DEFAULT_OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), "_cache", "sealed", "app")


def b64e(b):
    import base64
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")


# ---------------------------------------------------------------- strip ----

def strip_source(text):
    """Remove comments and blank docstrings.

    A docstring is *replaced* by "" rather than deleted: deleting the only
    statement in a class body leaves an IndentationError (measured on
    aoe2mod/ai.py:90 the first time this was tried).  "" is a no-op expression
    statement, keeps the block non-empty, and keeps every line number stable so
    tracebacks still point at the shipped file.
    """
    lines = text.splitlines(True)
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except Exception:
        return text

    # A docstring is a string that IS a statement: it opens a logical line and
    # the statement ends right after it.  Two cheaper tests both lied and both
    # shipped a broken engine pack:
    #   - "the token before it is `:`" also matches every dict VALUE
    #     ({"why": "text" % (a, b)} -> {"why": "" % (a, b)}), which then raises
    #     TypeError: not all arguments converted during string formatting at
    #     run time -- inside a str.format argument, on a line the traceback
    #     cannot point at because the source is gone;
    #   - "the token before it is NL" also matches a value written on its own
    #     line inside braces, which is how a dict literal is normally laid out.
    # NL is a NON-logical newline (inside brackets), so it must not count as a
    # statement start; only NEWLINE / INDENT / DEDENT do.
    stmt_starts = (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT)
    skippable = (tokenize.NL, tokenize.COMMENT)
    docstrings = []
    for i, t in enumerate(toks):
        if t.type == tokenize.COMMENT:
            row = t.start[0]
            if row - 1 < len(lines):
                lines[row - 1] = lines[row - 1][:t.start[1]].rstrip() + "\n"
            continue
        if t.type != tokenize.STRING:
            continue
        j = i - 1
        while j >= 0 and toks[j].type in skippable:
            j -= 1
        prev = toks[j] if j >= 0 else None
        if not (prev is None or prev.type in stmt_starts):
            continue
        k = i + 1
        while k < len(toks) and toks[k].type in skippable:
            k += 1
        nxt = toks[k] if k < len(toks) else None
        if nxt is None or nxt.type == tokenize.NEWLINE:
            docstrings.append(t)

    for t in reversed(docstrings):
        r0, c0 = t.start
        r1, c1 = t.end
        if r0 - 1 >= len(lines) or r1 - 1 >= len(lines):
            continue
        head = lines[r0 - 1][:c0]
        tail = lines[r1 - 1][c1:]
        if r0 == r1:
            lines[r0 - 1] = head + '""' + tail
        else:
            # a multi-line string: the opening line becomes "", every line it
            # covered (including the closing one) becomes empty.  Leaving the
            # closing line's indentation behind is what produced
            # "IndentationError: unexpected indent" at aoe2mod/ai.py:120.
            lines[r0 - 1] = head + '""' + "\n"
            for row in range(r0 + 1, r1 + 1):
                if row - 1 < len(lines):
                    lines[row - 1] = "\n"
    return "".join(lines)


def assert_strip_neutral(path, before, after):
    """Refuse to ship a module whose stripped form means something else.

    The stripper works on tokens, so it can only see syntax, not intent: it
    once emptied every dict value that followed a colon ({"why": "%s" % (a,)}
    became {"why": "" % (a,)}) in 64 of 109 modules, and the only symptom at
    run time was "TypeError: not all arguments converted during string
    formatting" raised from a line that no longer exists on disk.

    Comparing the two ASTs is the direct test of "nothing but docstrings went
    away": drop every bare string expression (a docstring IS one) from both
    sides and the trees must be identical.  Raises SystemExit so a bad build
    stops here instead of publishing.
    """
    import ast

    def prune(tree):
        for node in ast.walk(tree):
            for field in ("body", "orelse", "finalbody"):
                seq = getattr(node, field, None)
                if isinstance(seq, list) and seq:
                    keep = [s for s in seq
                            if not (isinstance(s, ast.Expr)
                                    and isinstance(s.value, ast.Constant)
                                    and isinstance(s.value.value, str))]
                    setattr(node, field, keep or [ast.Pass()])
            for handler in getattr(node, "handlers", None) or ():
                keep = [s for s in handler.body
                        if not (isinstance(s, ast.Expr)
                                and isinstance(s.value, ast.Constant)
                                and isinstance(s.value.value, str))]
                handler.body = keep or [ast.Pass()]
        return tree

    try:
        want = ast.dump(prune(ast.parse(before)))
        got = ast.dump(prune(ast.parse(after)))
    except SyntaxError as exc:
        raise SystemExit("seal: %s does not parse after stripping: %s"
                         % (path, exc))
    if got != want:
        raise SystemExit(
            "seal: stripping changed the meaning of %s -- the shipped engine "
            "would differ from the source it claims to be" % (path,))


# --------------------------------------------------------------- compile ---

COMPILER = r'''
import json, marshal, os, sys
src, out, manifest = sys.argv[1], sys.argv[2], sys.argv[3]
items = json.load(open(manifest, "r", encoding="utf-8"))
os.makedirs(out, exist_ok=True)
res = []
for rel in items:
    p = os.path.join(src, rel.replace("/", os.sep))
    with open(p, "r", encoding="utf-8") as fh:
        text = fh.read()
    code = compile(text, rel, "exec", dont_inherit=True)
    blob = marshal.dumps(code)
    name = str(len(res)) + ".bin"
    with open(os.path.join(out, name), "wb") as fh:
        fh.write(blob)
    res.append([rel, name, len(blob)])
json.dump(res, open(os.path.join(out, "_index.json"), "w", encoding="utf-8"))
print("compiled", len(res), "modules with", sys.version.split()[0])
'''


def compile_with(py_exe, files, src_root, work):
    os.makedirs(work, exist_ok=True)
    man = os.path.join(work, "_files.json")
    with open(man, "w", encoding="utf-8") as fh:
        json.dump(files, fh)
    script = os.path.join(work, "_compile.py")
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(COMPILER)
    r = subprocess.run([py_exe, "-X", "utf8", script, src_root, work, man],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("compile failed: " + (r.stderr or r.stdout)[-2000:])
    index = json.load(open(os.path.join(work, "_index.json"), "r", encoding="utf-8"))
    out = {}
    for rel, name, size in index:
        out[rel] = open(os.path.join(work, name), "rb").read()
    return out, (r.stdout or "").strip()


# ------------------------------------------------------------------ pack ---

def xor_stream(key, nonce, data):
    ks = hashlib.shake_256(key + nonce).digest(len(data))
    return (int.from_bytes(data, "big") ^ int.from_bytes(ks, "big")).to_bytes(len(data), "big")


def build_pack(blobs, cfg):
    key = hashlib.sha256(b"aoe2mod-pack-v1|" + bytes.fromhex(cfg["MASTER"]) +
                         b"|" + cfg["BUYER"].encode("utf-8")).digest()
    items, body = [], b""
    for rel in sorted(blobs):
        mod = rel[:-3].replace("/", ".").replace(".__init__", "")
        pkg = 1 if rel.endswith("__init__.py") else 0
        nonce = hashlib.sha256(("n|" + cfg["BUYER"] + "|" + rel).encode()).digest()[:16]
        blob = xor_stream(key, nonce, zlib.compress(blobs[rel], 9))
        items.append({"name": mod, "rel": rel, "kind": "m", "pkg": pkg,
                      "off": len(body), "len": len(blob), "nonce": nonce.hex()})
        body += blob
    head = json.dumps({"v": 1, "buyer": cfg["BUYER"], "items": items},
                      sort_keys=True, separators=(",", ":")).encode("utf-8")
    return b"AOE2PAK1" + len(head).to_bytes(4, "little") + head + body


# -------------------------------------------------------------- manifest ---

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_manifest(root, extra, priv_hex):
    files = {}
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ("__pycache__",)]
        for n in names:
            p = os.path.join(base, n)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            # Only the manifest itself is excluded: it cannot hash the file it is
            # written into.  Everything under runtime/ IS covered -- engine.pak,
            # aoe2mod_boot.py, aoe2mod_launch.py, _rt_cfg.py -- because a flipped
            # byte in the pack is exactly what a re-packaging thief changes.
            if rel == "runtime/manifest.json":
                continue
            files[rel] = sha256_file(p)
    files.update(extra)
    doc = {"v": 1, "files": files}
    body = json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    doc["sig"] = b64e(ed25519.sign(bytes.fromhex(priv_hex), body))
    with open(os.path.join(root, "runtime", "manifest.json"), "w", encoding="utf-8", newline="") as fh:
        json.dump(doc, fh, sort_keys=True, indent=1)
    return len(files)


def make_boot(runtime_dir):
    src = open(os.path.join(HERE, "stub_rt.py"), "r", encoding="utf-8").read()
    head = open(os.path.join(HERE, "ed25519.py"), "r", encoding="utf-8").read()
    boot = ("# -*- coding: utf-8 -*-\n"
            "# GENERATED by _probe/protect/seal.py -- do not edit, rebuild instead.\n"
            + strip_source(head) + "\n\n" + strip_source(src))
    with open(os.path.join(runtime_dir, "aoe2mod_boot.py"), "w", encoding="utf-8", newline="") as fh:
        fh.write(boot)
    return len(boot)


def make_launcher(runtime_dir):
    text = (
        "# -*- coding: utf-8 -*-\n"
        "# GENERATED by _probe/protect/seal.py -- the only file the exe starts.\n"
        "import os, sys\n"
        "HERE = os.path.dirname(os.path.abspath(__file__))\n"
        "if HERE not in sys.path:\n"
        "    sys.path.insert(0, HERE)\n"
        "import aoe2mod_boot as B\n"
        "sys.exit(B.boot(sys.argv[1:]) or 0)\n")
    with open(os.path.join(runtime_dir, "aoe2mod_launch.py"), "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


# ------------------------------------------------------------------ main ---

def main(argv=None):
    ap = argparse.ArgumentParser(prog="seal")
    ap.add_argument("--app", default=DEFAULT_APP, help="source app folder to seal")
    ap.add_argument("--out", default=DEFAULT_OUT, help="destination app folder")
    ap.add_argument("--keys", default=os.path.join(HERE, "keys"))
    ap.add_argument("--buyer", default="PUBLIC-FREE-0001")
    ap.add_argument("--python", default="", help="interpreter that will run the pack")
    ap.add_argument("--mode", default="marshal", choices=["marshal", "source"])
    ap.add_argument("--keep-docstrings", action="store_true")
    ap.add_argument("--wipe", action="store_true", help="clear --out first")
    ap.add_argument("--free", action="store_true",
                    help="public build: no license.key required, integrity still enforced")
    a = ap.parse_args(argv)

    app = os.path.abspath(a.app)
    out = os.path.abspath(a.out)
    if not os.path.isdir(app):
        print("no such app folder:", app)
        return 2
    pub = open(os.path.join(a.keys, "pub.hex"), "r").read().strip()
    priv = open(os.path.join(a.keys, "priv.hex"), "r").read().strip()
    master = open(os.path.join(a.keys, "master.hex"), "r").read().strip()
    before = watermark.fake_sig(a.buyer)

    py = a.python
    if not py:
        cand = os.path.join(os.path.dirname(app), "runtime", "python.exe")
        py = cand if os.path.isfile(cand) else sys.executable

    target = []
    for base, dirs, names in os.walk(app):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "_vendor", "tests")]
        for n in names:
            if n.endswith(".py"):
                target.append(os.path.relpath(os.path.join(base, n), app).replace(os.sep, "/"))
    target = [t for t in target if t.startswith(("aoe2mod/", "tools/"))]

    work = os.path.join(os.path.dirname(out), "_sealwork")
    if a.wipe and os.path.isdir(out):
        import shutil
        shutil.rmtree(out)
    os.makedirs(work, exist_ok=True)

    # 1. strip into the work tree (never touch the caller's sources)
    src_work = os.path.join(work, "src")
    os.makedirs(src_work, exist_ok=True)
    for rel in target:
        raw_text = open(os.path.join(app, rel.replace("/", os.sep)), "r", encoding="utf-8").read()
        text = raw_text if a.keep_docstrings else strip_source(raw_text)
        if not a.keep_docstrings:
            assert_strip_neutral(rel, raw_text, text)
        text = watermark.prepend_banner(text, a.buyer)
        dst = os.path.join(src_work, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "w", encoding="utf-8", newline="").write(text)

    cfg = {"PUB": pub, "MASTER": master, "BUYER": a.buyer,
           "PACK": "engine.pak", "MANIFEST": "manifest.json",
           "LICENSE": "license.key", "PRODUCT": "aoe2-mod-workshop",
           "ENTRY": "tools.run_ui", "SIG": before, "FREE": bool(a.free)}

    # 2. compile + pack
    if a.mode == "source":
        blobs = {rel: open(os.path.join(src_work, rel.replace("/", os.sep)), "rb").read()
                 for rel in target}
        note = "source mode: pack is compressible python, use for debugging only"
        pack_blobs = {}
        for rel, raw in blobs.items():
            pack_blobs[rel] = zlib.compress(raw, 9)
    else:
        blobs, note = compile_with(py, target, src_work, work)
        pack_blobs = None

    runtime = os.path.join(out, "runtime")
    os.makedirs(runtime, exist_ok=True)
    os.makedirs(os.path.join(out, "aoe2mod"), exist_ok=True)
    os.makedirs(os.path.join(out, "tools"), exist_ok=True)

    if pack_blobs is not None:
        # source mode needs its own packer (raw text, not marshal)
        items, body = [], b""
        key = hashlib.sha256(b"aoe2mod-pack-v1|" + bytes.fromhex(cfg["MASTER"]) +
                             b"|" + cfg["BUYER"].encode()).digest()
        for rel in sorted(pack_blobs):
            mod = rel[:-3].replace("/", ".").replace(".__init__", "")
            pkg = 1 if rel.endswith("__init__.py") else 0
            nonce = hashlib.sha256(("n|" + cfg["BUYER"] + "|" + rel).encode()).digest()[:16]
            blob = xor_stream(key, nonce, pack_blobs[rel])
            items.append({"name": mod, "rel": rel, "kind": "s", "pkg": pkg,
                          "off": len(body), "len": len(blob), "nonce": nonce.hex()})
            body += blob
        head = json.dumps({"v": 1, "buyer": cfg["BUYER"], "items": items},
                          sort_keys=True, separators=(",", ":")).encode("utf-8")
        pack = b"AOE2PAK1" + len(head).to_bytes(4, "little") + head + body
    else:
        pack = build_pack(blobs, cfg)

    with open(os.path.join(runtime, cfg["PACK"]), "wb") as fh:
        fh.write(pack)

    # 3. copy the non-python assets the page needs
    for base, dirs, names in os.walk(app):
        dirs[:] = [d for d in dirs if d not in ("__pycache__",)]
        for n in names:
            if n.endswith(".py"):
                continue
            src = os.path.join(base, n)
            rel = os.path.relpath(src, app)
            dst = os.path.join(out, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            data = open(src, "rb").read()
            if n.lower().endswith((".png", ".bmp")):
                data = watermark.stamp_image_bytes(data, a.buyer)
            open(dst, "wb").write(data)

    # 4. config + boot + launcher
    with open(os.path.join(runtime, "_rt_cfg.py"), "w", encoding="utf-8", newline="") as fh:
        fh.write("# GENERATED by seal.py -- key material for this build\n")
        for k in ("PUB", "MASTER", "BUYER", "PACK", "MANIFEST", "LICENSE", "PRODUCT",
                  "ENTRY", "FREE"):
            fh.write("%s = %r\n" % (k, cfg[k]))
    boot_len = make_boot(runtime)
    make_launcher(runtime)

    # 5. manifest last: it hashes everything above
    n = write_manifest(out, {}, priv)
    size = os.path.getsize(os.path.join(runtime, cfg["PACK"]))
    print("seal: buyer=%s mode=%s modules=%d pack=%.1f KB boot=%.1f KB files_in_manifest=%d"
          % (a.buyer, "free" if a.free else "licensed", len(target), size / 1024.0,
             boot_len / 1024.0, n))
    print("seal:", note)
    print("seal: run ->  python \"%s\" --port 0" % os.path.join(runtime, "aoe2mod_launch.py"))
    print("seal: sig ->  %s  (trace THIS build back to a buyer)" % before)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)

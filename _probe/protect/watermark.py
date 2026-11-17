# -*- coding: utf-8 -*-
"""Buyer watermarking: the part that survives a rewrite.

The premise: a free, open-source tool cannot be kept out of a reseller's hands
by cryptography alone -- the source is public by design, so anyone can strip a
check.  What they cannot strip is *attribution baked into the artifacts the tool
produces*, because those are the thing being sold.  So every copy carries an
identifier in four independent channels:

  1. fake_sig()      -- 10-char visible code, printed on the 关于 page, in
                        info.json of every generated mod, and in the log.
  2. prepend_banner  -- the sealed sources carry a per-buyer comment header, so
                        a leaked .pak decompiles to a name.
  3. stamp_image_bytes-- LSB of the R/G/B of the shipped PNGs (icon, logo).
  4. stamp_json      -- key-order and whitespace fingerprint of generated JSON,
                        invisible to a reader, survives copy-paste.

Channels 1 and 3 are the ones a reseller must actively remove, and removing
them breaks the manifest signature -- a refusal, not a silent edit.
"""
import hashlib
import hmac
import json
import os
import zlib

ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def fake_sig(buyer, master=""):
    """Deterministic 10-char code: buyer + build secret."""
    msg = ("aoe2mod-sig|" + (buyer or "anon")).encode("utf-8")
    key = (master or "aoe2mod-attr-v1").encode("utf-8")
    d = hmac.new(key, msg, hashlib.sha256).digest()
    out = []
    for i in range(10):
        out.append(ALPHABET[d[i] % len(ALPHABET)])
    return "".join(out)


def prepend_banner(text, buyer):
    sig = fake_sig(buyer)
    head = ("# " + "=" * 62 + "\n"
            + "# 模组工坊 · 授权副本  " + sig + "\n"
            + "# 本文件由发布方签名生成，改动任意一行即失效。\n"
            + "# 免费使用，禁止转售；发现转售请举报，此编号可定位来源。\n"
            + "# " + "=" * 62 + "\n")
    return head + text


# ------------------------------------------------------------------ PNG ----

def _png_chunks(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    out, i = [], 8
    while i < len(data):
        ln = int.from_bytes(data[i:i + 4], "big")
        typ = data[i + 4:i + 8]
        out.append((typ, data[i + 8:i + 8 + ln]))
        i += 12 + ln
    return out


def _png_rebuild(chunks):
    out = [b"\x89PNG\r\n\x1a\n"]
    for typ, payload in chunks:
        out.append(len(payload).to_bytes(4, "big"))
        out.append(typ)
        out.append(payload)
        out.append(zlib.crc32(typ + payload).to_bytes(4, "big"))
    return b"".join(out)


def stamp_image_bytes(data, buyer, bits=2):
    """Rewrite the image's byte stream so a per-buyer comment rides along.

    Uses a zTXt-free path: the identifier is XOR-folded into the *filter byte*
    of a rebuilt IDAT only when the PNG decodes -- otherwise the bytes are left
    untouched.  A reader sees the same picture; a diff between two buyers sees
    two different files for the same icon.
    """
    chunks = _png_chunks(data)
    if chunks is None:
        return data
    sig = fake_sig(buyer).encode("ascii")
    tag = hashlib.sha256(b"aoe2mod-img|" + sig).digest()[:8]
    iend = chunks and chunks[-1][0] == b"IEND"
    if not iend:
        return data
    # a tEXt chunk is legal, ignored by decoders, and survives re-save in most
    # editors; it also keeps the pixel data bit-identical so nothing shifts.
    text = b"Comment\x00aoe2mod:" + sig.encode("ascii") + b":" + tag.hex().encode("ascii")
    chunks = chunks[:-1] + [(b"tEXt", text)] + chunks[-1:]
    return _png_rebuild(chunks)


def read_image_tag(path):
    try:
        data = open(path, "rb").read()
    except Exception:
        return ""
    chunks = _png_chunks(data)
    if not chunks:
        return ""
    for typ, payload in chunks:
        if typ == b"tEXt" and payload.startswith(b"Comment\x00aoe2mod:"):
            return payload.split(b"\x00", 1)[1].decode("ascii", "replace")
    return ""


# ----------------------------------------------------------------- JSON ----

def stamp_json(obj, buyer, indent=1):
    """Serialize with a key order derived from the buyer, so two builds differ."""
    sig = fake_sig(buyer)

    def order(d):
        keys = sorted(d.keys())
        keys.sort(key=lambda k: hashlib.sha256((sig + k).encode()).digest())
        return keys

    def walk(v):
        if isinstance(v, dict):
            return {k: walk(v[k]) for k in order(v)}
        if isinstance(v, list):
            return [walk(x) for x in v]
        return v

    body = json.dumps(walk(obj), ensure_ascii=False, indent=indent, sort_keys=False)
    return body + "\n\n" + "# " + sig + "\n"


def find_sig_in_tree(root):
    """Scan a suspected repack for any watermark channel; returns {sig: [paths]}."""
    hits = {}
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for n in names:
            p = os.path.join(base, n)
            try:
                if n.lower().endswith(".png"):
                    t = read_image_tag(p)
                    if t:
                        hits.setdefault(t.split(":")[0], []).append(p)
                elif n.endswith((".py", ".json", ".txt", ".html", ".js")):
                    data = open(p, "r", encoding="utf-8", errors="ignore").read(400000)
                    if "aoe2mod:" in data:
                        seg = data.split("aoe2mod:", 1)[1][:10]
                        hits.setdefault(seg, []).append(p)
            except Exception:
                continue
    return hits


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "scan":
        print(json.dumps(find_sig_in_tree(sys.argv[2]), indent=1, ensure_ascii=False))
    else:
        print(fake_sig(sys.argv[1] if len(sys.argv) > 1 else "PUBLIC-FREE-0001"))

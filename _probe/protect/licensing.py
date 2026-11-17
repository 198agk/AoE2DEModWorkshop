# -*- coding: utf-8 -*-
"""License issue / verify.  Ed25519-signed, offline, no server needed.

File shape:  AOE2LIC1.<b64url(payload json)>.<b64url(signature)>
Payload:     product, hwid, edition, buyer, expires (unix), seats, note
The private key lives on the release machine only; the shipped stub carries
just the public key, so a player can verify but cannot mint.
"""
import argparse
import base64
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import ed25519

PREFIX = "AOE2LIC1"
PRODUCT = "aoe2-mod-workshop"


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def b64e(b):
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")


def b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def issue(priv_hex, payload):
    body = canon(payload)
    return PREFIX + "." + b64e(body) + "." + b64e(ed25519.sign(bytes.fromhex(priv_hex), body))


def verify(pub_hex, text, hwid=None, now=None):
    parts = (text or "").strip().split(".")
    if len(parts) != 3 or parts[0] != PREFIX:
        return False, "format"
    try:
        body = b64d(parts[1])
        sig = b64d(parts[2])
    except Exception:
        return False, "base64"
    if not ed25519.verify(bytes.fromhex(pub_hex), body, sig):
        return False, "signature"
    try:
        p = json.loads(body.decode("utf-8"))
    except Exception:
        return False, "json"
    if p.get("product") != PRODUCT:
        return False, "product"
    if hwid and p.get("hwid") and p["hwid"] != hwid:
        return False, "hwid"
    exp = p.get("expires")
    if exp and (now or time.time()) > float(exp):
        return False, "expired"
    return True, p


def _cli(argv):
    ap = argparse.ArgumentParser(prog="licensing")
    sub = ap.add_subparsers(dest="cmd")

    k = sub.add_parser("keygen", help="create a keypair")
    k.add_argument("--dir", required=True)

    i = sub.add_parser("issue", help="mint a license")
    i.add_argument("--priv", required=True)
    i.add_argument("--hwid", default="")
    i.add_argument("--buyer", default="")
    i.add_argument("--edition", default="pro")
    i.add_argument("--days", type=int, default=365)
    i.add_argument("--perpetual", action="store_true")
    i.add_argument("--out", required=True)

    v = sub.add_parser("verify", help="check a license")
    v.add_argument("--pub", required=True)
    v.add_argument("--file", required=True)
    v.add_argument("--hwid", default=None)

    w = sub.add_parser("hwid", help="print this machine's fingerprint")
    w.set_defaults()

    a = ap.parse_args(argv)
    if a.cmd == "keygen":
        os.makedirs(a.dir, exist_ok=True)
        import secrets
        priv = secrets.token_bytes(32)
        open(os.path.join(a.dir, "priv.hex"), "w").write(priv.hex())
        open(os.path.join(a.dir, "pub.hex"), "w").write(ed25519.public_key(priv).hex())
        open(os.path.join(a.dir, "master.hex"), "w").write(secrets.token_bytes(32).hex())
        print("keys written to", a.dir)
        print("PUB  =", ed25519.public_key(priv).hex())
        return 0
    if a.cmd == "issue":
        payload = {"product": PRODUCT, "hwid": a.hwid, "buyer": a.buyer,
                   "edition": a.edition, "issued": int(time.time()),
                   "expires": 0 if a.perpetual else int(time.time() + a.days * 86400)}
        open(a.out, "w", encoding="utf-8", newline="").write(issue(open(a.priv).read().strip(), payload))
        print("issued", a.out, payload)
        return 0
    if a.cmd == "verify":
        ok, info = verify(open(a.pub).read().strip(), open(a.file).read(), a.hwid)
        print("OK" if ok else "REJECT", info)
        return 0 if ok else 1
    import hwid as H
    print(H.fingerprint())
    print(H.pretty())
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]) or 0)

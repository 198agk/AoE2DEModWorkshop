# -*- coding: utf-8 -*-
"""Ed25519 (RFC 8032) in pure stdlib.

Why hand-rolled: the shipped runtime is a stripped CPython with the standard
library only (see _probe/make_bundle.py), so "cryptography" is not on the
target machine and adding it would grow the 34.5 MB runtime.  This is the
standard reference construction; it is NOT constant-time, which is fine here
because the private key never leaves the release machine -- only verify() runs
on the player's PC.
"""
import hashlib

p = 2 ** 255 - 19
q = 2 ** 252 + 27742317777372353535851937790883648493


def _sha512(m):
    return hashlib.sha512(m).digest()


def _inv(x):
    return pow(x, p - 2, p)


d = -121665 * _inv(121666) % p
I = pow(2, (p - 1) // 4, p)


def _recover_x(y, sign):
    if y >= p:
        return None
    x2 = (y * y - 1) * _inv(d * y * y + 1)
    if x2 == 0:
        return 0 if sign == 0 else None
    x = pow(x2, (p + 3) // 8, p)
    if (x * x - x2) % p != 0:
        x = x * I % p
    if (x * x - x2) % p != 0:
        return None
    if (x & 1) != sign:
        x = p - x
    return x


_g_y = 4 * _inv(5) % p
_g_x = _recover_x(_g_y, 0)
G = (_g_x, _g_y, 1, _g_x * _g_y % p)


def _add(P, Q):
    A = (P[1] - P[0]) * (Q[1] - Q[0]) % p
    B = (P[1] + P[0]) * (Q[1] + Q[0]) % p
    C = 2 * P[3] * Q[3] * d % p
    D = 2 * P[2] * Q[2] % p
    E = B - A
    F = D - C
    Gv = D + C
    Hv = B + A
    return (E * F, Gv * Hv, F * Gv, E * Hv)


def _mul(s, P):
    Q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            Q = _add(Q, P)
        P = _add(P, P)
        s >>= 1
    return Q


def _compress(P):
    zinv = _inv(P[2])
    x = P[0] * zinv % p
    y = P[1] * zinv % p
    return (y | ((x & 1) << 255)).to_bytes(32, "little")


def _decompress(s):
    if len(s) != 32:
        return None
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    if x is None:
        return None
    return (x, y, 1, x * y % p)


def _expand(secret):
    h = _sha512(secret)
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def public_key(secret):
    a, _ = _expand(secret)
    return _compress(_mul(a, G))


def sign(secret, msg):
    a, prefix = _expand(secret)
    A = _compress(_mul(a, G))
    r = int.from_bytes(_sha512(prefix + msg), "little") % q
    Rs = _compress(_mul(r, G))
    h = int.from_bytes(_sha512(Rs + A + msg), "little") % q
    s = (r + h * a) % q
    return Rs + s.to_bytes(32, "little")


def verify(public, msg, signature):
    if len(public) != 32 or len(signature) != 64:
        return False
    A = _decompress(public)
    R = _decompress(signature[:32])
    if A is None or R is None:
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= q:
        return False
    h = int.from_bytes(_sha512(signature[:32] + public + msg), "little") % q
    return _compress(_mul(s, G)) == _compress(_add(R, _mul(h, A)))

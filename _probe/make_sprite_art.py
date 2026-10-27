"""Export the INPUTS of the sprite-swap decision, not its answer.

`build_sprite` used to read one frozen map (`sprite_pairs.json`: villager ->
sheep, 466 names) and ignore the unit and donor in the request entirely. So
"让弓兵的样子换成长弓兵" reported the archer in its preview and rewrote 244
VILLAGER records on disk -- measured, see `_probe/test_sprite_target.py`.

The answer cannot be frozen because it is a function of (target, donor): 2,281
unit ids have loose art, and precomputing every pair is 2,281^2. What CAN be
measured once is the INPUT the decision runs on -- per unit, which file draws
which animation, and how many frames it has. The matching rule then lives in one
place (this project's rule: `aoe2mod/game/sprites.py`), and a gate proves the Rust
copy reaches the same answer as the reference for a set of pairs.

Shape:

    {
      "anims": ["attack", "death", ...],        # token -> small int
      "arts": [ {"stem": "...", "tokens": {"attack": "u_.._attackA_x1", ...},
                 "grids": {"attack": [[30, 16]]},
                 "variants": [{"stem": "...", "files": {"walk": "u_.._walk_x1"}}]} ],
      "units": { "<unit id>": [civ, art_index, civ, art_index, ...] }
    }

`units` is per civilization because 312 unit ids genuinely have different art in
different civilizations (`SpriteIndex.art` reads `standing_graphic`, which is a
per-civ record field). A single art per id would silently pick one civ's picture
for every civ.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "_golden", "sprite_art.json")


def main():
    import aoe2mod.api as A
    from aoe2mod.game import sprites as S

    tk = A.open_toolkit()
    tk._ensure()
    idx = S.art_index(tk.game_root, tk._stats["graphics"])

    arts, art_index_of = [], {}
    units = {}
    anims = {}
    for ci, civ in enumerate(tk._civs):
        for u in civ.get("units") or ():
            uid = u.get("id")
            art = idx.art(u)
            if uid is None or not art or art.get("kind") != "loose":
                continue
            body = {
                "stem": art.get("stem") or "",
                "tokens": art.get("tokens") or {},
                "grids": {
                    k: [[int(g[0]), int(g[1])] for g in v]
                    for k, v in (art.get("grids") or {}).items()
                },
            }
            variants = []
            for v in art.get("resource_variants") or ():
                variants.append({
                    "stem": v.get("stem") or "",
                    "files": dict(v.get("files") or {}),
                })
            if variants:
                body["variants"] = variants
            key = json.dumps(body, sort_keys=True, ensure_ascii=False)
            ai = art_index_of.get(key)
            if ai is None:
                ai = len(arts)
                art_index_of[key] = ai
                arts.append(body)
                for tok in body["tokens"]:
                    anims.setdefault(tok, len(anims))
            units.setdefault(str(uid), []).extend([ci, ai])

    # `civ_names` is index-aligned with the `ci` numbers in `units`: the civ index
    # is a position in `civs`, not an id anything else has a table for, so the
    # consumer cannot look the name up on its own.  Without it, scoping a rename
    # to 「不列颠」 would need a second table and a second way to get the mapping
    # wrong.
    out = {
        "gv": 54,
        "anims": anims,
        "arts": arts,
        "units": units,
        "civ_names": [c.get("name") or "" for c in tk._civs],
    }
    blob = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(blob)

    # Self-check: the archer and the longbowman must both be present and must
    # have DIFFERENT art, because that difference is the whole point of the
    # table.  A flat table would pass every size check and fail this.
    def art_of(uid, civ=1):
        for i in range(0, len(units.get(str(uid), [])), 2):
            if units[str(uid)][i] == civ:
                return arts[units[str(uid)][i + 1]]
        return None

    a4, a8 = art_of(4), art_of(8)
    assert a4 and a8, "the archer or the longbowman has no loose art"
    assert a4["stem"] != a8["stem"], "archer and longbowman share a stem -- wrong table"
    assert "u_arc_archer_idleA_x1" in a4["tokens"].values(), a4["tokens"]
    assert "u_arc_longbowman_idleA_x1" in a8["tokens"].values(), a8["tokens"]

    # The civ names must stay index-aligned with the art indices, or a scoped
    # rename would quietly reach the wrong civilization.  `British` is 1 and the
    # archer's art there must be the archer's, not somebody else's.
    names = out["civ_names"]
    assert names[1] == "British", names[:3]
    assert art_of(4, 1)["stem"] == "Archer", art_of(4, 1)["stem"]

    print("wrote %s" % OUT)
    print("  arts      %d" % len(arts))
    print("  unit ids  %d" % len(units))
    print("  anims     %d %s" % (len(anims), sorted(anims)[:6]))
    print("  bytes     %d (%.1f KB)" % (len(blob.encode("utf-8")), len(blob.encode("utf-8")) / 1024.0))
    print("  verification ok True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

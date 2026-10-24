# -*- coding: utf-8 -*-
"""`_pair_rows` on the shapes that actually occur, plus the two it must refuse.

Pure function over rows, no game data: the pairing is a naming rule, so it can be
pinned without opening a `.dat`.  The interesting cases are the ones the page cannot
show: a leftover interface half whose build was deleted, and a mod whose TITLE ends in
「（界面）」 on purpose -- that one must not be silently merged with a stranger.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from aoe2mod.ui import server as S  # noqa: E402

FAILS = []


def check(label, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + label + (" :: %s" % (detail,) if detail else ""))
    if not ok:
        FAILS.append(label)


def main():
    pair = [
        {"title": "dsh 分开投递"},
        {"title": "dsh 分开投递（界面）"},
        {"title": "别人做的模组"},
    ]
    S._pair_rows(pair)
    check("the data half is marked", pair[0]["role"] == "data", pair[0]["role"])
    check("the interface half is marked", pair[1]["role"] == "ui", pair[1]["role"])
    check("each names the other", pair[0]["paired_with"] == "dsh 分开投递（界面）"
          and pair[1]["paired_with"] == "dsh 分开投递", pair)
    check("an unrelated mod keeps role None", pair[2]["role"] is None, pair[2])
    check("and claims no partner", pair[2]["paired_with"] is None, pair[2])

    # A leftover interface half: its build is gone.  It is a real state (an old
    # build was uninstalled before the verb was paired), and hiding it would be
    # worse than showing it -- so it stays its own row with no role.
    lonely = [{"title": "dsh 分开投递（界面）"}, {"title": "别人做的模组"}]
    S._pair_rows(lonely)
    check("an orphan interface half is not paired", lonely[0]["role"] is None,
          lonely[0])
    check("and does not borrow a stranger", lonely[1]["role"] is None, lonely[1])

    # A mod that really is titled with the word must not steal a partner.
    wordy = [{"title": "我的（界面）"}, {"title": "我的"}]
    S._pair_rows(wordy)
    check("a title that ends in the word is a real pairing",
          wordy[0]["role"] == "ui" and wordy[1]["role"] == "data", wordy)
    wordy2 = [{"title": "我的（界面）"}]
    S._pair_rows(wordy2)
    check("and alone it pairs with nobody", wordy2[0]["role"] is None, wordy2[0])

    # Duplicate titles must not make a row name itself as its partner.
    dup = [{"title": "同名"}, {"title": "同名（界面）"}, {"title": "同名（界面）"}]
    S._pair_rows(dup)
    check("a row never pairs with itself",
          all(r.get("paired_with") != r.get("title") for r in dup), dup)

    # Existing fields survive: the page reads dat_rank off the same row.
    kept = [{"title": "a", "dat_rank": 2, "ships_dat": True},
            {"title": "a（界面）", "dat_rank": None}]
    S._pair_rows(kept)
    check("pairing does not disturb the data-mod rank", kept[0]["dat_rank"] == 2, kept)

    print()
    if FAILS:
        print("PAIR ROWS: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("PAIR ROWS: A SPLIT BUILD BECOMES ONE PAIR, AN ORPHAN STAYS A LONE ROW")
    return 0


if __name__ == "__main__":
    sys.exit(main())

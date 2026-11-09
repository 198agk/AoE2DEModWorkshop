# -*- coding: utf-8 -*-
"""The Chinese word for each engine animation key, in ONE table.

Why this file exists
--------------------
Two features name animations to the player: a reskin sentence ("目标有 attack,
death, decay, idle, idlec, walk" is half English to the only reader there is) and
the 看动画 chips in the editor.  They were two tables, and they drifted -- one
said `idlec` was 「闲着没事动一下」, the other 「闲着的另一个动作」, and `idleb`
was 「站着的第二个动作」 in one and 「站着不动」 in the other.  A player reading a
chip and then a sentence about the same unit got two names for one animation,
which is the kind of wrongness that makes both screens look unreliable.

The table lives in `game/` because both callers may depend on `game/` and only
one may depend on `intent/`: `intent/reskin.py` already imports `game/sprites`,
and `game/filmstrip.py` must stay usable without the intent layer.  So the words
live at the bottom of the dependency graph and `intent/reskin.py` re-exports them.

An unknown key is NEVER given an invented word.  `word()` returns None and the
caller prints the engine's own spelling (`动作「lush bamboo」`), because a made-up
word cannot be searched for in a wiki and a real one can.
"""

#: The moments a player actually notices, ordered by when they look for them.
#: Several keys can describe one moment (`work` and `task` are both "chopping"),
#: which is why `_moments` de-duplicates by WORD rather than by key.
MOMENT_WORD = {
    "idle": "站着不动",
    "walk": "走路",
    "attack": "攻击",
    "death": "倒下",
    "decay": "腐烂",
    "work": "干活（砍树、挖矿、种田、盖房）",
    "task": "干活（砍树、挖矿、种田、盖房）",
    "carry": "搬着东西走路",
    "seed": "播种",
    "idlec": "闲着没事动一下",
    "conversion": "被招降",
    "heal": "治疗",
    "build": "盖房",
}

#: The engine's OTHER spellings: building states, the A/B/C variants, and the
#: packed / emplaced states a siege unit has.  These are not "rare", they are
#: simply not what a reskin sentence used to mention; the editor's chip row shows
#: every one of them, so a missing entry is a chip in English.
_MOMENT_EXTRA = {
    "age": "建成后的样子",
    "age1": "第一个时代的样子",
    "age2": "第二个时代的样子",
    "age3": "第三个时代的样子",
    "age4": "第四个时代的样子",
    "destruction": "倒塌中",
    "rubble": "成为废墟",
    "idleA": "站着不动",
    "idleB": "站着不动",
    "idleC": "闲着的另一个动作",
    "walkA": "走路",
    "walkB": "走路",
    "attackA": "攻击",
    "attackB": "攻击",
    "deathA": "倒下",
    "decayA": "腐烂",
    "emplacement": "架起来的样子",
    "emplacements": "架起来的样子",
    "all emplacements": "架起来的样子",
    "defensive emplacement": "防守位置上架起来的样子",
    "offensive emplacement": "进攻位置上架起来的样子",
    "packed": "收起来的样子",
    "unpacked": "放下来的样子",
}

MOMENT_WORD.update({k.lower(): v for k, v in _MOMENT_EXTRA.items()})
#: `_moment_names` looks a token up with spaces removed ("All Emplacements" ->
#: "allemplacements"), so the spaced spellings above need that form too.  Doing it
#: here rather than in every lookup keeps ONE normalisation rule in the project.
MOMENT_WORD.update({k.replace(" ", ""): v
                    for k, v in list(MOMENT_WORD.items()) if " " in k})

#: Reading order for a chip row: the animation a player looks for first comes
#: first.  Keys absent from this list sort after every listed one, alphabetically,
#: so an unknown engine key lands at the end instead of at the front.
ORDER = ["idle", "idlea", "idleb", "idlec", "walk", "walka", "walkb",
         "attack", "attacka", "attackb", "work", "task", "carry", "seed",
         "heal", "build", "conversion", "packed", "unpacked", "emplacement",
         "emplacements", "allemplacements", "defensiveemplacement",
         "offensiveemplacement", "death", "deatha", "decay", "decaya",
         "age", "age1", "age2", "age3", "age4", "destruction", "rubble"]


def word(key):
    """The Chinese word for an animation key, or None when there is none."""
    return MOMENT_WORD.get((key or "").lower())


#: The same table under the name the picture code uses.  Two names for one
#: table is cheaper than a second table under a second name.
ANIM_ZH = MOMENT_WORD


def order_key(key):
    """Sort key placing the common animations first, unknown ones last."""
    k = (key or "").lower()
    try:
        return (ORDER.index(k), "")
    except ValueError:
        return (len(ORDER), k)

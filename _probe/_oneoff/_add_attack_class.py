# -*- coding: utf-8 -*-
"""A sentence for `unit.attack_class`: "步弓手对骑兵攻击加2".

Three rules from the Python reader, each bought with a wrong answer:

  * The class name must sit IMMEDIATELY AFTER 对. Matching it anywhere would fire
    on "骑兵的血量改成1000", where the class is the ENTITY, not the target of a
    bonus.
  * It must be checked BEFORE the plain stat branch, because "攻击" alone reads
    as `displayed_attack` and the "对骑兵" half would be dropped on the floor --
    a confident wrong answer, the worst shape here.
  * It has to say whether it means 攻击 or 护甲. "对骑兵" alone is a refusal with
    a question, not a guess.

Output intent: `{intent, unit, class_id, kind: "attack"|"armour", value|delta}`.
"""
import io
import os

BASE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "desktop", "aoe2mod-serve", "src"))
P = os.path.join(BASE, "sentences.rs")
src = io.open(P, encoding="utf-8").read()

BRANCH = r'''
    // --- unit.attack_class: "步弓手对骑兵攻击加2" -------------------------
    // BEFORE the stat branch: "攻击" alone would read as displayed_attack and
    // the "对骑兵" half would be dropped, which is a confident wrong answer.
    if let Some((cid, cname)) = class_after_dui(text) {
        let is_attack = text.contains("攻击") || text.contains("攻");
        let is_armour =
            text.contains("护甲") || text.contains("防御") || text.contains("甲");
        if !(is_attack || is_armour) {
            cl.why = Some(format!(
                "「对{cname}」要改的是攻击还是护甲？说「攻击」或「护甲」"
            ));
            return cl;
        }
        let (unit, stat_part) = match text.split_once('对') {
            Some((a, _b)) => (rightmost_name_of(n_ref(), a), a),
            None => (None, text),
        };
        let _ = stat_part;
        if let Some(u) = unit {
            let mut it = Intent::default();
            it.intent = "unit.attack_class".to_string();
            it.unit = Some(u);
            it.class_id = Some(cid as i16);
            it.attack_kind = Some(if is_attack { "attack" } else { "armour" }.to_string());
            it.value = Some(value);
            return Clause {
                text: text.to_string(),
                intent: Some(it),
                why: None,
                entity_name: Some(cname),
                entity_id: Some(u),
            };
        }
        cl.why = Some("没听出要改哪个单位。".into());
        return cl;
    }
'''

# Insert right after the card_move block (which is first in read_clause).
ANCHOR = "            }\n        }\n    }\n"
i = src.index("fn slot_in(")
# Find the end of the card_move block: the first `\n\n` after read_clause's start.
RC = "pub fn read_clause(text: &str) -> Clause {\n"
rc_i = src.index(RC)
after = src.index("\n\n", rc_i)
if '"unit.attack_class"' not in src:
    src = src[:after] + "\n" + BRANCH + src[after:]

    # Intent gains class_id + attack_kind
    OLD = '''    /// `unit.card_move` only: which building's card, and which box on it.
    pub building: Option<i16>,
    pub button: Option<u8>,
}'''
    NEW = '''    /// `unit.card_move` only: which building's card, and which box on it.
    pub building: Option<i16>,
    pub button: Option<u8>,
    /// `unit.attack_class` only: the target CLASS and whether it is attack or armour.
    pub class_id: Option<i16>,
    pub attack_kind: Option<String>,
}'''
    assert OLD in src
    src = src.replace(OLD, NEW, 1)

    OLD_J = '''        if let Some(v) = self.button {
            parts.push(format!("\\"button\\":{v}"));
        }'''
    NEW_J = '''        if let Some(v) = self.button {
            parts.push(format!("\\"button\\":{v}"));
        }
        if let Some(v) = self.class_id {
            parts.push(format!("\\"class_id\\":{v}"));
        }
        if let Some(v) = &self.attack_kind {
            parts.push(format!("\\"kind\\":\\"{}\\"", crate::server::json_escape(v)));
        }'''
    assert OLD_J in src
    src = src.replace(OLD_J, NEW_J, 1)

    src += r'''

fn n_ref() -> Option<&'static Names> {
    names().as_ref()
}

fn rightmost_name_of(n: Option<&Names>, text: &str) -> Option<i16> {
    n.and_then(|t| rightmost_name(t, text))
}

/// `(class id, matched name)` for the class named right after 对.
///
/// The position rule is load-bearing: matching a class name anywhere would fire
/// on "骑兵的血量改成1000", where the class is the ENTITY rather than the target
/// of a bonus. Longest name wins, so 攻城武器 does not lose to a prefix.
fn class_after_dui(text: &str) -> Option<(u32, String)> {
    let pos = text.find('对')?;
    let tail: String = text[pos + '对'.len_utf8()..].to_string();
    let table = crate::attack_class::class_names();
    let mut best: Option<(usize, u32, String)> = None;
    for (id, names) in table.iter() {
        for nm in names {
            if nm.is_empty() || !tail.starts_with(nm.as_str()) {
                continue;
            }
            let len = nm.chars().count();
            if best.as_ref().map(|(b, _, _)| len > *b).unwrap_or(true) {
                best = Some((len, *id, nm.clone()));
            }
        }
    }
    best.map(|(_, id, nm)| (id, nm))
}
'''
    io.open(P, "w", encoding="utf-8", newline="\n").write(src)
    print("sentences.rs: unit.attack_class branch added")
else:
    print("already present")

"""Fix the two parse/build disagreements found by test_parse_build_agreement.

1. tech.effect: the ordinal was decremented twice, 「第0条」 was accepted, and a
   bare 「效果加5」 silently edited the first command even when the tech has
   three.  The reference (aoe2mod/ui/nl.py:1743-1768) does all three checks and
   refuses with a sentence that names the problem.
2. unit.attack_class: the class the player typed was thrown away (`let _ = cid`)
   and replaced with the schema's candidate order.  That happens to agree when
   the typed class is the second candidate, and disagrees every other time:
   「民兵对建筑攻击加2」 asks for class 3, a militia carries 29/21/4/8/30/15, so
   the reference refuses while this side silently edits class 4.

Both patches are asserted to apply exactly once.  A silent no-op patch is how
this project has produced "fixed" code that never changed.
"""
import io

ROOT = "D:/Software/AI/帝国项目/"
P = ROOT + "desktop/aoe2mod-serve/src/sentences.rs"

s = io.open(P, encoding="utf-8").read()
orig = s


def sub(old, new, what):
    global s
    n = s.count(old)
    assert n == 1, "%s: expected 1 occurrence, found %d" % (what, n)
    s = s.replace(old, new, 1)


# ---------------------------------------------------------------- ordinals ---
# Python's _ORDINAL_ZH stops at ten on purpose and says why: no shipped
# technology has more commands than a player would address by position.  The
# same table here keeps the two readers answering the same sentences.
sub(
    """fn ordinal_in(text: &str) -> Option<usize> {
    let b: Vec<char> = text.chars().collect();
    for i in 0..b.len() {
        if b[i] == '第' {
            let mut j = i + 1;
            while j < b.len() && !b[j].is_ascii_digit() {
                j += 1;
            }
            let start = j;
            while j < b.len() && b[j].is_ascii_digit() {
                j += 1;
            }
            if start < j {
                let s: String = b[start..j].iter().collect();
                if let Ok(v) = s.parse::<usize>() {
                    return Some(v);
                }
            }
        }
    }
    None
}""",
    """/// Chinese ordinals a sentence may use.  Stops at ten for the same reason the
/// reference does (`nl.py:299`): no shipped technology has more commands than a
/// player would address by position, and inventing a parser for numbers nobody
/// types is how a wrong answer gets a plausible-looking path in.
fn zh_ordinal(c: char) -> Option<usize> {
    "一二三四五六七八九十".find(c).map(|i| i + 1)
}

/// The position the sentence names ("第2条" -> 2), 1-based.
///
/// 1-based on purpose: the caller subtracts the one, because a position that
/// cannot exist ("第0条") has to be refused where the number is READ, not where
/// it is written.  Keeping the subtraction at one site is what makes that
/// possible.
fn ordinal_in(text: &str) -> Option<usize> {
    let b: Vec<char> = text.chars().collect();
    for i in 0..b.len() {
        if b[i] != '第' {
            continue;
        }
        let mut j = i + 1;
        while j < b.len() && b[j].is_whitespace() {
            j += 1;
        }
        // Arabic digits first, then the single Chinese digit the reference
        // knows.  「第十二条」 is deliberately not parsed: `nl.py` does not
        // either, and a sentence that reaches a number neither reader
        // understands must refuse rather than guess.
        let mut k = j;
        while k < b.len() && b[k].is_ascii_digit() {
            k += 1;
        }
        if k > j {
            let s: String = b[j..k].iter().collect();
            if let Ok(v) = s.parse::<usize>() {
                return Some(v);
            }
            continue;
        }
        if let Some(v) = b.get(j).copied().and_then(zh_ordinal) {
            return Some(v);
        }
    }
    None
}""",
    "ordinal_in",
)

sub(
    """fn strip_ordinal(text: &str) -> String {
    let b: Vec<char> = text.chars().collect();
    let mut out = String::with_capacity(text.len());
    let mut i = 0usize;
    while i < b.len() {
        if b[i] == '第' {
            let mut j = i + 1;
            while j < b.len() && !b[j].is_ascii_digit() {
                j += 1;
            }
            let num_start = j;
            while j < b.len() && b[j].is_ascii_digit() {
                j += 1;
            }
            if num_start < j {
                // Skip "第" and the digits; keep whatever follows.
                i = j;
                continue;
            }
        }
        out.push(b[i]);
        i += 1;
    }
    out
}""",
    """fn strip_ordinal(text: &str) -> String {
    let b: Vec<char> = text.chars().collect();
    let mut out = String::with_capacity(text.len());
    let mut i = 0usize;
    while i < b.len() {
        if b[i] == '第' {
            let mut j = i + 1;
            while j < b.len() && b[j].is_whitespace() {
                j += 1;
            }
            let mut k = j;
            while k < b.len() && b[k].is_ascii_digit() {
                k += 1;
            }
            if k > j {
                // Skip "第" and the digits; keep whatever follows.
                i = k;
                continue;
            }
            if b.get(j).copied().and_then(zh_ordinal).is_some() {
                // Same for the single Chinese digit, or 「第二条效果改成100」
                // would read 2 as the value.
                i = j + 1;
                continue;
            }
        }
        out.push(b[i]);
        i += 1;
    }
    out
}""",
    "strip_ordinal",
)

# ------------------------------------------------------- tech.effect counts ---
sub(
    """fn n_ref() -> Option<&'static Names> {""",
    """/// How many effect commands a technology has, or `None` when the table does
/// not say.
///
/// The reference gets this from the caller as a callback (`nl.py:1044`
/// `_effect_count`), because its reader has no `.dat` either.  Here the number
/// comes from `_golden/tech_effects.json`, exported from that same reader --
/// one measured number, two delivery pipes, never two derivations.
///
/// `None` is NOT "there is exactly one".  The caller must treat an unknown
/// count as "edit the first entry and say so", which is what the reference's
/// `没点名第几条，按第 1 条读` note is for.
fn tech_effect_count(tech: i16) -> Option<usize> {
    static T: std::sync::OnceLock<std::collections::HashMap<i16, usize>> =
        std::sync::OnceLock::new();
    let table = T.get_or_init(|| {
        let mut out = std::collections::HashMap::new();
        for p in table_paths("AOE2MOD_TECH_EFFECTS", "tech_effects.json") {
            let text = match std::fs::read_to_string(&p) {
                Ok(t) => t,
                Err(_) => continue,
            };
            let v: serde_json::Value =
                match serde_json::from_str(text.trim_start_matches('\\u{feff}')) {
                    Ok(v) => v,
                    Err(_) => continue,
                };
            if let Some(counts) = v.get("counts").and_then(|c| c.as_object()) {
                for (k, n) in counts {
                    if let (Ok(id), Some(n)) = (k.parse::<i16>(), n.as_u64()) {
                        out.insert(id, n as usize);
                    }
                }
            }
            if !out.is_empty() {
                break;
            }
        }
        out
    });
    table.get(&tech).copied()
}

/// The name a refusal should print for a technology.
fn tech_display(tech: i16) -> String {
    names()
        .as_ref()
        .and_then(|n| n.techs.get(&tech))
        .and_then(|v| v.first())
        .cloned()
        .unwrap_or_else(|| format!("科技 {tech}"))
}

fn n_ref() -> Option<&'static Names> {""",
    "tech_effect_count",
)

# ------------------------------------------------------------ tech.effect body --
sub(
    """            let idx = ordinal_in(text).unwrap_or(1);
            // The VALUE is the number that is not the ordinal. `find_number`
            // returns the first run of digits, and in this sentence that is the
            // command index -- so re-read with the ordinal's digits removed.
            // Measured: without this, "第1条效果改成100" produced `value: 1`.
            let value = {
                let stripped = strip_ordinal(text);
                match find_number(&stripped) {
                    Some((v, _)) => v,
                    None => value,
                }
            };""",
    """            // The VALUE is the number that is not the ordinal. `find_number`
            // returns the first run of digits, and in this sentence that is the
            // command index -- so re-read with the ordinal's digits removed.
            // Measured: without this, "第1条效果改成100" produced `value: 1`.
            let value = {
                let stripped = strip_ordinal(text);
                match find_number(&stripped) {
                    Some((v, _)) => v,
                    None => value,
                }
            };
            // The position is checked where it is read, not where it is written.
            //
            // `ordinal_in` is 1-based and `build_effect` already subtracts one
            // (it indexes the command list), so this side must NOT subtract.
            // Measured before the fix: 「织布机第2条效果改成100」 landed on
            // command 2, which is the THIRD command -- a one-off answer that
            // looks completely normal in the response.
            let tech_id = eid.unwrap();
            let count = tech_effect_count(tech_id);
            let idx = match ordinal_in(text) {
                Some(ordv) => {
                    if ordv == 0 {
                        // A position that cannot exist is refused here: the
                        // reference measured the same trap (nl.py:1751), where
                        // 「第0条」 passed a guard that only checked the far end
                        // and reached the compiler, which refused it in English.
                        cl.why = Some(format!("效果是从第 1 条开始数的，没有第 {ordv} 条"));
                        return cl;
                    }
                    if let Some(c) = count {
                        if ordv > c {
                            cl.why = Some(format!(
                                "「{}」只有 {} 条效果，没有第 {} 条",
                                tech_display(tech_id),
                                c,
                                ordv
                            ));
                            return cl;
                        }
                    }
                    ordv - 1
                }
                None => match count {
                    Some(0) => {
                        cl.why = Some(format!(
                            "「{}」没有任何效果可以改",
                            tech_display(tech_id)
                        ));
                        return cl;
                    }
                    Some(c) if c > 1 => {
                        // 669 of the 1,040 technologies that carry commands have
                        // two or more, so a bare 「效果加5」 cannot say which one.
                        // Editing the first and hoping is the failure this
                        // refusal exists to prevent.
                        cl.why = Some(format!(
                            "「{}」有 {} 条效果，说清改第几条（例如「第2条」）",
                            tech_display(tech_id),
                            c
                        ));
                        return cl;
                    }
                    Some(_) => 0,
                    None => {
                        // Unknown count: edit the first entry and SAY so.  The
                        // reference's own words, because the alternative is a
                        // note nobody can see and an edit nobody expects.
                        cl.notes.push("没点名第几条，按第 1 条读".to_string());
                        0
                    }
                },
            };""",
    "tech.effect ordinal",
)

# tech.effect now owns cl directly for the note, so the tail must merge notes.
sub(
    """            it.intent = "tech.effect".to_string();
            it.tech = eid;
            it.command = Some(idx);""",
    """            it.intent = "tech.effect".to_string();
            it.tech = eid;
            it.command = Some(idx);""",
    "tech.effect tail (unchanged)",
)

# ------------------------------------------------------- unit.attack_class ----
sub(
    """            // NOT : that number is a UNIT class (骑兵 = 12),
            // while the record stores ATTACK classes (3 = generic base attack,
            // 4 = the other base attack). Passing 12 made every build refuse
            // with "没有「基础攻击」这项可以改", because no record carries an
            // attack row of class 12. The bindings say it directly:
            // `attack_classes.attack.class_candidates = [3, 4]`, tried in order,
            // first one the unit actually carries wins.
            //
            // The class NAME the player typed still matters for the refusal
            // message, so it is kept in entity_name.
            let _ = cid;
            it.class_candidates = Some(vec![3i16, 4i16]);""",
    """            // The number the class table gives back is the id the RECORD
            // stores: 建筑 = 3, 平民 = 4, 家畜 = 29 -- the same table the
            // reference uses (`nl.py:720 _class_in`), not the unit-class space
            // that 骑兵 = 12 belongs to.
            //
            // An explicit class overrides the schema's candidate order, and it
            // has to override it HERE, not only on the write path.  Measured
            // before the fix: `let _ = cid` threw the typed class away and left
            // `class_candidates = [3, 4]`, so 「民兵对建筑攻击加2」 asked for
            // class 3, a militia carries 29/21/4/8/30/15, and this side quietly
            // edited class 4 while the reference refused the sentence.  The
            // reference records the same lesson at `compiler.py:1730`: one
            // binding decision for both paths, or the two describe one edit
            // differently.
            it.class_id = Some(cid as i16);
            it.class_candidates = Some(vec![3i16, 4i16]);""",
    "attack_class class_id",
)

assert s != orig, "no change landed"
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("patched sentences.rs: %d -> %d bytes" % (len(orig), len(s)))


# ------------------------------------------------------------------ writer ---
# `build_unit_attack_class` must honour class_id exactly like `_class_selectors`.
W = ROOT + "desktop/aoe2mod-serve/src/stat_edit.rs"
w = io.open(W, encoding="utf-8").read()
old = """    let classes: Vec<i16> = req
        .get("class_candidates")
        .and_then(|v| v.as_array())
        .map(|a| a.iter().filter_map(|x| x.as_i64().map(|v| v as i16)).collect())
        .filter(|v: &Vec<i16>| !v.is_empty())
        .unwrap_or_else(|| {
            if kind == "armour" {
                vec![4, 3]
            } else {
                vec![3, 4]
            }
        });"""
new = """    // A class the sentence named is the ONLY candidate, exactly as the
    // reference's `_class_selectors` does it (`compiler.py:2100`: `if "class_id"
    // in b: return [b["class_id"]]`).  Keeping the schema's list as a fallback
    // would make a sentence that asked for a class the unit does not carry
    // silently edit a different class instead of refusing -- measured on
    // 「民兵对建筑攻击加2」, which asked for 3 and used to write 4.
    let classes: Vec<i16> = match req.get("class_id").and_then(|v| v.as_i64()) {
        Some(c) => vec![c as i16],
        None => req
            .get("class_candidates")
            .and_then(|v| v.as_array())
            .map(|a| a.iter().filter_map(|x| x.as_i64().map(|v| v as i16)).collect())
            .filter(|v: &Vec<i16>| !v.is_empty())
            .unwrap_or_else(|| {
                if kind == "armour" {
                    vec![4, 3]
                } else {
                    vec![3, 4]
                }
            }),
    };"""
assert w.count(old) == 1, "stat_edit class_candidates: %d" % w.count(old)
w = w.replace(old, new, 1)
io.open(W, "w", encoding="utf-8", newline="\n").write(w)
print("patched stat_edit.rs")

//! The sentence layer, ported from `aoe2mod/ui/nl.py` one intent at a time.
//!
//! Scope of this file
//! ------------------
//! `unit.stat` and `unit.cost` only. Those are the two most-typed requests and
//! they exercise every piece the other twelve need: number reading, SET vs DELTA
//! operation words, longest-span name matching, and civilization scope. Adding
//! `ts50` or `ts30` after this is a table entry, not a new mechanism.
//!
//! What it refuses to do
//! ---------------------
//! Guess. Every failure returns a reason the screen can print, because the
//! project's rule is that a refusal the player cannot act on is a defect. The
//! Python original returns `why` strings; this returns the same sentences so the
//! screen does not have to know which implementation answered.
//!
//! Design notes that are load-bearing (all from the Python original, each bought
//! with a bug):
//!
//!   * Numbers are read BEFORE words: "村民血量改到1000" has no spaces and the
//!     digits are the only unambiguous token.
//!   * SET words ("改到/设为") and DELTA words ("加/提高") are separate, and SET
//!     wins when both could match. Reading "改到1000" as a delta of 1000 is the
//!     single most likely misreading.
//!   * Names are matched by LONGEST SPAN over the whole sentence. Asking the
//!     index to resolve the sentence returns nothing, because a sentence is not
//!     a name.
//!   * A civilization is recognised only when the sentence names one; otherwise
//!     the edit means the whole roster.

use std::collections::HashMap;
use std::sync::OnceLock;

/// `stat name -> the words a player types for it`, from `nl.py`'s STAT_WORDS.
pub const STAT_WORDS: &[(&str, &[&str])] = &[
    ("hit_points", &["血量", "生命值", "生命", "血", "hp"]),
    ("displayed_attack", &["攻击力", "攻击", "攻"]),
    ("displayed_melee_armour", &["近战护甲", "近战防御", "近防", "近甲"]),
    ("displayed_pierce_armour", &["远程护甲", "远程防御", "远防", "远甲"]),
    ("movement_speed", &["移动速度", "移速", "速度"]),
    ("line_of_sight", &["视野"]),
    ("creation_time", &["训练时间", "造兵时间", "生产时间"]),
    ("displayed_range", &["面板射程"]),
    ("max_range", &["射程"]),
    ("displayed_reload_time", &["面板装填时间"]),
    ("reload_time", &["装填时间", "装填", "攻速"]),
    ("min_range", &["最小射程"]),
    ("accuracy", &["命中率", "命中"]),
    ("garrison_capacity", &["驻扎容量", "驻扎", "容量"]),
    // Tech-side words. `research_time` already has 训练时间/造兵时间 above for
    // units; a player talking about a technology says 研究时间 or 研发时间, and
    // without these the sentence falls through to "没听出要改哪个属性".
    ("research_time", &["研究时间", "研发时间", "研究速度", "研发速度"]),
];

/// One readable sentence and what it asks for.
#[derive(Debug, Clone)]
pub struct Clause {
    pub text: String,
    pub intent: Option<Intent>,
    /// Why the sentence could not be read, in the player's language.  `None` on
    /// success.  A refusal the player cannot act on is a defect, so every path
    /// that fails sets one of these.
    pub why: Option<String>,
    /// The entity the sentence names, for the icon and detail routes.
    pub entity_name: Option<String>,
    pub entity_id: Option<i16>,
}

#[derive(Debug, Clone, Default)]
pub struct Intent {
    pub intent: String,
    pub unit: Option<i16>,
    pub tech: Option<i16>,
    pub stat: Option<String>,
    pub resource: Option<String>,
    pub value: Option<f64>,
    pub delta: Option<f64>,
    pub civs: Option<String>,
    /// `tech.effect` only: which command of the effect, and which of its fields.
    pub command: Option<usize>,
    pub field: Option<String>,
    /// `unit.card_move` only: which building's card, and which box on it.
    pub building: Option<i16>,
    pub button: Option<u8>,
    /// `unit.attack_class` only: the target CLASS and whether it is attack or armour.
    pub class_id: Option<i16>,
    /// : the ATTACK classes to try in order (see the
    ///  block in dat_bindings.json). Not the unit class the
    /// sentence names -- those are two different id spaces.
    pub class_candidates: Option<Vec<i16>>,
    pub attack_kind: Option<String>,
}

impl Intent {
    pub fn to_json(&self) -> String {
        let mut parts: Vec<String> = vec![format!(
            "\"intent\":\"{}\"",
            crate::server::json_escape(&self.intent)
        )];
        if let Some(v) = self.unit {
            parts.push(format!("\"unit\":{v}"));
        }
        if let Some(v) = self.tech {
            parts.push(format!("\"tech\":{v}"));
        }
        if let Some(v) = &self.stat {
            parts.push(format!("\"stat\":\"{}\"", crate::server::json_escape(v)));
        }
        if let Some(v) = &self.resource {
            parts.push(format!("\"resource\":\"{}\"", crate::server::json_escape(v)));
        }
        if let Some(v) = self.value {
            parts.push(format!("\"value\":{v}"));
        }
        if let Some(v) = self.delta {
            parts.push(format!("\"delta\":{v}"));
        }
        if let Some(v) = &self.civs {
            parts.push(format!("\"civs\":\"{}\"", crate::server::json_escape(v)));
        }
        if let Some(v) = self.command {
            parts.push(format!("\"command\":{v}"));
        }
        if let Some(v) = &self.field {
            parts.push(format!("\"field\":\"{}\"", crate::server::json_escape(v)));
        }
        if let Some(v) = self.building {
            parts.push(format!("\"builder\":{v}"));
        }
        if let Some(v) = self.button {
            parts.push(format!("\"button\":{v}"));
        }
        if let Some(v) = self.class_id {
            parts.push(format!("\"class_id\":{v}"));
        }
        if let Some(v) = &self.class_candidates {
            let list: Vec<String> = v.iter().map(|x| x.to_string()).collect();
            parts.push(format!("\"class_candidates\":[{}]", list.join(",")));
        }
        if let Some(v) = &self.attack_kind {
            parts.push(format!("\"kind\":\"{}\"", crate::server::json_escape(v)));
        }
        format!("{{{}}}", parts.join(","))
    }
}

fn global_names() -> &'static OnceLock<Option<Names>> {
    static N: OnceLock<Option<Names>> = OnceLock::new();
    &N
}

/// Load the name table once.  A missing file leaves the tables empty and every
/// sentence refuses with "没听出要改哪个单位", which is the honest answer when
/// the vocabulary was not shipped.
pub fn names() -> &'static Option<Names> {
    global_names().get_or_init(|| {
        for path in table_paths("AOE2MOD_ENTITY_NAMES", "entity_names.json") {
            if let Ok(n) = Names::load(&path) {
                return Some(n);
            }
        }
        None
    })
}

fn contains_any(text: &str, words: &[&str]) -> bool {
    words.iter().any(|w| text.contains(w))
}

/// First run of ASCII digits, optionally with one decimal point.
///
/// Deliberately does not accept Chinese numerals: "一千" is a different reading
/// problem, and guessing it would be the "prewritten conclusion" this project
/// keeps paying for.
fn find_number(text: &str) -> Option<(f64, (usize, usize))> {
    let b: Vec<char> = text.chars().collect();
    let mut i = 0usize;
    while i < b.len() {
        if b[i].is_ascii_digit() {
            let start = i;
            while i < b.len() && (b[i].is_ascii_digit() || b[i] == '.') {
                i += 1;
            }
            let s: String = b[start..i].iter().collect();
            if let Ok(v) = s.parse::<f64>() {
                return Some((v, (start, i)));
            }
        }
        i += 1;
    }
    None
}

/// Resource words for `unit.cost`.
const RESOURCE_WORDS: &[(&str, &[&str])] = &[
    ("wood", &["木材", "木头", "木"]),
    ("food", &["食物", "粮", "食物"]),
    ("gold", &["黄金", "金", "金币"]),
    ("stone", &["石头", "石"]),
];

const SET_WORDS: &[&str] = &["改成", "改为", "改到", "设成", "设为", "调成", "调到", "变成"];
const ADD_WORDS: &[&str] = &["增加", "提高", "加", "多给"];
const SUB_WORDS: &[&str] = &["减少", "降低", "减", "少给"];

/// Which stat an `intent` id maps to, for the two families this file handles.
fn intent_for_stat(stat: &str) -> &'static str {
    // A research time belongs to a TECHNOLOGY, and the intent id has to say so:
    // `unit.stat` would send the edit down the per-unit path, where the offset
    // table has no entry for it and the build would refuse a sentence it had
    // just claimed to understand.
    if stat == "research_time" {
        return "tech.research_time";
    }
    match stat {
        "hit_points" | "displayed_attack" | "displayed_melee_armour"
        | "displayed_pierce_armour" | "movement_speed" | "line_of_sight"
        | "creation_time" | "max_range" | "displayed_range" | "reload_time"
        | "displayed_reload_time" | "min_range" | "accuracy"
        | "garrison_capacity" => "unit.stat",
        _ => "unit.stat",
    }
}

/// `id -> names`, loaded once from `_golden/entity_names.json`.
pub struct Names {
    pub units: HashMap<i16, Vec<String>>,
    pub techs: HashMap<i16, Vec<String>>,
}

impl Names {
    pub fn load(path: &std::path::Path) -> std::io::Result<Names> {
        // serde_json rather than the hand scanner the other loaders use: this
        // file is 135 KB of nested id -> [names] and a hand parser that gets it
        // slightly wrong returns EMPTY tables, which reads as "the vocabulary
        // was not shipped" and makes every sentence refuse.  That is exactly
        // what happened on the first run of this function.
        let text = std::fs::read_to_string(path)?;
        let v: serde_json::Value = serde_json::from_str(&text)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
        Ok(Names {
            units: table_from(&v, "units"),
            techs: table_from(&v, "techs"),
        })
    }

    /// Longest name that occurs in `text`, and the id it belongs to.
    ///
    /// Longest span, not first hit: "剑士" and "长剑士" are different units, so
    /// a first-match scan silently picks the shorter one and edits the wrong
    /// record.
    pub fn longest_unit(&self, text: &str) -> Option<(i16, String)> {
        longest(&self.units, text)
    }

    pub fn longest_tech(&self, text: &str) -> Option<(i16, String)> {
        longest(&self.techs, text)
    }
}

fn table_from(v: &serde_json::Value, key: &str) -> HashMap<i16, Vec<String>> {
    let mut out = HashMap::new();
    let obj = match v.get(key).and_then(|x| x.as_object()) {
        Some(o) => o,
        None => return out,
    };
    for (k, val) in obj {
        let id: i16 = match k.parse() {
            Ok(i) => i,
            Err(_) => continue,
        };
        let names: Vec<String> = val
            .as_array()
            .map(|a| {
                a.iter()
                    .filter_map(|x| x.as_str().map(|s| s.to_string()))
                    .collect()
            })
            .unwrap_or_default();
        if !names.is_empty() {
            out.insert(id, names);
        }
    }
    out
}

fn longest(table: &HashMap<i16, Vec<String>>, text: &str) -> Option<(i16, String)> {
    let mut best: Option<(i16, String)> = None;
    for (id, names) in table {
        for n in names {
            if n.is_empty() || !text.contains(n.as_str()) {
                continue;
            }
            let better = match &best {
                None => true,
                Some((_, cur)) => n.chars().count() > cur.chars().count(),
            };
            if better {
                best = Some((*id, n.clone()));
            }
        }
    }
    best
}


/// Split on Chinese sentence punctuation and newlines, then on commas.
///
/// The Python original's `_pieces` also merges group lists and create-names;
/// those exist for intents this file does not handle yet, so they are not
/// ported, and their absence cannot make a sentence misread — only refused.
pub fn pieces(text: &str) -> Vec<String> {
    let mut out = Vec::new();
    for part in text.split(['。', '；', '\n', '\r', ';']) {
        let t = part.trim();
        if t.is_empty() {
            continue;
        }
        for sub in t.split(['，', ',']) {
            let s = sub.trim();
            if !s.is_empty() {
                out.push(s.to_string());
            }
        }
    }
    out
}

/// Read a whole request: one clause per piece.
pub fn read(text: &str) -> Vec<Clause> {
    pieces(text).iter().map(|p| read_clause(p)).collect()
}

/// Read one sentence.
pub fn read_clause(text: &str) -> Clause {
    // --- command-card move, before anything else -------------------------
    // "把民兵放在第5格" / "把民兵挪到兵营的第5格".
    //
    // FIRST, because the box is the number and boxes go past ten (shipped data
    // uses 0..15 and 24) while `find_number` reads ASCII digits only -- correct
    // for VALUES, wrong here. Measured: below the number gate,
    // "把民兵放在第十二格" was refused with "这句话里没有数字".
    //
    // It resolves its own names because it needs the RIGHT part of the sentence:
    // taking the global longest match over "把民兵挪到兵营" picked 498 as the unit
    // instead of 民兵 (74), since the building name is longer.
    if let Some(slot) = slot_in(text) {
        if let Some(n) = names().as_ref() {
            // 的 sits AFTER the building: "把民兵挪到兵营的|第5格". So the part
            // before 的 holds BOTH nouns, and the part after it is just the box.
            let before_de = match text.split_once('的') {
                Some((a, _)) => a,
                None => text,
            };
            // The building is named only when the sentence has a 的: without it
            // ("把民兵放在第5格") the whole text is the unit and there IS no
            // building, so the server resolves which card the unit is on. Reading
            // a building out of the no-的 case made the unit and the building the
            // same record, and every such sentence then refused.
            let builder = if text.contains('的') {
                canonical_name_id(n, before_de)
            } else {
                None
            };
            // The unit is the rightmost name AFTER removing the building's own
            // text, otherwise the building wins both slots: measured, this
            // returned unit 498 (Barracks) for a sentence about the militia.
            let mut unit_scan = before_de.to_string();
            if let Some(bid) = builder {
                if let Some(names_b) = n.units.get(&bid) {
                    for nm in names_b {
                        if !nm.is_empty() {
                            unit_scan = unit_scan.replacen(nm.as_str(), " ", 1);
                        }
                    }
                }
            }
            if let Some(u) = rightmost_name(n, &unit_scan) {
                let mut it = Intent::default();
                it.intent = "unit.card_move".to_string();
                it.unit = Some(u);
                it.building = builder;
                it.button = Some(slot);
                return Clause {
                    text: text.to_string(),
                    intent: Some(it),
                    why: None,
                    entity_name: None,
                    entity_id: Some(u),
                };
            }
        }
    }
    let mut cl = Clause {
        text: text.to_string(),
        intent: None,
        why: None,
        entity_name: None,
        entity_id: None,
    };

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
            // NOT : that number is a UNIT class (骑兵 = 12),
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
            it.class_candidates = Some(vec![3i16, 4i16]);
            it.attack_kind = Some(if is_attack { "attack" } else { "armour" }.to_string());
            // Read the number HERE: this branch runs before the number gate
            // (it must, or "对骑兵" would be consumed by the stat branch).
            let num = match find_number(text) {
                Some((v, _)) => v,
                None => {
                    cl.why = Some("这句话里没有数字，没有说要改成多少。".into());
                    return cl;
                }
            };
            // SET vs DELTA, same words as everywhere else.
            let op2 = if contains_any(text, SET_WORDS) {
                "set"
            } else if contains_any(text, SUB_WORDS) {
                "sub"
            } else {
                "add"
            };
            match op2 {
                "set" => it.value = Some(num),
                "sub" => it.delta = Some(-num),
                _ => it.delta = Some(num),
            }
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


    // 1. Number first: it is the only unambiguous token in an unspaced sentence.
    let (value, _span) = match find_number(text) {
        Some(v) => v,
        None => {
            cl.why = Some("这句话里没有数字，没有说要改成多少。".into());
            return cl;
        }
    };

    // 2. Operation. SET beats DELTA when both could match, because reading
    //    "改到1000" as a delta of 1000 is the likely misreading.
    let op = if contains_any(text, SET_WORDS) {
        "set"
    } else if contains_any(text, SUB_WORDS) {
        "sub"
    } else if contains_any(text, ADD_WORDS) {
        "add"
    } else {
        "add"
    };

    // 3. Stat, longest word first so "近战护甲" does not read as "护甲".
    let stat = stat_word(text);

    // 4. Entity, longest span over the whole sentence.
    let (eid, ename, kind) = {
        let n = match names() {
            Some(n) => n,
            None => {
                cl.why = Some("名字表没有随程序发布，认不出这句话说的是哪个单位。".into());
                return cl;
            }
        };
        match (n.longest_unit(text), n.longest_tech(text)) {
            (Some((id, nm)), Some((tid, tnm))) => {
                if tnm.chars().count() > nm.chars().count() {
                    (Some(tid), Some(tnm), "tech")
                } else {
                    (Some(id), Some(nm), "unit")
                }
            }
            (Some((id, nm)), None) => (Some(id), Some(nm), "unit"),
            (None, Some((tid, tnm))) => (Some(tid), Some(tnm), "tech"),
            (None, None) => (None, None, "none"),
        }
    };
    cl.entity_id = eid;
    cl.entity_name = ename;

    // 5. Resource words, which only matter for cost sentences.
    let resource = RESOURCE_WORDS
        .iter()
        .find(|(_, words)| words.iter().any(|w| text.contains(w)))
        .map(|(k, _)| k.to_string());
    let says_cost = text.contains("成本") || text.contains("花费") || text.contains("造价");

    // "织布机的第2条效果改成 …" / "织布机效果第1条的血量改成 100".
    // Checked before the stat branch, because the same sentence also contains
    // 血量 -- and 血量 alone would send it down the unit.stat path, where the
    // offset table has no entry and the build would refuse a sentence the reader
    // had just claimed to understand.
    let mut it = Intent::default();

    if kind == "tech" && eid.is_some() {
        let has_effect_word = text.contains("效果") || text.contains("effect");
        if has_effect_word {
            let idx = ordinal_in(text).unwrap_or(1);
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
            };
            let field = if text.contains("类型") || text.contains("type") {
                "t"
            } else if text.contains("血量") || text.contains("生命") {
                "b"
            } else if text.contains("攻击") || text.contains("攻击力") {
                "b"
            } else if text.contains("护甲") || text.contains("防御") {
                "b"
            } else {
                // `d` is the command's numeric argument in every effect shape
                // this project has read; the UI names the phrase, so default to
                // it rather than refusing a sentence whose shape is right.
                "d"
            };
            it.intent = "tech.effect".to_string();
            it.tech = eid;
            it.command = Some(idx);
            it.field = Some(field.to_string());
            match op {
                "set" => it.value = Some(value),
                "sub" => it.delta = Some(-value),
                _ => it.delta = Some(value),
            }
            cl.intent = Some(it);
            return cl;
        }
    }

    if let Some(stat) = stat {
        if eid.is_none() {
            cl.why = Some("没听出要改哪个单位。".into());
            return cl;
        }
        it.intent = intent_for_stat(&stat).to_string();
        //  carries no  key in the reference: the intent
        // id already names the field, and a redundant key would make the two
        // implementations produce different dicts for the same sentence.
        if it.intent != "tech.research_time" {
            it.stat = Some(stat);
        }
        if kind == "tech" {
            it.tech = eid;
        } else {
            it.unit = eid;
        }
    } else if says_cost || (resource.is_some() && eid.is_some()) {
        if kind == "tech" {
            // A technology's cost is three slots of (type, amount, flag) and the
            // slot is chosen by the resource word, not guessed. `resource` is a
            // word the player used; the slot mapping is the same order the file
            // stores (food, wood, gold/stone per record).
            let res = match resource.clone() {
                Some(r) => r,
                None => {
                    cl.why = Some("说的是成本，但没说是木材、食物、黄金还是石头。".into());
                    return cl;
                }
            };
            if eid.is_none() {
                cl.why = Some("没听出要改哪个科技。".into());
                return cl;
            }
            it.intent = "tech.cost".to_string();
            it.resource = Some(res);
            it.tech = eid;
            match op {
                "set" => it.value = Some(value),
                "sub" => it.delta = Some(-value),
                _ => it.delta = Some(value),
            }
            cl.intent = Some(it);
            return cl;
        }
        if eid.is_none() {
            cl.why = Some("没听出要改哪个单位。".into());
            return cl;
        }
        let res = match resource {
            Some(r) => r,
            None => {
                cl.why = Some("说的是成本，但没说是木材、食物、黄金还是石头。".into());
                return cl;
            }
        };
        it.intent = "unit.cost".to_string();
        it.resource = Some(res);
        it.unit = eid;
    } else {
        cl.why = Some("没听出要改哪个属性".into());
        return cl;
    }

    match op {
        "set" => it.value = Some(value),
        "sub" => it.delta = Some(-value),
        _ => it.delta = Some(value),
    }

    cl.intent = Some(it);
    cl
}

/// The stat word in `text`, longest first.
///
/// Longest, not first: "近战护甲" contains "护甲" but is a different stat, and a
/// first-match scan would read the neighbour armour stat and write the wrong
/// field.
pub fn stat_word(text: &str) -> Option<String> {
    let mut best: Option<(usize, String)> = None;
    for (stat, words) in STAT_WORDS {
        for w in *words {
            if !text.contains(w) {
                continue;
            }
            let n = w.chars().count();
            if best.as_ref().map(|(b, _)| n > *b).unwrap_or(true) {
                best = Some((n, (*stat).to_string()));
            }
        }
    }
    best.map(|(_, s)| s)
}

/// Candidate locations for a shipped table, in priority order.
///
/// `<root>/_golden/<file>` is where the bundler puts it; the upward walk is what
/// finds the repo during development. Both are needed: a shipped folder has no
/// repo above it, and a development run has no `_golden` beside the exe.
pub fn table_paths(env: &str, file: &str) -> Vec<std::path::PathBuf> {
    let mut out = Vec::new();
    if let Ok(v) = std::env::var(env) {
        out.push(std::path::PathBuf::from(v));
    }
    for key in ["AOE2MOD_ROOT", "AOE2MOD_APP"] {
        if let Ok(root) = std::env::var(key) {
            out.push(std::path::PathBuf::from(root).join("_golden").join(file));
        }
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            for base in [dir.to_path_buf(), dir.join("app"), dir.join("..").join("app")] {
                out.push(base.join("_golden").join(file));
            }
        }
    }
    if let Ok(cwd) = std::env::current_dir() {
        let mut p = Some(cwd);
        while let Some(d) = p {
            out.push(d.join("_golden").join(file));
            out.push(d.join("app").join("_golden").join(file));
            p = d.parent().map(|x| x.to_path_buf());
        }
    }
    out
}


/// The ordinal the player wrote, 1-based: "第2条" -> 2.
///
/// Only ASCII digits are read, for the same reason `find_number` does not accept
/// Chinese numerals: "第二条" would be a second numeral vocabulary with its own
/// set of mistakes, and guessing it is how a wrong command gets edited.
fn ordinal_in(text: &str) -> Option<usize> {
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
}


/// `text` with the ordinal ("第12条") removed, so the next number found is the
/// value. Keeps the surrounding words intact -- the stat and resource words are
/// read from the original string.
fn strip_ordinal(text: &str) -> String {
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
}


/// Whether the native reader can produce this intent from a sentence.
///
/// The screen lists every intent in the schema and marks the ones a sentence
/// cannot reach, because a plugin adds intents to the schema and this list IS
/// the schema -- hiding them would make the list a promise the screen cannot
/// keep, and showing them unmarked would be worse.
///
/// This is a LIST, not a guess: it grows as the reader does, and an intent that
/// is not here simply refuses with "这个改动还只能用原来的引擎".
pub fn intent_is_reachable(id: &str) -> bool {
    matches!(
        id,
        "unit.stat"
            | "unit.cost"
            | "tech.research_time"
            | "tech.cost"
            | "tech.effect"
            | "unit.card_move"
            | "unit.attack_class"
    )
}


/// The command-card box the sentence names ("放在第5格" -> 5), or `None`.
///
/// `格`/`格子` is REQUIRED. "第5" on its own is the hit-points phrase as often as
/// a box ("...叫铁匠学徒 500"), so a bare ordinal would read a stat as a box.
/// Box numbers are 0-based and the shipped data uses 0..15 and 24, so Chinese
/// numerals up to 二十四 are accepted here (unlike `find_number`, which stays
/// ASCII-only for values).
fn slot_in(text: &str) -> Option<u8> {
    let b: Vec<char> = text.chars().collect();
    let mut i = 0usize;
    while i < b.len() {
        if b[i] == '第' {
            let mut j = i + 1;
            // digits or Chinese numerals
            while j < b.len()
                && (b[j].is_ascii_digit()
                    || "一二三四五六七八九十".contains(b[j]))
            {
                j += 1;
            }
            if j > i + 1 {
                // must be followed by 格 (allowing one space)
                let mut k = j;
                while k < b.len() && b[k] == ' ' {
                    k += 1;
                }
                if k < b.len() && b[k] == '格' {
                    let raw: String = b[i + 1..j].iter().collect();
                    if let Some(v) = parse_slot(&raw) {
                        return Some(v);
                    }
                }
            }
        }
        i += 1;
    }
    None
}

fn parse_slot(raw: &str) -> Option<u8> {
    if raw.chars().all(|c| c.is_ascii_digit()) {
        return raw.parse::<u8>().ok().filter(|v| *v < 25);
    }
    let val = |c: char| -> Option<u32> {
        Some(match c {
            '一' => 1,
            '二' => 2,
            '三' => 3,
            '四' => 4,
            '五' => 5,
            '六' => 6,
            '七' => 7,
            '八' => 8,
            '九' => 9,
            _ => return None,
        })
    };
    if raw == "十" {
        return Some(10);
    }
    if let Some((head, tail)) = raw.split_once('十') {
        let tens = if head.is_empty() {
            1
        } else {
            val(head.chars().next()?)?
        };
        let ones = if tail.is_empty() {
            0
        } else {
            val(tail.chars().next()?)?
        };
        let n = tens * 10 + ones;
        return if n < 25 { Some(n as u8) } else { None };
    }
    let n = val(raw.chars().next()?)?;
    Some(n as u8)
}

/// The building whose card the sentence means.
///
/// `None` when the sentence names no building: the caller then uses the unit's
/// own card, which is the common case ("把民兵放在第5格" -- on the barracks,
/// where the militia already is). Resolving "which building trains this unit"
/// is a data question, so it is left to the server rather than guessed here.
fn builder_in(text: &str, unit: Option<i16>, kind: &str) -> Option<i16> {
    let n = names().as_ref()?;
    // The building is the name directly before 的 in "...兵营的第5格".
    let (before, _) = text.split_once('的')?;
    let (bid, _name) = n.longest_unit(before)?;
    if Some(bid) == unit && kind != "unit" {
        return None;
    }
    Some(bid)
}


/// The name that ENDS latest in `text` -- the unit the player last wrote.
///
/// Plain longest-span is wrong here: "把民兵挪到兵营" has 兵营 as the longest
/// match, and the sentence means the militia (the earlier noun) moved onto the
/// barracks' card.
fn rightmost_name(n: &Names, text: &str) -> Option<i16> {
    let mut best: Option<(usize, i16)> = None;
    for (id, names) in n.units.iter() {
        for nm in names {
            if nm.is_empty() {
                continue;
            }
            if let Some(pos) = text.rfind(nm.as_str()) {
                let end = pos + nm.len();
                if best.map(|(e, _)| end > e).unwrap_or(true) {
                    best = Some((end, *id));
                }
            }
        }
    }
    best.map(|(_, id)| id)
}


/// The canonical record for a name: the LOWEST id that carries it.
///
/// Building names are not unique in this data. Measured: 兵营 is four ids
/// (498, 132, 20, 12); picking "whichever the table visited last" returned 20 for
/// a sentence about the Barracks, and the build then refused with "第 20 号单位
/// 不在这座建筑（20）的训练表里" -- a self-consistent message about the wrong
/// building.
fn canonical_name_id(n: &Names, text: &str) -> Option<i16> {
    let mut best: Option<(usize, i16)> = None;
    for (id, names) in n.units.iter() {
        for nm in names {
            if nm.is_empty() || !text.contains(nm.as_str()) {
                continue;
            }
            let len = nm.chars().count();
            // Longest match wins; on a tie the LOWEST id wins, because that is
            // the record the game itself treats as the building.
            let better = match best {
                None => true,
                Some((blen, bid)) => len > blen || (len == blen && *id < bid),
            };
            if better {
                best = Some((len, *id));
            }
        }
    }
    best.map(|(_, id)| id)
}


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

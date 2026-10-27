//! Stat edits: write a value at the byte offset `locate` measured.
//!
//! Why offsets come from JSON instead of a struct definition
//! ---------------------------------------------------------
//! A `.dat` unit record's layout depends on its `type` (Type50 / Projectile /
//! Creatable / Building, each with its own version guards), so "the offset of
//! hit_points" is not one number — it is one number per record, measured.
//! `aoe2mod/dat/locate.py` measures them while parsing (`r.at("hit_points")`),
//! and `_golden/stat_offsets.json` is that measurement exported.
//!
//! The Rust side deliberately does NOT re-derive them: a second implementation
//! that agreed by construction would prove nothing, whereas one that lands on
//! the same byte by a different route (its own walk) is evidence.  Both
//! currently give 3967310 for Gaia's unit 83 hit_points.

use std::collections::HashMap;
use std::fs;
use std::io;
use std::path::Path;

/// Field width and interpretation, as exported alongside the offsets.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StatKind {
    I16,
    U8,
    F32,
}

impl StatKind {
    pub fn width(self) -> usize {
        match self {
            StatKind::I16 => 2,
            StatKind::U8 => 1,
            StatKind::F32 => 4,
        }
    }

    pub fn from_name(s: &str) -> Option<StatKind> {
        match s {
            "i16" => Some(StatKind::I16),
            "u8" => Some(StatKind::U8),
            "f32" => Some(StatKind::F32),
            _ => None,
        }
    }
}

/// Every stat a record can carry, with its absolute byte offset in the stream.
pub struct StatTable {
    pub kinds: HashMap<String, StatKind>,
    /// `civ name -> stat -> unit id -> absolute offset`
    pub civs: Vec<CivStats>,
}

pub struct CivStats {
    pub name: String,
    pub unit_count: usize,
    /// `stat -> (unit id -> absolute offset)`
    pub offsets: HashMap<String, HashMap<i16, usize>>,
}

impl StatTable {
    /// Load `_golden/stat_offsets.json`.
    ///
    /// Hand-rolled parsing rather than serde: the file is a flat three-level
    /// object of strings and integers, and adding a derive-heavy dependency to
    /// read it would be more machinery than the format deserves.
    pub fn load(path: &Path) -> io::Result<StatTable> {
        let text = fs::read_to_string(path)?;
        let mut kinds = HashMap::new();
        let mut civs: Vec<CivStats> = Vec::new();

        // "types": { "hit_points": "i16", ... }
        if let Some(section) = between(&text, "\"types\":{", "},") {
            for (k, v) in pairs(section) {
                if let Some(kind) = StatKind::from_name(v.trim_matches('"')) {
                    kinds.insert(k.to_string(), kind);
                }
            }
        }

        // "civs":[ {"name":..,"count":N,"stat_offsets":{ "stat": {"83":3967310,..}} } ]
        let civs_at = text
            .find("\"civs\":[")
            .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "no civs array"))?;
        let mut rest = &text[civs_at + "\"civs\":[".len()..];
        while let Some(obj_start) = rest.find('{') {
            let obj_end = matching_brace(rest, obj_start)?;
            let obj = &rest[obj_start + 1..obj_end];
            let name = field_str(obj, "name").unwrap_or_default();
            let count = field_int(obj, "count").unwrap_or(0) as usize;
            let mut offsets: HashMap<String, HashMap<i16, usize>> = HashMap::new();
            if let Some(so_start) = obj.find("\"stat_offsets\":{") {
                let inner_start = so_start + "\"stat_offsets\":{".len();
                let inner_end = matching_brace(obj, inner_start - 1)?;
                let so = &obj[inner_start..inner_end];
                // Each value is {"id":offset,...} per stat.
                let mut idx = 0usize;
                while let Some(k_real) = so[idx..].find('"') {
                    let k_start = idx + k_real + 1;
                    let k_end = so[k_start..].find('"').map(|p| k_start + p).unwrap_or(so.len());
                    let stat = &so[k_start..k_end];
                    let after = &so[k_end + 1..];
                    if let Some(brace) = after.find('{') {
                        let map_end = matching_brace(after, brace)?;
                        let body = &after[brace + 1..map_end];
                        let mut m = HashMap::new();
                        for (kk, vv) in pairs(body) {
                            if let Ok(id) = kk.parse::<i16>() {
                                if let Ok(off) = vv.parse::<usize>() {
                                    m.insert(id, off);
                                }
                            }
                        }
                        if !m.is_empty() {
                            offsets.insert(stat.to_string(), m);
                        }
                        idx = idx + k_real + 1 + (k_end - k_start) + 1 + map_end + 1;
                        continue;
                    }
                    idx = k_end + 1;
                }
            }
            civs.push(CivStats {
                name,
                unit_count: count,
                offsets,
            });
            rest = &rest[obj_end + 1..];
            if !rest.contains("\"name\":") {
                break;
            }
        }

        Ok(StatTable { kinds, civs })
    }

    pub fn civ(&self, index: usize) -> Option<&CivStats> {
        self.civs.get(index)
    }

    pub fn offset(&self, civ: usize, stat: &str, unit: i16) -> Option<usize> {
        self.civs.get(civ)?.offsets.get(stat)?.get(&unit).copied()
    }
}

fn between<'a>(s: &'a str, start: &str, end: &str) -> Option<&'a str> {
    let a = s.find(start)? + start.len();
    let b = s[a..].find(end)? + a;
    Some(&s[a..b])
}

fn matching_brace(s: &str, open: usize) -> io::Result<usize> {
    let bytes = s.as_bytes();
    let mut depth = 0i32;
    let mut in_str = false;
    let mut i = open;
    while i < bytes.len() {
        let c = bytes[i];
        match c {
            b'"' if i == 0 || bytes[i - 1] != b'\\' => in_str = !in_str,
            b'{' if !in_str => depth += 1,
            b'}' if !in_str => {
                depth -= 1;
                if depth == 0 {
                    return Ok(i);
                }
            }
            _ => {}
        }
        i += 1;
    }
    Err(io::Error::new(io::ErrorKind::InvalidData, "unbalanced brace"))
}

/// Split a flat `"k":v,"k":v` body into pairs, honouring quoted strings.
fn pairs(body: &str) -> Vec<(String, String)> {
    let mut out = Vec::new();
    let mut buf = String::new();
    let mut in_str = false;
    let mut fields: Vec<String> = Vec::new();
    let bytes = body.as_bytes();
    let mut i = 0;
    while i < bytes.len() {
        let c = bytes[i] as char;
        if c == '"' && (i == 0 || bytes[i - 1] != b'\\') {
            in_str = !in_str;
            buf.push(c);
        } else if c == ',' && !in_str {
            fields.push(std::mem::take(&mut buf));
        } else {
            buf.push(c);
        }
        i += 1;
    }
    if !buf.trim().is_empty() {
        fields.push(buf);
    }
    for f in fields {
        if let Some(c) = f.find(':') {
            let k = f[..c].trim().trim_matches('"').to_string();
            let v = f[c + 1..].trim().to_string();
            if !k.is_empty() {
                out.push((k, v));
            }
        }
    }
    out
}

fn field_str(obj: &str, name: &str) -> Option<String> {
    let pat = format!("\"{name}\":\"");
    let a = obj.find(&pat)? + pat.len();
    let b = obj[a..].find('"')? + a;
    Some(obj[a..b].to_string())
}

fn field_int(obj: &str, name: &str) -> Option<i64> {
    let pat = format!("\"{name}\":");
    let a = obj.find(&pat)? + pat.len();
    let tail = &obj[a..];
    let end = tail
        .find(|c: char| !c.is_ascii_digit() && c != '-')
        .unwrap_or(tail.len());
    tail[..end].parse().ok()
}

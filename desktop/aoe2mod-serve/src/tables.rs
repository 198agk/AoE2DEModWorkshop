//! `/api/forms` and `/api/locale`: the page's own tables, read fresh per request.
//!
//! Why these are routes and not keys baked into `/api/meta`
//! --------------------------------------------
//! A plugin dropped in while the tool runs changes the sentence table, and
//! `meta` is fetched once at page load. Measured 2026-10-25: a vocabulary cache
//! keyed on a constant made a live plugin's words appear everywhere except the
//! reader. So both tables are read from disk on every request.
//!
//! A malformed file must not take the page down: the page falls back to the
//! free-text box, which is the older path. So a parse failure yields the
//! built-in defaults rather than an error.

use std::path::{Path, PathBuf};

/// Where the schema roots are: the shipped one, plus any plugin root.
///
/// `AOE2MOD_PLUGINS` REPLACES the default rather than adding to it, which is what
/// lets a test say "the plugin root is empty" and get exactly the shipped
/// schema -- if the repo directory were always appended, a test would silently
/// inherit whatever happened to be checked in.
pub fn schema_roots(app_dir: &Path) -> Vec<PathBuf> {
    let mut out = Vec::new();
    out.push(app_dir.join("aoe2mod/schema"));
    if let Ok(env) = std::env::var("AOE2MOD_PLUGINS") {
        for p in std::env::split_paths(&env) {
            if p.is_dir() {
                out.push(p);
            }
        }
    } else if let Some(parent) = app_dir.parent() {
        let plugins = parent.join("plugins");
        if plugins.is_dir() {
            out.push(plugins);
        }
    }
    out
}

/// The merged sentence table: `{version, op_choices, intents}`.
///
/// Merged rather than replaced, because a plugin adds intents to the shipped
/// ones. The merge is per-intent: a plugin that names an intent the shipped
/// table already has replaces that entry, which is how a plugin can correct a
/// template without owning the whole file.
pub fn load_sentences(app_dir: &Path) -> serde_json::Value {
    let mut doc = serde_json::json!({
        "version": 1,
        "op_choices": ["改成", "加", "减"],
        "intents": {},
    });
    for root in schema_roots(app_dir) {
        // A plugin root contains `<name>/schema/sentences.json`; the shipped
        // root contains `sentences.json` directly. Both shapes are accepted,
        // because both exist in this project.
        let mut candidates = vec![root.join("sentences.json")];
        if let Ok(entries) = std::fs::read_dir(&root) {
            for e in entries.flatten() {
                let p = e.path();
                if p.is_dir() {
                    candidates.push(p.join("schema/sentences.json"));
                }
            }
        }
        for path in candidates {
            let text = match std::fs::read_to_string(&path) {
                Ok(t) => t.replace('\u{feff}', ""),
                Err(_) => continue,
            };
            let part: serde_json::Value = match serde_json::from_str(&text) {
                Ok(v) => v,
                Err(e) => {
                    // Loud in the log, silent on the wire: the page keeps
                    // working with the other roots' templates.
                    eprintln!("sentences {}: {e}", path.display());
                    continue;
                }
            };
            merge(&mut doc, &part);
        }
    }
    doc
}

fn merge(doc: &mut serde_json::Value, part: &serde_json::Value) {
    if let Some(oc) = part.get("op_choices").and_then(|v| v.as_array()) {
        if !oc.is_empty() {
            doc["op_choices"] = serde_json::Value::Array(oc.clone());
        }
    }
    if let Some(intents) = part.get("intents").and_then(|v| v.as_object()) {
        for (k, v) in intents {
            doc["intents"][k.as_str()] = v.clone();
        }
    }
}

/// `{ok, forms, op_choices}`: a FLAT list of forms, in table order.
///
/// Flat, not grouped by intent. The Python original returns 21 form objects for
/// 14 intents, because one intent can offer several sentence shapes, and the
/// page renders the list. Grouping by intent would silently drop every intent's
/// second and third form -- which is what a first version of this function did
/// (14 instead of 21, with nothing on screen to say so).
pub fn forms(app_dir: &Path, intent: Option<&str>) -> serde_json::Value {
    let table = load_sentences(app_dir);
    let empty = serde_json::Map::new();
    let intents = table
        .get("intents")
        .and_then(|v| v.as_object())
        .unwrap_or(&empty);
    let mut out: Vec<serde_json::Value> = Vec::new();
    for (name, spec) in intents {
        if let Some(want) = intent {
            if name != want {
                continue;
            }
        }
        let forms = match spec.get("forms").and_then(|v| v.as_array()) {
            Some(f) => f,
            None => continue,
        };
        for f in forms {
            out.push(serde_json::json!({
                "intent": name,
                "intent_label": spec.get("label").cloned(),
                "id": f.get("id").cloned(),
                "label": f.get("label").cloned(),
                "template": f.get("template").cloned(),
                "slots": f.get("slots").cloned().unwrap_or(serde_json::json!([])),
            }));
        }
    }
    serde_json::json!({
        "ok": true,
        "forms": out,
        "op_choices": table.get("op_choices").cloned().unwrap_or(serde_json::json!([])),
    })
}

/// `{ok, locale, strings}`: the page's own wording.
///
/// The point of this table is that the page holds no Chinese prose of its own,
/// so a wording change is a data edit. A missing locale yields an empty table
/// rather than an error, and the markup keeps its inline Chinese as the
/// fallback -- that is why nothing goes blank when this file is absent.
pub fn locale(app_dir: &Path, name: &str) -> serde_json::Value {
    let mut strings = serde_json::Map::new();
    for root in schema_roots(app_dir) {
        let path = root.join("locales").join(format!("{name}.json"));
        let text = match std::fs::read_to_string(&path) {
            Ok(t) => t.replace('\u{feff}', ""),
            Err(_) => continue,
        };
        if let Ok(v) = serde_json::from_str::<serde_json::Value>(&text) {
            // The file is `{"$comment": ..., "locale": "zh", "strings": {...}}`
            // and the page wants the INNER object, flattened with dots. Taking
            // the whole document put `$comment` and a `strings.` prefix on every
            // key, which would have made every lookup miss.
            match v.get("strings") {
                Some(inner) => collect(&mut strings, inner, ""),
                None => collect(&mut strings, &v, ""),
            }
        }
    }
    serde_json::json!({
        "ok": true,
        "locale": name,
        "strings": serde_json::Value::Object(strings),
    })
}

/// Flatten nested objects to dotted keys, which is the shape the page expects
/// (`status.frobnicated` for `{"status":{"frobnicated":...}}`).
fn collect(out: &mut serde_json::Map<String, serde_json::Value>, v: &serde_json::Value, prefix: &str) {
    match v {
        serde_json::Value::Object(m) => {
            for (k, val) in m {
                let key = if prefix.is_empty() {
                    k.clone()
                } else {
                    format!("{prefix}.{k}")
                };
                collect(out, val, &key);
            }
        }
        other => {
            if !prefix.is_empty() {
                out.insert(prefix.to_string(), other.clone());
            }
        }
    }
}

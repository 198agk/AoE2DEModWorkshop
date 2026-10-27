//! `/api/ai-meta` and `/api/ai-sentences`: the optional AI entry point.
//!
//! The project's standing constraint is "AI only through an API with the
//! user's own key, and everything must still work offline". So the local grammar
//! is the fast path and a model is an upgrade, never a requirement.
//!
//! `available` is the only thing the page reads to decide whether to draw the AI
//! box at all: a box that always fails is worse than none. It is keyless and
//! makes no call -- it just says whether a key is configured.
//!
//! `writes: "sentences"` is not a hint. This build NEVER turns a model's answer
//! into an edit: the endpoint writes sentences and the reader judges them, so
//! every refusal and preview a human sees applies unchanged.

use serde_json::Value;

const KEY_ENV: &str = "AOE2MOD_AI_KEY";
const BASE_ENV: &str = "AOE2MOD_AI_BASE";
const MODEL_ENV: &str = "AOE2MOD_AI_MODEL";
const DEFAULT_BASE: &str = "https://api.deepseek.com";
const DEFAULT_MODEL: &str = "deepseek-chat";

pub struct Config {
    pub base: String,
    pub key: String,
    pub model: String,
}

/// `None` when no key is configured, which is the common case and not an error.
pub fn config() -> Option<Config> {
    let key = std::env::var(KEY_ENV).ok().filter(|s| !s.trim().is_empty())?;
    let base = std::env::var(BASE_ENV)
        .ok()
        .filter(|s| !s.trim().is_empty())
        .unwrap_or_else(|| DEFAULT_BASE.to_string());
    let model = std::env::var(MODEL_ENV)
        .ok()
        .filter(|s| !s.trim().is_empty())
        .unwrap_or_else(|| DEFAULT_MODEL.to_string());
    Some(Config {
        base: base.trim_end_matches('/').to_string(),
        key,
        model,
    })
}

/// The grammar shown on screen and given to the endpoint.
///
/// Rendered from `_golden/ai_grammar.json`, which is exported from the reader
/// itself (`_probe/make_ai_grammar.py`), because which intents a SENTENCE can
/// reach is a property of the hand-written reader and not something to
/// re-derive here.
///
/// The API-only line is not decoration: a model told only about ten of thirteen
/// will confidently write sentences for thirteen, and every one of those becomes
/// a refusal the player has to read.
pub fn grammar(app_dir: &std::path::Path) -> String {
    let doc = grammar_data(app_dir);
    let rows = doc.get("intents").and_then(|v| v.as_array()).cloned().unwrap_or_default();
    let mut lines: Vec<String> = vec!["这个工具能听懂的意图：".to_string()];
    let mut api_only: Vec<String> = Vec::new();
    for row in &rows {
        let reachable = row.get("by_sentence").and_then(|v| v.as_bool()).unwrap_or(false);
        let id = row.get("id").and_then(|v| v.as_str()).unwrap_or("");
        let title = row.get("title").and_then(|v| v.as_str()).unwrap_or("");
        let fields: Vec<String> = row
            .get("fields")
            .and_then(|v| v.as_array())
            .map(|a| a.iter().filter_map(|x| x.as_str().map(|s| s.to_string())).collect())
            .unwrap_or_default();
        if !reachable {
            api_only.push(id.to_string());
            continue;
        }
        lines.push(format!("· {id} —— {title}（字段：{}）", fields.join("、")));
    }
    api_only.sort();
    if !api_only.is_empty() {
        lines.push(format!(
            "只能用接口、句子还写不出来的：{}（不要为这些编句子）。",
            api_only.join("、")
        ));
    }
    lines.push(String::new());
    lines.push("已经验证能解析的例句：".to_string());
    if let Some(ex) = doc.get("examples").and_then(|v| v.as_array()) {
        for e in ex {
            if let Some(s) = e.as_str() {
                lines.push(format!("· {s}"));
            }
        }
    }
    lines.join("\n")
}

fn grammar_data(app_dir: &std::path::Path) -> Value {
    // Walk up from the app dir AND from the current dir: the shell starts this
    // wherever the exe lives, `cargo run` starts it in the crate dir, and a test
    // starts it wherever pytest is. A fixed relative path is a guess about the
    // caller's cwd.
    let mut roots: Vec<std::path::PathBuf> = Vec::new();
    let mut p = Some(app_dir.to_path_buf());
    while let Some(d) = p {
        roots.push(d.clone());
        p = d.parent().map(|x| x.to_path_buf());
    }
    if let Ok(cwd) = std::env::current_dir() {
        let mut p = Some(cwd);
        while let Some(d) = p {
            roots.push(d.clone());
            p = d.parent().map(|x| x.to_path_buf());
        }
    }
    for root in roots {
        for rel in ["_golden/ai_grammar.json", "ai_grammar.json"] {
            let path = root.join(rel);
            if let Ok(t) = std::fs::read_to_string(&path) {
                if let Ok(v) = serde_json::from_str::<Value>(&t) {
                    return v;
                }
            }
        }
    }
    serde_json::json!({"intents": [], "examples": []})
}

pub fn meta_json(app_dir: &std::path::Path) -> Value {
    let cfg = config();
    let table = crate::tables::load_sentences(app_dir);
    let empty = serde_json::Map::new();
    let intents = table
        .get("intents")
        .and_then(|v| v.as_object())
        .unwrap_or(&empty);
    let mut brief = Vec::new();
    for (id, spec) in intents {
        brief.push(serde_json::json!({
            "id": id,
            "title": spec.get("label")
                .or_else(|| spec.get("title"))
                .cloned()
                .unwrap_or_else(|| Value::String(id.clone())),
            "fields": spec.get("fields").cloned().unwrap_or(serde_json::json!([])),
        }));
    }
    serde_json::json!({
        "ok": true,
        "available": cfg.is_some(),
        "model": cfg.as_ref().map(|c| c.model.clone()),
        "base": cfg.as_ref().map(|c| c.base.clone()),
        "grammar": grammar(app_dir),
        "intents": brief,
        "writes": "sentences",
    })
}

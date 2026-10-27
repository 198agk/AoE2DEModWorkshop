"""One-off: keep the civilization scope in the build record.

Found while testing the new scope: `/api/rebuild` replays the intent a build
record kept, and that intent did not carry `civs`.  So rebuilding
「不列颠村民血量改成100」 replayed an UNSCOPED intent and silently widened the mod
to all 63 civilizations -- a recorded edit whose replay is a different edit.
Nothing reported it: the rebuild succeeded, the file existed, the count was
plausible.
"""
import io

# --- stat_edit.rs -------------------------------------------------------------
p = 'desktop/aoe2mod-serve/src/stat_edit.rs'
s = io.open(p, encoding='utf-8').read()

# A helper next to the other two scope helpers.
anchor = '''/// Whether a civilisation record is in scope.'''
helper = '''/// The intent a build record keeps, so that a later rebuild reproduces THIS
/// edit and not a wider one.
///
/// `civs` was left out of the record the first time round.  Rebuilding
/// 「不列颠村民血量改成100」 then replayed an intent with no scope and silently
/// widened the mod to all 63 civilizations -- the file existed, the count was
/// plausible, and the edit that came back was not the edit that was asked for.
fn recorded_intent(fields: serde_json::Value, req: &serde_json::Value) -> serde_json::Value {
    let mut obj = match fields {
        serde_json::Value::Object(m) => m,
        _ => serde_json::Map::new(),
    };
    if let Some(c) = req.get("civs") {
        if !c.is_null() {
            obj.insert("civs".to_string(), c.clone());
        }
    }
    serde_json::json!([serde_json::Value::Object(obj)])
}

/// Whether a civilisation record is in scope.'''
assert s.count(anchor) == 1
s = s.replace(anchor, helper, 1)

# Each builder's record.  The macro form differs per site, so this rewrites the
# opening and the closing of exactly the five `json!([{ ... }])` literals that
# describe a scoped edit.
SITES = [
    ('''        serde_json::json!([{
            "intent": "unit.stat",
            "unit": unit,
            "stat": stat,
            "value": new_value
        }]),''',
     '''        recorded_intent(
            serde_json::json!({
                "intent": "unit.stat",
                "unit": unit,
                "stat": stat,
                "value": new_value
            }),
            req,
        ),'''),
    ('''        serde_json::json!([{
            "intent": intent,
            "unit": unit,
            "resource": req.get("resource").cloned().unwrap_or(serde_json::Value::Null),
            "attack_kind": req.get("attack_kind").cloned().unwrap_or(serde_json::Value::Null),
            "value": new_value
        }]),''',
     '''        recorded_intent(
            serde_json::json!({
                "intent": intent,
                "unit": unit,
                "resource": req.get("resource").cloned().unwrap_or(serde_json::Value::Null),
                "attack_kind": req.get("attack_kind").cloned().unwrap_or(serde_json::Value::Null),
                "value": new_value
            }),
            req,
        ),'''),
    ('''        serde_json::json!([{
            "intent": intent,
            "tech": tech,
            "resource": req.get("resource").cloned().unwrap_or(serde_json::Value::Null),
            "value": new_value
        }]),''',
     '''        recorded_intent(
            serde_json::json!({
                "intent": intent,
                "tech": tech,
                "resource": req.get("resource").cloned().unwrap_or(serde_json::Value::Null),
                "value": new_value
            }),
            req,
        ),'''),
]
for old, new in SITES:
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new, 1)

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('stat_edit.rs: 3 records now keep civs')

# --- rebuild.rs ---------------------------------------------------------------
p = 'desktop/aoe2mod-serve/src/rebuild.rs'
s = io.open(p, encoding='utf-8').read()

old = '''            if let Some(d) = delta {
                req["delta"] = serde_json::json!(d);
            }'''
new = '''            if let Some(d) = delta {
                req["delta"] = serde_json::json!(d);
            }
            // Replay the scope too.  Without it the rebuild reproduces a WIDER
            // edit than the one that was recorded, which is the quietest way to
            // undo the player's "只改不列颠" without ever contradicting them.
            if let Some(c) = intent.get("civs") {
                if !c.is_null() {
                    req["civs"] = c.clone();
                }
            }'''
assert s.count(old) == 1
s = s.replace(old, new, 1)

old = '''/// intent. Only stat edits are replayable today; everything else says so.'''
new = '''/// intent. Only stat edits are replayable today; everything else says so.
///
/// A replayed intent must be the SAME edit, scope included: `civs` is copied
/// through, because dropping it turns 「只改不列颠」 into all 63 civilizations
/// and reports success.'''
assert s.count(old) == 1
s = s.replace(old, new, 1)

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('rebuild.rs: replay carries the scope')

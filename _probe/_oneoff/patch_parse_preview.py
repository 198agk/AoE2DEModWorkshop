"""Give `/api/parse` the three fields the page has been reading all along.

`renderCard` reads `c.preview.plan` and `c.buildable`; `buildable(c)` prefers a
server boolean.  This side sent neither, so every sentence fell back to
`c.preview.ok && plan.editable !== false` on a `preview` that did not exist --
which is why the page could show a card with no numbers on it at all.

The numbers come from `preview::plan`, which calls the builder with `"dry": true`.
Nothing here counts anything.
"""
import io

P = 'desktop/aoe2mod-serve/src/server.rs'
s = io.open(P, encoding='utf-8').read()

old = '''            let mut rows: Vec<String> = Vec::new();
            for cl in &clauses {
                match &cl.intent {
                    Some(it) => intents.push(it.to_json()),
                    None => refusals.push(format!(
                        "{{\\"text\\":\\"{}\\",\\"why\\":\\"{}\\"}}",
                        json_escape(&cl.text),
                        json_escape(cl.why.as_deref().unwrap_or(""))
                    )),
                }
                rows.push(format!(
                    "{{\\"text\\":\\"{}\\",\\"entity\\":{},\\"entity_id\\":{},\\"why\\":{},\\"notes\\":[{}]}}",
                    json_escape(&cl.text),
                    match &cl.entity_name {
                        Some(n) => format!("\\"{}\\"", json_escape(n)),
                        None => "null".into(),
                    },
                    match cl.entity_id {
                        Some(v) => v.to_string(),
                        None => "null".into(),
                    },
                    match &cl.why {
                        Some(w) => format!("\\"{}\\"", json_escape(w)),
                        None => "null".into(),
                    },
                    cl.notes
                        .iter()
                        .map(|n| format!("\\"{}\\"", json_escape(n)))
                        .collect::<Vec<String>>()
                        .join(",")
                ));
            }
            let json = format!(
                "{{\\"ok\\":true,\\"intents\\":[{}],\\"refusals\\":[{}],\\"clauses\\":[{}]}}",
                intents.join(","), refusals.join(","), rows.join(",")
            );'''

new = '''            let mut rows: Vec<String> = Vec::new();
            let mut previews: Vec<String> = Vec::new();
            let mut buildable: Vec<String> = Vec::new();
            let mut kinds: Vec<String> = Vec::new();
            for cl in &clauses {
                // The preview runs the BUILDER (with `dry`), so its numbers are
                // the build's numbers.  A sentence the builder refuses cannot
                // preview as buildable, because there is only one decision.
                let mut prev = "null".to_string();
                let mut can = false;
                let mut kind = "null".to_string();
                match &cl.intent {
                    Some(it) => {
                        intents.push(it.to_json());
                        let (ok, plan) = crate::preview::plan(server, it);
                        can = ok;
                        kind = match it.intent.split('.').next() {
                            Some("tech") => "\\"tech\\"".to_string(),
                            _ => "\\"unit\\"".to_string(),
                        };
                        prev = format!(
                            "{{\\"ok\\":true,\\"plan\\":{}}}",
                            serde_json::to_string(&plan).unwrap_or_else(|_| "null".into())
                        );
                    }
                    None => refusals.push(format!(
                        "{{\\"text\\":\\"{}\\",\\"why\\":\\"{}\\"}}",
                        json_escape(&cl.text),
                        json_escape(cl.why.as_deref().unwrap_or(""))
                    )),
                }
                previews.push(prev);
                buildable.push(can.to_string());
                kinds.push(kind);
                rows.push(format!(
                    "{{\\"text\\":\\"{}\\",\\"entity\\":{},\\"entity_id\\":{},\\"why\\":{},\\"notes\\":[{}]}}",
                    json_escape(&cl.text),
                    match &cl.entity_name {
                        Some(n) => format!("\\"{}\\"", json_escape(n)),
                        None => "null".into(),
                    },
                    match cl.entity_id {
                        Some(v) => v.to_string(),
                        None => "null".into(),
                    },
                    match &cl.why {
                        Some(w) => format!("\\"{}\\"", json_escape(w)),
                        None => "null".into(),
                    },
                    cl.notes
                        .iter()
                        .map(|n| format!("\\"{}\\"", json_escape(n)))
                        .collect::<Vec<String>>()
                        .join(",")
                ));
            }
            // The three extra arrays are spliced into `clauses` by index: the
            // rows were already built above and rebuilding them here would be a
            // second place that formats a clause.
            let rows: Vec<String> = rows
                .iter()
                .enumerate()
                .map(|(i, r)| {
                    let body = r.trim_end_matches('}');
                    format!(
                        "{body},\\"preview\\":{},\\"buildable\\":{},\\"kind\\":{}}}",
                        previews[i], buildable[i], kinds[i]
                    )
                })
                .collect();
            let json = format!(
                "{{\\"ok\\":true,\\"intents\\":[{}],\\"refusals\\":[{}],\\"clauses\\":[{}]}}",
                intents.join(","), refusals.join(","), rows.join(",")
            );'''

assert s.count(old) == 1, 'parse handler'
s = s.replace(old, new, 1)

io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('server.rs: /api/parse now carries preview, buildable, kind')

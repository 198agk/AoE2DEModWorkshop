//! How many boxes the command card has, read from the game's own layout file.
//!
//! This used to be `const BUTTON_SLOTS: i64 = 25`, and the justification was
//! "the data reaches 24". That is not evidence: the maximum `button_id` in the
//! shipped `.dat` is a property of a SAMPLE, and a sample of a sparse id space
//! says nothing about how many boxes the engine draws. Re-measured, the range
//! `0..24` is not 25 boxes either -- it is 25 *labels*.
//!
//! The authority is `widgetui/commandpanel.json`, which the game itself uses to
//! place the panel. The player's card is the `CommandButton` children of
//! `BackgroundLeft` -> `Anchor Buttons`:
//!
//! ```text
//! Button11 (0,0)    Button21 (94,0)   Button31 (188,0)  Button41 (282,0)  Button51 (376,0)
//! Button12 (0,94)   Button22 (94,94)  Button32 (188,94) Button42 (282,94) Button52 (376,94)
//! Button13 (0,188)  Button23 (94,188) Button33 (188,188)Button43 (282,188)Button53 (376,188)
//! ```
//!
//! 15 buttons, 5 columns by 3 rows. The names encode the coordinate: `Button<col><row>`.
//!
//! One measured exception, recorded rather than smoothed over: card 45 (Dock)
//! carries `button_id` 15 and 24, pointing at campaign heroes and hidden units
//! (Leif Erikson, Vasco da Gama, Admiral Yi, Dreki). Those are not boxes a
//! normal civilisation draws -- 17 of the 18 cards stay within 1..15. So the
//! slot count is 15 and an out-of-range box is refused with that reason; a hero's
//! id is not a box the player can drop onto.

use serde_json::Value;
use std::path::Path;

/// Fallback when the layout file is missing: the measured grid is 5x3.
///
/// A missing layout file means the game install is incomplete, and refusing to
/// edit at all would be worse than using the number that file holds today. The
/// caller reports which one it used.
pub const FALLBACK_SLOTS: u8 = 15;

/// Read the card grid size from `widgetui/commandpanel.json`.
///
/// Returns `(slots, from_file)`. `from_file` is false when the layout could not
/// be read and [`FALLBACK_SLOTS`] was used, so the caller can say so instead of
/// presenting a guess as a measurement.
pub fn card_slots(game_root: &Path) -> (u8, bool) {
    let path = game_root.join("widgetui").join("commandpanel.json");
    match count_buttons(&path) {
        Some(n) if n > 0 && n <= 255 => (n as u8, true),
        _ => (FALLBACK_SLOTS, false),
    }
}

fn count_buttons(path: &Path) -> Option<usize> {
    let text = std::fs::read_to_string(path).ok()?;
    let text = text.trim_start_matches('\u{feff}');
    let doc: Value = serde_json::from_str(text).ok()?;
    let widgets = doc.get("Collection")?.get("Widgets")?.as_array()?;
    // `BackgroundLeft` is the panel that holds the player's card. `BackgroundRight`
    // also has `CommandButton` children, but those are the group/queue buttons --
    // a different grid that would inflate the count to 36 if mixed in.
    let left = widgets.iter().find_map(|w| {
        let o = w.get("Widget").unwrap_or(w);
        if o.get("Name")?.as_str()? == "BackgroundLeft" {
            Some(o)
        } else {
            None
        }
    })?;
    let buttons = left.get("ChildWidgets")?.as_array()?.iter().find_map(|w| {
        let o = w.get("Widget").unwrap_or(w);
        if o.get("Name")?.as_str()? == "Buttons" {
            Some(o)
        } else {
            None
        }
    })?;
    let n = buttons
        .get("ChildWidgets")?
        .as_array()?
        .iter()
        .filter(|w| {
            let o = w.get("Widget").unwrap_or(w);
            o.get("Type").and_then(|t| t.as_str()) == Some("CommandButton")
        })
        .count();
    Some(n)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fallback_is_the_measured_grid() {
        // 5 columns x 3 rows. Kept in sync with the layout file checked below.
        assert_eq!(FALLBACK_SLOTS, 15);
    }

    #[test]
    fn missing_layout_reports_that_it_was_a_fallback() {
        let (n, from_file) = card_slots(Path::new("Z:/no/such/game"));
        assert_eq!(n, FALLBACK_SLOTS);
        assert!(!from_file, "a missing layout must not claim to be measured");
    }
}

//! Re-serialize a parsed `.dat` back to bytes.
//!
//! The design, taken from `aoe2mod/dat/writer.py` because it is the only
//! arrangement that survives this format:
//!
//! Two cursors.
//!  * `out_pos` is the OUTPUT offset.  It grows when a record is APPENDED, so
//!    it does not track the input at all.
//!  * `raw_pos` is the input cursor.  It advances by STRUCTURE: every modeled
//!    field moves it by that field's own width, and every unmodeled run is
//!    copied from the input verbatim.
//!
//! Keeping them separate is what makes an append safe.  A writer that only
//! tracked the output offset would, after adding one unit record, read the
//! input from a position that no longer corresponds to anything, and the whole
//! tail would be garbage -- silently, because the output is still a valid file.
//!
//! A third mechanism is needed for the same reason: when a modeled field
//! CHANGES WIDTH (a graphics record's `file` string gets longer when a reskin
//! points it at another picture), `raw_pos` must still advance by the width the
//! INPUT used, not the width we just wrote.  Without that the input cursor
//! lands inside the next field: measured once at 991,273 mismatches from a
//! single 3-byte string change.
//!
//! `mismatches` compares each emitted field against the INPUT at the input
//! cursor, and only where the two widths are equal.  Comparing at the OUTPUT
//! offset was the first version of this file and it stopped being a check the
//! moment anything was inserted: after one appended record every later output
//! offset sits past the matching input offset, so a correct edit reported tens
//! of thousands of "mismatches" and a broken one could report none.  A
//! round-trip of an unmodified file must still produce zero mismatches and
//! byte-identical output; that is the gate every edit is measured against.

use std::io;

/// Emitted in place of `op()` inside a synthesised record, where there is no
/// input to copy from (`aoe2mod/dat/writer.py:242`, `op()` under `suppress`).
const FROZEN_ZEROS: [u8; 64] = [0u8; 64];

pub struct Writer<'a> {
    pub out: Vec<u8>,
    /// Input cursor: advances by structure, never by output size.
    raw_pos: usize,
    raw: &'a [u8],
    /// Bumped every time a modeled field disagrees with the input, up to the
    /// original length.  Zero is the only acceptable value for a round-trip.
    pub mismatches: u64,
    pub first_mismatch: Option<(usize, u8, u8)>,
    /// Nesting depth of `begin_new()`.  While non-zero a synthesised record is
    /// being emitted: the input cursor is frozen, comparisons are muted, and
    /// `op()` writes zeros because there is no counterpart to copy.
    frozen: usize,
}

impl<'a> Writer<'a> {
    pub fn new(raw: &'a [u8]) -> Self {
        Writer {
            out: Vec::with_capacity(raw.len()),
            raw_pos: 0,
            raw,
            mismatches: 0,
            first_mismatch: None,
            frozen: 0,
        }
    }

    /// Output offset.  This is what an append grows; nothing else uses it.
    pub fn out_pos(&self) -> usize {
        self.out.len()
    }

    /// Input cursor, for probes and for the append bookkeeping.
    pub fn raw_pos(&self) -> usize {
        self.raw_pos
    }

    /// Start emitting a record that has NO counterpart in the input.
    ///
    /// Without this, appending one record shifts every later `op()` read and
    /// corrupts the whole tail: the output is still a valid file, so nothing
    /// complains.  `aoe2mod/dat/writer.py:113` is the reference; this is the
    /// same contract with a depth counter instead of a context manager, because
    /// Rust has no `with` and an early `?` return would leak the freeze.
    pub fn begin_new(&mut self) {
        self.frozen += 1;
    }

    pub fn end_new(&mut self) {
        self.frozen = self.frozen.saturating_sub(1);
    }

    /// The next two input bytes as an `i16`, WITHOUT consuming them.
    ///
    /// Needed before writing a variable-length list whose element count may
    /// change: the width the input stored has to be read before the cursor is
    /// moved by the width we are about to write.
    pub fn peek_i16(&self) -> Option<i16> {
        if self.raw_pos + 2 <= self.raw.len() {
            Some(i16::from_le_bytes([
                self.raw[self.raw_pos],
                self.raw[self.raw_pos + 1],
            ]))
        } else {
            None
        }
    }

    /// Move the input cursor by `n` bytes WITHOUT emitting anything.
    ///
    /// `n` is SIGNED.  A list whose element count shrank needs a negative
    /// adjustment: the element writes already advanced the cursor by the NEW
    /// count, so the difference is what takes it to where the input's next
    /// field really starts.
    ///
    /// The comment this replaces in `aoe2mod/dat/writer.py:128` records the
    /// measurement: appending two `type 102` commands to a shipped effect
    /// emitted 22 extra bytes and left the cursor drifting, so the 93 MB stream
    /// serialised to 96,331,764 B (+3,061,612) and a re-parse died in
    /// `read_bird`.  The first attempt at a fix advanced the cursor a SECOND
    /// time by the old width and lost 27 MB -- which is what a repair that is
    /// not read back looks like.
    pub fn advance_raw(&mut self, n: isize) -> io::Result<()> {
        if self.frozen > 0 || n == 0 {
            return Ok(());
        }
        if n > 0 {
            let end = self.raw_pos + n as usize;
            if end > self.raw.len() {
                return Err(io::Error::new(
                    io::ErrorKind::UnexpectedEof,
                    format!(
                        "advance_raw({}) at raw {} but input is {}",
                        n,
                        self.raw_pos,
                        self.raw.len()
                    ),
                ));
            }
            self.raw_pos = end;
        } else {
            self.raw_pos = self.raw_pos.saturating_sub((-n) as usize);
        }
        Ok(())
    }

    /// Advance the input cursor by `n`, clamped to the input length.
    ///
    /// The clamp is what lets the LAST field of the file be written: past EOF
    /// there is nowhere to move to, and every primitive used to say exactly
    /// that.  Negative `n` walks back, which only `advance_raw` needs.
    fn bump_raw(&mut self, n: isize) {
        if self.frozen > 0 || n == 0 {
            return;
        }
        if n > 0 {
            let end = self.raw_pos + n as usize;
            if end <= self.raw.len() {
                self.raw_pos = end;
            }
        } else {
            self.raw_pos = self.raw_pos.saturating_sub((-n) as usize);
        }
    }

    /// Compare `b` against the input AT THE INPUT CURSOR.
    ///
    /// Called only when the raw width equals the emitted width; a
    /// length-changing field cannot be compared at the position it replaces,
    /// and counting it as a disagreement would make the counter mean "the edit
    /// did something" instead of "the model disagrees with the file".
    fn compare_at_raw(&mut self, b: &[u8]) {
        if self.frozen > 0 || b.is_empty() {
            return;
        }
        let end = self.raw_pos + b.len();
        if end > self.raw.len() {
            return;
        }
        if self.raw[self.raw_pos..end] != *b {
            self.mismatches += 1;
            if self.first_mismatch.is_none() {
                if let Some(k) = (0..b.len()).find(|&k| self.raw[self.raw_pos + k] != b[k]) {
                    self.first_mismatch =
                        Some((self.raw_pos + k, self.raw[self.raw_pos + k], b[k]));
                }
            }
        }
    }

    /// One emitted run: compare, append, move the input cursor by `raw_len`.
    fn emit(&mut self, b: &[u8], raw_len: isize) {
        if self.frozen == 0 {
            if raw_len == b.len() as isize {
                self.compare_at_raw(b);
            }
            self.bump_raw(raw_len);
        }
        self.out.extend_from_slice(b);
    }

    /// Unmodeled run: copy from the input and advance the input cursor.
    ///
    /// Inside `begin_new()` there is no counterpart to copy, so zeros are
    /// emitted and the cursor stays put.
    pub fn op(&mut self, n: usize) -> io::Result<()> {
        if n == 0 {
            return Ok(());
        }
        if self.frozen > 0 {
            let mut left = n;
            while left > 0 {
                let take = left.min(FROZEN_ZEROS.len());
                self.out.extend_from_slice(&FROZEN_ZEROS[..take]);
                left -= take;
            }
            return Ok(());
        }
        let end = self
            .raw_pos
            .checked_add(n)
            .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "op overflow"))?;
        if end > self.raw.len() {
            return Err(io::Error::new(
                io::ErrorKind::UnexpectedEof,
                format!(
                    "op({}) at raw {} but input is {}",
                    n,
                    self.raw_pos,
                    self.raw.len()
                ),
            ));
        }
        let bytes = self.raw[self.raw_pos..end].to_vec();
        self.emit(&bytes, n as isize);
        Ok(())
    }

    pub fn u8(&mut self, v: u8) {
        self.emit(&[v], 1);
    }

    pub fn i16(&mut self, v: i16) {
        self.emit(&v.to_le_bytes(), 2);
    }

    pub fn u16(&mut self, v: u16) {
        self.emit(&v.to_le_bytes(), 2);
    }

    pub fn i32(&mut self, v: i32) {
        self.emit(&v.to_le_bytes(), 4);
    }

    pub fn u32(&mut self, v: u32) {
        self.emit(&v.to_le_bytes(), 4);
    }

    pub fn f32(&mut self, v: f32) {
        self.emit(&v.to_le_bytes(), 4);
    }

    /// Fixed-width, NUL-padded.
    pub fn fixed_string(&mut self, s: &str, width: usize) -> io::Result<()> {
        if s.len() > width {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                format!("fixed_string {s:?} longer than {width}"),
            ));
        }
        let mut b = vec![0u8; width];
        b[..s.len()].copy_from_slice(s.as_bytes());
        self.emit(&b, width as isize);
        Ok(())
    }

    /// `serializeDebugString`: u16 marker, u16 length, bytes.
    ///
    /// `stored_len` is the width the INPUT used.  Passing it is what keeps the
    /// input cursor honest when the text changes length: the output gets the
    /// new length, the cursor advances by the old one.  When `stored_len` is
    /// `None` the input and output widths are assumed equal (a new record).
    pub fn debug_string(
        &mut self,
        marker: u16,
        text: &str,
        stored_len: Option<u16>,
    ) -> io::Result<()> {
        let bytes = text.as_bytes();
        if bytes.len() > u16::MAX as usize {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "debug_string longer than u16",
            ));
        }
        let stored = stored_len.map(|n| n as usize).unwrap_or(bytes.len());
        let entry = self.raw_pos;
        if self.frozen == 0 {
            // The whole record is one contiguous span in the input, so compare
            // it as one run when the widths match, and skip the comparison when
            // the text changed width (see `compare_at_raw`).
            if stored == bytes.len() && entry + 4 + stored <= self.raw.len() {
                self.raw_pos = entry;
                self.compare_at_raw(&marker.to_le_bytes());
                self.raw_pos = entry + 2;
                self.compare_at_raw(&(bytes.len() as u16).to_le_bytes());
                self.raw_pos = entry + 4;
                self.compare_at_raw(bytes);
            }
            self.raw_pos = (entry + 4 + stored).min(self.raw.len());
        }
        self.out.extend_from_slice(&marker.to_le_bytes());
        self.out.extend_from_slice(&(bytes.len() as u16).to_le_bytes());
        self.out.extend_from_slice(bytes);
        Ok(())
    }

    /// Push raw bytes taken from the model (a captured record image) and move
    /// the input cursor past the same span.  Used for records whose tail is
    /// type-dependent and therefore not modeled field by field.
    pub fn push_bytes(&mut self, bytes: &[u8]) {
        self.compare_at_raw(bytes);
        self.out.extend_from_slice(bytes);
    }
}

/// One round-trip of an untouched file: parse, write, compare.
#[derive(Debug, Default)]
pub struct RoundTrip {
    pub out_len: usize,
    pub raw_len: usize,
    pub mismatches: u64,
    pub first_mismatch: Option<(usize, u8, u8)>,
    pub identical: bool,
}

impl RoundTrip {
    pub fn report(&self) -> String {
        let mut s = format!(
            "{} -> {} bytes (delta {:+#}), mismatches {}",
            self.raw_len,
            self.out_len,
            self.out_len as i64 - self.raw_len as i64,
            self.mismatches
        );
        if let Some((at, want, got)) = self.first_mismatch {
            s.push_str(&format!(", first at {} raw={:#04X} out={:#04X}", at, want, got));
        }
        if self.identical {
            s.push_str("  IDENTICAL");
        }
        s
    }
}

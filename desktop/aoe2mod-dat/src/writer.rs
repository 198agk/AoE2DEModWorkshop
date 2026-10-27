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
//! `strict` compares the output against the input as it goes.  A round-trip of
//! an unmodified file must produce zero mismatches and byte-identical output;
//! that is the gate every edit is measured against.

use std::io;

pub struct Writer<'a> {
    pub out: Vec<u8>,
    /// Input cursor: advances by structure, never by output size.
    raw_pos: usize,
    raw: &'a [u8],
    /// Bumped every time a modeled field disagrees with the input, up to the
    /// original length.  Zero is the only acceptable value for a round-trip.
    pub mismatches: u64,
    pub first_mismatch: Option<(usize, u8, u8)>,
    /// When true, an appended record freezes the input cursor so the replay of
    /// the pre-existing structure resumes at exactly the same offset.
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

    fn push(&mut self, bytes: &[u8]) {
        // Compare against the input while the output is still inside it.  Past
        // that point the output is new data and there is nothing to compare to.
        for (i, &b) in bytes.iter().enumerate() {
            let o = self.out.len() + i;
            if o < self.raw.len() && self.raw[o] != b {
                self.mismatches += 1;
                if self.first_mismatch.is_none() {
                    self.first_mismatch = Some((o, self.raw[o], b));
                }
            }
        }
        self.out.extend_from_slice(bytes);
    }

    /// Unmodeled run: copy from the input and advance the input cursor.
    pub fn op(&mut self, n: usize) -> io::Result<()> {
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
        self.push(&bytes);
        self.raw_pos = end;
        Ok(())
    }

    /// Advance the input cursor WITHOUT emitting anything.
    ///
    /// Needed when the model writes a list whose element count changed: the
    /// element writes already advanced the cursor by the NEW count, so the
    /// caller passes the width the INPUT stored for the whole list.
    pub fn advance_raw(&mut self, n: usize) -> io::Result<()> {
        let end = self.raw_pos + n;
        if end > self.raw.len() {
            return Err(io::Error::new(
                io::ErrorKind::UnexpectedEof,
                "advance_raw past input",
            ));
        }
        self.raw_pos = end;
        Ok(())
    }

    pub fn u8(&mut self, v: u8) {
        self.push(&[v]);
        if self.raw_pos < self.raw.len() {
            self.raw_pos += 1;
        }
    }

    pub fn i16(&mut self, v: i16) {
        self.push(&v.to_le_bytes());
        if self.raw_pos + 2 <= self.raw.len() {
            self.raw_pos += 2;
        }
    }

    pub fn u16(&mut self, v: u16) {
        self.push(&v.to_le_bytes());
        if self.raw_pos + 2 <= self.raw.len() {
            self.raw_pos += 2;
        }
    }

    pub fn i32(&mut self, v: i32) {
        self.push(&v.to_le_bytes());
        if self.raw_pos + 4 <= self.raw.len() {
            self.raw_pos += 4;
        }
    }

    pub fn u32(&mut self, v: u32) {
        self.push(&v.to_le_bytes());
        if self.raw_pos + 4 <= self.raw.len() {
            self.raw_pos += 4;
        }
    }

    pub fn f32(&mut self, v: f32) {
        self.push(&v.to_le_bytes());
        if self.raw_pos + 4 <= self.raw.len() {
            self.raw_pos += 4;
        }
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
        self.push(&b);
        self.advance_raw(width)?;
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
        self.push(&marker.to_le_bytes());
        self.push(&(bytes.len() as u16).to_le_bytes());
        self.push(bytes);
        match stored_len {
            Some(n) => self.advance_raw(4 + n as usize),
            None => self.advance_raw(4 + bytes.len()),
        }
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

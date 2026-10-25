use std::collections::BTreeMap;

use bytes::Bytes;
use rtc::rtp::codec::h264::H264Packet;
use rtc::rtp::packetizer::Depacketizer;

const STALE_TICKS: i32 = 90_000 / 10;
const MAX_PENDING: usize = 4096;

#[derive(Debug, PartialEq, Eq)]
pub struct Frame {
    pub data: Vec<u8>,
    pub timestamp: u64,
    pub key: bool,
}

#[derive(Debug, PartialEq, Eq)]
pub enum Output {
    Frame(Frame),
    Lost,
}

struct Packet {
    timestamp: u32,
    marker: bool,
    payload: Bytes,
}

#[derive(Default)]
struct Unwrapper {
    last: Option<u64>,
}

impl Unwrapper {
    fn unwrap(&mut self, value: u64, bits: u32) -> u64 {
        let span = 1u64 << bits;
        let Some(last) = self.last else {
            self.last = Some(value + span);
            return value + span;
        };
        let base = last & !(span - 1);
        let candidates = [base.wrapping_sub(span), base, base + span];
        let ext = candidates
            .into_iter()
            .map(|b| b.wrapping_add(value))
            .min_by_key(|c| c.abs_diff(last))
            .unwrap_or(last);
        if ext > last {
            self.last = Some(ext);
        }
        ext
    }
}

pub struct Assembler {
    pending: BTreeMap<u64, Packet>,
    next: Option<u64>,
    newest_ts: u32,
    need_key: bool,
    seq: Unwrapper,
    ts: Unwrapper,
}

impl Default for Assembler {
    fn default() -> Self {
        Self {
            pending: BTreeMap::new(),
            next: None,
            newest_ts: 0,
            need_key: true,
            seq: Unwrapper::default(),
            ts: Unwrapper::default(),
        }
    }
}

impl Assembler {
    pub fn push(&mut self, seq: u16, timestamp: u32, marker: bool, payload: Bytes) -> Vec<Output> {
        let ext = self.seq.unwrap(u64::from(seq), 16);
        if self.next.is_some_and(|n| ext < n) || payload.is_empty() {
            return Vec::new();
        }
        if self.pending.is_empty() || timestamp.wrapping_sub(self.newest_ts) as i32 > 0 {
            self.newest_ts = timestamp;
        }
        self.pending.insert(ext, Packet { timestamp, marker, payload });
        let mut out = Vec::new();
        if self.pending.len() > MAX_PENDING {
            self.pending.clear();
            self.next = None;
            self.need_key = true;
            out.push(Output::Lost);
            return out;
        }
        loop {
            if let Some(frame) = self.take_complete() {
                if let Some(o) = self.decode(frame) {
                    out.push(o);
                }
                continue;
            }
            if self.skip_stale() {
                out.push(Output::Lost);
                continue;
            }
            break;
        }
        out
    }

    fn take_complete(&mut self) -> Option<Vec<Packet>> {
        let start = match self.next {
            Some(n) => n,
            None => *self.pending.keys().next()?,
        };
        let mut end = start;
        loop {
            let p = self.pending.get(&end)?;
            if p.marker {
                break;
            }
            end += 1;
        }
        let frame: Vec<Packet> = (start..=end).filter_map(|s| self.pending.remove(&s)).collect();
        self.next = Some(end + 1);
        Some(frame)
    }

    fn skip_stale(&mut self) -> bool {
        let Some((&first, oldest)) = self.pending.iter().next() else {
            return false;
        };
        let stuck_ts = match self.next.and_then(|n| self.pending.get(&n)) {
            Some(p) => p.timestamp,
            None => oldest.timestamp,
        };
        if (self.newest_ts.wrapping_sub(stuck_ts) as i32) < STALE_TICKS {
            return false;
        }
        let resume = self
            .pending
            .iter()
            .find(|(_, p)| p.timestamp.wrapping_sub(stuck_ts) as i32 > 0)
            .map(|(s, _)| *s);
        let Some(resume) = resume else {
            return false;
        };
        let dropped: Vec<u64> = self.pending.range(first..resume).map(|(s, _)| *s).collect();
        for s in dropped {
            self.pending.remove(&s);
        }
        self.next = Some(resume);
        self.need_key = true;
        true
    }

    fn decode(&mut self, packets: Vec<Packet>) -> Option<Output> {
        let timestamp = packets.first().map(|p| p.timestamp)?;
        let mut depack = H264Packet::default();
        let mut data = Vec::new();
        for p in &packets {
            match depack.depacketize(&p.payload) {
                Ok(b) => data.extend_from_slice(&b),
                Err(_) => {
                    self.need_key = true;
                    return Some(Output::Lost);
                }
            }
        }
        if data.is_empty() {
            return None;
        }
        let key = has_idr(&data);
        if self.need_key && !key {
            return None;
        }
        self.need_key = false;
        let timestamp = self.ts.unwrap(u64::from(timestamp), 32);
        Some(Output::Frame(Frame { data, timestamp, key }))
    }
}

pub fn nal_types(data: &[u8]) -> impl Iterator<Item = u8> + '_ {
    data.windows(4).filter_map(|w| (w[0] == 0 && w[1] == 0 && w[2] == 1).then_some(w[3] & 0x1f))
}

fn has_idr(data: &[u8]) -> bool {
    let mut sps = false;
    let mut idr = false;
    for t in nal_types(data) {
        sps |= t == 7;
        idr |= t == 5;
    }
    sps && idr
}

#[cfg(test)]
#[path = "h264_tests.rs"]
mod tests;

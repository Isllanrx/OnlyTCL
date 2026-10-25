use super::*;

fn nal(t: u8, len: usize) -> Bytes {
    let mut v = vec![t];
    v.extend(std::iter::repeat_n(0xAB, len));
    Bytes::from(v)
}

fn fu(t: u8, start: bool, end: bool, body: &[u8]) -> Bytes {
    let indicator = 0x60 | 28;
    let mut header = t & 0x1f;
    if start {
        header |= 0x80;
    }
    if end {
        header |= 0x40;
    }
    let mut v = vec![indicator, header];
    v.extend_from_slice(body);
    Bytes::from(v)
}

fn frames(out: Vec<Output>) -> Vec<Frame> {
    out.into_iter()
        .filter_map(|o| match o {
            Output::Frame(f) => Some(f),
            Output::Lost => None,
        })
        .collect()
}

fn keyframe(a: &mut Assembler, seq: u16, ts: u32) -> Vec<Output> {
    let mut out = a.push(seq, ts, false, nal(0x67, 4));
    out.extend(a.push(seq.wrapping_add(1), ts, false, nal(0x68, 2)));
    out.extend(a.push(seq.wrapping_add(2), ts, false, fu(0x65, true, false, &[1, 2])));
    out.extend(a.push(seq.wrapping_add(3), ts, true, fu(0x65, false, true, &[3, 4])));
    out
}

#[test]
fn assembles_keyframe_into_annex_b() {
    let mut a = Assembler::default();
    let f = frames(keyframe(&mut a, 10, 1000));
    assert_eq!(f.len(), 1);
    assert!(f[0].key);
    assert_eq!(nal_types(&f[0].data).collect::<Vec<_>>(), vec![7, 8, 5]);
    assert!(f[0].data.ends_with(&[0x65, 1, 2, 3, 4]));
}

#[test]
fn drops_delta_frames_until_first_keyframe() {
    let mut a = Assembler::default();
    assert!(frames(a.push(1, 0, true, nal(0x41, 8))).is_empty());
    assert_eq!(frames(keyframe(&mut a, 2, 3000)).len(), 1);
    let f = frames(a.push(6, 6000, true, nal(0x41, 8)));
    assert_eq!(f.len(), 1);
    assert!(!f[0].key);
}

#[test]
fn reorders_out_of_order_packets() {
    let mut a = Assembler::default();
    keyframe(&mut a, 100, 0);
    let mut out = a.push(105, 3000, true, fu(0x01, false, true, &[9]));
    assert!(frames(out).is_empty());
    out = a.push(104, 3000, false, fu(0x01, true, false, &[8]));
    let f = frames(out);
    assert_eq!(f.len(), 1);
    assert!(f[0].data.ends_with(&[0x61, 8, 9]));
}

#[test]
fn waits_for_retransmission_within_window() {
    let mut a = Assembler::default();
    keyframe(&mut a, 0, 0);
    assert!(a.push(5, 3000, true, nal(0x41, 3)).is_empty());
    assert_eq!(frames(a.push(4, 3000, false, nal(0x41, 3))).len(), 1);
}

#[test]
fn reports_loss_and_resyncs_on_next_keyframe() {
    let mut a = Assembler::default();
    keyframe(&mut a, 0, 0);
    a.push(4, 3000, false, nal(0x41, 3));
    let mut lost = false;
    let mut ts = 6000;
    let mut seq = 6;
    while ts < 3000 + STALE_TICKS as u32 + 6000 {
        lost |= a.push(seq, ts, true, nal(0x41, 3)).contains(&Output::Lost);
        seq += 1;
        ts += 3000;
    }
    assert!(lost);
    assert!(frames(a.push(seq, ts, true, nal(0x41, 3))).is_empty());
    let f = frames(keyframe(&mut a, seq + 1, ts + 3000));
    assert_eq!(f.len(), 1);
    assert!(f[0].key);
}

#[test]
fn handles_sequence_and_timestamp_wrap() {
    let mut a = Assembler::default();
    let f = frames(keyframe(&mut a, 65534, u32::MAX - 100));
    assert_eq!(f.len(), 1);
    let g = frames(a.push(2, 2900, true, nal(0x41, 3)));
    assert_eq!(g.len(), 1);
    assert_eq!(g[0].timestamp - f[0].timestamp, 3001);
}

#[test]
fn ignores_duplicates_of_emitted_packets() {
    let mut a = Assembler::default();
    keyframe(&mut a, 0, 0);
    assert!(a.push(3, 0, true, fu(0x65, false, true, &[3, 4])).is_empty());
}

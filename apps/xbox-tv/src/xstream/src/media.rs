use std::sync::Arc;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, Instant};

use rtc::rtcp::payload_feedbacks::picture_loss_indication::PictureLossIndication;
use serde_json::{Value, json};
use webrtc::media_stream::track_remote::{TrackRemote, TrackRemoteEvent};

use crate::h264::{Assembler, Output};
use crate::session::Shared;

const PLI_INTERVAL: Duration = Duration::from_millis(250);

#[derive(Default)]
pub struct Counters {
    pub video_packets: AtomicU64,
    pub video_bytes: AtomicU64,
    pub frames: AtomicU64,
    pub key_frames: AtomicU64,
    pub losses: AtomicU64,
    pub plis: AtomicU64,
    pub audio_packets: AtomicU64,
    pub audio_bytes: AtomicU64,
}

impl Counters {
    pub fn snapshot(&self) -> Value {
        let g = |a: &AtomicU64| a.load(Ordering::Relaxed);
        json!({
            "videoPackets": g(&self.video_packets),
            "videoBytes": g(&self.video_bytes),
            "frames": g(&self.frames),
            "keyFrames": g(&self.key_frames),
            "losses": g(&self.losses),
            "plis": g(&self.plis),
            "audioPackets": g(&self.audio_packets),
            "audioBytes": g(&self.audio_bytes),
        })
    }
}

fn bump(a: &AtomicU64, n: u64) {
    a.fetch_add(n, Ordering::Relaxed);
}

pub async fn run_video(track: Arc<dyn TrackRemote>, shared: Arc<Shared>) {
    let sink = &shared.sink;
    let counters = &shared.counters;
    let mut assembler = Assembler::default();
    let mut first_ts: Option<u64> = None;
    let mut last_pli: Option<Instant> = None;
    let mut media_ssrc = 0;
    request_keyframe(&track, media_ssrc, counters, &mut last_pli).await;
    loop {
        let evt = tokio::select! {
            evt = track.poll() => evt,
            _ = shared.keyframe.notified() => {
                last_pli = None;
                request_keyframe(&track, media_ssrc, counters, &mut last_pli).await;
                continue;
            }
        };
        let Some(TrackRemoteEvent::OnRtpPacket(packet)) = evt else {
            if evt.is_none() {
                break;
            }
            continue;
        };
        bump(&counters.video_packets, 1);
        bump(&counters.video_bytes, packet.payload.len() as u64);
        media_ssrc = packet.header.ssrc;
        let outputs = assembler.push(
            packet.header.sequence_number,
            packet.header.timestamp,
            packet.header.marker,
            packet.payload,
        );
        for out in outputs {
            match out {
                Output::Frame(frame) => {
                    let base = *first_ts.get_or_insert(frame.timestamp);
                    let pts = (frame.timestamp - base) as i64 * 1_000_000 / 90_000;
                    bump(&counters.frames, 1);
                    if frame.key {
                        bump(&counters.key_frames, 1);
                    }
                    sink.video(&frame.data, pts, frame.key);
                }
                Output::Lost => {
                    bump(&counters.losses, 1);
                    request_keyframe(&track, media_ssrc, counters, &mut last_pli).await;
                }
            }
        }
    }
    sink.event(json!({"ev": "trackEnded", "kind": "video"}));
}

async fn request_keyframe(
    track: &Arc<dyn TrackRemote>,
    media_ssrc: u32,
    counters: &Counters,
    last: &mut Option<Instant>,
) {
    if last.is_some_and(|t| t.elapsed() < PLI_INTERVAL) {
        return;
    }
    let ssrc = if media_ssrc != 0 {
        media_ssrc
    } else {
        track.ssrcs().await.first().copied().unwrap_or(0)
    };
    if ssrc == 0 {
        return;
    }
    *last = Some(Instant::now());
    bump(&counters.plis, 1);
    let pli = PictureLossIndication { sender_ssrc: 0, media_ssrc: ssrc };
    if let Err(e) = track.write_rtcp(vec![Box::new(pli)]).await {
        log::warn!("xstream PLI to {ssrc} failed: {e}");
    }
}

pub async fn run_audio(track: Arc<dyn TrackRemote>, shared: Arc<Shared>) {
    let sink = &shared.sink;
    let counters = &shared.counters;
    let mut first_ts: Option<u32> = None;
    while let Some(evt) = track.poll().await {
        let TrackRemoteEvent::OnRtpPacket(packet) = evt else {
            continue;
        };
        if packet.payload.is_empty() {
            continue;
        }
        bump(&counters.audio_packets, 1);
        bump(&counters.audio_bytes, packet.payload.len() as u64);
        let base = *first_ts.get_or_insert(packet.header.timestamp);
        let ticks = packet.header.timestamp.wrapping_sub(base) as i64;
        sink.audio(&packet.payload, ticks * 1_000_000 / 48_000);
    }
    sink.event(json!({"ev": "trackEnded", "kind": "audio"}));
}

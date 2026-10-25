mod server;

use std::sync::Arc;
use std::time::Duration;

use rtc::peer_connection::transport::RTCIceCandidateInit;
use serde_json::{Value, json};
use tokio::sync::mpsc;
use tokio::time::timeout;
use xstream::h264::nal_types;
use xstream::sink::Sink;

#[derive(Debug)]
enum Msg {
    Event(Value),
    Channel(i32, Vec<u8>, bool),
    Video(Vec<u8>, i64, bool),
    Audio(Vec<u8>, i64),
}

struct TestSink(mpsc::UnboundedSender<Msg>);

impl Sink for TestSink {
    fn event(&self, event: Value) {
        let _ = self.0.send(Msg::Event(event));
    }
    fn channel(&self, id: i32, data: &[u8], text: bool) {
        let _ = self.0.send(Msg::Channel(id, data.to_vec(), text));
    }
    fn video(&self, data: &[u8], pts_us: i64, key: bool) {
        let _ = self.0.send(Msg::Video(data.to_vec(), pts_us, key));
    }
    fn audio(&self, data: &[u8], pts_us: i64) {
        let _ = self.0.send(Msg::Audio(data.to_vec(), pts_us));
    }
}

struct Client {
    h: i64,
    rx: mpsc::UnboundedReceiver<Msg>,
    candidates: Vec<RTCIceCandidateInit>,
    log: Vec<Msg>,
}

impl Client {
    fn cmd(&self, v: Value) {
        xstream::command(self.h, &v.to_string());
    }

    async fn next(&mut self) -> Msg {
        timeout(Duration::from_secs(20), self.rx.recv()).await.expect("timeout waiting for engine").expect("sink closed")
    }

    async fn result(&mut self, req: u32) -> Value {
        loop {
            match self.next().await {
                Msg::Event(e) if e["ev"] == "result" && e["req"] == req => {
                    assert_eq!(e["ok"], true, "request {req} failed: {e}");
                    return e["value"].clone();
                }
                Msg::Event(e) if e["ev"] == "ice" && !e["candidate"].is_null() => {
                    self.candidates.push(serde_json::from_value(e).expect("candidate json"));
                }
                Msg::Event(e) if e["ev"] == "fatal" || e["ev"] == "error" => panic!("engine error {e}"),
                other => self.log.push(other),
            }
        }
    }

    async fn until<F: FnMut(&Msg) -> bool>(&mut self, mut f: F) {
        if self.log.iter().any(&mut f) {
            return;
        }
        loop {
            let m = self.next().await;
            let hit = f(&m);
            self.log.push(m);
            if hit {
                return;
            }
        }
    }
}

const CRLF: &str = "\r\n";

fn munge_like_xcloud(sdp: &str) -> String {
    let lines: Vec<&str> = sdp.split(CRLF).collect();
    let opus_pt = lines
        .iter()
        .find_map(|l| l.strip_prefix("a=rtpmap:").and_then(|r| r.strip_suffix(" opus/48000/2")))
        .unwrap_or_else(|| panic!("opus pt in {sdp:?}"))
        .to_owned();
    let baseline: Vec<String> = lines
        .iter()
        .filter_map(|l| l.strip_prefix("a=fmtp:"))
        .filter(|l| l.contains("profile-level-id=42"))
        .map(|l| l.split(' ').next().unwrap_or_default().to_owned())
        .collect();
    lines
        .iter()
        .map(|l| {
            if l.starts_with(&format!("a=fmtp:{opus_pt} ")) {
                format!("{l};stereo=1")
            } else if let Some(rest) = l.strip_prefix("m=video ") {
                let parts: Vec<&str> = rest.split(' ').collect();
                let (head, pts) = parts.split_at(2);
                let mut ordered: Vec<&str> = pts.iter().copied().filter(|p| baseline.iter().any(|b| b == p)).collect();
                ordered.extend(pts.iter().copied().filter(|p| !baseline.iter().any(|b| b == p)));
                format!("m=video {} {}", head.join(" "), ordered.join(" "))
            } else {
                (*l).to_owned()
            }
        })
        .collect::<Vec<_>>()
        .join(CRLF)
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn engine_streams_media_and_data_end_to_end() {
    let (tx, rx) = mpsc::unbounded_channel();
    let h = xstream::open(Arc::new(TestSink(tx)), r#"{"iceServers":[]}"#).expect("open");
    let mut c = Client { h, rx, candidates: Vec::new(), log: Vec::new() };

    c.cmd(json!({"op": "createDataChannel", "id": 1, "label": "input", "ordered": true, "protocol": "1.0"}));
    c.cmd(json!({"op": "stats", "req": 99}));
    let early = c.result(99).await;
    assert_eq!(early["frames"], 0, "stats before negotiation must not build the peer connection: {early}");
    c.cmd(json!({"op": "createDataChannel", "id": 2, "label": "control", "protocol": "controlV1"}));
    c.cmd(json!({"op": "addTransceiver", "kind": "audio", "direction": "sendrecv"}));
    c.cmd(json!({"op": "addTransceiver", "kind": "video", "direction": "recvonly"}));
    c.cmd(json!({"op": "codecPrefs", "kind": "video", "codecs": [
        {"mimeType": "video/H264", "sdpFmtpLine": server::VIDEO_FMTP}
    ]}));
    c.cmd(json!({"op": "createOffer", "req": 1}));
    let offer = c.result(1).await;
    let sdp = offer["sdp"].as_str().expect("offer sdp").to_owned();
    assert!(sdp.contains("m=video") && sdp.contains("m=audio") && sdp.contains("m=application"));
    assert!(sdp.contains("H264/90000"));
    assert!(sdp.contains(CRLF), "SDP must use CRLF");
    let audio_section = sdp.split("m=").find(|m| m.starts_with("audio")).expect("audio m-line");
    assert!(audio_section.contains("a=sendrecv"), "audio must be offered sendrecv: {audio_section}");
    let video_section = sdp.split("m=").find(|m| m.starts_with("video")).expect("video m-line");
    assert!(video_section.contains("a=recvonly"), "video must be recvonly: {video_section}");

    let sdp = munge_like_xcloud(&sdp);
    c.cmd(json!({"op": "setLocal", "req": 2, "sdp": sdp}));
    let local = c.result(2).await;
    assert_eq!(local["sdp"].as_str(), Some(sdp.as_str()), "munged offer must be kept as local description");

    let answer = server::answer(sdp).await;
    c.cmd(json!({"op": "setRemote", "req": 3, "type": "answer", "sdp": answer.sdp}));
    c.result(3).await;
    tokio::time::sleep(Duration::from_millis(500)).await;
    c.cmd(json!({"op": "stats", "req": 4}));
    c.result(4).await;
    assert!(!c.candidates.is_empty(), "engine produced no ICE candidates");
    for cand in c.candidates.clone() {
        server::add_candidate(answer.pc.as_ref(), cand).await;
    }

    c.until(|m| matches!(m, Msg::Event(e) if e["ev"] == "state" && e["state"] == "connected")).await;
    c.until(|m| matches!(m, Msg::Event(e) if e["ev"] == "dcOpen" && e["id"] == 1)).await;
    c.until(|m| matches!(m, Msg::Event(e) if e["ev"] == "dcOpen" && e["id"] == 2)).await;

    assert!(xstream::send(h, 1, &[1, 2, 3], false));
    assert!(xstream::send(h, 2, b"hello", true));
    c.until(|m| matches!(m, Msg::Channel(1, d, false) if d == b"echo:\x01\x02\x03")).await;
    c.until(|m| matches!(m, Msg::Channel(2, d, true) if d == b"echo:hello")).await;

    let frames = 90u8;
    server::send_media(answer.video.clone(), answer.audio.clone(), frames).await;
    tokio::time::sleep(Duration::from_millis(500)).await;
    c.cmd(json!({"op": "stats", "req": 5}));
    let stats = c.result(5).await;

    let video: Vec<(&Vec<u8>, i64, bool)> = c
        .log
        .iter()
        .filter_map(|m| match m {
            Msg::Video(d, p, k) => Some((d, *p, *k)),
            _ => None,
        })
        .collect();
    let audio = c.log.iter().filter(|m| matches!(m, Msg::Audio(d, p) if !d.is_empty() && *p >= 0)).count();
    assert!(video.len() >= frames as usize - 2, "video frames {} stats {stats}", video.len());
    assert!(video[0].2, "first frame must be a keyframe");
    assert_eq!(video[0].0.as_slice(), server::keyframe(0).as_ref(), "keyframe bytes differ");
    assert_eq!(nal_types(video[0].0).collect::<Vec<_>>(), vec![7, 8, 5]);
    assert_eq!(video[1].0.as_slice(), server::delta(1).as_ref(), "delta bytes differ");
    assert!(video.windows(2).all(|w| w[1].1 > w[0].1), "pts must increase");
    assert_eq!(video.iter().filter(|v| v.2).count(), 3);
    assert!(audio >= frames as usize - 2, "audio packets {audio}");
    assert_eq!(stats["losses"], 0);
    assert!(stats["rtt"].as_f64().is_some(), "rtt missing: {stats}");
    assert!(stats["video"]["packetsReceived"].as_u64().unwrap_or(0) > 0, "inbound video missing: {stats}");

    let plis = stats["plis"].as_u64().expect("plis");
    c.cmd(json!({"op": "requestKeyframe"}));
    tokio::time::sleep(Duration::from_millis(200)).await;
    c.cmd(json!({"op": "stats", "req": 6}));
    let after = c.result(6).await;
    assert_eq!(after["plis"].as_u64(), Some(plis + 1), "requestKeyframe must send one PLI");

    xstream::close(h);
}

use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::Instant;

use bytes::BytesMut;
use rtc::peer_connection::configuration::media_engine::MediaEngine;
use rtc::peer_connection::configuration::RTCConfigurationBuilder;
use rtc::peer_connection::configuration::interceptor_registry::register_default_interceptors;
use rtc::interceptor::Registry;
use rtc::data_channel::RTCDataChannelInit;
use rtc::peer_connection::sdp::RTCSessionDescription;
use rtc::peer_connection::transport::{RTCIceCandidateInit, RTCIceServer};
use rtc::media_stream::MediaStreamTrack;
use rtc::rtp_transceiver::rtp_sender::{RTCRtpCodingParameters, RTCRtpEncodingParameters, RtpCodecKind};
use rtc::rtp_transceiver::{RTCRtpTransceiverDirection, RTCRtpTransceiverInit};
use serde_json::{Value, json};
use tokio::sync::{Notify, mpsc};
use webrtc::data_channel::{DataChannel, DataChannelEvent};
use webrtc::media_stream::track_local::TrackLocal;
use webrtc::media_stream::track_local::static_sample::TrackLocalStaticSample;
use webrtc::peer_connection::{
    PeerConnection, PeerConnectionBuilder, PeerConnectionEventHandler, RTCStatsReportEntry, StatsSelector,
};

use crate::codecs::{CodecPref, opus_codec, register_codecs};
use crate::events::Events;
use crate::media::Counters;
use crate::protocol::{Command, IceServer, Spec};
use crate::sink::Sink;

const CHAT_SSRC: u32 = 0x5843_4854;

pub type Outgoing = mpsc::UnboundedSender<(BytesMut, bool)>;

pub struct Shared {
    pub sink: Arc<dyn Sink>,
    pub counters: Arc<Counters>,
    pub writers: Mutex<HashMap<i32, Outgoing>>,
    pub keyframe: Notify,
}

pub struct Session {
    shared: Arc<Shared>,
    ice_servers: Vec<IceServer>,
    specs: Vec<Spec>,
    prefs: HashMap<String, Vec<CodecPref>>,
    offered: Mutex<Option<String>>,
}

impl Session {
    pub fn new(shared: Arc<Shared>, ice_servers: Vec<IceServer>) -> Self {
        Self { shared, ice_servers, specs: Vec::new(), prefs: HashMap::new(), offered: Mutex::new(None) }
    }

    pub async fn run(mut self, mut rx: mpsc::UnboundedReceiver<Command>) {
        log::info!("xstream session opened with {} ICE servers", self.ice_servers.len());
        while let Some(cmd) = rx.recv().await {
            match cmd {
                Command::CreateDataChannel(spec) => self.specs.push(Spec::Channel(spec)),
                Command::AddTransceiver { kind, direction } => {
                    self.specs.push(Spec::Transceiver { kind, direction })
                }
                Command::CodecPrefs { kind, codecs } => {
                    self.prefs.insert(kind, codecs);
                }
                Command::Close => return,
                Command::RequestKeyframe => {}
                Command::Stats { req } => {
                    let value = self.shared.counters.snapshot();
                    self.shared.sink.event(json!({"ev": "result", "req": req, "ok": true, "value": value}));
                }
                other => {
                    let specs = std::mem::take(&mut self.specs);
                    let count = specs.len();
                    let built = build(self.shared.clone(), &self.ice_servers, specs, &self.prefs).await;
                    match built {
                        Ok(pc) => {
                            log::info!("xstream peer connection built from {count} channel/transceiver specs");
                            self.connected(pc, other, rx).await
                        }
                        Err(e) => {
                            log::error!("xstream peer connection build failed: {e}");
                            self.shared.sink.event(json!({"ev": "fatal", "error": e}))
                        }
                    }
                    return;
                }
            }
        }
    }

    async fn connected<P: PeerConnection>(
        &self,
        pc: Arc<P>,
        first: Command,
        mut rx: mpsc::UnboundedReceiver<Command>,
    ) {
        let mut next = Some(first);
        loop {
            let cmd = match next.take() {
                Some(c) => c,
                None => match rx.recv().await {
                    Some(c) => c,
                    None => break,
                },
            };
            if matches!(cmd, Command::Close) {
                break;
            }
            self.apply(pc.as_ref(), cmd).await;
        }
        if let Err(e) = pc.close().await {
            log::warn!("xstream close: {e}");
        }
        self.shared.writers.lock().unwrap_or_else(|p| p.into_inner()).clear();
    }

    async fn apply<P: PeerConnection>(&self, pc: &P, cmd: Command) {
        let (req, result) = match cmd {
            Command::CreateOffer { req } => (req, self.offer(pc).await),
            Command::SetLocal { req, sdp } => (req, self.set_local(pc, sdp).await),
            Command::SetRemote { req, kind, sdp } => (req, set_remote(pc, &kind, sdp).await),
            Command::AddIce { req, candidate } => (req, add_ice(pc, candidate).await),
            Command::Stats { req } => (req, Ok(stats(pc, &self.shared).await)),
            Command::CreateDataChannel(c) => (
                c.req,
                match pc.create_data_channel(&c.label, None).await {
                    Ok(dc) => {
                        attach_channel(&self.shared, c.id, dc);
                        Ok(Value::Null)
                    }
                    Err(e) => Err(e.to_string()),
                },
            ),
            Command::RequestKeyframe => {
                self.shared.keyframe.notify_one();
                return;
            }
            Command::AddTransceiver { .. } | Command::CodecPrefs { .. } | Command::Close => return,
        };
        let event = match result {
            Ok(value) => json!({"ev": "result", "req": req, "ok": true, "value": value}),
            Err(error) => {
                log::warn!("xstream command {req} failed: {error}");
                json!({"ev": "result", "req": req, "ok": false, "error": error})
            }
        };
        self.shared.sink.event(event);
    }

    async fn offer<P: PeerConnection>(&self, pc: &P) -> Result<Value, String> {
        let desc = pc.create_offer(None).await.map_err(|e| e.to_string())?;
        *self.offered.lock().unwrap_or_else(|p| p.into_inner()) = Some(desc.sdp.clone());
        Ok(json!({"type": "offer", "sdp": desc.sdp}))
    }

    async fn set_local<P: PeerConnection>(&self, pc: &P, sdp: Option<String>) -> Result<Value, String> {
        let offered = self.offered.lock().unwrap_or_else(|p| p.into_inner()).take();
        let base = match offered {
            Some(s) => s,
            None => pc.create_offer(None).await.map_err(|e| e.to_string())?.sdp,
        };
        let desc = RTCSessionDescription::offer(base.clone()).map_err(|e| e.to_string())?;
        pc.set_local_description(desc).await.map_err(|e| e.to_string())?;
        let reported = match sdp {
            Some(page) if !page.is_empty() && same_transport(&page, &base) => page,
            Some(page) if !page.is_empty() => {
                log::warn!("xstream page SDP changed transport attributes; reporting engine offer");
                base
            }
            _ => base,
        };
        Ok(json!({"type": "offer", "sdp": reported}))
    }
}

fn transport_lines(sdp: &str) -> Vec<&str> {
    const KEYS: [&str; 6] = ["m=", "a=ice-ufrag:", "a=ice-pwd:", "a=fingerprint:", "a=setup:", "a=mid:"];
    sdp.lines()
        .map(str::trim_end)
        .filter(|l| KEYS.iter().any(|k| l.starts_with(k)))
        .map(|l| if l.starts_with("m=") { l.split(' ').next().unwrap_or(l) } else { l })
        .collect()
}

fn same_transport(page: &str, engine: &str) -> bool {
    transport_lines(page) == transport_lines(engine)
}

async fn build(
    shared: Arc<Shared>,
    ice_servers: &[IceServer],
    specs: Vec<Spec>,
    prefs: &HashMap<String, Vec<CodecPref>>,
) -> Result<Arc<impl PeerConnection + use<>>, String> {
    let mut me = MediaEngine::default();
    register_codecs(&mut me, prefs).map_err(|e| format!("codecs: {e}"))?;
    let registry = register_default_interceptors(Registry::new(), &mut me)
        .map_err(|e| format!("interceptors: {e}"))?;
    let servers = ice_servers
        .iter()
        .map(|s| RTCIceServer {
            urls: s.urls.clone(),
            username: s.username.clone().unwrap_or_default(),
            credential: s.credential.clone().unwrap_or_default(),
        })
        .collect();
    let config = RTCConfigurationBuilder::new().with_ice_servers(servers).build();
    let runtime = webrtc::runtime::default_runtime().ok_or("no runtime")?;
    let handler = Arc::new(Events::new(shared.clone(), runtime.clone()));
    let pc = PeerConnectionBuilder::new()
        .with_configuration(config)
        .with_media_engine(me)
        .with_interceptor_registry(registry)
        .with_handler(handler as Arc<dyn PeerConnectionEventHandler>)
        .with_runtime(runtime.clone())
        .with_udp_addrs(vec!["0.0.0.0:0".to_owned()])
        .build()
        .await
        .map_err(|e| format!("build: {e}"))?;
    let pc = Arc::new(pc);
    for spec in specs {
        match spec {
            Spec::Channel(c) => {
                let init = RTCDataChannelInit {
                    ordered: c.ordered.unwrap_or(true),
                    max_packet_life_time: c.max_packet_life_time,
                    max_retransmits: c.max_retransmits,
                    protocol: c.protocol.clone().unwrap_or_default(),
                    negotiated: None,
                };
                let dc = pc
                    .create_data_channel(&c.label, Some(init))
                    .await
                    .map_err(|e| format!("channel {}: {e}", c.label))?;
                attach_channel(&shared, c.id, dc);
            }
            Spec::Transceiver { kind, direction } => {
                add_transceiver(pc.as_ref(), &kind, direction.as_deref()).await?;
            }
        }
    }
    Ok(pc)
}

async fn stats<P: PeerConnection>(pc: &P, shared: &Shared) -> Value {
    let report = pc.get_stats(Instant::now(), StatsSelector::None).await;
    let mut out = shared.counters.snapshot();
    if let Some(pair) = report.candidate_pairs().find(|p| p.nominated) {
        out["rtt"] = json!(pair.current_round_trip_time);
        out["availableIncomingBitrate"] = json!(pair.available_incoming_bitrate);
    }
    for entry in report.iter() {
        if let RTCStatsReportEntry::InboundRtp(s) = entry {
            let r = &s.received_rtp_stream_stats;
            let kind = if r.rtp_stream_stats.kind == RtpCodecKind::Audio { "audio" } else { "video" };
            out[kind] = json!({
                "ssrc": r.rtp_stream_stats.ssrc,
                "packetsReceived": r.packets_received,
                "packetsLost": r.packets_lost,
                "jitter": r.jitter,
                "bytesReceived": s.bytes_received,
                "nackCount": s.nack_count,
                "pliCount": s.pli_count,
                "firCount": s.fir_count,
            });
        }
    }
    out
}

async fn add_transceiver<P: PeerConnection>(pc: &P, kind: &str, direction: Option<&str>) -> Result<(), String> {
    let kind = if kind == "audio" { RtpCodecKind::Audio } else { RtpCodecKind::Video };
    let direction = match direction {
        Some("sendrecv") => RTCRtpTransceiverDirection::Sendrecv,
        Some("sendonly") => RTCRtpTransceiverDirection::Sendonly,
        Some("inactive") => RTCRtpTransceiverDirection::Inactive,
        _ => RTCRtpTransceiverDirection::Recvonly,
    };
    let init = Some(RTCRtpTransceiverInit { direction, ..Default::default() });
    let sends = matches!(direction, RTCRtpTransceiverDirection::Sendrecv | RTCRtpTransceiverDirection::Sendonly);
    let added = if sends && kind == RtpCodecKind::Audio {
        let track = silent_audio_track().map_err(|e| format!("local audio track: {e}"))?;
        pc.add_transceiver_from_track(track, init).await.map(|_| ())
    } else {
        pc.add_transceiver_from_kind(kind, init).await.map(|_| ())
    };
    added.map_err(|e| format!("transceiver {kind:?} {direction:?}: {e}"))
}

fn silent_audio_track() -> rtc::shared::error::Result<Arc<dyn TrackLocal>> {
    let track = MediaStreamTrack::new(
        "xstream-chat".to_owned(),
        "xstream-chat-audio".to_owned(),
        "xstream-chat".to_owned(),
        RtpCodecKind::Audio,
        vec![RTCRtpEncodingParameters {
            rtp_coding_parameters: RTCRtpCodingParameters { ssrc: Some(CHAT_SSRC), ..Default::default() },
            codec: opus_codec(),
            ..Default::default()
        }],
    );
    Ok(Arc::new(TrackLocalStaticSample::new(Instant::now(), track)?))
}

async fn set_remote<P: PeerConnection>(pc: &P, kind: &str, sdp: String) -> Result<Value, String> {
    let desc = match kind {
        "offer" => RTCSessionDescription::offer(sdp),
        "pranswer" => RTCSessionDescription::pranswer(sdp),
        _ => RTCSessionDescription::answer(sdp),
    }
    .map_err(|e| e.to_string())?;
    pc.set_remote_description(desc).await.map_err(|e| e.to_string())?;
    Ok(Value::Null)
}

async fn add_ice<P: PeerConnection>(pc: &P, candidate: RTCIceCandidateInit) -> Result<Value, String> {
    let trimmed = candidate.candidate.trim().trim_start_matches("a=").to_owned();
    if trimmed.is_empty() {
        return Ok(Value::Null);
    }
    let candidate = RTCIceCandidateInit { candidate: trimmed, ..candidate };
    pc.add_ice_candidate(candidate).await.map_err(|e| e.to_string())?;
    Ok(Value::Null)
}

pub fn attach_channel(shared: &Arc<Shared>, id: i32, dc: Arc<dyn DataChannel>) {
    let (tx, mut rx) = mpsc::unbounded_channel::<(BytesMut, bool)>();
    shared.writers.lock().unwrap_or_else(|p| p.into_inner()).insert(id, tx);
    let writer = dc.clone();
    tokio::spawn(async move {
        while let Some((data, text)) = rx.recv().await {
            let sent = if text {
                writer.send_text(&String::from_utf8_lossy(&data)).await
            } else {
                writer.send(data).await
            };
            if let Err(e) = sent {
                log::warn!("xstream send on channel {id}: {e}");
            }
        }
    });
    let shared = shared.clone();
    tokio::spawn(async move {
        while let Some(evt) = dc.poll().await {
            match evt {
                DataChannelEvent::OnOpen => shared.sink.event(json!({"ev": "dcOpen", "id": id})),
                DataChannelEvent::OnMessage(m) => shared.sink.channel(id, &m.data, m.is_string),
                DataChannelEvent::OnClose => {
                    shared.sink.event(json!({"ev": "dcClose", "id": id}));
                    break;
                }
                DataChannelEvent::OnError => shared.sink.event(json!({"ev": "dcError", "id": id})),
                _ => {}
            }
        }
        shared.writers.lock().unwrap_or_else(|p| p.into_inner()).remove(&id);
    });
}

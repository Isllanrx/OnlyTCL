use std::sync::Arc;
use std::sync::atomic::{AtomicI32, Ordering};

use rtc::rtp_transceiver::rtp_sender::RtpCodecKind;
use serde_json::json;
use webrtc::data_channel::DataChannel;
use webrtc::media_stream::track_remote::TrackRemote;
use webrtc::peer_connection::{
    PeerConnectionEventHandler, RTCIceConnectionState, RTCIceGatheringState, RTCPeerConnectionIceEvent,
    RTCPeerConnectionState,
};
use webrtc::runtime::Runtime;

use crate::media::{run_audio, run_video};
use crate::session::{Shared, attach_channel};

const REMOTE_CHANNEL_BASE: i32 = 1 << 20;

pub struct Events {
    shared: Arc<Shared>,
    runtime: Arc<dyn Runtime>,
    remote_ids: AtomicI32,
}

impl Events {
    pub fn new(shared: Arc<Shared>, runtime: Arc<dyn Runtime>) -> Self {
        Self { shared, runtime, remote_ids: AtomicI32::new(REMOTE_CHANNEL_BASE) }
    }
}

#[async_trait::async_trait]
impl PeerConnectionEventHandler for Events {
    async fn on_ice_candidate(&self, event: RTCPeerConnectionIceEvent) {
        match event.candidate.to_json() {
            Ok(c) => self.shared.sink.event(json!({
                "ev": "ice",
                "candidate": c.candidate,
                "sdpMid": c.sdp_mid,
                "sdpMLineIndex": c.sdp_mline_index,
                "usernameFragment": c.username_fragment,
            })),
            Err(e) => log::warn!("xstream candidate encode: {e}"),
        }
    }

    async fn on_ice_gathering_state_change(&self, state: RTCIceGatheringState) {
        let state = state.to_string();
        if state == "complete" {
            self.shared.sink.event(json!({"ev": "ice", "candidate": null}));
        }
        self.shared.sink.event(json!({"ev": "gathering", "state": state}));
    }

    async fn on_ice_connection_state_change(&self, state: RTCIceConnectionState) {
        self.shared.sink.event(json!({"ev": "iceState", "state": state.to_string()}));
    }

    async fn on_connection_state_change(&self, state: RTCPeerConnectionState) {
        self.shared.sink.event(json!({"ev": "state", "state": state.to_string()}));
    }

    async fn on_data_channel(&self, dc: Arc<dyn DataChannel>) {
        let id = self.remote_ids.fetch_add(1, Ordering::Relaxed);
        let label = dc.label().await.unwrap_or_default();
        let protocol = dc.protocol().await.unwrap_or_default();
        self.shared.sink.event(json!({"ev": "dc", "id": id, "label": label, "protocol": protocol}));
        attach_channel(&self.shared, id, dc);
    }

    async fn on_track(&self, track: Arc<dyn TrackRemote>) {
        let kind = track.kind().await;
        let shared = self.shared.clone();
        let name = if kind == RtpCodecKind::Audio { "audio" } else { "video" };
        self.shared.sink.event(json!({"ev": "track", "kind": name}));
        if kind == RtpCodecKind::Audio {
            self.runtime.spawn(Box::pin(run_audio(track, shared)));
        } else {
            self.runtime.spawn(Box::pin(run_video(track, shared)));
        }
    }
}

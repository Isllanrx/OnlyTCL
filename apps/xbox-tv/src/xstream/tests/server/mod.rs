use std::sync::Arc;
use std::time::{Duration, Instant};

use bytes::{Bytes, BytesMut};
use rtc::interceptor::Registry;
use rtc::media::Sample;
use rtc::media_stream::MediaStreamTrack;
use rtc::peer_connection::configuration::RTCConfigurationBuilder;
use rtc::peer_connection::configuration::interceptor_registry::register_default_interceptors;
use rtc::peer_connection::configuration::media_engine::{MIME_TYPE_H264, MIME_TYPE_OPUS, MediaEngine};
use rtc::peer_connection::sdp::RTCSessionDescription;
use rtc::peer_connection::transport::RTCIceCandidateInit;
use rtc::rtp_transceiver::rtp_sender::{
    RTCRtpCodec, RTCRtpCodecParameters, RTCRtpCodingParameters, RTCRtpEncodingParameters, RtpCodecKind,
};
use webrtc::data_channel::{DataChannel, DataChannelEvent};
use webrtc::media_stream::Track;
use webrtc::media_stream::track_local::TrackLocal;
use webrtc::media_stream::track_local::static_sample::TrackLocalStaticSample;
use webrtc::peer_connection::{
    PeerConnection, PeerConnectionBuilder, PeerConnectionEventHandler, RTCIceGatheringState,
};
use webrtc::rtp_transceiver::RtpSender;
use webrtc::runtime::{Runtime, Sender, channel, default_runtime};

pub const VIDEO_FMTP: &str = "level-asymmetry-allowed=1;packetization-mode=1;profile-level-id=42e01f";

struct Echo {
    runtime: Arc<dyn Runtime>,
    gathered: Sender<()>,
}

#[async_trait::async_trait]
impl PeerConnectionEventHandler for Echo {
    async fn on_ice_gathering_state_change(&self, state: RTCIceGatheringState) {
        if state == RTCIceGatheringState::Complete {
            let _ = self.gathered.try_send(());
        }
    }

    async fn on_data_channel(&self, dc: Arc<dyn DataChannel>) {
        self.runtime.spawn(Box::pin(async move {
            while let Some(evt) = dc.poll().await {
                if let DataChannelEvent::OnMessage(m) = evt {
                    let mut reply = BytesMut::from(&b"echo:"[..]);
                    reply.extend_from_slice(&m.data);
                    let _ = if m.is_string {
                        dc.send_text(&String::from_utf8_lossy(&reply)).await
                    } else {
                        dc.send(reply).await
                    };
                }
            }
        }));
    }
}

pub fn keyframe(n: u8) -> Bytes {
    let mut v = vec![0, 0, 0, 1, 0x67, 0x42, 0xe0, 0x1f, 0, 0, 0, 1, 0x68, 0xce, 0x38, 0x80, 0, 0, 0, 1, 0x65];
    v.extend((0..4000u32).map(|i| ((i as u8) ^ n) | 1));
    Bytes::from(v)
}

pub fn delta(n: u8) -> Bytes {
    let mut v = vec![0, 0, 0, 1, 0x41];
    v.extend((0..700u32).map(|i| ((i as u8).wrapping_add(n)) | 1));
    Bytes::from(v)
}

fn codec(kind: RtpCodecKind) -> RTCRtpCodecParameters {
    let (mime, rate, channels, fmtp, pt) = match kind {
        RtpCodecKind::Audio => (MIME_TYPE_OPUS, 48_000, 2, "minptime=10;useinbandfec=1", 111),
        _ => (MIME_TYPE_H264, 90_000, 0, VIDEO_FMTP, 102),
    };
    RTCRtpCodecParameters {
        rtp_codec: RTCRtpCodec {
            mime_type: mime.to_owned(),
            clock_rate: rate,
            channels,
            sdp_fmtp_line: fmtp.to_owned(),
            rtcp_feedback: vec![],
        },
        payload_type: pt,
        ..Default::default()
    }
}

pub struct Answer<P: PeerConnection> {
    pub pc: Arc<P>,
    pub sdp: String,
    pub video: (Arc<TrackLocalStaticSample>, Arc<dyn RtpSender>),
    pub audio: (Arc<TrackLocalStaticSample>, Arc<dyn RtpSender>),
}

async fn local_track(
    pc: &impl PeerConnection,
    kind: RtpCodecKind,
) -> (Arc<TrackLocalStaticSample>, Arc<dyn RtpSender>) {
    let track = Arc::new(
        TrackLocalStaticSample::new(
            Instant::now(),
            MediaStreamTrack::new(
                format!("s-{kind}"),
                format!("t-{kind}"),
                format!("l-{kind}"),
                kind,
                vec![RTCRtpEncodingParameters {
                    rtp_coding_parameters: RTCRtpCodingParameters {
                        ssrc: Some(if kind == RtpCodecKind::Audio { 1111 } else { 2222 }),
                        ..Default::default()
                    },
                    codec: codec(kind).rtp_codec,
                    ..Default::default()
                }],
            ),
        )
        .expect("track"),
    );
    let sender = pc.add_track(track.clone() as Arc<dyn TrackLocal>).await.expect("add_track");
    (track, sender)
}

pub async fn answer(offer: String) -> Answer<impl PeerConnection> {
    let mut me = MediaEngine::default();
    me.register_codec(codec(RtpCodecKind::Audio), RtpCodecKind::Audio).expect("opus");
    me.register_codec(codec(RtpCodecKind::Video), RtpCodecKind::Video).expect("h264");
    let registry = register_default_interceptors(Registry::new(), &mut me).expect("interceptors");
    let runtime = default_runtime().expect("runtime");
    let (gathered, mut gathered_rx) = channel::<()>(1);
    let handler = Arc::new(Echo { runtime: runtime.clone(), gathered });
    let pc = PeerConnectionBuilder::new()
        .with_configuration(RTCConfigurationBuilder::new().build())
        .with_media_engine(me)
        .with_interceptor_registry(registry)
        .with_handler(handler as Arc<dyn PeerConnectionEventHandler>)
        .with_runtime(runtime)
        .with_udp_addrs(vec!["0.0.0.0:0".to_owned()])
        .build()
        .await
        .expect("server pc");
    pc.set_remote_description(RTCSessionDescription::offer(offer).expect("offer"))
        .await
        .expect("set_remote");
    let video = local_track(&pc, RtpCodecKind::Video).await;
    let audio = local_track(&pc, RtpCodecKind::Audio).await;
    let answer = pc.create_answer(None).await.expect("answer");
    pc.set_local_description(answer).await.expect("set_local");
    let _ = tokio::time::timeout(Duration::from_secs(10), gathered_rx.recv()).await;
    let sdp = pc.local_description().await.expect("local desc").sdp;
    Answer { pc: Arc::new(pc), sdp, video, audio }
}

pub async fn add_candidate(pc: &impl PeerConnection, c: RTCIceCandidateInit) {
    pc.add_ice_candidate(c).await.expect("server add_ice");
}

pub async fn payload_type(sender: &Arc<dyn RtpSender>) -> u8 {
    sender.get_parameters().await.expect("params").rtp_parameters.codecs[0].payload_type
}

pub async fn send_media(
    video: (Arc<TrackLocalStaticSample>, Arc<dyn RtpSender>),
    audio: (Arc<TrackLocalStaticSample>, Arc<dyn RtpSender>),
    frames: u8,
) {
    let vpt = payload_type(&video.1).await;
    let apt = payload_type(&audio.1).await;
    let vssrc = *video.0.ssrcs().await.first().expect("vssrc");
    let assrc = *audio.0.ssrcs().await.first().expect("assrc");
    let mut tick = tokio::time::interval(Duration::from_millis(16));
    for n in 0..frames {
        tick.tick().await;
        let data = if n % 30 == 0 { keyframe(n) } else { delta(n) };
        let sample = Sample { data, duration: Duration::from_millis(16), ..Sample::new(Instant::now()) };
        video.0.sample_writer(vssrc, vpt).write_sample(&sample).await.expect("video sample");
        let opus = Sample {
            data: Bytes::from(vec![0xfc, n, 1, 2, 3]),
            duration: Duration::from_millis(20),
            ..Sample::new(Instant::now())
        };
        audio.0.sample_writer(assrc, apt).write_sample(&opus).await.expect("audio sample");
    }
}

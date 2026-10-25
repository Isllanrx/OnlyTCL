use std::collections::HashMap;

use rtc::peer_connection::configuration::media_engine::{MIME_TYPE_H264, MIME_TYPE_OPUS, MediaEngine};
use rtc::rtp_transceiver::rtp_sender::{RTCPFeedback, RTCRtpCodec, RTCRtpCodecParameters, RtpCodecKind};
use serde::Deserialize;

const DEFAULT_H264: [&str; 4] = ["4d001f", "64001f", "42e01f", "42001f"];
const OPUS_PT: u8 = 111;

#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CodecPref {
    pub mime_type: String,
    #[serde(default)]
    pub sdp_fmtp_line: Option<String>,
}

pub fn h264_fmtps(prefs: Option<&Vec<CodecPref>>) -> Vec<String> {
    let mut out: Vec<String> = Vec::new();
    for p in prefs.into_iter().flatten() {
        if !p.mime_type.eq_ignore_ascii_case(MIME_TYPE_H264) {
            continue;
        }
        let line = p.sdp_fmtp_line.clone().unwrap_or_default();
        if !line.contains("packetization-mode=1") || out.contains(&line) {
            continue;
        }
        out.push(line);
    }
    if out.is_empty() {
        out = DEFAULT_H264
            .iter()
            .map(|p| format!("level-asymmetry-allowed=1;packetization-mode=1;profile-level-id={p}"))
            .collect();
    }
    out
}

fn video_feedback() -> Vec<RTCPFeedback> {
    [("nack", ""), ("nack", "pli"), ("ccm", "fir"), ("goog-remb", "")]
        .into_iter()
        .map(|(typ, parameter)| RTCPFeedback { typ: typ.to_owned(), parameter: parameter.to_owned() })
        .collect()
}

pub fn opus_codec() -> RTCRtpCodec {
    RTCRtpCodec {
        mime_type: MIME_TYPE_OPUS.to_owned(),
        clock_rate: 48_000,
        channels: 2,
        sdp_fmtp_line: "minptime=10;useinbandfec=1".to_owned(),
        rtcp_feedback: vec![],
    }
}

pub fn register_codecs(me: &mut MediaEngine, prefs: &HashMap<String, Vec<CodecPref>>) -> rtc::shared::error::Result<()> {
    me.register_codec(
        RTCRtpCodecParameters { rtp_codec: opus_codec(), payload_type: OPUS_PT, ..Default::default() },
        RtpCodecKind::Audio,
    )?;
    let mut pt = 96u8;
    for fmtp in h264_fmtps(prefs.get("video")) {
        if pt == OPUS_PT {
            pt += 1;
        }
        me.register_codec(
            RTCRtpCodecParameters {
                rtp_codec: RTCRtpCodec {
                    mime_type: MIME_TYPE_H264.to_owned(),
                    clock_rate: 90_000,
                    channels: 0,
                    sdp_fmtp_line: fmtp,
                    rtcp_feedback: video_feedback(),
                },
                payload_type: pt,
                ..Default::default()
            },
            RtpCodecKind::Video,
        )?;
        pt += 1;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn keeps_page_order_and_drops_non_h264() {
        let prefs = vec![
            CodecPref { mime_type: "video/VP9".into(), sdp_fmtp_line: None },
            CodecPref {
                mime_type: "video/H264".into(),
                sdp_fmtp_line: Some("level-asymmetry-allowed=1;packetization-mode=1;profile-level-id=640c1f".into()),
            },
            CodecPref {
                mime_type: "video/H264".into(),
                sdp_fmtp_line: Some("level-asymmetry-allowed=1;packetization-mode=0;profile-level-id=42001f".into()),
            },
        ];
        let f = h264_fmtps(Some(&prefs));
        assert_eq!(f.len(), 1);
        assert!(f[0].ends_with("640c1f"));
    }

    #[test]
    fn falls_back_to_defaults() {
        assert_eq!(h264_fmtps(None).len(), DEFAULT_H264.len());
    }
}

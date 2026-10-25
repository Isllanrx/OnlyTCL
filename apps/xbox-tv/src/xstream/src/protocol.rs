use rtc::peer_connection::transport::RTCIceCandidateInit;
use serde::Deserialize;

use crate::codecs::CodecPref;

#[derive(Debug, Clone, Default, Deserialize)]
pub struct IceServer {
    #[serde(deserialize_with = "one_or_many")]
    pub urls: Vec<String>,
    pub username: Option<String>,
    pub credential: Option<String>,
}

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Config {
    #[serde(default)]
    pub ice_servers: Vec<IceServer>,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ChannelSpec {
    #[serde(default)]
    pub req: u32,
    pub id: i32,
    pub label: String,
    pub ordered: Option<bool>,
    pub max_retransmits: Option<u16>,
    pub max_packet_life_time: Option<u16>,
    pub protocol: Option<String>,
}

#[derive(Debug)]
pub enum Spec {
    Channel(ChannelSpec),
    Transceiver { kind: String, direction: Option<String> },
}

#[derive(Debug, Deserialize)]
#[serde(tag = "op", rename_all = "camelCase")]
pub enum Command {
    CreateDataChannel(ChannelSpec),
    AddTransceiver {
        kind: String,
        direction: Option<String>,
    },
    CodecPrefs {
        kind: String,
        codecs: Vec<CodecPref>,
    },
    CreateOffer {
        req: u32,
    },
    SetLocal {
        req: u32,
        sdp: Option<String>,
    },
    SetRemote {
        req: u32,
        #[serde(rename = "type")]
        kind: String,
        sdp: String,
    },
    AddIce {
        req: u32,
        candidate: RTCIceCandidateInit,
    },
    Stats {
        req: u32,
    },
    RequestKeyframe,
    Close,
}

fn one_or_many<'de, D>(d: D) -> Result<Vec<String>, D::Error>
where
    D: serde::Deserializer<'de>,
{
    #[derive(Deserialize)]
    #[serde(untagged)]
    enum Urls {
        One(String),
        Many(Vec<String>),
    }
    Ok(match Urls::deserialize(d)? {
        Urls::One(u) => vec![u],
        Urls::Many(v) => v,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_page_commands() {
        let c: Command = serde_json::from_str(
            r#"{"op":"createDataChannel","id":3,"label":"input","ordered":true,"protocol":"1.0"}"#,
        )
        .unwrap();
        assert!(matches!(c, Command::CreateDataChannel(ChannelSpec { id: 3, .. })));
        let c: Command = serde_json::from_str(
            r#"{"op":"addIce","req":7,"candidate":{"candidate":"a=candidate:1 1 UDP 1 1.2.3.4 9 typ host","sdpMid":"0","sdpMLineIndex":0}}"#,
        )
        .unwrap();
        let Command::AddIce { req: 7, candidate } = c else { panic!("addIce") };
        assert_eq!(candidate.sdp_mid.as_deref(), Some("0"));
        let c: Command = serde_json::from_str(r#"{"op":"setRemote","req":2,"type":"answer","sdp":"v=0"}"#).unwrap();
        assert!(matches!(c, Command::SetRemote { req: 2, .. }));
        let cfg: Config =
            serde_json::from_str(r#"{"iceServers":[{"urls":"stun:a"},{"urls":["turn:b"],"username":"u"}]}"#).unwrap();
        assert_eq!(cfg.ice_servers[0].urls, vec!["stun:a"]);
        assert_eq!(cfg.ice_servers[1].username.as_deref(), Some("u"));
    }
}

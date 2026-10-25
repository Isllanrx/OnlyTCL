use crate::metrics::METRICS;

#[derive(Debug, serde::Serialize)]
pub struct TvCommandResult {
    pub handled: bool,
    pub action: String,
    pub target: String,
    pub feedback_message: String,
    pub tokens_saved: usize,
}

/// Fast local zero-token voice command parser for Android TV
pub fn process_tv_command(query: &str) -> TvCommandResult {
    let q = query.trim().to_lowercase();

    // 1. YouTube
    if q.contains("abrir youtube") || q.contains("iniciar youtube") || q == "youtube" {
        METRICS.record_local_command(50);
        return TvCommandResult {
            handled: true,
            action: "launch_app".to_string(),
            target: "com.google.android.youtube.tv".to_string(),
            feedback_message: "Abrindo o YouTube...".to_string(),
            tokens_saved: 50,
        };
    }

    // 2. Netflix
    if q.contains("abrir netflix") || q.contains("iniciar netflix") || q == "netflix" {
        METRICS.record_local_command(50);
        return TvCommandResult {
            handled: true,
            action: "launch_app".to_string(),
            target: "com.netflix.ninja".to_string(),
            feedback_message: "Abrindo a Netflix...".to_string(),
            tokens_saved: 50,
        };
    }

    // 3. Twitch / ZeusBR
    if q.contains("abrir twitch") || q.contains("abrir zeus") || q == "twitch" || q == "zeusbr" {
        METRICS.record_local_command(50);
        return TvCommandResult {
            handled: true,
            action: "launch_app".to_string(),
            target: "com.isllantoso.zeusbr".to_string(),
            feedback_message: "Abrindo ZeusBR Twitch...".to_string(),
            tokens_saved: 50,
        };
    }

    // 4. Prime Video
    if q.contains("abrir prime") || q.contains("prime video") || q.contains("amazon prime") {
        METRICS.record_local_command(50);
        return TvCommandResult {
            handled: true,
            action: "launch_app".to_string(),
            target: "com.amazon.amazonvideo.livingroom".to_string(),
            feedback_message: "Abrindo Prime Video...".to_string(),
            tokens_saved: 50,
        };
    }

    // 5. GloboPlay
    if q.contains("abrir globoplay") || q.contains("globo play") {
        METRICS.record_local_command(50);
        return TvCommandResult {
            handled: true,
            action: "launch_app".to_string(),
            target: "com.globo.globotv".to_string(),
            feedback_message: "Abrindo Globoplay...".to_string(),
            tokens_saved: 50,
        };
    }

    // 6. Spotify
    if q.contains("abrir spotify") || q.contains("tocar spotify") || q == "spotify" {
        METRICS.record_local_command(50);
        return TvCommandResult {
            handled: true,
            action: "launch_app".to_string(),
            target: "com.spotify.tv.android".to_string(),
            feedback_message: "Abrindo Spotify...".to_string(),
            tokens_saved: 50,
        };
    }

    // 7. Configurações da TV
    if q.contains("configurações") || q.contains("ajustes da tv") || q.contains("abrir ajustes") {
        METRICS.record_local_command(40);
        return TvCommandResult {
            handled: true,
            action: "open_settings".to_string(),
            target: "android.settings.SETTINGS".to_string(),
            feedback_message: "Abrindo configurações da TV...".to_string(),
            tokens_saved: 40,
        };
    }

    // 8. Tela Inicial (Home)
    if q.contains("tela inicial") || q.contains("ir para início") || q.contains("voltar para início") || q == "início" || q == "home" {
        METRICS.record_local_command(40);
        return TvCommandResult {
            handled: true,
            action: "go_home".to_string(),
            target: "android.intent.action.MAIN".to_string(),
            feedback_message: "Voltando para a tela inicial...".to_string(),
            tokens_saved: 40,
        };
    }

    // 9. Controle de Volume
    if q.contains("aumentar volume") || q.contains("mais alto") {
        METRICS.record_local_command(35);
        return TvCommandResult {
            handled: true,
            action: "volume_up".to_string(),
            target: "KEYCODE_VOLUME_UP".to_string(),
            feedback_message: "Aumentando volume...".to_string(),
            tokens_saved: 35,
        };
    }
    if q.contains("diminuir volume") || q.contains("mais baixo") {
        METRICS.record_local_command(35);
        return TvCommandResult {
            handled: true,
            action: "volume_down".to_string(),
            target: "KEYCODE_VOLUME_DOWN".to_string(),
            feedback_message: "Diminuindo volume...".to_string(),
            tokens_saved: 35,
        };
    }
    if q.contains("mutar") || q.contains("silenciar") || q.contains("mudo") {
        METRICS.record_local_command(35);
        return TvCommandResult {
            handled: true,
            action: "volume_mute".to_string(),
            target: "KEYCODE_VOLUME_MUTE".to_string(),
            feedback_message: "Mudo ativado.".to_string(),
            tokens_saved: 35,
        };
    }

    // Not a local TV command; pass to Claude AI
    TvCommandResult {
        handled: false,
        action: "none".to_string(),
        target: "".to_string(),
        feedback_message: "".to_string(),
        tokens_saved: 0,
    }
}

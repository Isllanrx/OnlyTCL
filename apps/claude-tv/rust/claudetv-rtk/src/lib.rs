pub mod filter;
pub mod router;
pub mod metrics;

use jni::JNIEnv;
use jni::objects::{JClass, JString};
use jni::sys::jstring;

use crate::filter::filter_context;
use crate::router::process_tv_command;
use crate::metrics::METRICS;

/// JNI native: Filters conversation context to compress tokens and eliminate bloat
#[unsafe(no_mangle)]
pub extern "system" fn Java_com_anthropic_claude_tv_ClaudeTvRtk_nativeFilterContext(
    mut env: JNIEnv,
    _class: JClass,
    j_input: JString,
) -> jstring {
    let input: String = match env.get_string(&j_input) {
        Ok(s) => s.into(),
        Err(_) => return j_input.as_raw(),
    };

    let result = filter_context(&input);
    let json = serde_json::to_string(&result).unwrap_or_else(|_| "{}".to_string());

    match env.new_string(json) {
        Ok(js) => js.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

/// JNI native: Fast zero-token parser for local TV voice commands
#[unsafe(no_mangle)]
pub extern "system" fn Java_com_anthropic_claude_tv_ClaudeTvRtk_nativeProcessTvCommand(
    mut env: JNIEnv,
    _class: JClass,
    j_query: JString,
) -> jstring {
    let query: String = match env.get_string(&j_query) {
        Ok(s) => s.into(),
        Err(_) => return std::ptr::null_mut(),
    };

    let result = process_tv_command(&query);
    let json = serde_json::to_string(&result).unwrap_or_else(|_| "{}".to_string());

    match env.new_string(json) {
        Ok(js) => js.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

/// JNI native: Returns RTK metrics in JSON format
#[unsafe(no_mangle)]
pub extern "system" fn Java_com_anthropic_claude_tv_ClaudeTvRtk_nativeGetMetrics(
    env: JNIEnv,
    _class: JClass,
) -> jstring {
    let json = METRICS.to_json();
    match env.new_string(json) {
        Ok(js) => js.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

/// JNI native: Resets RTK metrics
#[unsafe(no_mangle)]
pub extern "system" fn Java_com_anthropic_claude_tv_ClaudeTvRtk_nativeResetMetrics(
    _env: JNIEnv,
    _class: JClass,
) {
    METRICS.reset();
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_filter_context() {
        let b64 = "A".repeat(500);
        let input = format!("Hello\n\n\n\nWorld\ndata:image/png;base64,{}\nEnd", b64);
        let res = filter_context(&input);
        assert!(res.tokens_saved > 0);
        assert!(res.filtered_text.contains("[media: base64 omitted"));
    }

    #[test]
    fn test_tv_command_youtube() {
        let res = process_tv_command("por favor abrir youtube");
        assert!(res.handled);
        assert_eq!(res.target, "com.google.android.youtube.tv");
        assert_eq!(res.tokens_saved, 50);
    }

    #[test]
    fn test_tv_command_claude() {
        let res = process_tv_command("quantos planetas existem no sistema solar?");
        assert!(!res.handled);
    }
}

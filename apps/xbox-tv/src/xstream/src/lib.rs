mod codecs;
mod events;
pub mod h264;
mod media;
mod protocol;
mod session;
pub mod sink;

use std::collections::HashMap;
use std::sync::{Arc, Mutex, OnceLock};

use bytes::BytesMut;
use jni::errors::ThrowRuntimeExAndDefault;
use jni::objects::{JByteArray, JObject, JString};
use jni::sys::{jboolean, jint, jlong};
use jni::{EnvUnowned, Env};
use serde_json::json;
use tokio::runtime::Runtime;
use tokio::sync::{Notify, mpsc};

use crate::media::Counters;
use crate::protocol::{Command, Config};
use crate::session::{Session, Shared};
use crate::sink::{JavaSink, Sink};

struct Handle {
    commands: mpsc::UnboundedSender<Command>,
    shared: Arc<Shared>,
}

fn runtime() -> &'static Runtime {
    static RT: OnceLock<Runtime> = OnceLock::new();
    RT.get_or_init(|| {
        tokio::runtime::Builder::new_multi_thread()
            .worker_threads(2)
            .thread_name("xstream")
            .enable_all()
            .build()
            .unwrap_or_else(|e| panic!("xstream runtime: {e}"))
    })
}

fn init_logging() {
    #[cfg(target_os = "android")]
    android_logger::init_once(android_logger::Config::default().with_max_level(log::LevelFilter::Info).with_tag("xstream"));
}

pub fn open(sink: Arc<dyn Sink>, config: &str) -> Result<i64, String> {
    let config: Config = serde_json::from_str(config).map_err(|e| format!("config: {e}"))?;
    let shared = Arc::new(Shared { sink, counters: Arc::new(Counters::default()), writers: Mutex::new(HashMap::new()), keyframe: Notify::new() });
    let (tx, rx) = mpsc::unbounded_channel();
    let session = Session::new(shared.clone(), config.ice_servers);
    runtime().spawn(session.run(rx));
    Ok(Box::into_raw(Box::new(Handle { commands: tx, shared })) as i64)
}

fn handle<'a>(h: jlong) -> Option<&'a Handle> {
    (h != 0).then(|| unsafe { &*(h as *const Handle) })
}

pub fn command(h: i64, json: &str) {
    let Some(handle) = handle(h) else { return };
    match serde_json::from_str::<Command>(json) {
        Ok(cmd) => {
            if handle.commands.send(cmd).is_err() {
                handle.shared.sink.event(json!({"ev": "error", "error": "session closed"}));
            }
        }
        Err(e) => handle.shared.sink.event(json!({"ev": "error", "error": format!("bad command: {e}")})),
    }
}

pub fn send(h: i64, id: i32, data: &[u8], text: bool) -> bool {
    let Some(handle) = handle(h) else { return false };
    let writers = handle.shared.writers.lock().unwrap_or_else(|p| p.into_inner());
    writers.get(&id).is_some_and(|w| w.send((BytesMut::from(data), text)).is_ok())
}

pub fn close(h: i64) {
    if h == 0 {
        return;
    }
    let handle = unsafe { Box::from_raw(h as *mut Handle) };
    let _ = handle.commands.send(Command::Close);
}

fn java_string(env: &Env, s: &JString) -> jni::errors::Result<String> {
    s.try_to_string(env)
}

#[unsafe(no_mangle)]
pub extern "system" fn Java_gamepass_fire_tv_XStream_nativeOpen<'l>(
    mut env: EnvUnowned<'l>,
    this: JObject<'l>,
    config: JString<'l>,
) -> jlong {
    init_logging();
    env.with_env(|env| -> jni::errors::Result<jlong> {
        let config = java_string(env, &config)?;
        let sink = Arc::new(JavaSink::new(env.get_java_vm()?, env.new_global_ref(&this)?));
        match open(sink, &config) {
            Ok(h) => Ok(h),
            Err(e) => {
                log::error!("xstream open: {e}");
                Ok(0)
            }
        }
    })
    .resolve::<ThrowRuntimeExAndDefault>()
}

#[unsafe(no_mangle)]
pub extern "system" fn Java_gamepass_fire_tv_XStream_nativeCommand<'l>(
    mut env: EnvUnowned<'l>,
    _this: JObject<'l>,
    h: jlong,
    json: JString<'l>,
) {
    env.with_env(|env| -> jni::errors::Result<()> {
        command(h, &java_string(env, &json)?);
        Ok(())
    })
    .resolve::<ThrowRuntimeExAndDefault>()
}

#[unsafe(no_mangle)]
pub extern "system" fn Java_gamepass_fire_tv_XStream_nativeSend<'l>(
    mut env: EnvUnowned<'l>,
    _this: JObject<'l>,
    h: jlong,
    id: jint,
    data: JByteArray<'l>,
    text: jboolean,
) -> jboolean {
    env.with_env(|env| -> jni::errors::Result<jboolean> {
        let bytes = env.convert_byte_array(&data)?;
        Ok(send(h, id, &bytes, text.into()).into())
    })
    .resolve::<ThrowRuntimeExAndDefault>()
}

#[unsafe(no_mangle)]
pub extern "system" fn Java_gamepass_fire_tv_XStream_nativeClose<'l>(
    mut env: EnvUnowned<'l>,
    _this: JObject<'l>,
    h: jlong,
) {
    env.with_env(|_env| -> jni::errors::Result<()> {
        close(h);
        Ok(())
    })
    .resolve::<ThrowRuntimeExAndDefault>()
}

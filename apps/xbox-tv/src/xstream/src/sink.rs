use jni::objects::JObject;
use jni::refs::Global;
use jni::{JValue, JavaVM, jni_sig, jni_str};
use serde_json::Value;

pub trait Sink: Send + Sync + 'static {
    fn event(&self, event: Value);
    fn channel(&self, id: i32, data: &[u8], text: bool);
    fn video(&self, data: &[u8], pts_us: i64, key: bool);
    fn audio(&self, data: &[u8], pts_us: i64);
}

pub struct JavaSink {
    vm: JavaVM,
    target: Global<JObject<'static>>,
}

impl JavaSink {
    pub fn new(vm: JavaVM, target: Global<JObject<'static>>) -> Self {
        Self { vm, target }
    }

    fn call<F>(&self, what: &str, f: F)
    where
        F: FnOnce(&mut jni::Env, &JObject<'static>) -> jni::errors::Result<()>,
    {
        let target = self.target.as_obj();
        if let Err(e) = self.vm.attach_current_thread(|env| f(env, target)) {
            log::error!("xstream callback {what} failed: {e}");
        }
    }
}

impl Sink for JavaSink {
    fn event(&self, event: Value) {
        let json = event.to_string();
        self.call("onEvent", |env, target| {
            let s = env.new_string(&json)?;
            env.call_method(target, jni_str!("onEvent"), jni_sig!("(Ljava/lang/String;)V"), &[JValue::Object(&s)])?;
            Ok(())
        });
    }

    fn channel(&self, id: i32, data: &[u8], text: bool) {
        self.call("onChannelMessage", |env, target| {
            let arr = env.byte_array_from_slice(data)?;
            env.call_method(
                target,
                jni_str!("onChannelMessage"),
                jni_sig!("(I[BZ)V"),
                &[JValue::Int(id), JValue::Object(&arr), JValue::Bool(text.into())],
            )?;
            Ok(())
        });
    }

    fn video(&self, data: &[u8], pts_us: i64, key: bool) {
        self.call("onVideo", |env, target| {
            let arr = env.byte_array_from_slice(data)?;
            env.call_method(
                target,
                jni_str!("onVideo"),
                jni_sig!("([BJZ)V"),
                &[JValue::Object(&arr), JValue::Long(pts_us), JValue::Bool(key.into())],
            )?;
            Ok(())
        });
    }

    fn audio(&self, data: &[u8], pts_us: i64) {
        self.call("onAudio", |env, target| {
            let arr = env.byte_array_from_slice(data)?;
            env.call_method(
                target,
                jni_str!("onAudio"),
                jni_sig!("([BJ)V"),
                &[JValue::Object(&arr), JValue::Long(pts_us)],
            )?;
            Ok(())
        });
    }
}

package gamepass.fire.tv;

import android.app.Activity;
import android.app.Application;
import android.content.Context;
import android.graphics.Color;
import android.media.AudioManager;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Base64;
import android.util.Log;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.WebView;
import androidx.webkit.JavaScriptReplyProxy;
import androidx.webkit.WebMessageCompat;
import androidx.webkit.WebViewCompat;
import androidx.webkit.WebViewFeature;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.Set;
import org.json.JSONException;
import org.json.JSONObject;

public final class XStreamBridge implements WebViewCompat.WebMessageListener, XStream.Listener, SurfaceHolder.Callback {
    private static final String TAG = "XStreamBridge";
    static final String OBJECT = "XStreamNative";
    static final String LIB = "www/xstream-lib.js";
    static final String ASSET = "www/xstream.js";
    private static final String KEYFRAME = "{\"op\":\"requestKeyframe\"}";
    static final String TUNNEL_FLAG = "xstream-tunnel";
    private static final Set<String> ORIGINS = Collections.singleton("*");

    private final Handler main = new Handler(Looper.getMainLooper());
    private final WebView webView;
    private SurfaceView surfaceView;
    private JavaScriptReplyProxy reply;
    private volatile XStream stream;
    private volatile VideoSink video;
    private volatile AudioSink audio;
    private boolean surfaceReady;
    private boolean surfaceWanted;
    private int audioSession;

    private XStreamBridge(WebView webView) {
        this.webView = webView;
    }

    static String wrap(String lib, String main) {
        return "(function () {\n'use strict';\n" + lib + "\n" + main + "\n})();\n";
    }

    public static boolean install(Context context, WebView webView, String script) {
        if (!WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER)
                || !WebViewFeature.isFeatureSupported(WebViewFeature.DOCUMENT_START_SCRIPT)) {
            Log.w(TAG, "WebView lacks message listener support; native stream disabled");
            return false;
        }
        if (!XStream.available()) return false;
        XStreamBridge bridge = new XStreamBridge(webView);
        WebViewCompat.addWebMessageListener(webView, OBJECT, ORIGINS, bridge);
        WebViewCompat.addDocumentStartJavaScript(webView, script, ORIGINS);
        if (context instanceof Activity) bridge.watch((Activity) context);
        Log.i(TAG, "native stream bridge installed");
        return true;
    }

    private void watch(Activity activity) {
        activity.getApplication().registerActivityLifecycleCallbacks(new Application.ActivityLifecycleCallbacks() {
            @Override public void onActivityCreated(Activity a, Bundle b) {}
            @Override public void onActivityStarted(Activity a) {}
            @Override public void onActivityResumed(Activity a) {}
            @Override public void onActivityPaused(Activity a) {}
            @Override public void onActivityStopped(Activity a) {}
            @Override public void onActivitySaveInstanceState(Activity a, Bundle b) {}
            @Override public void onActivityDestroyed(Activity a) {
                if (a == activity) closeStream();
            }
        });
    }

    @Override
    public void onPostMessage(WebView view, WebMessageCompat message, Uri origin, boolean isMainFrame, JavaScriptReplyProxy proxy) {
        if (message.getType() != WebMessageCompat.TYPE_STRING) return;
        try {
            handle(new JSONObject(message.getData()), proxy);
        } catch (JSONException e) {
            Log.w(TAG, "malformed page message", e);
        }
    }

    private void handle(JSONObject m, JavaScriptReplyProxy proxy) throws JSONException {
        switch (m.getString("t")) {
            case "send": {
                boolean text = m.optBoolean("text");
                String data = m.getString("data");
                byte[] bytes = text ? data.getBytes(StandardCharsets.UTF_8) : Base64.decode(data, Base64.NO_WRAP);
                if (stream != null) stream.send(m.getInt("id"), bytes, text);
                break;
            }
            case "cmd":
                if (stream != null) stream.command(m.getJSONObject("cmd").toString());
                break;
            case "open":
                closeStream();
                reply = proxy;
                audioSession = tunnelSession();
                stream = XStream.open(m.optJSONObject("config") == null ? "{}" : m.getJSONObject("config").toString(), this);
                Log.i(TAG, "page opened native session " + (stream != null) + ", tunnel session " + audioSession);
                if (stream == null) post("{\"ev\":\"fatal\",\"error\":\"native open failed\"}");
                break;
            case "error":
                Log.e(TAG, "page " + m.optString("where") + ": " + m.optString("error"));
                break;
            case "surface":
                setSurface(m.getBoolean("on"));
                break;
            case "decoderStats":
                post("{\"ev\":\"decoderStats\",\"req\":" + m.getInt("req") + ",\"video\":"
                        + (video == null ? "null" : video.stats()) + ",\"audio\":"
                        + (audio == null ? "null" : audio.stats()) + "}");
                break;
            case "close":
                closeStream();
                break;
            default:
                Log.w(TAG, "unknown page message " + m.getString("t"));
        }
    }

    private int tunnelSession() {
        Context context = webView.getContext();
        File dir = context.getExternalFilesDir(null);
        if (dir == null || !new File(dir, TUNNEL_FLAG).exists()) return 0;
        if (Decoders.pick(VideoSink.MIME, true) == null) {
            Log.w(TAG, "tunnel requested but no hardware H.264 decoder supports tunneled playback");
            return 0;
        }
        AudioManager am = (AudioManager) context.getSystemService(Context.AUDIO_SERVICE);
        int id = am == null ? 0 : am.generateAudioSessionId();
        return id > 0 ? id : 0;
    }

    private boolean attachSurface() {
        if (surfaceView != null) return true;
        if (!(webView.getParent() instanceof ViewGroup)) {
            Log.w(TAG, "WebView has no parent view; cannot place video surface");
            return false;
        }
        ViewGroup parent = (ViewGroup) webView.getParent();
        surfaceView = new SurfaceView(webView.getContext());
        surfaceView.getHolder().addCallback(this);
        parent.addView(surfaceView, parent.indexOfChild(webView), new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        return true;
    }

    private void setSurface(boolean on) {
        if (on && !attachSurface()) {
            post("{\"ev\":\"fatal\",\"error\":\"no video surface\"}");
            return;
        }
        surfaceWanted = on;
        if (surfaceView != null) surfaceView.setVisibility(on ? View.VISIBLE : View.GONE);
        webView.setBackgroundColor(on ? Color.TRANSPARENT : Color.BLACK);
        if (!on) releaseVideo();
    }

    private void releaseVideo() {
        if (video != null) {
            video.close();
            video = null;
        }
    }

    private void closeStream() {
        if (stream != null) {
            stream.close();
            stream = null;
        }
        releaseVideo();
        if (audio != null) {
            audio.close();
            audio = null;
        }
        if (surfaceWanted) setSurface(false);
        reply = null;
    }

    private void post(String json) {
        main.post(() -> {
            JavaScriptReplyProxy r = reply;
            if (r != null) r.postMessage(json);
        });
    }

    @Override
    public void onEvent(String json) {
        post(json);
    }

    @Override
    public void onChannelMessage(int id, byte[] data, boolean text) {
        String payload = text ? new String(data, StandardCharsets.UTF_8) : Base64.encodeToString(data, Base64.NO_WRAP);
        try {
            post(new JSONObject().put("ev", "msg").put("id", id).put("text", text).put("data", payload).toString());
        } catch (JSONException e) {
            Log.w(TAG, "cannot encode channel message", e);
        }
    }

    @Override
    public void onVideo(byte[] frame, long ptsUs, boolean key) {
        VideoSink v = video;
        if (v != null) {
            v.push(frame, ptsUs, key);
            return;
        }
        main.post(this::createVideo);
    }

    private void createVideo() {
        XStream s = stream;
        if (video != null || !surfaceReady || !surfaceWanted || s == null) return;
        video = new VideoSink(surfaceView.getHolder().getSurface(), audioSession, () -> {
            AudioSink a = audio;
            return a == null ? -1 : a.syncedPtsUs();
        }, () -> main.post(() -> {
            if (stream == s) s.command(KEYFRAME);
        }));
        s.command(KEYFRAME);
    }

    @Override
    public void onAudio(byte[] packet, long ptsUs) {
        AudioSink a = audio;
        if (a != null) {
            a.push(packet, ptsUs);
            return;
        }
        main.post(() -> {
            if (audio == null && stream != null) audio = new AudioSink(audioSession);
        });
    }

    @Override
    public void surfaceCreated(SurfaceHolder holder) {
        surfaceReady = true;
    }

    @Override
    public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) {}

    @Override
    public void surfaceDestroyed(SurfaceHolder holder) {
        surfaceReady = false;
        releaseVideo();
    }
}

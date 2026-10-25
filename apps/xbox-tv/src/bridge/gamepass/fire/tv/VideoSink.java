package gamepass.fire.tv;

import android.media.MediaCodec;
import android.media.MediaCodecInfo;
import android.media.MediaFormat;
import android.os.Build;
import android.os.Handler;
import android.os.HandlerThread;
import android.util.Log;
import android.view.Surface;
import java.nio.ByteBuffer;
import java.util.ArrayDeque;
import java.util.HashMap;
import java.util.Map;
import java.util.function.LongSupplier;

final class VideoSink extends MediaCodec.Callback {
    private static final String TAG = "XStreamVideo";
    static final String MIME = "video/avc";
    private static final int MAX_QUEUED = 6;
    private static final int MAX_WIDTH = 1920;
    private static final int MAX_HEIGHT = 1080;
    private static final long TUNNEL_WATCHDOG_MS = 2000;

    private static final class Frame {
        final byte[] data;
        final long ptsUs;
        final boolean key;

        Frame(byte[] data, long ptsUs, boolean key) {
            this.data = data;
            this.ptsUs = ptsUs;
            this.key = key;
        }
    }

    private final HandlerThread thread = new HandlerThread("xstream-video", android.os.Process.THREAD_PRIORITY_URGENT_DISPLAY);
    private final Handler handler;
    private final ArrayDeque<Frame> frames = new ArrayDeque<>();
    private final ArrayDeque<Integer> inputs = new ArrayDeque<>();
    private final Map<Long, Long> queuedAt = new HashMap<>();
    private final Surface surface;
    private final int audioSession;
    private final LongSupplier audioPtsUs;
    private final Runnable keyframeRequest;
    private MediaCodec codec;
    private boolean tunnelAllowed;
    private volatile boolean tunneled;
    private long ptsOffsetUs;
    private boolean waitingKey = true;
    private volatile long decoded;
    private volatile long dropped;
    private volatile long decodeNanos;
    private volatile int width;
    private volatile int height;

    VideoSink(Surface surface, int audioSession, LongSupplier audioPtsUs, Runnable keyframeRequest) {
        this.surface = surface;
        this.audioSession = audioSession;
        this.audioPtsUs = audioPtsUs;
        this.keyframeRequest = keyframeRequest;
        this.tunnelAllowed = audioSession != 0;
        thread.start();
        handler = new Handler(thread.getLooper());
    }

    void push(byte[] data, long ptsUs, boolean key) {
        handler.post(() -> accept(new Frame(data, ptsUs, key)));
    }

    private void accept(Frame f) {
        if (codec == null) {
            if (!f.key) return;
            start(f);
            if (codec == null) return;
        }
        if (waitingKey && !f.key) {
            dropped++;
            return;
        }
        waitingKey = false;
        if (frames.size() >= MAX_QUEUED) {
            dropped += frames.size();
            frames.clear();
            if (!f.key) {
                dropped++;
                requestKeyframe();
                return;
            }
        }
        frames.add(f);
        feed();
    }

    private void start(Frame first) {
        long audioPts = tunnelAllowed ? audioPtsUs.getAsLong() : -1;
        boolean tunnel = audioPts >= 0;
        String name = Decoders.pick(MIME, tunnel);
        if (name == null && tunnel) {
            tunnel = false;
            name = Decoders.pick(MIME, false);
        }
        MediaFormat format = format(tunnel);
        MediaCodec c = null;
        try {
            c = name != null ? MediaCodec.createByCodecName(name) : MediaCodec.createDecoderByType(MIME);
            c.setCallback(this, handler);
            try {
                c.configure(format, surface, null, 0);
            } catch (RuntimeException e) {
                Log.w(TAG, "configure rejected (tunnel=" + tunnel + "), retrying on surface without low latency", e);
                c.reset();
                c.setCallback(this, handler);
                tunnel = false;
                format = format(false);
                format.removeKey(MediaFormat.KEY_LOW_LATENCY);
                c.configure(format, surface, null, 0);
            }
            c.setVideoScalingMode(MediaCodec.VIDEO_SCALING_MODE_SCALE_TO_FIT);
            if (tunnel) c.setOnFrameRenderedListener((mc, pts, ns) -> decoded++, handler);
            c.start();
            codec = c;
            tunneled = tunnel;
            ptsOffsetUs = tunnel ? audioPts - first.ptsUs : 0;
            if (tunnel) handler.postDelayed(this::checkTunnel, TUNNEL_WATCHDOG_MS);
            Log.i(TAG, "decoder " + c.getName() + " started" + (tunnel ? " tunneled, session " + audioSession : " on surface"));
        } catch (Exception e) {
            Log.e(TAG, "cannot start H.264 decoder", e);
            if (c != null) c.release();
        }
    }

    private MediaFormat format(boolean tunnel) {
        MediaFormat format = MediaFormat.createVideoFormat(MIME, MAX_WIDTH, MAX_HEIGHT);
        format.setInteger(MediaFormat.KEY_MAX_WIDTH, MAX_WIDTH);
        format.setInteger(MediaFormat.KEY_MAX_HEIGHT, MAX_HEIGHT);
        format.setInteger(MediaFormat.KEY_MAX_INPUT_SIZE, 1 << 20);
        format.setInteger(MediaFormat.KEY_PRIORITY, 0);
        format.setInteger(MediaFormat.KEY_FRAME_RATE, 60);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) format.setInteger(MediaFormat.KEY_LOW_LATENCY, 1);
        if (tunnel) {
            format.setFeatureEnabled(MediaCodecInfo.CodecCapabilities.FEATURE_TunneledPlayback, true);
            format.setInteger(MediaFormat.KEY_AUDIO_SESSION_ID, audioSession);
        }
        return format;
    }

    private void checkTunnel() {
        if (codec == null || !tunneled || decoded > 0) return;
        Log.w(TAG, "tunneled decoder rendered nothing in " + TUNNEL_WATCHDOG_MS + " ms; falling back to surface output");
        dropTunnel();
    }

    private void dropTunnel() {
        tunnelAllowed = false;
        release();
        requestKeyframe();
    }

    private void feed() {
        while (codec != null && !frames.isEmpty() && !inputs.isEmpty()) {
            Frame f = frames.poll();
            int index = inputs.poll();
            try {
                ByteBuffer buf = codec.getInputBuffer(index);
                if (buf == null || buf.capacity() < f.data.length) {
                    Log.w(TAG, "frame of " + f.data.length + " bytes does not fit input buffer");
                    inputs.addFirst(index);
                    dropped += 1 + frames.size();
                    frames.clear();
                    requestKeyframe();
                    continue;
                }
                buf.clear();
                buf.put(f.data);
                long pts = f.ptsUs + ptsOffsetUs;
                queuedAt.put(pts, System.nanoTime());
                codec.queueInputBuffer(index, 0, f.data.length, pts, f.key ? MediaCodec.BUFFER_FLAG_KEY_FRAME : 0);
            } catch (IllegalStateException e) {
                Log.e(TAG, "queueInputBuffer failed", e);
                return;
            }
        }
    }

    @Override
    public void onInputBufferAvailable(MediaCodec c, int index) {
        if (c != codec) return;
        inputs.add(index);
        feed();
    }

    @Override
    public void onOutputBufferAvailable(MediaCodec c, int index, MediaCodec.BufferInfo info) {
        if (c != codec) return;
        Long t = queuedAt.remove(info.presentationTimeUs);
        if (t != null) decodeNanos += System.nanoTime() - t;
        if (queuedAt.size() > 64) queuedAt.clear();
        decoded++;
        c.releaseOutputBuffer(index, true);
    }

    @Override
    public void onError(MediaCodec c, MediaCodec.CodecException e) {
        Log.e(TAG, "decoder error (tunnel=" + tunneled + ")", e);
        if (c != codec) return;
        if (tunneled) {
            dropTunnel();
            return;
        }
        release();
        requestKeyframe();
    }

    @Override
    public void onOutputFormatChanged(MediaCodec c, MediaFormat format) {
        width = format.getInteger(MediaFormat.KEY_WIDTH);
        height = format.getInteger(MediaFormat.KEY_HEIGHT);
    }

    private void release() {
        if (codec == null) return;
        try {
            codec.stop();
        } catch (IllegalStateException e) {
            Log.w(TAG, "decoder stop", e);
        }
        codec.release();
        codec = null;
        tunneled = false;
        ptsOffsetUs = 0;
        inputs.clear();
        frames.clear();
        queuedAt.clear();
    }

    private void requestKeyframe() {
        waitingKey = true;
        keyframeRequest.run();
    }

    String stats() {
        long n = decoded;
        return "{\"framesDecoded\":" + n + ",\"framesDropped\":" + dropped
                + ",\"totalDecodeTime\":" + (decodeNanos / 1e9) + ",\"frameWidth\":" + width
                + ",\"frameHeight\":" + height + ",\"tunneled\":" + tunneled + "}";
    }

    void close() {
        handler.post(() -> {
            release();
            thread.quitSafely();
        });
    }
}

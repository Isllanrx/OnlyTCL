package gamepass.fire.tv;

import android.media.AudioAttributes;
import android.media.AudioFormat;
import android.media.AudioTrack;
import android.media.MediaCodec;
import android.media.MediaFormat;
import android.os.Handler;
import android.os.HandlerThread;
import android.util.Log;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.ArrayDeque;

final class AudioSink extends MediaCodec.Callback {
    private static final String TAG = "XStreamAudio";
    private static final String MIME = "audio/opus";
    private static final int RATE = 48000;
    private static final int PRE_SKIP = 312;
    private static final int MAX_QUEUED = 10;

    private final HandlerThread thread = new HandlerThread("xstream-audio", android.os.Process.THREAD_PRIORITY_URGENT_AUDIO);
    private final Handler handler;
    private final ArrayDeque<byte[]> packets = new ArrayDeque<>();
    private final ArrayDeque<Long> times = new ArrayDeque<>();
    private final ArrayDeque<Integer> inputs = new ArrayDeque<>();
    private final int session;
    private MediaCodec codec;
    private AudioTrack track;
    private boolean synced;
    private boolean failed;
    private volatile long played;
    private volatile long dropped;
    private volatile long syncedPtsUs = -1;

    AudioSink(int session) {
        this.session = session;
        thread.start();
        handler = new Handler(thread.getLooper());
    }

    void push(byte[] packet, long ptsUs) {
        handler.post(() -> accept(packet, ptsUs));
    }

    private void accept(byte[] packet, long ptsUs) {
        if (codec == null && !failed) start();
        if (codec == null) return;
        if (packets.size() >= MAX_QUEUED) {
            dropped += packets.size();
            packets.clear();
            times.clear();
        }
        packets.add(packet);
        times.add(ptsUs);
        feed();
    }

    private static ByteBuffer le64(long v) {
        return ByteBuffer.allocate(8).order(ByteOrder.LITTLE_ENDIAN).putLong(0, v);
    }

    private static ByteBuffer opusHead() {
        ByteBuffer b = ByteBuffer.allocate(19).order(ByteOrder.LITTLE_ENDIAN);
        b.put(new byte[] {'O', 'p', 'u', 's', 'H', 'e', 'a', 'd', 1, 2});
        b.putShort((short) PRE_SKIP);
        b.putInt(RATE);
        b.putShort((short) 0);
        b.put((byte) 0);
        b.flip();
        return b;
    }

    private void start() {
        try {
            MediaFormat format = MediaFormat.createAudioFormat(MIME, RATE, 2);
            format.setByteBuffer("csd-0", opusHead());
            format.setByteBuffer("csd-1", le64(PRE_SKIP * 1_000_000_000L / RATE));
            format.setByteBuffer("csd-2", le64(80_000_000L));
            if (session != 0) {
                try {
                    track = buildTrack(true);
                    synced = true;
                } catch (RuntimeException e) {
                    Log.w(TAG, "HW A/V sync track rejected; video stays off the tunnel", e);
                }
            }
            if (track == null) track = buildTrack(false);
            track.play();
            MediaCodec c = MediaCodec.createDecoderByType(MIME);
            c.setCallback(this, handler);
            c.configure(format, null, null, 0);
            c.start();
            codec = c;
            Log.i(TAG, "decoder " + c.getName() + " started, track buffer " + track.getBufferSizeInFrames());
        } catch (Exception e) {
            Log.e(TAG, "cannot start Opus playback", e);
            failed = true;
            release();
        }
    }

    private AudioTrack buildTrack(boolean hwSync) {
        int min = AudioTrack.getMinBufferSize(RATE, AudioFormat.CHANNEL_OUT_STEREO, AudioFormat.ENCODING_PCM_16BIT);
        AudioAttributes.Builder attributes = new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_GAME)
                .setContentType(AudioAttributes.CONTENT_TYPE_MOVIE);
        if (hwSync) attributes.setFlags(AudioAttributes.FLAG_HW_AV_SYNC);
        AudioTrack.Builder builder = new AudioTrack.Builder()
                .setAudioAttributes(attributes.build())
                .setAudioFormat(new AudioFormat.Builder()
                        .setSampleRate(RATE)
                        .setChannelMask(AudioFormat.CHANNEL_OUT_STEREO)
                        .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                        .build())
                .setBufferSizeInBytes(min * 2)
                .setTransferMode(AudioTrack.MODE_STREAM);
        if (hwSync) builder.setSessionId(session);
        else builder.setPerformanceMode(AudioTrack.PERFORMANCE_MODE_LOW_LATENCY);
        return builder.build();
    }

    long syncedPtsUs() {
        return syncedPtsUs;
    }

    private void feed() {
        while (codec != null && !packets.isEmpty() && !inputs.isEmpty()) {
            byte[] p = packets.poll();
            long pts = times.poll();
            int index = inputs.poll();
            try {
                ByteBuffer buf = codec.getInputBuffer(index);
                if (buf == null || buf.capacity() < p.length) {
                    inputs.addFirst(index);
                    dropped++;
                    continue;
                }
                buf.clear();
                buf.put(p);
                codec.queueInputBuffer(index, 0, p.length, pts, 0);
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
        ByteBuffer out = c.getOutputBuffer(index);
        if (out != null && info.size > 0 && track != null) {
            out.position(info.offset);
            out.limit(info.offset + info.size);
            int written = synced
                    ? track.write(out, info.size, AudioTrack.WRITE_BLOCKING, info.presentationTimeUs * 1000)
                    : track.write(out, info.size, AudioTrack.WRITE_NON_BLOCKING);
            if (written < info.size) {
                dropped++;
            } else {
                played++;
                if (synced) syncedPtsUs = info.presentationTimeUs;
            }
        }
        c.releaseOutputBuffer(index, false);
    }

    @Override
    public void onError(MediaCodec c, MediaCodec.CodecException e) {
        Log.e(TAG, "decoder error", e);
        if (c == codec) release();
    }

    @Override
    public void onOutputFormatChanged(MediaCodec c, MediaFormat format) {
        Log.i(TAG, "output format " + format);
    }

    private void release() {
        if (codec != null) {
            try {
                codec.stop();
            } catch (IllegalStateException e) {
                Log.w(TAG, "decoder stop", e);
            }
            codec.release();
            codec = null;
        }
        if (track != null) {
            track.release();
            track = null;
        }
        synced = false;
        syncedPtsUs = -1;
        inputs.clear();
        packets.clear();
        times.clear();
    }

    String stats() {
        return "{\"audioPlayed\":" + played + ",\"audioDropped\":" + dropped + ",\"hwAvSync\":" + (syncedPtsUs >= 0) + "}";
    }

    void close() {
        handler.post(() -> {
            release();
            thread.quitSafely();
        });
    }
}

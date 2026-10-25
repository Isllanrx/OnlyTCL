package gamepass.fire.tv;

public final class XStream {
    public interface Listener {
        void onEvent(String json);

        void onChannelMessage(int id, byte[] data, boolean text);

        void onVideo(byte[] frame, long ptsUs, boolean key);

        void onAudio(byte[] packet, long ptsUs);
    }

    private static Boolean loaded;

    private final Listener listener;
    private long handle;
    private volatile boolean closed;

    private XStream(Listener listener) {
        this.listener = listener;
    }

    public static synchronized boolean available() {
        if (loaded == null) {
            try {
                System.loadLibrary("xstream");
                loaded = true;
            } catch (UnsatisfiedLinkError e) {
                android.util.Log.e("XStream", "libxstream not loadable", e);
                loaded = false;
            }
        }
        return loaded;
    }

    public static XStream open(String configJson, Listener listener) {
        XStream s = new XStream(listener);
        s.handle = s.nativeOpen(configJson);
        return s.handle == 0 ? null : s;
    }

    public void command(String json) {
        if (handle != 0) nativeCommand(handle, json);
    }

    public boolean send(int id, byte[] data, boolean text) {
        return handle != 0 && nativeSend(handle, id, data, text);
    }

    public void close() {
        closed = true;
        long h = handle;
        handle = 0;
        if (h != 0) nativeClose(h);
    }

    void onEvent(String json) {
        if (!closed) listener.onEvent(json);
    }

    void onChannelMessage(int id, byte[] data, boolean text) {
        if (!closed) listener.onChannelMessage(id, data, text);
    }

    void onVideo(byte[] frame, long ptsUs, boolean key) {
        if (!closed) listener.onVideo(frame, ptsUs, key);
    }

    void onAudio(byte[] packet, long ptsUs) {
        if (!closed) listener.onAudio(packet, ptsUs);
    }

    private native long nativeOpen(String configJson);

    private native void nativeCommand(long handle, String json);

    private native boolean nativeSend(long handle, int id, byte[] data, boolean text);

    private native void nativeClose(long handle);
}

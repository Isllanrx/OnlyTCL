package gamepass.fire.tv;

import android.media.MediaCodecInfo;
import android.media.MediaCodecList;
import android.os.Build;
import java.util.Locale;

final class Decoders {
    private Decoders() {}

    static String pick(String mime, boolean tunneled) {
        for (MediaCodecInfo info : new MediaCodecList(MediaCodecList.REGULAR_CODECS).getCodecInfos()) {
            if (info.isEncoder() || !supports(info, mime) || !isHardware(info)) continue;
            if (tunneled && !info.getCapabilitiesForType(mime)
                    .isFeatureSupported(MediaCodecInfo.CodecCapabilities.FEATURE_TunneledPlayback)) continue;
            return info.getName();
        }
        return null;
    }

    private static boolean supports(MediaCodecInfo info, String mime) {
        for (String type : info.getSupportedTypes()) {
            if (type.equalsIgnoreCase(mime)) return true;
        }
        return false;
    }

    static boolean isHardware(MediaCodecInfo info) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            return info.isHardwareAccelerated() && !info.isSoftwareOnly();
        }
        String name = info.getName().toLowerCase(Locale.ROOT);
        return !name.startsWith("omx.google.") && !name.startsWith("c2.android.") && !name.contains(".sw.");
    }
}

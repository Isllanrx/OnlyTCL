package gamepass.fire.tv;

import android.content.Context;
import android.util.Log;
import android.webkit.WebView;
import androidx.webkit.WebViewCompat;
import androidx.webkit.WebViewFeature;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Collections;

public class TvShim {
    private static final String TAG = "XboxTvShim";
    private static final String ASSET = "www/tv-shim.js";
    private static final String ORIGIN = "*";

    public static void install(Context context, WebView webView) {
        if (!WebViewFeature.isFeatureSupported(WebViewFeature.DOCUMENT_START_SCRIPT)) {
            Log.e(TAG, "DOCUMENT_START_SCRIPT unsupported by this WebView; shim not installed");
            return;
        }
        try {
            WebViewCompat.addDocumentStartJavaScript(webView, readAsset(context, ASSET), Collections.singleton(ORIGIN));
        } catch (IOException e) {
            Log.e(TAG, "Cannot read " + ASSET, e);
        }
        try {
            XStreamBridge.install(context, webView,
                    XStreamBridge.wrap(readAsset(context, XStreamBridge.LIB), readAsset(context, XStreamBridge.ASSET)));
        } catch (IOException e) {
            Log.e(TAG, "Cannot read " + XStreamBridge.ASSET, e);
        }
    }

    private static String readAsset(Context context, String name) throws IOException {
        try (InputStream in = context.getAssets().open(name)) {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) != -1) out.write(buf, 0, n);
            return new String(out.toByteArray(), StandardCharsets.UTF_8);
        }
    }
}

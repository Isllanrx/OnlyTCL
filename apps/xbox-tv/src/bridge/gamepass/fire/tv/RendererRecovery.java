package gamepass.fire.tv;

import android.app.Activity;
import android.util.Log;
import android.view.ViewGroup;
import android.webkit.RenderProcessGoneDetail;
import android.webkit.WebView;

public final class RendererRecovery {
    private RendererRecovery() {}

    public static boolean onGone(Activity activity, WebView webView, RenderProcessGoneDetail detail) {
        Log.e("XboxRenderer", "WebView renderer gone, crashed=" + detail.didCrash()
                + " priority=" + detail.rendererPriorityAtExit());
        GamepadBridge.setInGame(false);
        if (webView.getParent() instanceof ViewGroup) {
            ((ViewGroup) webView.getParent()).removeView(webView);
        }
        if (!activity.isFinishing() && !activity.isDestroyed()) activity.recreate();
        return true;
    }
}

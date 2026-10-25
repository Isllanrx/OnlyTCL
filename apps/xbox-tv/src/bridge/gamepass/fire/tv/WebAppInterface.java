package gamepass.fire.tv;

import android.webkit.JavascriptInterface;

public final class WebAppInterface {
    @JavascriptInterface
    public String getVersionName() {
        return "3.2.1";
    }

    @JavascriptInterface
    public String getGamepadState() {
        return GamepadBridge.state();
    }

    @JavascriptInterface
    public void setInGame(boolean inGame) {
        GamepadBridge.setInGame(inGame);
    }
}

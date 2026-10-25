package com.anthropic.claude.tv;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.view.KeyEvent;
import android.view.accessibility.AccessibilityEvent;

/**
 * Recebe a tecla de voz do controle (219/231/4139) quando o sistema a entrega a serviços de
 * acessibilidade e a roteia pelo contexto (ADR-011). Demais teclas seguem sem custo.
 */
public final class ClaudeTvAccessibilityService extends AccessibilityService {

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {}

    @Override
    public void onInterrupt() {}

    @Override
    protected void onServiceConnected() {
        AccessibilityServiceInfo info = getServiceInfo();
        if (info == null) info = new AccessibilityServiceInfo();
        info.flags |= AccessibilityServiceInfo.FLAG_REQUEST_FILTER_KEY_EVENTS;
        setServiceInfo(info);
    }

    @Override
    protected boolean onKeyEvent(KeyEvent event) {
        int keyCode = event.getKeyCode();
        if (keyCode != ClaudeTvHelper.KEYCODE_VOICE_ASSIST
                && keyCode != ClaudeTvHelper.KEYCODE_TCL_HOVRING
                && keyCode != ClaudeTvHelper.KEYCODE_ASSIST) {
            return false;
        }
        if (event.getAction() == KeyEvent.ACTION_DOWN && event.getRepeatCount() == 0) {
            ClaudeTvHelper.handleAccessibilityVoiceKey(this);
        }
        return true;
    }
}

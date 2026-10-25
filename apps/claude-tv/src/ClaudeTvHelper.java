package com.anthropic.claude.tv;

import android.app.Activity;
import android.app.ActivityManager;
import android.app.Service;
import android.app.UiModeManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.res.Configuration;
import android.graphics.Outline;
import android.graphics.PixelFormat;
import android.os.SystemClock;
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewOutlineProvider;
import android.view.Window;
import android.view.WindowManager;
import android.widget.Toast;
import java.lang.ref.WeakReference;
import java.util.List;

/**
 * Adaptação do Claude à TV TCL (Android TV 11). Pontos de entrada chamados pelos hooks smali:
 * onActivityCreate, handleKeyDown (MainActivity), onOverlayCreate (AssistantOverlayActivity),
 * resolveOverlayVoice (BellModeService e sessões), shouldSuppressIconButton (composer) e
 * handleAccessibilityVoiceKey (ClaudeTvAccessibilityService).
 */
public final class ClaudeTvHelper {
    private static final String TAG = "ClaudeTV";

    static final int KEYCODE_TCL_HOVRING = 4139;
    static final int KEYCODE_VOICE_ASSIST = KeyEvent.KEYCODE_VOICE_ASSIST;
    static final int KEYCODE_ASSIST = KeyEvent.KEYCODE_ASSIST;

    private static final String MAIN_ACTIVITY = "com.anthropic.claude.mainactivity.MainActivity";
    private static final String OVERLAY_ACTIVITY = "com.anthropic.claude.mainactivity.AssistantOverlayActivity";
    private static final String BELL_MODE_SERVICE = "com.anthropic.claude.bell.BellModeService";
    private static final String EXTRA_START_CHAT_MODE = "com.anthropic.claude.intent.extra.START_CHAT_MODE";
    private static final String EXTRA_VOICE_ENTRY_SOURCE = "com.anthropic.claude.intent.extra.START_CHAT_VOICE_ENTRY_SOURCE";

    /** A TCL pode entregar 219 e 231/4139 para o mesmo toque no controle. */
    private static final long VOICE_KEY_DEBOUNCE_MS = 1200L;
    private static long lastVoiceLaunchUptime;
    private static volatile WeakReference<Activity> overlayActivity = new WeakReference<>(null);
    private static volatile WeakReference<Activity> mainActivity = new WeakReference<>(null);

    private ClaudeTvHelper() {}

    public static void onActivityCreate(Activity activity) {
        if (activity == null) return;
        mainActivity = new WeakReference<>(activity);
        Window window = activity.getWindow();
        window.setWindowAnimations(0);
        window.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN);
        activity.overridePendingTransition(0, 0);
        VoicePanel.start(activity, false);
    }

    /** Hooks de BellModeService.onCreate/onDestroy: o painel de voz lê a sessão (campo w) desse serviço. */
    public static void onBellCreate(Service service) {
        VoicePanel.bellService = service;
    }

    public static void onBellDestroy(Service service) {
        if (VoicePanel.bellService == service) VoicePanel.bellService = null;
    }

    /**
     * Configura o overlay como cartão na base da tela. Retorna true só quando a configuração falha e
     * a voz foi redirecionada para a tela cheia (o hook encerra o onCreate do overlay nesse caso).
     */
    public static boolean onOverlayCreate(final Activity activity) {
        if (activity == null) return false;
        try {
            Window window = activity.getWindow();
            window.clearFlags(WindowManager.LayoutParams.FLAG_DIM_BEHIND);
            window.setWindowAnimations(0);
            window.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN
                    | WindowManager.LayoutParams.SOFT_INPUT_ADJUST_PAN);
            window.setFormat(PixelFormat.TRANSLUCENT);
            activity.overridePendingTransition(0, 0);

            boolean television = isTelevision(activity);
            WindowManager.LayoutParams lp = window.getAttributes();
            lp.dimAmount = 0f;
            final DisplayMetrics dm = activity.getResources().getDisplayMetrics();
            if (television) {
                // Cartão de 72% × 85%: o bottom sheet de celular esticado a 1920 px sobrepunha o conteúdo.
                lp.gravity = Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL;
                lp.width = (int) (dm.widthPixels * 0.72f);
                lp.height = (int) (dm.heightPixels * 0.85f);
                lp.y = (int) (18 * dm.density);
            }
            window.setAttributes(lp);

            View decor = window.getDecorView();
            final float radius = 28f * dm.density;
            decor.setOutlineProvider(new ViewOutlineProvider() {
                @Override
                public void getOutline(View view, Outline outline) {
                    outline.setRoundRect(0, 0, view.getWidth(), view.getHeight(), radius);
                }
            });
            decor.setClipToOutline(true);
            decor.setFocusable(true);
            decor.requestFocus();
            decor.setOnKeyListener(new View.OnKeyListener() {
                @Override
                public boolean onKey(View v, int keyCode, KeyEvent event) {
                    if (keyCode != KeyEvent.KEYCODE_BACK && keyCode != KeyEvent.KEYCODE_MENU) return false;
                    if (event.getAction() != KeyEvent.ACTION_DOWN || event.getRepeatCount() != 0) return true;
                    if (keyCode == KeyEvent.KEYCODE_BACK) {
                        // Mantém processo e Activity quentes para a próxima abertura (como o Katniss).
                        activity.moveTaskToBack(true);
                        activity.overridePendingTransition(0, 0);
                    } else {
                        expandOverlayToFullScreen(activity);
                    }
                    return true;
                }
            });

            if (television) {
                overlayActivity = new WeakReference<>(activity);
                VoicePanel.start(activity, true);
            }
            return false;
        } catch (RuntimeException e) {
            Log.e(TAG, "Falha ao configurar o overlay; abrindo a voz em tela cheia", e);
            startFullScreenVoice(activity);
            activity.finish();
            return true;
        }
    }

    public static String resolveOverlayVoice(String selectedVoice) {
        if (selectedVoice != null && !selectedVoice.trim().isEmpty() && !selectedVoice.equalsIgnoreCase("buttery")) {
            return selectedVoice.toLowerCase();
        }
        return "airy";
    }

    /** Botões sem uso na TV (anexos, ditado). */
    public static boolean shouldSuppressIconButton(String description) {
        if (description == null) return false;
        String d = description.toLowerCase();
        return d.contains("attachment") || d.contains("anexo")
                || (d.contains("chat") && (d.contains("add") || d.contains("adicionar")))
                || d.contains("dictation") || d.contains("ditado");
    }

    public static boolean handleKeyDown(Activity activity, int keyCode, KeyEvent event) {
        if (activity == null || event == null || event.getAction() != KeyEvent.ACTION_DOWN || event.getRepeatCount() != 0) {
            return false;
        }
        switch (keyCode) {
            case KEYCODE_TCL_HOVRING:
            case KeyEvent.KEYCODE_VOICE_ASSIST:
            case KeyEvent.KEYCODE_SEARCH:
            case KeyEvent.KEYCODE_MEDIA_RECORD:
            case KeyEvent.KEYCODE_ASSIST:
                return isBellModeRunning(activity) || startFullScreenVoice(activity);
            case KeyEvent.KEYCODE_MENU:
                newIncognitoChat(activity);
                return true;
            default:
                return false;
        }
    }

    /** Tecla de voz recebida pelo serviço de acessibilidade, roteada pelo contexto atual. */
    static void handleAccessibilityVoiceKey(Context context) {
        if (isBellModeRunning(context) || isAlive(overlayActivity.get())) return;
        Activity main = mainActivity.get();
        if (isAlive(main)) {
            startFullScreenVoice(main);
        } else {
            launchClaudeOverlay(context);
        }
    }

    private static boolean startFullScreenVoice(Context context) {
        if (!acquireVoiceLaunch()) return true;
        try {
            context.startActivity(buildFullScreenVoiceIntent(context));
            return true;
        } catch (RuntimeException e) {
            Log.e(TAG, "Falha ao abrir o modo de voz em tela cheia", e);
            return false;
        }
    }

    private static void launchClaudeOverlay(Context context) {
        if (!acquireVoiceLaunch()) return;
        Intent intent = new Intent("android.intent.action.VOICE_ASSIST");
        intent.setClassName(context.getPackageName(), OVERLAY_ACTIVITY);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP
                | Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_NO_ANIMATION);
        try {
            context.startActivity(intent);
        } catch (RuntimeException e) {
            Log.e(TAG, "Falha ao abrir o overlay de voz", e);
        }
    }

    private static void expandOverlayToFullScreen(Activity activity) {
        try {
            activity.startActivity(buildFullScreenVoiceIntent(activity));
            activity.finish();
        } catch (RuntimeException e) {
            Log.e(TAG, "Falha ao expandir o overlay para tela cheia", e);
        }
    }

    private static void newIncognitoChat(Activity activity) {
        Toast.makeText(activity, "Nova conversa incógnita", Toast.LENGTH_SHORT).show();
        Intent intent = new Intent(activity, activity.getClass());
        intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        activity.startActivity(intent);
    }

    private static synchronized boolean acquireVoiceLaunch() {
        long now = SystemClock.uptimeMillis();
        if (lastVoiceLaunchUptime != 0L && now - lastVoiceLaunchUptime < VOICE_KEY_DEBOUNCE_MS) return false;
        lastVoiceLaunchUptime = now;
        return true;
    }

    /** Mesmo intent do botão "Expandir para tela cheia" do overlay, sem chat id (conversa nova). */
    private static Intent buildFullScreenVoiceIntent(Context context) {
        Intent intent = new Intent();
        intent.setClassName(context.getPackageName(), MAIN_ACTIVITY);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        intent.putExtra(EXTRA_START_CHAT_MODE, "BELL_MODE");
        intent.putExtra(EXTRA_VOICE_ENTRY_SOURCE, "APP_INTENT");
        return intent;
    }

    /** O app não expõe o estado da voz; getRunningServices ainda lista os serviços do próprio app (API 26+). */
    private static boolean isBellModeRunning(Context context) {
        ActivityManager am = (ActivityManager) context.getSystemService(Context.ACTIVITY_SERVICE);
        List<ActivityManager.RunningServiceInfo> services = am.getRunningServices(Integer.MAX_VALUE);
        for (ActivityManager.RunningServiceInfo s : services) {
            if (BELL_MODE_SERVICE.equals(s.service.getClassName())) return true;
        }
        return false;
    }

    private static boolean isAlive(Activity activity) {
        return activity != null && !activity.isFinishing() && !activity.isDestroyed();
    }

    private static boolean isTelevision(Context context) {
        UiModeManager ui = (UiModeManager) context.getSystemService(Context.UI_MODE_SERVICE);
        return (ui != null && ui.getCurrentModeType() == Configuration.UI_MODE_TYPE_TELEVISION)
                || context.getPackageManager().hasSystemFeature(PackageManager.FEATURE_LEANBACK);
    }
}

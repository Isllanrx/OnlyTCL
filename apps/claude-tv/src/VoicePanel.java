package com.anthropic.claude.tv;

import android.app.Activity;
import android.app.Service;
import android.content.Context;
import android.content.ContextWrapper;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.util.DisplayMetrics;
import android.util.Log;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.view.inspector.WindowInspector;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.lang.ref.WeakReference;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

/**
 * Tela de voz mínima (ADR-012, Fase 2a). Enquanto há sessão de voz no BellModeService, esconde a árvore
 * Compose da MainActivity (some o measure/draw dela) e mostra estado, fala do usuário e resposta em TextViews.
 * As classes da sessão são ofuscadas e ficam no pacote padrão, então o acesso é por reflexão resolvida uma vez.
 *
 * Sessão (Claude 1.260930.20): BellModeService.w (w83); estado w83.g() (enum q53, nomes preservados);
 * mudo w83.t() instanceof a63; turnos w83.I (y93) → .g (lista de aoz/boz, campo a = texto); fala parcial
 * do usuário y93.i (estado Compose, getValue()).
 */
final class VoicePanel {
    private static final String TAG = "ClaudeTV";
    private static final long POLL_MS = 250L;

    static volatile Service bellService;

    private static final Handler handler = new Handler(Looper.getMainLooper());
    private static WeakReference<Activity> activityRef = new WeakReference<>(null);
    private static Session session;
    private static View panel;
    private static TextView stateView;
    private static TextView userLabel;
    private static TextView userView;
    private static TextView replyView;
    private static boolean polling;
    private static boolean compact;
    /** Ritmo médio de leitura da voz do Claude em pt-BR. */
    private static final long SPEECH_CHARS_PER_SEC = 14L;
    private static String pacedReplyId;
    private static long speakStartMs;
    private static boolean cardAttached;
    private static final java.util.ArrayList<View> hiddenRoots = new java.util.ArrayList<>();

    private VoicePanel() {}

    /** @param compactCard true no cartão do overlay (fonte e margens menores). */
    static void start(Activity activity, boolean compactCard) {
        Activity previous = activityRef.get();
        if (previous != activity) {
            if (previous != null && !previous.isDestroyed()) hide(previous);
            panel = null;
        }
        activityRef = new WeakReference<>(activity);
        compact = compactCard;
        if (!polling) {
            polling = true;
            handler.post(TICK);
        }
    }

    private static final Runnable TICK = new Runnable() {
        @Override
        public void run() {
            Activity activity = activityRef.get();
            if (activity == null || activity.isDestroyed()) {
                // O sistema remove as janelas filhas da Activity destruída; só o estado local é limpo.
                polling = false;
                panel = null;
                cardAttached = false;
                hiddenRoots.clear();
                return;
            }
            try {
                update(activity);
            } catch (ReflectiveOperationException | RuntimeException e) {
                Log.e(TAG, "Painel de voz desativado: sessão do Claude mudou de formato", e);
                hide(activity);
                polling = false;
                return;
            }
            handler.postDelayed(this, POLL_MS);
        }
    };

    private static void update(Activity activity) throws ReflectiveOperationException {
        Service service = bellService;
        if (service == null) {
            hide(activity);
            return;
        }
        if (session == null) session = new Session(service.getClass());
        Object w83 = session.voiceSession.get(service);
        if (w83 == null) {
            hide(activity);
            return;
        }
        show(activity);
        String state = ((Enum<?>) session.state.invoke(w83)).name();
        setIfChanged(stateView, stateLabel(state, session.mutedClass.isInstance(session.mute.invoke(w83))));
        Object turns = session.turns.get(w83);
        Object partial = session.partialGet.invoke(session.partial.get(turns));
        Object[] rows = ((java.util.List<?>) session.rows.get(turns)).toArray();
        String user = partial instanceof String && !((String) partial).isEmpty() ? (String) partial : null;
        Object replyRow = null;
        for (int i = rows.length - 1; i >= 0; i--) {
            Object row = rows[i];
            if (replyRow == null && session.assistantRow.isInstance(row)) {
                replyRow = row;
            } else if (user == null && session.userRow.isInstance(row)) {
                user = (String) session.userText.get(row);
            }
            if (replyRow != null && user != null) break;
        }
        String reply = replyRow == null ? "" : paced(replyRow, "TAP_TO_INTERRUPT".equals(state));
        setIfChanged(userView, user == null ? "" : user);
        int userVisibility = user == null ? View.GONE : View.VISIBLE;
        if (userView.getVisibility() != userVisibility) {
            userView.setVisibility(userVisibility);
            userLabel.setVisibility(userVisibility);
        }
        setIfChanged(replyView, tail(reply));
    }

    /**
     * Revela a resposta no ritmo da fala, sem o karaokê do app (desligado: reconstruía o texto a cada palavra
     * num laço de 16 ms). O tempo conta a partir do primeiro tique em "falando" de cada resposta; fora da fala
     * mostra o texto completo só quando a resposta terminou.
     */
    private static String paced(Object row, boolean speaking) throws IllegalAccessException {
        String text = (String) session.assistantText.get(row);
        String id = (String) session.assistantId.get(row);
        if (id == null ? pacedReplyId != null : !id.equals(pacedReplyId)) {
            pacedReplyId = id;
            speakStartMs = 0L;
        }
        if (speaking && speakStartMs == 0L) speakStartMs = SystemClock.uptimeMillis();
        if (speakStartMs == 0L) return session.assistantComplete.getBoolean(row) ? text : "";
        if (!speaking) return text;
        int reveal = (int) ((SystemClock.uptimeMillis() - speakStartMs) * SPEECH_CHARS_PER_SEC / 1000L);
        if (reveal >= text.length()) return text;
        int cut = text.lastIndexOf(' ', reveal);
        return cut <= 0 ? "" : text.substring(0, cut);
    }

    private static String stateLabel(String state, boolean muted) {
        if (muted) return "Microfone desligado";
        switch (state) {
            case "CONNECTING": case "RECONNECTING": return "Conectando…";
            case "LISTENING": case "HOLD_TO_TALK": case "RELEASE_TO_SEND": case "TAP_TO_SEND": return "Ouvindo";
            case "JUST_A_SEC": case "THINKING": return "Pensando…";
            case "SEARCHING": return "Pesquisando…";
            case "WORKING": case "WAITING_FOR_TOOL_APPROVAL": return "Trabalhando…";
            case "TAP_TO_INTERRUPT": return "Falando";
            case "VOLUME_MUTED": return "Volume no mínimo";
            case "MUTED": return "Microfone desligado";
            case "RATE_LIMIT_EXCEEDS": return "Limite de uso atingido";
            case "ERROR_FATAL": case "ERROR_TEMPORARY": case "DISCONNECTED": return "Sem conexão";
            default: return "";
        }
    }

    /** Só o fim da resposta: o texto inteiro custaria layout proporcional ao tamanho a cada mudança. */
    private static String tail(String text) {
        // Cabe na coluna sem rolagem: ~10 linhas na tela cheia, ~3 no cartão do overlay (medido 17:06).
        if (compact) text = text.replace("\n\n", "\n");
        int max = compact ? 170 : 520;
        if (text.length() <= max) return text;
        int cut = text.indexOf(' ', text.length() - max);
        return "…" + text.substring(cut < 0 ? text.length() - max : cut);
    }

    private static void setIfChanged(TextView view, String text) {
        if (!text.contentEquals(view.getText())) view.setText(text);
    }

    private static void show(Activity activity) {
        if (compact) {
            showCard(activity);
            return;
        }
        ViewGroup content = activity.findViewById(android.R.id.content);
        if (panel == null || panel.getParent() != content) {
            panel = build(activity);
            content.addView(panel, new FrameLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        }
        if (panel.getVisibility() == View.VISIBLE) return;
        for (int i = 0; i < content.getChildCount(); i++) {
            View child = content.getChildAt(i);
            if (child != panel) child.setVisibility(View.GONE);
        }
        panel.setVisibility(View.VISIBLE);
    }

    private static void hide(Activity activity) {
        if (compact) {
            hideCard(activity);
            return;
        }
        if (panel == null || panel.getVisibility() != View.VISIBLE) return;
        ViewGroup content = activity.findViewById(android.R.id.content);
        panel.setVisibility(View.GONE);
        for (int i = 0; i < content.getChildCount(); i++) {
            View child = content.getChildAt(i);
            if (child != panel) child.setVisibility(View.VISIBLE);
        }
    }

    /**
     * Overlay: a UI de voz é um ModalBottomSheet do Compose em janela própria, acima da Activity. O cartão
     * vira uma janela filha da Activity e as janelas do sheet ficam GONE (sem measure/draw) durante a voz.
     */
    private static void showCard(Activity activity) {
        if (panel == null) panel = build(activity);
        if (!cardAttached) {
            panel.setVisibility(View.VISIBLE);
            activity.getWindowManager().addView(panel, cardParams(activity));
            cardAttached = true;
        }
        View decor = activity.getWindow().getDecorView();
        for (View root : WindowInspector.getGlobalWindowViews()) {
            if (root != decor && root != panel && root.getVisibility() == View.VISIBLE
                    && activityOf(root.getContext()) == activity) {
                root.setVisibility(View.GONE);
                hiddenRoots.add(root);
            }
        }
    }

    private static void hideCard(Activity activity) {
        if (cardAttached) {
            activity.getWindowManager().removeViewImmediate(panel);
            cardAttached = false;
        }
        for (View root : hiddenRoots) root.setVisibility(View.VISIBLE);
        hiddenRoots.clear();
    }

    private static WindowManager.LayoutParams cardParams(Activity activity) {
        DisplayMetrics dm = activity.getResources().getDisplayMetrics();
        WindowManager.LayoutParams lp = new WindowManager.LayoutParams(
                (int) (dm.widthPixels * 0.72f), (int) (dm.heightPixels * 0.6f),
                WindowManager.LayoutParams.TYPE_APPLICATION_ATTACHED_DIALOG,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE,
                PixelFormat.TRANSLUCENT); // cantos arredondados precisam de alfa fora do cartão
        lp.token = activity.getWindow().getDecorView().getWindowToken();
        lp.gravity = Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL;
        lp.y = (int) (18 * dm.density);
        lp.windowAnimations = 0;
        return lp;
    }

    private static Activity activityOf(Context context) {
        while (context instanceof ContextWrapper) {
            if (context instanceof Activity) return (Activity) context;
            context = ((ContextWrapper) context).getBaseContext();
        }
        return null;
    }

    private static View build(Activity activity) {
        float density = activity.getResources().getDisplayMetrics().density;
        int screenWidth = activity.getResources().getDisplayMetrics().widthPixels;
        int pad = (int) ((compact ? 32 : 64) * density);
        float scale = compact ? 0.8f : 1f;

        FrameLayout root = new FrameLayout(activity);
        if (compact) {
            GradientDrawable card = new GradientDrawable();
            card.setColor(Color.BLACK);
            card.setCornerRadius(28 * density);
            root.setBackground(card);
        } else {
            root.setBackgroundColor(Color.BLACK);
        }
        LinearLayout column = new LinearLayout(activity);
        column.setOrientation(LinearLayout.VERTICAL);
        column.setPadding(pad, pad, pad, pad);
        // Coluna de leitura de ~70% da tela cheia: linhas de 1920 px cansam a leitura a distância.
        int columnWidth = compact ? ViewGroup.LayoutParams.MATCH_PARENT : (int) (screenWidth * 0.7f);
        root.addView(column, new FrameLayout.LayoutParams(columnWidth, ViewGroup.LayoutParams.MATCH_PARENT,
                Gravity.CENTER_HORIZONTAL));

        stateView = text(activity, 20 * scale, 0xFFD97757, Typeface.BOLD, 28);
        userLabel = text(activity, 14 * scale, 0xFF8A8A8A, Typeface.BOLD, 4);
        userLabel.setText("VOCÊ");
        userView = text(activity, 22 * scale, 0xFFBDBDBD, Typeface.NORMAL, 24);
        TextView replyLabel = text(activity, 14 * scale, 0xFFD97757, Typeface.BOLD, 4);
        replyLabel.setText("CLAUDE");
        replyView = text(activity, 26 * scale, Color.WHITE, Typeface.NORMAL, 0);
        replyView.setLineSpacing(0f, 1.2f);
        userLabel.setVisibility(View.GONE);
        userView.setVisibility(View.GONE);

        column.addView(stateView);
        column.addView(userLabel);
        column.addView(userView);
        column.addView(replyLabel);
        column.addView(replyView);
        // Nasce oculto: show() só esconde a árvore Compose na transição para visível.
        root.setVisibility(View.GONE);
        return root;
    }

    private static TextView text(Activity activity, float sp, int color, int style, int bottomDp) {
        TextView view = new TextView(activity);
        view.setTextSize(TypedValue.COMPLEX_UNIT_SP, sp);
        view.setTextColor(color);
        view.setTypeface(Typeface.DEFAULT, style);
        view.setPadding(0, 0, 0, (int) (bottomDp * activity.getResources().getDisplayMetrics().density));
        return view;
    }

    /** Membros resolvidos uma vez a partir do classloader do app. */
    private static final class Session {
        final Field voiceSession;
        final Method state;
        final Method mute;
        final Class<?> mutedClass;
        final Field turns;
        final Field rows;
        final Field partial;
        final Method partialGet;
        final Class<?> assistantRow;
        final Field assistantText;
        final Field assistantComplete;
        final Field assistantId;
        final Class<?> userRow;
        final Field userText;

        Session(Class<?> bellClass) throws ReflectiveOperationException {
            ClassLoader loader = bellClass.getClassLoader();
            voiceSession = bellClass.getField("w");
            Class<?> w83 = voiceSession.getType();
            state = w83.getMethod("g");
            mute = w83.getMethod("t");
            mutedClass = Class.forName("a63", false, loader);
            turns = w83.getField("I");
            rows = turns.getType().getField("g");
            partial = turns.getType().getField("i");
            partialGet = partial.getType().getMethod("getValue");
            assistantRow = Class.forName("aoz", false, loader);
            assistantText = assistantRow.getField("a");
            assistantComplete = assistantRow.getField("c");
            assistantId = assistantRow.getField("f");
            userRow = Class.forName("boz", false, loader);
            userText = userRow.getField("a");
            // Classes ofuscadas podem ser package-private: membros públicos delas exigem setAccessible.
            java.lang.reflect.AccessibleObject.setAccessible(new java.lang.reflect.AccessibleObject[] {
                    voiceSession, state, mute, turns, rows, partial, partialGet, assistantText, assistantComplete,
                    assistantId, userText}, true);
        }
    }
}

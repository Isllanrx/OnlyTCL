package com.ansub.tvhome;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.media.tv.TvContract;
import android.media.tv.TvInputInfo;
import android.media.tv.TvInputManager;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;

final class Inputs {

    static final class Entry {
        final String id, label;
        final boolean console;

        Entry(String id, String label, boolean console) {
            this.id = id;
            this.label = label;
            this.console = console;
        }
    }

    private static final String[][] LIVE_TV = {{"com.android.tv", "com.android.tv.MainActivity"},
            {"com.droidlogic.android.tv", "com.android.tv.TvActivity"},
            {AntennaActivity.LIVE_TV_PKG, AntennaActivity.LIVE_TV_ACTIVITY}};
    private static final String INPUT_PLAYER = "com.google.android.tv.inputplayer";

    private Inputs() {}

    static boolean isInput(String key) {
        return key.indexOf('/') > 0;
    }

    static List<Entry> hdmi(Context c, int max) {
        List<TvInputInfo> found = new ArrayList<>();
        TvInputManager tim = (TvInputManager) c.getSystemService(Context.TV_INPUT_SERVICE);
        if (tim != null) for (TvInputInfo in : tim.getTvInputList())
            if (in.getType() == TvInputInfo.TYPE_HDMI && in.getParentId() == null && !in.isHidden(c)) found.add(in);
        Collections.sort(found, (a, b) -> a.getId().compareTo(b.getId()));
        List<Entry> out = new ArrayList<>();
        for (TvInputInfo in : found) {
            if (out.size() >= max) break;
            CharSequence stock = in.loadLabel(c);
            String base = stock != null && stock.length() > 0 ? stock.toString() : "HDMI";
            CharSequence custom = in.loadCustomLabel(c);
            String name = custom != null && custom.length() > 0 ? withoutDeviceType(custom.toString()) : base;
            String low = name.toLowerCase(Locale.ROOT);
            boolean console = low.contains("console") || low.contains("jogo") || low.contains("game");
            String number = base.replaceAll("\\D+", "");
            out.add(new Entry(in.getId(), console ? "Console " + number : name, console));
        }
        return out;
    }

    private static String withoutDeviceType(String label) {
        if (!"Philips".equalsIgnoreCase(android.os.Build.MANUFACTURER)) return label;
        int amp = label.lastIndexOf('&');
        return amp > 0 && label.substring(amp + 1).matches("[A-Z][A-Z0-9_]{2,}") ? label.substring(0, amp).trim() : label;
    }

    static void open(Activity a, String id) {
        Intent view = new Intent(Intent.ACTION_VIEW, TvContract.buildChannelUriForPassthroughInput(id));
        PackageManager pm = a.getPackageManager();
        List<Intent> tries = new ArrayList<>();
        ResolveInfo def = pm.resolveActivity(view, PackageManager.MATCH_DEFAULT_ONLY);
        if (def != null && def.activityInfo != null && INPUT_PLAYER.equals(def.activityInfo.packageName))
            tries.add(new Intent(view).setClassName(INPUT_PLAYER, def.activityInfo.name));
        for (String[] live : LIVE_TV) {
            Intent t = new Intent(view).setClassName(live[0], live[1]);
            if (t.resolveActivity(pm) != null) tries.add(t);
        }
        tries.add(view);
        for (Intent t : tries) {
            t.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            try {
                a.startActivity(t);
                return;
            } catch (Exception ignored) {}
        }
    }
}

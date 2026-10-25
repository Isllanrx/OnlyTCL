package com.ansub.tvhome;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.media.tv.TvContract;
import android.media.tv.TvInputInfo;
import android.media.tv.TvInputManager;
import android.os.Bundle;

public class AntennaActivity extends Activity {

    static final String LIVE_TV_PKG = "com.tcl.tv";
    static final String LIVE_TV_ACTIVITY = "com.tcl.tv.TVActivity";

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        open(this);
        finish();
    }

    static void open(Activity from) {
        String input = antennaInput(from);
        if (input != null && start(from, new Intent(Intent.ACTION_VIEW, TvContract.buildChannelsUriForInput(input))
                .setClassName(LIVE_TV_PKG, LIVE_TV_ACTIVITY))) return;
        if (input != null && start(from, new Intent(Intent.ACTION_VIEW, TvContract.buildChannelsUriForInput(input)))) return;
        start(from, from.getPackageManager().getLeanbackLaunchIntentForPackage(LIVE_TV_PKG));
    }

    static String antennaInput(Context c) {
        TvInputManager tim = (TvInputManager) c.getSystemService(Context.TV_INPUT_SERVICE);
        if (tim == null) return null;
        String best = null;
        for (TvInputInfo in : tim.getTvInputList()) {
            if (in.getType() != TvInputInfo.TYPE_TUNER || in.getParentId() != null || in.isPassthroughInput()) continue;
            ApplicationInfo app = in.getServiceInfo().applicationInfo;
            if ((app.flags & ApplicationInfo.FLAG_SYSTEM) == 0) continue;
            if (best == null || in.getId().compareTo(best) < 0) best = in.getId();
        }
        return best;
    }

    private static boolean start(Activity from, Intent i) {
        if (i == null) return false;
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        try {
            from.startActivity(i);
            return true;
        } catch (Exception e) {
            return false;
        }
    }
}

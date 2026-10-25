package gamepass.fire.tv;

import android.content.ContentResolver;
import android.content.Context;
import android.content.SharedPreferences;
import android.provider.Settings;
import android.text.TextUtils;
import android.util.Log;

public final class AccessibilitySuspendManager {
    private static final String TAG = "XboxA11y";
    private static final String KEY_SERVICES = "services";
    private static final String KEY_ENABLED = "enabled";

    private AccessibilitySuspendManager() {}

    public static void suspend(Context context) {
        ContentResolver cr = context.getContentResolver();
        String services = Settings.Secure.getString(cr, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES);
        if (TextUtils.isEmpty(services)) return;
        boolean saved = prefs(context).edit()
                .putString(KEY_SERVICES, services)
                .putInt(KEY_ENABLED, Settings.Secure.getInt(cr, Settings.Secure.ACCESSIBILITY_ENABLED, 0))
                .commit();
        if (!saved) {
            Log.w(TAG, "state not persisted; accessibility left on");
            return;
        }
        try {
            Settings.Secure.putString(cr, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES, "");
            Settings.Secure.putInt(cr, Settings.Secure.ACCESSIBILITY_ENABLED, 0);
        } catch (SecurityException e) {
            Log.w(TAG, "WRITE_SECURE_SETTINGS not granted", e);
        }
    }

    public static void restore(Context context) {
        SharedPreferences prefs = prefs(context);
        String services = prefs.getString(KEY_SERVICES, null);
        if (services == null) return;
        try {
            ContentResolver cr = context.getContentResolver();
            Settings.Secure.putString(cr, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES, services);
            Settings.Secure.putInt(cr, Settings.Secure.ACCESSIBILITY_ENABLED, prefs.getInt(KEY_ENABLED, 1));
            prefs.edit().clear().commit();
        } catch (SecurityException e) {
            Log.w(TAG, "cannot restore " + services, e);
        }
    }

    private static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences("a11y_suspend", Context.MODE_PRIVATE);
    }
}

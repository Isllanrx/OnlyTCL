package com.isllantoso.zeusremote

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.os.SystemClock
import android.util.Log

class TcastReviver(private val context: Context) {
    private var lastLaunch = 0L

    @Synchronized
    fun launch() {
        val now = SystemClock.uptimeMillis()
        if (lastLaunch != 0L && now - lastLaunch < DEBOUNCE_MS) return
        lastLaunch = now
        val intent = Intent().setClassName(PACKAGE, SPLASH_ACTIVITY).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        try {
            context.startActivity(intent)
            Log.i(TAG, "T-Cast aberto para religar o serviço")
        } catch (e: ActivityNotFoundException) {
            Log.w(TAG, "T-Cast não instalado", e)
        } catch (e: SecurityException) {
            Log.w(TAG, "abertura do T-Cast negada", e)
        }
    }

    private companion object {
        const val TAG = "ZeusRemote/Revive"
        const val PACKAGE = "com.tcl.MultiScreenInteraction_TV"
        const val SPLASH_ACTIVITY = "com.tcl.multiscreeninteractiontv.UI.activity.SplashActivity"
        const val DEBOUNCE_MS = 30_000L
    }
}

package com.isllantoso.zeusremote

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.os.SystemClock
import android.util.Log

class ClaudeVoice(private val context: Context) {
    private var lastLaunch = 0L

    @Synchronized
    fun launch() {
        val now = SystemClock.uptimeMillis()
        if (lastLaunch != 0L && now - lastLaunch < DEBOUNCE_MS) return
        lastLaunch = now
        val intent = Intent()
            .setClassName(PACKAGE, MAIN_ACTIVITY)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
            .putExtra(EXTRA_START_CHAT_MODE, "BELL_MODE")
            .putExtra(EXTRA_VOICE_ENTRY_SOURCE, "APP_INTENT")
        try {
            context.startActivity(intent)
        } catch (e: ActivityNotFoundException) {
            Log.w(TAG, "Claude não instalado", e)
        } catch (e: SecurityException) {
            Log.w(TAG, "abertura do Claude negada", e)
        }
    }

    private companion object {
        const val TAG = "ZeusRemote/Voice"
        const val PACKAGE = "com.anthropic.claude"
        const val MAIN_ACTIVITY = "com.anthropic.claude.mainactivity.MainActivity"
        const val EXTRA_START_CHAT_MODE = "com.anthropic.claude.intent.extra.START_CHAT_MODE"
        const val EXTRA_VOICE_ENTRY_SOURCE = "com.anthropic.claude.intent.extra.START_CHAT_VOICE_ENTRY_SOURCE"
        const val DEBOUNCE_MS = 1_200L
    }
}

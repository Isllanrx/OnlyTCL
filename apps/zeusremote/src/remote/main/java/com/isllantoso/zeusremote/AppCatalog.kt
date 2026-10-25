package com.isllantoso.zeusremote

import android.content.Intent
import android.content.pm.ActivityInfo
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.drawable.Drawable
import android.util.Log
import java.io.ByteArrayOutputStream
import java.util.concurrent.ConcurrentHashMap
import org.json.JSONArray
import org.json.JSONObject

class AppCatalog(private val pm: PackageManager, private val self: String) {
    private val images = ConcurrentHashMap<String, ByteArray>()
    @Volatile private var known: Map<String, ActivityInfo> = emptyMap()

    fun serve(path: String): ControlServer.Asset? = when {
        path == "/apps.json" -> ControlServer.Asset("application/json; charset=utf-8", list())
        path.startsWith(ICON_PREFIX) -> image(path.removePrefix(ICON_PREFIX))?.let { ControlServer.Asset("image/png", it) }
        else -> null
    }

    private fun launchers(): List<ActivityInfo> =
        pm.queryIntentActivities(Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LEANBACK_LAUNCHER), 0)
            .map { it.activityInfo }
            .filter { it.packageName != self }
            .distinctBy { it.packageName }

    private fun list(): ByteArray {
        val apps = JSONArray()
        val activities = launchers()
        known = activities.associateBy { it.packageName }
        activities
            .map { Triple(it.packageName, it.applicationInfo.loadLabel(pm).toString(), it.bannerResource != 0) }
            .sortedBy { it.second.lowercase() }
            .forEach { (pkg, name, wide) -> apps.put(JSONObject().put("pkg", pkg).put("name", name).put("wide", wide)) }
        return apps.toString().toByteArray(Charsets.UTF_8)
    }

    private fun image(pkg: String): ByteArray? {
        if (!RemoteCommand.isPackage(pkg)) return null
        images[pkg]?.let { return it }
        val activity = known[pkg] ?: return null
        return try {
            val banner = activity.loadBanner(pm)
            val png = if (banner != null) render(banner, BANNER_WIDTH, BANNER_HEIGHT) else render(activity.loadIcon(pm), ICON_SIZE, ICON_SIZE)
            images[pkg] = png
            png
        } catch (e: RuntimeException) {
            Log.w(TAG, "ícone de $pkg indisponível", e)
            null
        }
    }

    private fun render(drawable: Drawable, width: Int, height: Int): ByteArray {
        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        drawable.setBounds(0, 0, width, height)
        drawable.draw(Canvas(bitmap))
        val out = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.PNG, 100, out)
        bitmap.recycle()
        return out.toByteArray()
    }

    private companion object {
        const val TAG = "ZeusRemote/Apps"
        const val ICON_PREFIX = "/icon/"
        const val BANNER_WIDTH = 320
        const val BANNER_HEIGHT = 180
        const val ICON_SIZE = 160
    }
}

package com.isllantoso.zeusremote

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.net.ConnectivityManager
import android.net.LinkProperties
import android.net.Network
import android.os.IBinder
import android.util.Log
import java.io.IOException
import java.net.InetAddress
import java.util.UUID
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

class BridgeService : Service() {
    private val watchdog = Executors.newSingleThreadScheduledExecutor { Thread(it, "bridge-watchdog").apply { isDaemon = true } }
    private lateinit var link: TcastLink
    private lateinit var pages: Map<String, ControlServer.Asset>
    private lateinit var catalog: AppCatalog
    private lateinit var voice: ClaudeVoice
    private lateinit var reviver: TcastReviver
    private var server: ControlServer? = null
    private var postedUrl: String? = null
    private val networkCallback = object : ConnectivityManager.NetworkCallback() {
        override fun onAvailable(network: Network) = networkChanged()
        override fun onLost(network: Network) = networkChanged()
        override fun onLinkPropertiesChanged(network: Network, linkProperties: LinkProperties) = networkChanged()
    }

    override fun onCreate() {
        super.onCreate()
        pages = pageAssets()
        catalog = AppCatalog(packageManager, packageName)
        voice = ClaudeVoice(this)
        reviver = TcastReviver(this)
        link = TcastLink(clientId(), LanAddress::current)
        publishNotification()
        try {
            getSystemService(ConnectivityManager::class.java).registerDefaultNetworkCallback(networkCallback)
        } catch (e: RuntimeException) {
            Log.w(TAG, "monitor de rede indisponível; a supervisão periódica cobre", e)
        }
        watchdog.scheduleWithFixedDelay(::supervise, 0, CHECK_SECONDS, TimeUnit.SECONDS)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY

    override fun onDestroy() {
        runCatching { getSystemService(ConnectivityManager::class.java).unregisterNetworkCallback(networkCallback) }
        watchdog.shutdownNow()
        server?.stop()
        link.shutdown()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun networkChanged() {
        link.networkChanged()
        if (!watchdog.isShutdown) watchdog.execute(::supervise)
    }

    private fun supervise() {
        try {
            ensureServer()
            ensureNotification()
        } catch (e: Exception) {
            Log.e(TAG, "falha na supervisão da ponte", e)
        }
    }

    private fun ensureServer() {
        if (server?.isServing() == true) return
        server?.let {
            Log.w(TAG, "servidor de controle parou; reiniciando")
            it.stop()
        }
        val control = ControlServer(pages, catalog::serve, voice::launch, reviver::launch, link)
        server = try {
            control.start()
            control
        } catch (e: IOException) {
            Log.e(TAG, "porta ${ControlServer.PORT} indisponível; nova tentativa em ${CHECK_SECONDS}s", e)
            control.stop()
            null
        }
    }

    private fun ensureNotification() {
        val posted = getSystemService(NotificationManager::class.java).activeNotifications.any { it.id == NOTIFICATION_ID }
        if (!posted || postedUrl != LanAddress.current()?.let { urlOf(it) }) publishNotification()
    }

    private fun publishNotification() {
        val url = LanAddress.current()?.let { urlOf(it) }
        val pinned = notification(url)
        postedUrl = url
        try {
            startForeground(NOTIFICATION_ID, pinned)
        } catch (e: RuntimeException) {
            Log.w(TAG, "startForeground recusado; mantendo só a notificação fixa", e)
        }
        getSystemService(NotificationManager::class.java).notify(NOTIFICATION_ID, pinned)
    }

    private fun pageAssets(): Map<String, ControlServer.Asset> = PAGE_TYPES.mapKeys { "/${it.key}" }.mapValues { (path, type) ->
        ControlServer.Asset(type, assets.open(path.removePrefix("/")).use { it.readBytes() })
    }

    private fun clientId(): String {
        val prefs = getSharedPreferences("zeusremote", MODE_PRIVATE)
        return prefs.getString(KEY_CLIENT_ID, null) ?: "zeusremote-${UUID.randomUUID().toString().take(12)}".also {
            prefs.edit().putString(KEY_CLIENT_ID, it).apply()
        }
    }

    private fun notification(url: String?): Notification {
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(NotificationChannel(CHANNEL_ID, getString(R.string.app_name), NotificationManager.IMPORTANCE_MIN))
        return Notification.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_remote)
            .setContentTitle(getString(R.string.app_name))
            .setContentText(url ?: getString(R.string.no_network))
            .setOngoing(true)
            .build()
            .apply { flags = flags or Notification.FLAG_NO_CLEAR }
    }

    companion object {
        private const val TAG = "ZeusRemote/Service"
        private const val CHANNEL_ID = "bridge"
        private const val NOTIFICATION_ID = 1
        private const val KEY_CLIENT_ID = "client_id"
        private const val CHECK_SECONDS = 5L
        private val PAGE_TYPES = mapOf(
            "index.html" to "text/html; charset=utf-8",
            "app.css" to "text/css; charset=utf-8",
            "app.js" to "text/javascript; charset=utf-8",
        )

        fun start(context: Context) {
            context.startForegroundService(Intent(context, BridgeService::class.java))
        }

        fun controlUrl(): String? = LanAddress.current()?.let { urlOf(it) }

    }
}

private fun urlOf(address: InetAddress) = "http://${address.hostAddress}:${ControlServer.PORT}"

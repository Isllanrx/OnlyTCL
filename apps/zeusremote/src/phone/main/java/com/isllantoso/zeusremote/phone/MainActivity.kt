package com.isllantoso.zeusremote.phone

import android.app.Activity
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.view.Gravity
import android.view.View
import android.view.WindowInsets
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import android.widget.TextView
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private lateinit var web: WebView
    private lateinit var status: TextView
    private lateinit var worker: ExecutorService
    private var host: String = TvFinder.DEFAULT_HOST
    private var searching = false
    private val watch = HostWatch()
    private val handler = Handler(Looper.getMainLooper())
    private val tick = object : Runnable {
        override fun run() {
            probe()
            handler.postDelayed(this, PROBE_MS)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        worker = Executors.newSingleThreadExecutor()
        host = prefs().getString(KEY_HOST, null) ?: TvFinder.DEFAULT_HOST
        web = WebView(this).apply {
            setBackgroundColor(BACKGROUND)
            overScrollMode = View.OVER_SCROLL_NEVER
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.setSupportZoom(false)
            settings.builtInZoomControls = false
            settings.displayZoomControls = false
            webViewClient = Client()
        }
        status = TextView(this).apply {
            setBackgroundColor(BACKGROUND)
            setTextColor(Color.rgb(0xEE, 0xF0, 0xF6))
            textSize = 17f
            gravity = Gravity.CENTER
            setPadding(PADDING, PADDING, PADDING, PADDING)
            visibility = View.GONE
            setOnClickListener { search() }
        }
        val root = FrameLayout(this).apply {
            setBackgroundColor(BACKGROUND)
            addView(web)
            addView(status)
        }
        if (Build.VERSION.SDK_INT >= EDGE_TO_EDGE_SDK) padForSystemBars(root)
        setContentView(root)
        web.loadUrl(TvFinder.url(host))
    }

    override fun onResume() {
        super.onResume()
        handler.removeCallbacks(tick)
        handler.postDelayed(tick, PROBE_MS)
        if (searching) return
        val current = host
        worker.execute { if (!TvFinder.isRemote(current)) runOnUiThread(::search) }
    }

    override fun onPause() {
        handler.removeCallbacks(tick)
        super.onPause()
    }

    override fun onDestroy() {
        handler.removeCallbacks(tick)
        worker.shutdownNow()
        web.destroy()
        super.onDestroy()
    }

    private fun probe() {
        if (searching || isFinishing || isDestroyed) return
        val current = host
        worker.execute {
            val reachable = TvFinder.isRemote(current)
            if (watch.record(reachable, SystemClock.elapsedRealtime())) runOnUiThread(::search)
        }
    }

    private fun search() {
        if (searching || isFinishing) return
        searching = true
        showStatus(getString(R.string.searching))
        val known = listOf(host, TvFinder.DEFAULT_HOST)
        worker.execute {
            val found = TvFinder.find(known)
            runOnUiThread {
                searching = false
                if (isDestroyed) return@runOnUiThread
                if (found == null) {
                    showStatus(getString(R.string.not_found))
                } else {
                    host = found
                    watch.reset()
                    prefs().edit().putString(KEY_HOST, found).apply()
                    status.visibility = View.GONE
                    web.loadUrl(TvFinder.url(found))
                }
            }
        }
    }

    private fun showStatus(text: String) {
        status.text = text
        status.visibility = View.VISIBLE
    }

    private fun prefs() = getSharedPreferences("zeusremote", MODE_PRIVATE)

    private fun padForSystemBars(root: View) {
        root.setOnApplyWindowInsetsListener { view, insets ->
            val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.ime())
            view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            insets
        }
    }

    private inner class Client : WebViewClient() {
        override fun onReceivedError(view: WebView, request: WebResourceRequest, error: WebResourceError) {
            if (request.isForMainFrame) search()
        }
    }

    private companion object {
        const val KEY_HOST = "host"
        const val EDGE_TO_EDGE_SDK = 35
        const val PADDING = 64
        const val PROBE_MS = 10_000L
        val BACKGROUND = Color.rgb(0x07, 0x08, 0x0C)
    }
}

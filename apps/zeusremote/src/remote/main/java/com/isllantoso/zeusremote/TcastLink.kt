package com.isllantoso.zeusremote

import android.util.Log
import java.io.BufferedOutputStream
import java.io.DataInputStream
import java.io.IOException
import java.io.OutputStream
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.Socket
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledFuture
import java.util.concurrent.TimeUnit

enum class TcastStatus(val wire: String) {
    UP("status:tcast:up"),
    DOWN("status:tcast:down"),
}

class TcastLink(
    private val clientId: String,
    private val address: () -> InetAddress?,
    private val port: Int = TcastFrame.PORT,
    private val timings: Timings = Timings(),
) {
    data class Timings(
        val connectTimeoutMs: Int = 2_000,
        val heartbeatMs: Long = 10_000,
        val idleCloseMs: Long = 60_000,
        val retryInitialMs: Long = 500,
        val retryMaxMs: Long = 10_000,
    )

    private val worker = Executors.newSingleThreadScheduledExecutor { Thread(it, "tcast-link").apply { isDaemon = true } }
    private val backoff = Backoff(timings.retryInitialMs, timings.retryMaxMs)
    private var socket: Socket? = null
    private var output: OutputStream? = null
    private var connectedTo: InetAddress? = null
    private var heartbeat: ScheduledFuture<*>? = null
    private var idleClose: ScheduledFuture<*>? = null
    private var retry: ScheduledFuture<*>? = null
    private var clients = 0

    @Volatile var status: TcastStatus? = null
        private set
    @Volatile var onInbound: (String) -> Unit = {}
    @Volatile var onStatus: (TcastStatus?) -> Unit = {}

    fun clientAttached() = post {
        clients++
        idleClose?.cancel(false)
        idleClose = null
        if (output == null) reconnect()
    }

    fun clientDetached() = post {
        clients = (clients - 1).coerceAtLeast(0)
        if (clients == 0 && idleClose == null) {
            idleClose = worker.schedule(guarded(::closeIdle), timings.idleCloseMs, TimeUnit.MILLISECONDS)
        }
    }

    fun networkChanged() = post {
        if (clients > 0) {
            disconnect()
            reconnect()
        }
    }

    fun send(body: String) = post { write(TcastFrame.encode(body)) }

    fun shutdown() {
        post { disconnect() }
        worker.shutdown()
    }

    private fun post(task: () -> Unit) {
        if (!worker.isShutdown) worker.execute(guarded(task))
    }

    private fun guarded(task: () -> Unit) = Runnable {
        try {
            task()
        } catch (e: Exception) {
            Log.e(TAG, "falha inesperada no enlace com o T-Cast", e)
        }
    }

    private fun closeIdle() {
        idleClose = null
        if (clients > 0) return
        retry?.cancel(false)
        retry = null
        disconnect()
        setStatus(null)
    }

    private fun write(frame: ByteArray) {
        if (output == null && !connect()) {
            scheduleRetry()
            return
        }
        try {
            transmit(frame)
        } catch (e: IOException) {
            Log.w(TAG, "envio ao T-Cast falhou; reconectando", e)
            disconnect()
            if (connect()) {
                try {
                    transmit(frame)
                } catch (second: IOException) {
                    Log.w(TAG, "reenvio ao T-Cast falhou", second)
                    disconnect()
                    scheduleRetry()
                }
            } else {
                scheduleRetry()
            }
        }
    }

    private fun transmit(frame: ByteArray) {
        val out = output ?: throw IOException("sem conexão com o T-Cast")
        out.write(frame)
        out.flush()
    }

    private fun reconnect() {
        retry?.cancel(false)
        retry = null
        if (!connect()) scheduleRetry()
    }

    private fun scheduleRetry() {
        if (clients == 0 || retry != null || worker.isShutdown) return
        retry = worker.schedule(guarded {
            retry = null
            if (clients > 0 && output == null && !connect()) scheduleRetry()
        }, backoff.next(), TimeUnit.MILLISECONDS)
    }

    private fun connect(): Boolean {
        val host = address()
        if (host == null) {
            setStatus(TcastStatus.DOWN)
            return false
        }
        val s = Socket()
        try {
            s.tcpNoDelay = true
            s.keepAlive = true
            s.connect(InetSocketAddress(host, port), timings.connectTimeoutMs)
            val out = BufferedOutputStream(s.getOutputStream())
            out.write(TcastFrame.handshake(clientId))
            out.flush()
            socket = s
            output = out
            connectedTo = host
            startReader(s)
            heartbeat = worker.scheduleWithFixedDelay(guarded(::beat), timings.heartbeatMs, timings.heartbeatMs, TimeUnit.MILLISECONDS)
            backoff.reset()
            setStatus(TcastStatus.UP)
            return true
        } catch (e: IOException) {
            runCatching { s.close() }
            if (status != TcastStatus.DOWN) Log.w(TAG, "T-Cast indisponível em $host:$port: ${e.message}")
            setStatus(TcastStatus.DOWN)
            return false
        }
    }

    private fun beat() {
        if (output == null) return
        if (address() != connectedTo) {
            Log.i(TAG, "endereço da TV mudou; reconectando ao T-Cast")
            dropAndReconnect()
            return
        }
        try {
            transmit(TcastFrame.HEARTBEAT)
        } catch (e: IOException) {
            Log.w(TAG, "heartbeat do T-Cast falhou", e)
            dropAndReconnect()
        }
    }

    private fun dropAndReconnect() {
        disconnect()
        if (clients > 0) reconnect()
    }

    private fun startReader(s: Socket) {
        Thread({
            try {
                val input = DataInputStream(s.getInputStream())
                while (true) {
                    val size = input.readInt()
                    if (size > MAX_INBOUND_FRAME) throw IOException("frame do T-Cast grande demais: $size")
                    if (size <= 0) continue
                    val body = ByteArray(size).also(input::readFully).toString(Charsets.UTF_8)
                    RemoteCommand.toClient(body)?.let(onInbound)
                }
            } catch (e: IOException) {
                Log.i(TAG, "leitura do T-Cast encerrada: ${e.message}")
            } catch (e: RuntimeException) {
                Log.e(TAG, "falha ao processar frame do T-Cast", e)
            }
            post { if (socket === s) dropAndReconnect() }
        }, "tcast-reader").apply { isDaemon = true }.start()
    }

    private fun disconnect() {
        heartbeat?.cancel(false)
        heartbeat = null
        runCatching { socket?.close() }
        socket = null
        output = null
        connectedTo = null
    }

    private fun setStatus(next: TcastStatus?) {
        if (status == next) return
        status = next
        Log.i(TAG, "T-Cast: ${next ?: "ocioso"}")
        onStatus(next)
    }

    private companion object {
        const val TAG = "ZeusRemote/Tcast"
        const val MAX_INBOUND_FRAME = 1 shl 20
    }
}

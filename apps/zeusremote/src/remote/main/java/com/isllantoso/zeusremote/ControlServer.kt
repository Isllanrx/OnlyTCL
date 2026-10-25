package com.isllantoso.zeusremote

import android.util.Log
import java.io.BufferedInputStream
import java.io.BufferedOutputStream
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.net.InetSocketAddress
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.CopyOnWriteArraySet
import java.util.concurrent.Executors

class ControlServer(
    private val assets: Map<String, Asset>,
    private val dynamic: (String) -> Asset?,
    private val onVoice: () -> Unit,
    private val onRevive: () -> Unit,
    private val link: TcastLink,
) {
    class Asset(val type: String, val body: ByteArray)

    private class Client(private val socket: Socket, private val output: OutputStream) {
        @Synchronized fun send(opcode: Int, payload: ByteArray) = WsCodec.writeFrame(output, opcode, payload)
        fun close() = runCatching { socket.close() }
    }

    private val server = ServerSocket()
    private val pool = Executors.newFixedThreadPool(MAX_CONNECTIONS) { Thread(it, "control-conn").apply { isDaemon = true } }
    private val clients = CopyOnWriteArraySet<Client>()
    private var acceptThread: Thread? = null

    fun start() {
        server.reuseAddress = true
        server.bind(InetSocketAddress(PORT))
        link.onInbound = ::broadcast
        link.onStatus = { status -> status?.let { broadcast(it.wire) } }
        acceptThread = Thread(::acceptLoop, "control-accept").apply { isDaemon = true }.also(Thread::start)
        Log.i(TAG, "servidor de controle na porta $PORT")
    }

    fun isServing(): Boolean = acceptThread?.isAlive == true && !server.isClosed

    fun stop() {
        runCatching { server.close() }
        clients.forEach(Client::close)
        pool.shutdownNow()
    }

    private fun broadcast(message: String) {
        val payload = message.toByteArray(Charsets.UTF_8)
        for (client in clients) {
            try {
                client.send(WsCodec.OP_TEXT, payload)
            } catch (e: IOException) {
                Log.i(TAG, "envio ao cliente falhou: ${e.message}")
                client.close()
            }
        }
    }

    private fun acceptLoop() {
        val backoff = Backoff(ACCEPT_RETRY_INITIAL_MS, ACCEPT_RETRY_MAX_MS)
        while (!server.isClosed) {
            try {
                val socket = server.accept()
                backoff.reset()
                pool.execute { handle(socket) }
            } catch (e: IOException) {
                if (server.isClosed) return
                Log.w(TAG, "accept falhou; tentando de novo", e)
                Thread.sleep(backoff.next())
            } catch (e: RuntimeException) {
                if (server.isClosed) return
                Log.e(TAG, "falha ao despachar conexão", e)
            }
        }
    }

    private fun handle(socket: Socket) = socket.use {
        try {
            socket.tcpNoDelay = true
            socket.soTimeout = HEADER_TIMEOUT_MS
            val input = BufferedInputStream(socket.getInputStream())
            val output = BufferedOutputStream(socket.getOutputStream())
            val request = HttpRequest.read(input) ?: return@use
            val asset = assets[if (request.path == "/") "/index.html" else request.path] ?: dynamic(request.path)
            when {
                request.method != "GET" -> respond(output, "405 Method Not Allowed", Asset("text/plain", "405".toByteArray()))
                request.path == "/ws" && request.isWebSocketUpgrade -> serveWebSocket(socket, input, output, request)
                asset != null -> respond(output, "200 OK", asset)
                else -> respond(output, "404 Not Found", Asset("text/plain", "404".toByteArray()))
            }
        } catch (e: IOException) {
            Log.i(TAG, "conexão de ${socket.inetAddress?.hostAddress} encerrada: ${e.message}")
        } catch (e: Exception) {
            Log.e(TAG, "falha ao atender ${socket.inetAddress?.hostAddress}", e)
        }
    }

    private fun respond(output: OutputStream, status: String, asset: Asset) {
        val head = "HTTP/1.1 $status\r\nContent-Type: ${asset.type}\r\nContent-Length: ${asset.body.size}\r\n" +
            "Cache-Control: no-cache\r\nConnection: close\r\n\r\n"
        output.write(head.toByteArray(Charsets.ISO_8859_1))
        output.write(asset.body)
        output.flush()
    }

    private fun serveWebSocket(socket: Socket, input: InputStream, output: OutputStream, request: HttpRequest) {
        output.write(WsCodec.handshakeResponse(request.headers.getValue("sec-websocket-key")))
        output.flush()
        socket.soTimeout = CLIENT_IDLE_TIMEOUT_MS
        val client = Client(socket, output)
        clients.add(client)
        link.clientAttached()
        try {
            link.status?.let { client.send(WsCodec.OP_TEXT, it.wire.toByteArray(Charsets.UTF_8)) }
            while (true) {
                val frame = WsCodec.readFrame(input) ?: return
                when (frame.opcode) {
                    WsCodec.OP_TEXT -> command(frame.text)
                    WsCodec.OP_PING -> client.send(WsCodec.OP_PONG, frame.payload)
                    WsCodec.OP_CLOSE -> {
                        client.send(WsCodec.OP_CLOSE, ByteArray(0))
                        return
                    }
                }
            }
        } finally {
            clients.remove(client)
            link.clientDetached()
        }
    }

    private fun command(text: String) {
        when (text) {
            VOICE_COMMAND -> onVoice()
            REVIVE_COMMAND -> if (link.status == TcastStatus.DOWN) onRevive()
            else -> RemoteCommand.toTcast(text)?.let(link::send)
        }
    }

    companion object {
        const val PORT = 8765
        private const val VOICE_COMMAND = "v:claude"
        private const val REVIVE_COMMAND = "r:tcast"
        private const val TAG = "ZeusRemote/Server"
        private const val MAX_CONNECTIONS = 16
        private const val HEADER_TIMEOUT_MS = 5_000
        private const val CLIENT_IDLE_TIMEOUT_MS = 60_000
        private const val ACCEPT_RETRY_INITIAL_MS = 100L
        private const val ACCEPT_RETRY_MAX_MS = 2_000L
    }
}

package com.isllantoso.zeusremote

import java.io.DataInputStream
import java.io.DataOutputStream
import java.io.EOFException
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.net.SocketTimeoutException
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class TcastLinkTest {
    private val loopback = InetAddress.getByName("127.0.0.1")
    private val fast = TcastLink.Timings(
        connectTimeoutMs = 500,
        heartbeatMs = 10_000,
        idleCloseMs = 10_000,
        retryInitialMs = 30,
        retryMaxMs = 120,
    )
    private val servers = mutableListOf<ServerSocket>()
    private val links = mutableListOf<TcastLink>()
    private val accepted = mutableListOf<Socket>()
    private lateinit var statuses: LinkedBlockingQueue<String>

    @Before
    fun setUp() {
        statuses = LinkedBlockingQueue()
    }

    @After
    fun tearDown() {
        links.forEach(TcastLink::shutdown)
        accepted.forEach { runCatching { it.close() } }
        servers.forEach { runCatching { it.close() } }
    }

    private fun listen(port: Int = 0, wildcard: Boolean = false): ServerSocket =
        (if (wildcard) ServerSocket(port, 50) else ServerSocket(port, 50, loopback)).also { servers += it }

    private fun freePort(): Int = ServerSocket(0, 1, loopback).use { it.localPort }

    private fun link(
        port: Int,
        timings: TcastLink.Timings = fast,
        address: () -> InetAddress? = { loopback },
    ): TcastLink = TcastLink("test-client", address, port, timings).also {
        it.onStatus = { status -> statuses.add(status?.name ?: "IDLE") }
        links += it
    }

    private fun ServerSocket.take(timeoutMs: Int = 3_000): Socket {
        soTimeout = timeoutMs
        return accept().also { accepted += it }
    }

    private fun Socket.frame(timeoutMs: Int = 3_000): String {
        soTimeout = timeoutMs
        val input = DataInputStream(getInputStream())
        val size = input.readInt()
        return if (size == 0) "" else ByteArray(size).also(input::readFully).toString(Charsets.UTF_8)
    }

    private fun awaitStatus(expected: TcastStatus?, timeoutMs: Long = 3_000) {
        val deadline = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(timeoutMs)
        while (true) {
            val left = TimeUnit.NANOSECONDS.toMillis(deadline - System.nanoTime())
            val seen = statuses.poll(left.coerceAtLeast(1), TimeUnit.MILLISECONDS) ?: throw AssertionError("status ${expected ?: "IDLE"} não chegou")
            if (seen == (expected?.name ?: "IDLE")) return
        }
    }

    @Test
    fun backoffDoublesUntilCapAndResets() {
        val backoff = Backoff(500, 3_000)
        assertEquals(listOf(500L, 1_000L, 2_000L, 3_000L, 3_000L), List(5) { backoff.next() })
        backoff.reset()
        assertEquals(500L, backoff.next())
    }

    @Test
    fun attachConnectsSendsHandshakeAndReportsUp() {
        val server = listen()
        val link = link(server.localPort)
        link.clientAttached()
        val peer = server.take()
        assertEquals("159>>ZeusRemote>>0>>test-client", peer.frame())
        awaitStatus(TcastStatus.UP)
        assertEquals(TcastStatus.UP, link.status)
    }

    @Test
    fun sendWritesEncodedFrameOnOpenConnection() {
        val server = listen()
        val link = link(server.localPort)
        link.clientAttached()
        val peer = server.take()
        peer.frame()
        link.send("149>>13")
        assertEquals("149>>13", peer.frame())
    }

    @Test
    fun reconnectsWithoutNewKeyAfterTcastDropsConnection() {
        val server = listen()
        val link = link(server.localPort)
        link.clientAttached()
        server.take().apply { frame() }.close()
        val second = server.take()
        assertTrue(second.frame().startsWith("159>>"))
        awaitStatus(TcastStatus.UP)
        link.send("149>>15")
        assertEquals("149>>15", second.frame())
    }

    @Test
    fun reportsDownWhenRefusedAndRecoversWhenTcastReturns() {
        val port = freePort()
        val link = link(port)
        link.clientAttached()
        awaitStatus(TcastStatus.DOWN)
        assertEquals(TcastStatus.DOWN, link.status)
        val server = listen(port)
        val peer = server.take()
        assertTrue(peer.frame().startsWith("159>>"))
        awaitStatus(TcastStatus.UP)
    }

    @Test
    fun keepsRetryingWhileDownWithoutKeyPresses() {
        val port = freePort()
        val link = link(port)
        link.clientAttached()
        awaitStatus(TcastStatus.DOWN)
        Thread.sleep(400)
        val server = listen(port)
        server.take()
        awaitStatus(TcastStatus.UP)
    }

    @Test
    fun keyPressWhileDownDoesNotThrowAndStaysDown() {
        val port = freePort()
        val link = link(port)
        link.send("149>>11")
        awaitStatus(TcastStatus.DOWN)
        link.send("149>>11")
        assertEquals(TcastStatus.DOWN, link.status)
    }

    @Test
    fun keyPressConnectsOnDemandWhenNoClientAttached() {
        val server = listen()
        val link = link(server.localPort)
        link.send("149>>12")
        val peer = server.take()
        assertTrue(peer.frame().startsWith("159>>"))
        assertEquals("149>>12", peer.frame())
    }

    @Test
    fun noAddressMeansDownAndRecoversWhenAddressAppears() {
        val server = listen()
        val present = AtomicBoolean(false)
        val link = link(server.localPort) { if (present.get()) loopback else null }
        link.clientAttached()
        awaitStatus(TcastStatus.DOWN)
        present.set(true)
        server.take()
        awaitStatus(TcastStatus.UP)
    }

    @Test
    fun sendsPeriodicHeartbeat() {
        val server = listen()
        val link = link(server.localPort, fast.copy(heartbeatMs = 40))
        link.clientAttached()
        val peer = server.take()
        peer.frame()
        assertEquals("", peer.frame())
        assertEquals("", peer.frame())
    }

    @Test
    fun reconnectsWhenHeartbeatSeesAddressChange() {
        val server = listen(wildcard = true)
        val current = AtomicReference(loopback)
        val link = link(server.localPort, fast.copy(heartbeatMs = 40)) { current.get() }
        link.clientAttached()
        val first = server.take()
        first.frame()
        current.set(InetAddress.getByName("127.0.0.2"))
        val second = server.take()
        assertTrue(second.frame().startsWith("159>>"))
        first.soTimeout = 1_000
        val closed = try {
            first.getInputStream().read() == -1
        } catch (e: java.io.IOException) {
            true
        }
        assertTrue(closed)
    }

    @Test
    fun networkChangedDropsAndReopensConnection() {
        val server = listen()
        val link = link(server.localPort)
        link.clientAttached()
        val first = server.take()
        first.frame()
        link.networkChanged()
        val second = server.take()
        assertTrue(second.frame().startsWith("159>>"))
    }

    @Test
    fun networkChangedWithoutClientsDoesNotConnect() {
        val server = listen()
        val link = link(server.localPort)
        link.networkChanged()
        server.soTimeout = 300
        try {
            server.accept().also { accepted += it }
            throw AssertionError("conectou sem cliente")
        } catch (expected: SocketTimeoutException) {
            assertNull(link.status)
        }
    }

    @Test
    fun closesConnectionAfterLastClientLeavesAndStopsRetrying() {
        val server = listen()
        val link = link(server.localPort, fast.copy(idleCloseMs = 80))
        link.clientAttached()
        val peer = server.take()
        peer.frame()
        link.clientDetached()
        awaitStatus(null)
        peer.soTimeout = 1_000
        assertEquals(-1, peer.getInputStream().read())
        server.soTimeout = 300
        try {
            server.accept().also { accepted += it }
            throw AssertionError("reconectou sem clientes")
        } catch (expected: SocketTimeoutException) {
            assertNull(link.status)
        }
    }

    @Test
    fun newClientCancelsPendingIdleClose() {
        val server = listen()
        val link = link(server.localPort, fast.copy(idleCloseMs = 150))
        link.clientAttached()
        val peer = server.take()
        peer.frame()
        link.clientDetached()
        link.clientAttached()
        Thread.sleep(400)
        link.send("149>>14")
        assertEquals("149>>14", peer.frame())
    }

    @Test
    fun inboundInputListReachesCallbackAndOtherFramesAreIgnored() {
        val server = listen()
        val link = link(server.localPort)
        val received = LinkedBlockingQueue<String>()
        link.onInbound = received::add
        link.clientAttached()
        val peer = server.take()
        peer.frame()
        val out = DataOutputStream(peer.getOutputStream())
        fun push(body: String) {
            val bytes = body.toByteArray()
            out.writeInt(bytes.size)
            out.write(bytes)
            out.flush()
        }
        push("159>>version>>ignored")
        push("269>>1>>{\"data\":[]}")
        assertEquals("inputs:{\"data\":[]}", received.poll(3, TimeUnit.SECONDS))
        assertNull(received.poll(100, TimeUnit.MILLISECONDS))
    }

    @Test
    fun oversizedInboundFrameDropsConnectionAndReconnects() {
        val server = listen()
        val link = link(server.localPort)
        link.clientAttached()
        val first = server.take()
        first.frame()
        DataOutputStream(first.getOutputStream()).apply {
            writeInt(Int.MAX_VALUE)
            flush()
        }
        val second = server.take()
        assertTrue(second.frame().startsWith("159>>"))
    }

    @Test(expected = EOFException::class)
    fun fakePeerReadsEofWhenLinkShutsDown() {
        val server = listen()
        val link = link(server.localPort)
        link.clientAttached()
        val peer = server.take()
        peer.frame()
        link.shutdown()
        peer.frame()
    }
}

package com.isllantoso.zeusremote

import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.net.ProtocolException
import java.nio.ByteBuffer
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ProtocolTest {
    @Test
    fun tcastFrameHasBigEndianLengthPrefix() {
        val frame = TcastFrame.encode("149>>15")
        val buffer = ByteBuffer.wrap(frame)
        val size = buffer.int
        assertEquals(frame.size - 4, size)
        assertEquals("149>>15", String(frame, 4, size, Charsets.UTF_8))
    }

    @Test
    fun handshakeDisablesEncryption() {
        val frame = TcastFrame.handshake("zeusremote-abc")
        assertEquals("159>>ZeusRemote>>0>>zeusremote-abc", String(frame, 4, frame.size - 4, Charsets.UTF_8))
    }

    @Test
    fun heartbeatIsZeroLengthFrame() {
        assertArrayEquals(byteArrayOf(0, 0, 0, 0), TcastFrame.HEARTBEAT)
    }

    @Test
    fun keyCommandAcceptsOnlyMappedCodes() {
        assertEquals("149>>15", RemoteCommand.toTcast("k:15"))
        assertEquals("149>>29", RemoteCommand.toTcast("k:29"))
        assertEquals("149>>68", RemoteCommand.toTcast("k:68"))
        assertNull(RemoteCommand.toTcast("k:17"))
        assertNull(RemoteCommand.toTcast("k:266"))
        assertNull(RemoteCommand.toTcast("p"))
        assertNull(RemoteCommand.toTcast("k:abc"))
    }

    @Test
    fun textCommandNeutralizesSeparatorAndLimitsLength() {
        assertEquals("155>>netflix", RemoteCommand.toTcast("t:netflix"))
        assertEquals("155>>", RemoteCommand.toTcast("t:"))
        assertEquals("155>>a> > >b", RemoteCommand.toTcast("t:a>>>b"))
        assertEquals("155>>x:y", RemoteCommand.toTcast("t:x:y"))
        assertNull(RemoteCommand.toTcast("t:" + "a".repeat(RemoteCommand.MAX_TEXT + 1)))
        assertNull(RemoteCommand.toTcast("t:a\nb"))
    }

    @Test
    fun inputCommandsListAndSwitch() {
        assertEquals("269>>1", RemoteCommand.toTcast("i:list"))
        assertEquals("269>>2>>com.tcl.tvinput/.HdmiInputService/HW5", RemoteCommand.toTcast("i:com.tcl.tvinput/.HdmiInputService/HW5"))
        assertNull(RemoteCommand.toTcast("i:a>>b"))
        assertNull(RemoteCommand.toTcast("i:"))
    }

    @Test
    fun appCommandOnlyOpensValidPackages() {
        assertEquals("223>>OPEN>>com.netflix.ninja", RemoteCommand.toTcast("a:com.netflix.ninja"))
        assertNull(RemoteCommand.toTcast("a:com.x>>UNINSTALL>>com.y"))
        assertNull(RemoteCommand.toTcast("a:netflix"))
    }

    @Test
    fun forwardsOnlyInputListToClients() {
        assertEquals("inputs:{\"data\":[]}", RemoteCommand.toClient("269>>1>>{\"data\":[]}"))
        assertNull(RemoteCommand.toClient("159>>ok"))
    }

    @Test
    fun acceptKeyMatchesRfc6455Example() {
        assertEquals("s3pPLMBiTxaQ9kYGzzhZRbK+xOo=", WsCodec.acceptKey("dGhlIHNhbXBsZSBub25jZQ=="))
    }

    @Test
    fun readsMaskedTextFrame() {
        val mask = byteArrayOf(0x37, 0xfa.toByte(), 0x21, 0x3d)
        val text = "k:11".toByteArray()
        val masked = ByteArray(text.size) { (text[it].toInt() xor mask[it % 4].toInt()).toByte() }
        val bytes = byteArrayOf(0x81.toByte(), (0x80 or text.size).toByte()) + mask + masked
        val frame = WsCodec.readFrame(ByteArrayInputStream(bytes))!!
        assertEquals(WsCodec.OP_TEXT, frame.opcode)
        assertEquals("k:11", frame.text)
    }

    @Test
    fun returnsNullOnCleanEof() {
        assertNull(WsCodec.readFrame(ByteArrayInputStream(ByteArray(0))))
    }

    @Test(expected = ProtocolException::class)
    fun rejectsUnmaskedClientFrame() {
        WsCodec.readFrame(ByteArrayInputStream(byteArrayOf(0x81.toByte(), 0x01, 0x41)))
    }

    @Test(expected = ProtocolException::class)
    fun rejectsOversizedPayload() {
        val bytes = byteArrayOf(0x81.toByte(), (0x80 or 127).toByte()) + ByteBuffer.allocate(8).putLong(1L shl 20).array()
        WsCodec.readFrame(ByteArrayInputStream(bytes))
    }

    @Test
    fun writesUnmaskedControlFrame() {
        val out = ByteArrayOutputStream()
        WsCodec.writeFrame(out, WsCodec.OP_PONG, "hi".toByteArray())
        assertArrayEquals(byteArrayOf(0x8A.toByte(), 0x02, 'h'.code.toByte(), 'i'.code.toByte()), out.toByteArray())
    }

    @Test
    fun writesExtendedLengthTextFrame() {
        val out = ByteArrayOutputStream()
        WsCodec.writeFrame(out, WsCodec.OP_TEXT, ByteArray(300))
        val bytes = out.toByteArray()
        assertEquals(0x81, bytes[0].toInt() and 0xFF)
        assertEquals(126, bytes[1].toInt())
        assertEquals(300, ((bytes[2].toInt() and 0xFF) shl 8) or (bytes[3].toInt() and 0xFF))
        assertEquals(304, bytes.size)
    }

    @Test(expected = IOException::class)
    fun rejectsOversizedControlFrame() {
        WsCodec.writeFrame(ByteArrayOutputStream(), WsCodec.OP_PONG, ByteArray(126))
    }

    @Test
    fun parsesWebSocketUpgradeRequest() {
        val raw = "GET /ws?x=1 HTTP/1.1\r\nHost: tv\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n" +
            "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n\r\n"
        val request = HttpRequest.read(ByteArrayInputStream(raw.toByteArray()))!!
        assertEquals("GET", request.method)
        assertEquals("/ws", request.path)
        assertTrue(request.isWebSocketUpgrade)
    }

    @Test(expected = IOException::class)
    fun rejectsOversizedHeader() {
        val raw = "GET / HTTP/1.1\r\nX: " + "a".repeat(9000) + "\r\n\r\n"
        HttpRequest.read(ByteArrayInputStream(raw.toByteArray()))
    }
}

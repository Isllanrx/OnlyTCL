package com.isllantoso.zeusremote

import java.io.DataInputStream
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.net.ProtocolException
import java.security.MessageDigest
import java.util.Base64

object WsCodec {
    const val OP_TEXT = 0x1
    const val OP_CLOSE = 0x8
    const val OP_PING = 0x9
    const val OP_PONG = 0xA

    private const val GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    private const val MAX_PAYLOAD = 4 * 1024

    class Frame(val opcode: Int, val payload: ByteArray) {
        val text: String get() = payload.toString(Charsets.UTF_8)
    }

    fun acceptKey(key: String): String {
        val digest = MessageDigest.getInstance("SHA-1").digest((key + GUID).toByteArray(Charsets.ISO_8859_1))
        return Base64.getEncoder().encodeToString(digest)
    }

    fun handshakeResponse(key: String): ByteArray = (
        "HTTP/1.1 101 Switching Protocols\r\n" +
            "Upgrade: websocket\r\n" +
            "Connection: Upgrade\r\n" +
            "Sec-WebSocket-Accept: ${acceptKey(key)}\r\n\r\n"
        ).toByteArray(Charsets.ISO_8859_1)

    fun readFrame(input: InputStream): Frame? {
        val data = DataInputStream(input)
        val b0 = input.read()
        if (b0 == -1) return null
        val b1 = data.readUnsignedByte()
        if (b1 and 0x80 == 0) throw ProtocolException("frame do cliente sem máscara")
        val length = when (val len = b1 and 0x7F) {
            126 -> data.readUnsignedShort().toLong()
            127 -> data.readLong()
            else -> len.toLong()
        }
        if (length !in 0..MAX_PAYLOAD) throw ProtocolException("payload grande demais: $length")
        val mask = ByteArray(4).also(data::readFully)
        val payload = ByteArray(length.toInt()).also(data::readFully)
        for (i in payload.indices) payload[i] = (payload[i].toInt() xor mask[i % 4].toInt()).toByte()
        return Frame(b0 and 0x0F, payload)
    }

    fun writeFrame(output: OutputStream, opcode: Int, payload: ByteArray = ByteArray(0)) {
        if (opcode >= OP_CLOSE && payload.size > 125) throw IOException("payload de controle grande demais: ${payload.size}")
        output.write(0x80 or opcode)
        when {
            payload.size <= 125 -> output.write(payload.size)
            payload.size <= 0xFFFF -> {
                output.write(126)
                output.write(payload.size shr 8)
                output.write(payload.size and 0xFF)
            }
            else -> {
                output.write(127)
                for (shift in 56 downTo 0 step 8) output.write((payload.size.toLong() shr shift).toInt() and 0xFF)
            }
        }
        output.write(payload)
        output.flush()
    }
}

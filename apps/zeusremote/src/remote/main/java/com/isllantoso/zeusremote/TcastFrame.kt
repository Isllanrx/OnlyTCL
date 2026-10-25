package com.isllantoso.zeusremote

import java.nio.ByteBuffer

object TcastFrame {
    const val PORT = 6553
    const val DEVICE_NAME = "ZeusRemote"

    val HEARTBEAT: ByteArray = ByteArray(Int.SIZE_BYTES)

    fun encode(body: String): ByteArray {
        val data = body.toByteArray(Charsets.UTF_8)
        return ByteBuffer.allocate(Int.SIZE_BYTES + data.size).putInt(data.size).put(data).array()
    }

    fun handshake(clientId: String): ByteArray = encode("159>>$DEVICE_NAME>>0>>$clientId")
}

object RemoteCommand {
    const val MAX_TEXT = 100
    const val INPUTS_PREFIX = "269>>1>>"
    private const val KEYBOARD_ENTER = 68

    private val keys = (1..16).toSet() + (18..23) + (27..29) + KEYBOARD_ENTER
    private val inputId = Regex("[A-Za-z0-9._/:%-]{1,200}")
    private val packageName = Regex("[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z0-9_]+)+")
    private val separatorRun = Regex(">(?=>)")

    fun toTcast(message: String): String? {
        val kind = message.substringBefore(':', "")
        val arg = message.substringAfter(':', "")
        return when (kind) {
            "k" -> arg.toIntOrNull()?.takeIf { it in keys }?.let { "149>>$it" }
            "t" -> arg.takeIf { it.length <= MAX_TEXT && '\n' !in it }?.let { "155>>${it.replace(separatorRun, "> ")}" }
            "i" -> if (arg == "list") "269>>1" else arg.takeIf(inputId::matches)?.let { "269>>2>>$it" }
            "a" -> arg.takeIf(::isPackage)?.let { "223>>OPEN>>$it" }
            else -> null
        }
    }

    fun isPackage(name: String): Boolean = packageName.matches(name)

    fun toClient(tcastBody: String): String? =
        tcastBody.takeIf { it.startsWith(INPUTS_PREFIX) }?.let { "inputs:" + it.removePrefix(INPUTS_PREFIX) }
}

package com.isllantoso.zeusremote

import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.InputStream

class HttpRequest(val method: String, val path: String, val headers: Map<String, String>) {
    val isWebSocketUpgrade: Boolean
        get() = headers["upgrade"].equals("websocket", ignoreCase = true) && headers.containsKey("sec-websocket-key")

    companion object {
        private const val MAX_HEADER_BYTES = 8 * 1024

        fun read(input: InputStream): HttpRequest? {
            var budget = MAX_HEADER_BYTES
            val requestLine = readLine(input, budget) ?: return null
            budget -= requestLine.length
            val parts = requestLine.split(' ')
            if (parts.size < 3) throw IOException("linha de requisição inválida")
            val headers = mutableMapOf<String, String>()
            while (true) {
                val line = readLine(input, budget) ?: throw IOException("cabeçalho incompleto")
                if (line.isEmpty()) break
                budget -= line.length
                val colon = line.indexOf(':')
                if (colon > 0) headers[line.substring(0, colon).trim().lowercase()] = line.substring(colon + 1).trim()
            }
            return HttpRequest(parts[0], parts[1].substringBefore('?'), headers)
        }

        private fun readLine(input: InputStream, budget: Int): String? {
            val buf = ByteArrayOutputStream()
            while (true) {
                val b = input.read()
                if (b == -1) return if (buf.size() == 0) null else throw IOException("conexão fechada no cabeçalho")
                if (b == '\n'.code) break
                if (b != '\r'.code) buf.write(b)
                if (buf.size() > budget) throw IOException("cabeçalho grande demais")
            }
            return buf.toString(Charsets.ISO_8859_1.name())
        }
    }
}

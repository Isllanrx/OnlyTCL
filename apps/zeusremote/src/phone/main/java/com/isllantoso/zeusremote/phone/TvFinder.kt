package com.isllantoso.zeusremote.phone

import java.io.IOException
import java.net.HttpURLConnection
import java.net.Inet4Address
import java.net.NetworkInterface
import java.net.SocketException
import java.net.URL
import java.util.concurrent.ExecutorCompletionService
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

object TvFinder {
    const val PORT = 8765
    const val DEFAULT_HOST = "192.168.76.209"

    private const val MARKER = "<title>ZeusRemote</title>"
    private const val DIRECT_TIMEOUT_MS = 1_500
    private const val SCAN_TIMEOUT_MS = 700
    private const val SCAN_THREADS = 48
    private const val SCAN_DEADLINE_SECONDS = 20L
    private val LAN_PREFIXES = listOf("wlan", "eth", "ap", "swlan")

    fun url(host: String) = "http://$host:$PORT/"

    fun subnetHosts(local: String?): List<String> {
        val parts = local?.split('.')?.takeIf { it.size == 4 } ?: return emptyList()
        val prefix = parts.take(3).joinToString(".")
        return (1..254).map { "$prefix.$it" }.filter { it != local }
    }

    fun isRemote(host: String, timeoutMs: Int = DIRECT_TIMEOUT_MS): Boolean = try {
        val connection = URL(url(host)).openConnection() as HttpURLConnection
        connection.connectTimeout = timeoutMs
        connection.readTimeout = timeoutMs
        try {
            connection.responseCode == HttpURLConnection.HTTP_OK &&
                connection.inputStream.bufferedReader().use { it.readText() }.contains(MARKER)
        } finally {
            connection.disconnect()
        }
    } catch (e: IOException) {
        false
    }

    fun find(preferred: List<String>): String? {
        preferred.distinct().firstOrNull { isRemote(it) }?.let { return it }
        val hosts = subnetHosts(localIpv4()) - preferred.toSet()
        if (hosts.isEmpty()) return null
        val pool = Executors.newFixedThreadPool(SCAN_THREADS)
        try {
            val results = ExecutorCompletionService<String?>(pool)
            hosts.forEach { host -> results.submit { host.takeIf { isRemote(it, SCAN_TIMEOUT_MS) } } }
            repeat(hosts.size) {
                val done = results.poll(SCAN_DEADLINE_SECONDS, TimeUnit.SECONDS) ?: return null
                done.get()?.let { return it }
            }
            return null
        } finally {
            pool.shutdownNow()
        }
    }

    private fun localIpv4(): String? {
        val interfaces = try {
            NetworkInterface.getNetworkInterfaces()?.toList() ?: return null
        } catch (e: SocketException) {
            return null
        }
        val candidates = interfaces
            .filter { it.isUp && !it.isLoopback }
            .flatMap { nic -> nic.inetAddresses.toList().filterIsInstance<Inet4Address>().filter { it.isSiteLocalAddress }.map { nic.name to it } }
        val lan = candidates.firstOrNull { (name, _) -> LAN_PREFIXES.any(name::startsWith) } ?: candidates.firstOrNull()
        return lan?.second?.hostAddress
    }
}

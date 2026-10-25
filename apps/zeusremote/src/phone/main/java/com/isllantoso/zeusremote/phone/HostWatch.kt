package com.isllantoso.zeusremote.phone

class HostWatch(private val failuresToSearch: Int = 2, private val minSearchGapMs: Long = 30_000) {
    private var failures = 0
    private var lastSearchMs: Long? = null

    fun record(reachable: Boolean, nowMs: Long): Boolean {
        if (reachable) {
            failures = 0
            return false
        }
        failures++
        if (failures < failuresToSearch) return false
        val last = lastSearchMs
        if (last != null && nowMs - last < minSearchGapMs) return false
        lastSearchMs = nowMs
        return true
    }

    fun reset() {
        failures = 0
    }
}

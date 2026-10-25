package com.isllantoso.zeusremote

class Backoff(private val initialMs: Long, private val maxMs: Long) {
    private var current = initialMs

    fun next(): Long = current.also { current = minOf(current * 2, maxMs) }

    fun reset() {
        current = initialMs
    }
}

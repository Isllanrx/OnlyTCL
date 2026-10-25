package com.isllantoso.zeusremote.phone

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class HostWatchTest {
    @Test
    fun singleFailureDoesNotTriggerSearch() {
        assertFalse(HostWatch().record(false, 0))
    }

    @Test
    fun secondConsecutiveFailureTriggersSearch() {
        val watch = HostWatch()
        assertFalse(watch.record(false, 0))
        assertTrue(watch.record(false, 10_000))
    }

    @Test
    fun successBetweenFailuresResetsCounter() {
        val watch = HostWatch()
        assertFalse(watch.record(false, 0))
        assertFalse(watch.record(true, 10_000))
        assertFalse(watch.record(false, 20_000))
    }

    @Test
    fun searchesAreSpacedByMinimumGapWhileTvStaysAway() {
        val watch = HostWatch(failuresToSearch = 2, minSearchGapMs = 30_000)
        watch.record(false, 0)
        assertTrue(watch.record(false, 10_000))
        assertFalse(watch.record(false, 20_000))
        assertFalse(watch.record(false, 39_999))
        assertTrue(watch.record(false, 40_000))
    }

    @Test
    fun resetAfterFoundHostRequiresFreshFailures() {
        val watch = HostWatch()
        watch.record(false, 0)
        assertTrue(watch.record(false, 10_000))
        watch.reset()
        assertFalse(watch.record(false, 50_000))
        assertTrue(watch.record(false, 60_000))
    }
}

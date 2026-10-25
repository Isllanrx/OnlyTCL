package com.isllantoso.zeusremote.phone

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TvFinderTest {
    @Test
    fun subnetCoversLanWithoutOwnAddress() {
        val hosts = TvFinder.subnetHosts("192.168.76.170")
        assertEquals(253, hosts.size)
        assertEquals("192.168.76.1", hosts.first())
        assertEquals("192.168.76.254", hosts.last())
        assertFalse("192.168.76.170" in hosts)
        assertTrue("192.168.76.209" in hosts)
    }

    @Test
    fun noSubnetWithoutLocalAddress() {
        assertTrue(TvFinder.subnetHosts(null).isEmpty())
        assertTrue(TvFinder.subnetHosts("fe80::1").isEmpty())
    }

    @Test
    fun urlUsesBridgePort() {
        assertEquals("http://192.168.76.209:8765/", TvFinder.url("192.168.76.209"))
    }
}

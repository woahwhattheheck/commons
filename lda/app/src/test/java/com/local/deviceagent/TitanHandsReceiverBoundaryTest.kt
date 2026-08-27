package com.local.deviceagent

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * Named regressions for the exported TITAN receiver's ADB component boundary.
 * Source + companion runtime constants; no device, no Commons admission gate.
 */
class TitanHandsReceiverBoundaryTest {

    @Test fun testAdbReceiverBoundaryIsPlatformDump() {
        assertEquals("android.permission.DUMP", TitanHandsReceiver.ADB_SENDER_PERMISSION)
        assertEquals("com.local.deviceagent.TITAN_HANDS", TitanHandsReceiver.ACTION)
        assertEquals("SCREEN_GENERATION_MISMATCH", TitanHandsReceiver.GENERATION_MISMATCH_REASON)
        assertEquals(TitanHandsMarks.GENERATION_MISMATCH_REASON, TitanHandsReceiver.GENERATION_MISMATCH_REASON)
    }

    @Test fun testManifestReceiverDeclaresDumpBoundary() {
        val manifest = findManifest().readText()
        val receiver = receiverBlock(manifest)
        assertTrue(receiver.contains("android:name=\".TitanHandsReceiver\""))
        assertTrue(receiver.contains("android:exported=\"true\""))
        assertTrue(receiver.contains("android:permission=\"android.permission.DUMP\""))
        assertFalse(receiver.contains("login"))
        assertFalse(receiver.contains("allowlist"))
        assertFalse(receiver.contains("approval"))
    }

    private fun findManifest(): File {
        var dir = File(System.getProperty("user.dir"))
        repeat(8) {
            val candidates = listOf(
                File(dir, "src/main/AndroidManifest.xml"),
                File(dir, "app/src/main/AndroidManifest.xml"),
                File(dir, "lda/app/src/main/AndroidManifest.xml"),
            )
            candidates.firstOrNull { it.isFile }?.let { return it }
            dir = dir.parentFile ?: return@repeat
        }
        throw AssertionError("AndroidManifest.xml not found from ${System.getProperty("user.dir")}")
    }

    private fun receiverBlock(manifest: String): String {
        val start = manifest.indexOf("android:name=\".TitanHandsReceiver\"")
        assertTrue("TitanHandsReceiver missing from manifest", start >= 0)
        val lt = manifest.lastIndexOf("<receiver", start)
        val end = manifest.indexOf("</receiver>", start)
        assertTrue(lt >= 0 && end > lt)
        return manifest.substring(lt, end)
    }
}

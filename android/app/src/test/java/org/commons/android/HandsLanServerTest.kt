package org.commons.android

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.net.HttpURLConnection
import java.net.URL
import java.nio.charset.StandardCharsets

class HandsLanServerTest {
    @Test
    fun observeWithoutPairingDoesNotDrive() {
        val code = Pairing.mint()
        val server = HttpJsonServer(
            port = 0,
            handler = { request ->
                JSONObject()
                    .put("ok", true)
                    .put("kind", "observation_delta")
                    .put("op", request.optString("op"))
            },
            health = { JSONObject().put("ok", true).put("kind", "health-full") },
            publicHealth = { JSONObject().put("ok", true).put("kind", "health") },
            expectedPairing = { code },
            bindHost = "127.0.0.1",
        )
        server.start()
        try {
            val port = server.boundPort
            val missing = JSONObject(post(port, """{"op":"observe"}""", pairing = null))
            assertFalse(missing.optBoolean("ok"))
            assertEquals("PAIRING_REQUIRED", missing.getString("failure_reason"))
            val wrong = JSONObject(post(port, """{"op":"observe"}""", pairing = "deadbeef"))
            assertEquals("PAIRING_MISMATCH", wrong.getString("failure_reason"))
            val empty = JSONObject(post(port, "", pairing = null))
            assertEquals("PAIRING_REQUIRED", empty.getString("failure_reason"))
            val ok = JSONObject(post(port, """{"op":"observe"}""", pairing = code))
            assertTrue(ok.getBoolean("ok"))
            assertEquals("observation_delta", ok.getString("kind"))
            val health = JSONObject(get(port, "/health"))
            assertEquals("health", health.getString("kind"))
        } finally {
            server.stop()
        }
    }

    @Test
    fun lanBindWithoutPairingDoesNotListen() {
        val server = HttpJsonServer(
            port = 0,
            handler = { JSONObject().put("ok", true) },
            health = { JSONObject().put("ok", true) },
            publicHealth = { JSONObject().put("ok", true) },
            expectedPairing = { "" },
            bindHost = "0.0.0.0",
        )
        try {
            server.start()
            org.junit.Assert.fail("LAN bind without pairing should not start")
        } catch (exc: IllegalStateException) {
            assertTrue(exc.message!!.contains("on-device pairing"))
        } finally {
            server.stop()
        }
    }

    private fun post(port: Int, body: String, pairing: String?): String {
        var last: Exception? = null
        repeat(40) {
            try {
                val connection = URL("http://127.0.0.1:$port/").openConnection() as HttpURLConnection
                connection.requestMethod = "POST"
                connection.doOutput = true
                connection.connectTimeout = 2000
                connection.readTimeout = 2000
                connection.setRequestProperty("Content-Type", "application/json")
                if (pairing != null) connection.setRequestProperty("X-Commons-Pairing", pairing)
                connection.outputStream.use { it.write(body.toByteArray(StandardCharsets.UTF_8)) }
                val stream = if (connection.responseCode in 200..299) connection.inputStream else connection.errorStream
                return stream.use { it.readBytes().toString(Charsets.UTF_8) }
            } catch (exc: Exception) {
                last = exc
                Thread.sleep(25)
            }
        }
        throw last ?: IllegalStateException("post failed")
    }

    private fun get(port: Int, path: String): String {
        val connection = URL("http://127.0.0.1:$port$path").openConnection() as HttpURLConnection
        connection.requestMethod = "GET"
        connection.connectTimeout = 2000
        connection.readTimeout = 2000
        return connection.inputStream.use { it.readBytes().toString(Charsets.UTF_8) }
    }
}

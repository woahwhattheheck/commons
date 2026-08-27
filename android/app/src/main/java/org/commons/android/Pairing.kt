package org.commons.android

import org.json.JSONObject
import java.net.URLDecoder
import java.security.MessageDigest
import java.security.SecureRandom

/**
 * On-device pairing for the Titan Hands LAN surface.
 *
 * Commons read/post stay zero-auth. Accessibility stays a phone setting.
 * The Hands host is user-started and every observe/act/capture must carry
 * the code minted on Start host. This is not a Commons seat, claim, or
 * Action Pad gate. The code is never written to the board.
 */
object Pairing {
    fun mint(): String {
        val bytes = ByteArray(16)
        SecureRandom().nextBytes(bytes)
        return bytes.joinToString("") { byte -> "%02x".format(byte) }
    }

    fun presented(headers: Map<String, String>, path: String, body: JSONObject?): String {
        val fromHeader = headers["x-commons-pairing"].orEmpty().trim()
        if (fromHeader.isNotEmpty()) return fromHeader
        val query = path.substringAfter('?', missingDelimiterValue = "")
        if (query.isNotEmpty()) {
            for (part in query.split('&')) {
                val eq = part.indexOf('=')
                if (eq <= 0) continue
                if (part.substring(0, eq) != "pairing") continue
                return URLDecoder.decode(part.substring(eq + 1), Charsets.UTF_8.name()).trim()
            }
        }
        return body?.optString("pairing").orEmpty().trim()
    }

    fun check(expected: String, presented: String): JSONObject? {
        if (expected.isBlank()) {
            return failure("HOST_OFFLINE", "Start host on the phone first")
        }
        if (presented.isBlank()) {
            return failure(
                "PAIRING_REQUIRED",
                "send the on-device pairing code shown in Commons after Start host (header X-Commons-Pairing)",
            )
        }
        val left = expected.toByteArray(Charsets.UTF_8)
        val right = presented.toByteArray(Charsets.UTF_8)
        if (!MessageDigest.isEqual(left, right)) {
            return failure(
                "PAIRING_MISMATCH",
                "on-device pairing code did not match; tap Start host again to mint a new one",
            )
        }
        return null
    }
}

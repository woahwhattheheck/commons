package com.tokenjunkielabs.proofpocket.core

import org.json.JSONObject

object ReceiptCodec {
    fun decodeAndVerify(json: String): Pair<Receipt?, ReceiptVerification> = try {
        val root = JSONObject(json)
        val payload = root.getJSONObject("payload")
        require(payload.getString("schema") == "proofpocket.receipt.v1") { "unsupported receipt schema" }
        val evidenceJson = payload.getJSONArray("evidence")
        val evidence = buildList {
            for (i in 0 until evidenceJson.length()) {
                val e = evidenceJson.getJSONObject(i)
                add(Evidence(
                    id = e.getString("id"),
                    name = e.getString("name"),
                    mimeType = e.getString("mimeType"),
                    sha256 = e.getString("sha256"),
                    sizeBytes = e.getLong("sizeBytes"),
                    sourceModifiedAtUtc = if (e.isNull("sourceModifiedAtUtc")) null else e.getString("sourceModifiedAtUtc"),
                ))
            }
        }
        val receipt = Receipt(
            receiptId = root.getString("receiptId").lowercase(),
            projectId = payload.getString("projectId"),
            projectTitle = payload.getString("projectTitle"),
            claim = payload.getString("claim"),
            issuedAtUtc = payload.getString("issuedAtUtc"),
            evidence = evidence,
        )
        receipt to ReceiptEngine.verify(receipt)
    } catch (e: Exception) {
        null to ReceiptVerification(false, "invalid receipt JSON: ${e.message}")
    }
}

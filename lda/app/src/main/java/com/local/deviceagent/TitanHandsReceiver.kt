package com.local.deviceagent

import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Base64
import org.json.JSONObject

/**
 * Thin ADB transport for TITAN Hands.
 *
 * This is deliberately not a second handset operator. Perception and actuation stay in the LDA's
 * existing [ActionAccessibilityService.snapshotScreen] and
 * [ActionAccessibilityService.performActionJson] implementation. The receiver only transports one
 * operation in and one result out so an off-device model can drive the same translated handset.
 *
 * Input and output JSON are base64-wrapped because `adb shell am broadcast` otherwise damages
 * quotes, spaces, and Unicode. The receiver does not listen to accessibility events or capture
 * pixels; normal observations are the compact numbered LDA screen representation.
 */
class TitanHandsReceiver : BroadcastReceiver() {

    companion object {
        const val ACTION = "com.local.deviceagent.TITAN_HANDS"
        const val BRIDGE_VERSION = "lda-titan-hands/1"
    }

    override fun onReceive(context: Context, intent: Intent?) {
        val response = try {
            when (intent?.getStringExtra("op")?.trim()?.lowercase()) {
                "capabilities" -> capabilities()
                "observe" -> observe()
                "act" -> act(intent)
                else -> failure("UNKNOWN_OPERATION", "op must be capabilities, observe, or act")
            }
        } catch (t: Throwable) {
            failure("BRIDGE_ERROR", t.message ?: t.javaClass.simpleName)
        }
        setResultCode(if (response.optBoolean("ok")) Activity.RESULT_OK else Activity.RESULT_CANCELED)
        setResultData(encode(response.toString()))
    }

    private fun capabilities(): JSONObject = JSONObject()
        .put("ok", true)
        .put("bridge", BRIDGE_VERSION)
        .put("platform", "android")
        .put("implementation", "lda-kotlin")
        .put("accessibility_ready", ActionAccessibilityService.instance != null)
        .put("perception", "ActionAccessibilityService.snapshotScreen")
        .put("actuation", "ActionAccessibilityService.performActionJson")

    private fun observe(): JSONObject {
        val service = ActionAccessibilityService.instance
            ?: return failure("ACCESSIBILITY_UNAVAILABLE", "enable Local Agent accessibility service")
        return JSONObject()
            .put("ok", true)
            .put("bridge", BRIDGE_VERSION)
            .put("platform", "android")
            .put("implementation", "lda-kotlin")
            .put("pixels", "not-captured")
            .put("snapshot", service.snapshotScreen())
    }

    private fun act(intent: Intent): JSONObject {
        val service = ActionAccessibilityService.instance
            ?: return failure("ACCESSIBILITY_UNAVAILABLE", "enable Local Agent accessibility service")
        val encoded = intent.getStringExtra("action_b64").orEmpty()
        if (encoded.isBlank()) return failure("INVALID_REQUEST", "act requires action_b64")
        val raw = try { decode(encoded) } catch (_: Throwable) {
            return failure("INVALID_REQUEST", "action_b64 is not valid UTF-8 base64")
        }
        if (raw.isBlank()) return failure("INVALID_REQUEST", "action JSON is empty")

        // Populate the numbered currentNodes table immediately before resolving an action. This is
        // the LDA's own perceive -> act contract and prevents stale/wrong-window element targeting.
        val before = service.snapshotScreen()
        val wasBusy = AgentService.isAgentBusy
        AgentService.isAgentBusy = true
        service.resumeInjection()
        return try {
            val outcome = service.performActionJson(raw, allowGated = true)
            JSONObject()
                .put("ok", outcome.result != ActionResult.FAILED && outcome.result != ActionResult.NEEDS_CONFIRM)
                .put("bridge", BRIDGE_VERSION)
                .put("platform", "android")
                .put("implementation", "lda-kotlin")
                .put("result", outcome.result.name)
                .put("summary", outcome.summary)
                .put("kickback", outcome.kickback)
                .put("say", outcome.say ?: JSONObject.NULL)
                .put("question", outcome.question ?: JSONObject.NULL)
                .put("confirm_prompt", outcome.confirmPrompt ?: JSONObject.NULL)
                .put("before", before)
        } finally {
            AgentService.isAgentBusy = wasBusy
        }
    }

    private fun failure(reason: String, message: String): JSONObject = JSONObject()
        .put("ok", false)
        .put("bridge", BRIDGE_VERSION)
        .put("platform", "android")
        .put("implementation", "lda-kotlin")
        .put("failure_reason", reason)
        .put("message", message)

    private fun encode(value: String): String =
        Base64.encodeToString(value.toByteArray(Charsets.UTF_8), Base64.NO_WRAP)

    private fun decode(value: String): String =
        String(Base64.decode(value, Base64.DEFAULT), Charsets.UTF_8)
}

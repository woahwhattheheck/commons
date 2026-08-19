package com.local.deviceagent

import android.app.KeyguardManager
import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts

/**
 * Tiny, invisible gate shown before the agent activates when the owner has enabled
 * "Require fingerprint / PIN" and the inactivity window has lapsed. It asks the device
 * to confirm the user's credential (fingerprint / PIN / pattern), and on success
 * re-dispatches the original activation intent to [AgentService]. Uses the framework
 * KeyguardManager so no extra dependency is needed.
 */
class AuthGateActivity : ComponentActivity() {

    private val confirm =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { res ->
            if (res.resultCode == RESULT_OK) onAuthOk() else finish()
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val km = getSystemService(KEYGUARD_SERVICE) as? KeyguardManager
        // No secure lock configured -> nothing to verify against; just proceed.
        if (km == null || !km.isDeviceSecure) { onAuthOk(); return }
        @Suppress("DEPRECATION")
        val intent = km.createConfirmDeviceCredentialIntent(
            "Local Agent", "Confirm it's you to start the agent"
        )
        if (intent == null) onAuthOk() else confirm.launch(intent)
    }

    private fun onAuthOk() {
        SettingsManager(this).setLastAuthMs(System.currentTimeMillis())
        intent.getStringExtra(EXTRA_PENDING_ACTION)?.let { action ->
            val i = Intent(this, AgentService::class.java).setAction(action)
            intent.getStringExtra(EXTRA_PENDING_COMMAND)?.let { i.putExtra(AgentService.EXTRA_COMMAND, it) }
            startForegroundService(i)
        }
        finish()
    }

    companion object {
        const val EXTRA_PENDING_ACTION = "pending_action"
        const val EXTRA_PENDING_COMMAND = "pending_command"
    }
}

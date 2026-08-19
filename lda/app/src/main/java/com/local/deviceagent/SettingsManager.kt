package com.local.deviceagent

import android.content.Context
import android.content.SharedPreferences

class SettingsManager(context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("agent_settings", Context.MODE_PRIVATE)

    // Voice mode: "minimal" (brief speech, default), "explanation" (narrate the
    // reasoning aloud), or "silent" (no speech at all).
    fun getVoiceMode(): String = prefs.getString("voice_mode", "minimal") ?: "minimal"

    fun setVoiceMode(mode: String) {
        prefs.edit().putString("voice_mode", mode).apply()
    }

    fun isSilent(): Boolean = getVoiceMode() == "silent"

    /** The brain narrates its reasoning only in explanation mode. */
    fun isNarrationEnabled(): Boolean = getVoiceMode() == "explanation"

    fun getTriggerWord(): String =
        prefs.getString("trigger_word", "hey agent") ?: "hey agent"

    fun setTriggerWord(word: String) {
        prefs.edit().putString("trigger_word", word).apply()
    }

    /** Absolute path to the imported on-device LLM model file, or null if unset. */
    fun getModelPath(): String? = prefs.getString("model_path", null)

    fun setModelPath(path: String?) {
        prefs.edit().putString("model_path", path).apply()
    }

    /** Optional small "helper" submodel. Planning / progress / common-sense run here (on
     *  CPU) so the big vision model isn't overwhelmed. Null = use the main model for those
     *  too (the default; the helper is opt-in). */
    fun getMiniModelPath(): String? = prefs.getString("mini_model_path", null)

    fun setMiniModelPath(path: String?) {
        prefs.edit().putString("mini_model_path", path).apply()
    }

    /** Whether the optional helper submodel is allowed to load. Default OFF on purpose:
     *  running a SECOND model resident alongside the big vision model can exhaust phone
     *  RAM and trip the OS low-memory killer (black wallpaper, other apps closing, even
     *  the agent itself getting killed). Leave it off for a stable phone; turn it on to
     *  experiment once you know the device has the headroom. */
    fun isMiniModelEnabled(): Boolean = prefs.getBoolean("mini_model_enabled", false)

    fun setMiniModelEnabled(on: Boolean) {
        prefs.edit().putBoolean("mini_model_enabled", on).apply()
    }

    /** Whether the agent may operate its OWN app (this chat, menus, settings). OFF by default and
     *  recommended off: acting on its own UI risks self-prompting loops and lets it change its own
     *  settings. While off, the agent leaves to the home screen if it ever lands on its own app. */
    fun isSelfInteractionAllowed(): Boolean = prefs.getBoolean("self_interaction", false)

    fun setSelfInteractionAllowed(on: Boolean) {
        prefs.edit().putBoolean("self_interaction", on).apply()
    }

    /** Verifier-first: take a fast text-only second opinion on each consequential action. Its
     *  output is CONSTRAINED to OK / retarget-to-element / back (it can't free-form rewrite the
     *  action), so it can fix a wrong target without ever mangling a good action or dropping
     *  text. Default ON; toggle off to compare. */
    fun isVerifierEnabled(): Boolean = prefs.getBoolean("verifier_enabled", true)

    fun setVerifierEnabled(on: Boolean) {
        prefs.edit().putBoolean("verifier_enabled", on).apply()
    }

    /** Containment: block the agent from operating terminal / shell / code-runner / remote-
     *  desktop apps (where it could RUN CODE) without the owner's say-so. Default ON - another
     *  AI tried to get the agent to run code. Turn off only to deliberately allow it. */
    fun isCodeExecutionBlocked(): Boolean = prefs.getBoolean("block_code_exec", true)

    fun setCodeExecutionBlocked(on: Boolean) {
        prefs.edit().putBoolean("block_code_exec", on).apply()
    }

    /** Self-protection: stop the agent from operating its OWN source repo (it once wandered onto
     *  the project's GitHub page, where a tap on Delete/commit could trash the codebase). Default
     *  ON; turn off only to deliberately allow it. */
    fun isSelfProtectEnabled(): Boolean = prefs.getBoolean("self_protect", true)

    fun setSelfProtectEnabled(on: Boolean) {
        prefs.edit().putBoolean("self_protect", on).apply()
    }

    /** Navigate by tapping the screen like a person (default) vs using open_app shortcuts. */
    fun isHumanNavigation(): Boolean = prefs.getBoolean("human_nav", true)

    fun setHumanNavigation(on: Boolean) {
        prefs.edit().putBoolean("human_nav", on).apply()
    }

    /** Use a male TTS voice when one is installed (falls back to a deeper pitch). Default on. */
    fun isMaleVoice(): Boolean = prefs.getBoolean("male_voice", true)

    fun setMaleVoice(on: Boolean) {
        prefs.edit().putBoolean("male_voice", on).apply()
    }

    /** Master on/off. When off, the home screen won't auto-start the agent/mic/
     *  overlay services, so the agent is fully dormant until turned back on. */
    fun isAgentEnabled(): Boolean = prefs.getBoolean("agent_enabled", true)

    fun setAgentEnabled(on: Boolean) {
        prefs.edit().putBoolean("agent_enabled", on).apply()
    }

    /** Heat protection level - the thermal status at/above which the agent stops.
     *  "minimal" (default) only bails when the phone is critically hot and about
     *  to throttle/shutdown to avoid damage; "medium" and "high" stop earlier.
     *  Phones run warm under sustained GPU inference, so the cautious old default
     *  cut tasks short - minimal lets it keep working until it genuinely matters. */
    fun getHeatProtection(): String = prefs.getString("heat_protection", "minimal") ?: "minimal"

    fun setHeatProtection(level: String) {
        prefs.edit().putString("heat_protection", level).apply()
    }

    /** PowerManager thermal status (0..6) at/above which a task is stopped.
     *  minimal=5 EMERGENCY (about to self-protect from damage), medium=4 CRITICAL,
     *  high=3 SEVERE (the old, over-eager behavior). */
    fun getThermalCutoff(): Int = when (getHeatProtection()) {
        "high" -> 3
        "medium" -> 4
        else -> 5
    }

    /** Allow normally-restricted, potentially destructive actions (closing the
     *  user's browser tabs/windows, altering or deleting files). Default OFF. */
    fun isRiskyActionsAllowed(): Boolean = prefs.getBoolean("risky_actions", false)

    fun setRiskyActionsAllowed(on: Boolean) {
        prefs.edit().putBoolean("risky_actions", on).apply()
    }

    /** Auto-decline incoming phone calls (call screening). Default OFF so the user
     *  never silently misses a call unless they opt in. */
    fun isAutoDeclineCalls(): Boolean = prefs.getBoolean("auto_decline_calls", false)

    fun setAutoDeclineCalls(on: Boolean) {
        prefs.edit().putBoolean("auto_decline_calls", on).apply()
    }

    /** Require device auth (fingerprint / PIN) to activate the agent after a period of
     *  inactivity. OFF by default (annoying while testing); SHOULD default ON if ever
     *  distributed. Guards against unauthorized activation / prompt-injection misuse. */
    fun isBiometricRequired(): Boolean = prefs.getBoolean("biometric_required", false)

    fun setBiometricRequired(on: Boolean) {
        prefs.edit().putBoolean("biometric_required", on).apply()
    }

    /** Minutes of inactivity after which activation re-prompts for auth (default 10). */
    fun getReauthMinutes(): Int = prefs.getInt("reauth_minutes", 10)

    fun setReauthMinutes(m: Int) {
        prefs.edit().putInt("reauth_minutes", m).apply()
    }

    fun getLastAuthMs(): Long = prefs.getLong("last_auth_ms", 0L)
    fun setLastAuthMs(t: Long) { prefs.edit().putLong("last_auth_ms", t).apply() }

    /** True if auth is required and the last successful auth is older than the window. */
    fun needsReauth(): Boolean {
        if (!isBiometricRequired()) return false
        return System.currentTimeMillis() - getLastAuthMs() > getReauthMinutes() * 60_000L
    }

    /** Agent pacing. "balanced" (default) matches the tested behavior; "fast" is
     *  snappier with less settle time; "careful" waits longer on slow screens. */
    fun getSpeed(): String = prefs.getString("speed", "balanced") ?: "balanced"

    fun setSpeed(s: String) {
        prefs.edit().putString("speed", s).apply()
    }

    /** Inter-step settle delay (ms) derived from the speed setting. Kept short so
     *  a confirmed action fires almost immediately; the loop re-observes each step
     *  and stall-detection catches a screen that hadn't settled yet. */
    fun getStepDelayMs(): Long = when (getSpeed()) {
        "fast" -> 250L
        "careful" -> 1200L
        else -> 550L
    }

    /** Whether the one-time first-run welcome (offer to scan the phone for navigation) has
     *  been shown. We only ask once, and only ACT on it with the owner's explicit yes. */
    fun isFirstRunDone(): Boolean = prefs.getBoolean("first_run_done", false)

    fun setFirstRunDone(done: Boolean) {
        prefs.edit().putBoolean("first_run_done", done).apply()
    }

    /** Whether the owner pressed "Don't show again" on the startup "How it works" intro. When true
     *  the intro no longer pops up on launch; it's still reachable under Settings - How it works. */
    fun isIntroHidden(): Boolean = prefs.getBoolean("intro_hidden", false)

    fun setIntroHidden(hidden: Boolean) {
        prefs.edit().putBoolean("intro_hidden", hidden).apply()
    }

    /** Speech recognition for the spoken COMMAND (after the wake word). "ondevice" (default, PRIVATE -
     *  nothing leaves the phone) uses Android's on-device recognizer; "cloud" uses Google's network
     *  recognizer (more accurate, but sends the spoken command off the device). The wake word itself is
     *  ALWAYS the local Vosk listener, either way. Chosen once on first run, changeable in Settings. */
    fun getSpeechMode(): String = prefs.getString("speech_mode", "ondevice") ?: "ondevice"
    fun setSpeechMode(mode: String) { prefs.edit().putString("speech_mode", mode).apply() }
    fun isCloudSpeech(): Boolean = getSpeechMode() == "cloud"

    /** Whether the one-time first-run speech-source choice (on-device vs cloud) has been made. */
    fun isSpeechChoiceMade(): Boolean = prefs.getBoolean("speech_choice_made", false)
    fun setSpeechChoiceMade(done: Boolean) { prefs.edit().putBoolean("speech_choice_made", done).apply() }

    /** DATA FLYWHEEL: capture each decided step (perceived screen + chosen action + outcome) to a LOCAL
     *  file, to build an eval set / fine-tune an action model later. Stays on the device; captured only
     *  during owner-initiated tasks. On by default so the dataset accrues; clear it from Settings. */
    fun isDataCaptureEnabled(): Boolean = prefs.getBoolean("data_capture", true)
    fun setDataCaptureEnabled(on: Boolean) { prefs.edit().putBoolean("data_capture", on).apply() }

    /** Passive learning: watch how the OWNER navigates (taps + app switches) and record compact
     *  navigation facts into memory. OFF by default - it widens accessibility monitoring and
     *  costs some battery, so it's an explicit opt-in. No model inference runs while watching. */
    fun isPassiveLearningEnabled(): Boolean = prefs.getBoolean("passive_learning", false)

    fun setPassiveLearningEnabled(on: Boolean) {
        prefs.edit().putBoolean("passive_learning", on).apply()
    }
}

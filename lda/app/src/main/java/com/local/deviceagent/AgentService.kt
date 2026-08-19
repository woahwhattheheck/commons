package com.local.deviceagent

import android.app.NotificationManager
import android.app.SearchManager
import android.app.Service
import android.content.Intent
import android.media.AudioManager
import android.media.ToneGenerator
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.speech.tts.Voice
import org.json.JSONObject
import org.vosk.Model
import org.vosk.Recognizer
import org.vosk.android.RecognitionListener
import org.vosk.android.SpeechService
import java.util.Locale
import kotlin.concurrent.thread

/**
 * Foreground service that owns the microphone (via Vosk) and TTS.
 *
 * A single always-on, offline Vosk recognizer does triple duty with no system
 * earcons:
 *  - IDLE: listen for the wake word ("hey agent") → capture a command.
 *  - CAPTURING: the next utterance is taken as the spoken command. The floating
 *    button (ACTION_LISTEN_NOW) jumps straight here, so push-to-speak and
 *    hands-free share one path.
 *  - BUSY: while a task runs, listen for "stop"/"cancel" so a shouted "stop"
 *    halts the agent immediately (checked on partial results for speed).
 *
 * Vosk is paused whenever the agent speaks so it never transcribes its own
 * voice (no self-triggering).
 */
class AgentService : Service(), TextToSpeech.OnInitListener, RecognitionListener {

    companion object {
        const val ACTION_STOP = "com.local.deviceagent.STOP"
        const val ACTION_STOP_TASK = "com.local.deviceagent.STOP_TASK"
        const val ACTION_RESUME = "com.local.deviceagent.RESUME"
        const val ACTION_LISTEN_NOW = "com.local.deviceagent.LISTEN_NOW"
        const val ACTION_CONVERSATION = "com.local.deviceagent.CONVERSATION"
        const val ACTION_RUN_COMMAND = "com.local.deviceagent.RUN_COMMAND"
        const val ACTION_TRAIN_START = "com.local.deviceagent.TRAIN_START"
        const val ACTION_TRAIN_FINISH = "com.local.deviceagent.TRAIN_FINISH"
        const val ACTION_LEARN_MODE = "com.local.deviceagent.LEARN_MODE"
        const val EXTRA_COMMAND = "command"
        const val EXTRA_GOAL = "goal"
        const val EXTRA_FROM_CHAT = "from_chat"

        private const val SAMPLE_RATE = 16000.0f
        private const val CAPTURE_TIMEOUT_MS = 10000L
        private const val TTS_PAUSE_SAFETY_MS = 12000L
        private const val ANSWER_TIMEOUT_MS = 30000L
        // At/under this battery %, the agent refuses to run / shuts down — a hard
        // failsafe so it can never drain a nearly-dead phone. CRITICAL applies even while
        // charging; LOW_BATTERY_FLOOR is the higher floor when UNPLUGGED (GPU inference drains
        // fast and can die mid-task, so we don't even start a heavy task on a near-dead battery).
        private const val CRITICAL_BATTERY = 3
        private const val LOW_BATTERY_FLOOR = 5
        // Free the model this long after the agent goes IDLE (task done / chat walked-away), so RAM is
        // light when you're not using it. STRICTLY idle-only: it's cancelled the instant a task starts
        // and can't fire mid-task or mid-inference (see idleRelease's guard), so it never reaps a
        // working agent - it's housekeeping once the work is genuinely over, not a clock that kills it.
        private const val IDLE_RELEASE_MS = 30_000L

        @Volatile var isAgentBusy = false

        // Set while the service is alive so other UI (the Train screen) can reuse the ONE
        // model-backed brain instead of loading a second copy of the model into RAM.
        @Volatile var instance: AgentService? = null
    }

    /** The shared brain, or null if the model/service isn't up yet. */
    fun brainOrNull(): AgentBrain? = if (::brain.isInitialized) brain else null

    // Frees the model once the agent is genuinely IDLE so RAM is light when you're not using it. The
    // guard is the whole point: it unloads ONLY when no task is running, we're idle, AND no decision is
    // mid-inference - so it can never reap a working agent (the mid-task unload the owner hit). During a
    // task it's cancelled outright (acquireWakeLock); a real memory emergency is handled by onTrimMemory.
    private val idleRelease = Runnable {
        if (!isAgentBusy && mode == Mode.IDLE && brainOrNull()?.isGenerating() != true) brainOrNull()?.let {
            it.close()
            AgentLog.log("model", "released the model after going idle to keep RAM light (reloads instantly on next use)")
        }
    }

    /** Warm the model up so the first reply isn't the cold-start wait, and (re)arm the idle release so
     *  it frees once you're done. Called from the chat screen on open and on each message: each call
     *  pushes the release out, so the model stays warm while you're actively chatting and frees ~30s
     *  after you walk away. */
    fun warmBrain() {
        if (::brain.isInitialized) brain.prewarm()
        handler.removeCallbacks(idleRelease)
        handler.postDelayed(idleRelease, IDLE_RELEASE_MS)
    }

    private enum class Mode { LOADING, IDLE, CAPTURING, BUSY }

    private lateinit var tts: TextToSpeech
    private lateinit var settings: SettingsManager
    private lateinit var brain: AgentBrain
    private lateinit var orchestrator: AgentOrchestrator
    private val handler = Handler(Looper.getMainLooper())
    private val confirmationOverlay = ConfirmationOverlay()
    private val inputOverlay = InputOverlay()   // typed-answer popup for the agent's questions
    private val wakeLock by lazy {
        (getSystemService(POWER_SERVICE) as PowerManager)
            .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "agent:task")
    }

    private var model: Model? = null
    private var recognizer: Recognizer? = null
    private var speechService: SpeechService? = null
    @Volatile private var loading = false

    private var ttsReady = false
    private var defaultVoice: Voice? = null
    private var maleVoice: Voice? = null
    private var maleVoiceSearched = false
    @Volatile private var ttsSpeaking = false
    private var mode = Mode.LOADING
    private var lastObjective = ""
    private var awaitingAnswer = false
    private var awaitingFollowUp = false
    // Conversation mode: the next spoken command should run as a continuous back-and-forth.
    private var pendingContinuous = false
    // True while running a task the owner launched from the text-chat screen, so when it ends we
    // return to the chat and ask for further instructions instead of just going idle.
    private var taskFromChat = false
    // The most recent task that ended WITHOUT finishing. The agent never silently re-attempts it -
    // it asks first (in the return-to-chat summary), and only the owner's explicit "yes / continue"
    // resumes it. Cleared once resumed, declined, or superseded by a different command.
    private var lastUnfinishedTask = ""
    // What the owner is currently teaching by demonstration (from the floating Train flow).
    private var trainingGoal = ""

    private val cancelWords = listOf("stop", "cancel", "abort", "halt")
    private val captureTimeout = Runnable { if (mode == Mode.CAPTURING) goIdle() }
    private val resumeListeningRunnable = Runnable { resumeListening() }
    private val answerTimeout = Runnable {
        if (awaitingAnswer) stopCurrentTask("I didn't catch an answer, so I'll stop for now.")
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
        settings = SettingsManager(this)
        AgentLog.init(applicationContext)
        AgentMemory.pruneJunkObservations(applicationContext)   // auto-clean junk the owner shouldn't have to delete
        NotificationHelper.createChannel(this)
        startForeground(
            NotificationHelper.SERVICE_NOTIFICATION_ID,
            NotificationHelper.buildNotification(this, "Starting…", false)
        )

        tts = TextToSpeech(this, this)

        brain = AgentBrain(applicationContext)
        orchestrator = AgentOrchestrator(
            brain = brain,
            speak = { text -> speak(text) },
            onComplete = { success, doneSay ->
                isAgentBusy = false
                releaseWakeLock()
                AgentLog.log("diag", "end :: ${DeviceStats.snapshot(applicationContext)}")
                if (lastObjective.isNotBlank())
                    TaskHistory.add(applicationContext, lastObjective, if (success) "finished" else "stopped",
                        plan = orchestrator.lastPlan(), steps = orchestrator.lastSteps())
                // Remember an UNFINISHED task so we can offer to resume it - but only ever with the
                // owner's say-so (never silently). A clean finish clears any pending resume.
                lastUnfinishedTask = if (!success && lastObjective.isNotBlank())
                    lastObjective.lineSequence().first().trim() else ""
                val fromChat = taskFromChat; taskFromChat = false
                if (fromChat) {
                    // Task was launched from the text chat: post a real SUMMARY (what happened + any
                    // files/logins it created), then bring the chat back for the next instruction.
                    ChatStore.add(applicationContext, "agent", buildChatOutcome(success, doneSay))
                    try {
                        startActivity(Intent(this, ChatActivity::class.java)
                            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_REORDER_TO_FRONT))
                    } catch (_: Exception) {}
                    goIdle()
                } else if (success) completeAndOfferMore(doneSay) else goIdle()
            },
            // Last-resort fallback ONLY when the agent is genuinely stuck - not a default crutch.
            onStuck = { obj -> tryDeterministic(obj) },
            onAsk = { q -> handler.post { askUser(q) } },
            stepDelay = { settings.getStepDelayMs() },
            onStatus = { s -> handler.post { if (isAgentBusy) { updateNotification(s, false); speakStatus(s) } } },
            safetyCheck = { deviceSafetyReason() },
            confirm = { message, onYes, onNo ->
                handler.post {
                    speak(message)
                    updateNotification("Waiting for your confirmation…", false)
                    confirmationOverlay.show(
                        this, message,
                        onYes = { confirmationOverlay.dismiss(); onYes() },
                        onNo = { confirmationOverlay.dismiss(); onNo() }
                    )
                }
            }
        )

        startVoicePipeline()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> { stopSelf(); return START_NOT_STICKY }
            ACTION_STOP_TASK -> stopCurrentTask()
            ACTION_RESUME -> goIdle()
            ACTION_LISTEN_NOW -> { if (!gateActivation(ACTION_LISTEN_NOW, null)) onListenNow() }
            ACTION_CONVERSATION -> {
                // Like verbal input, but the spoken command runs as a continuous back-and-forth.
                pendingContinuous = true
                if (!gateActivation(ACTION_LISTEN_NOW, null)) onListenNow()
            }
            ACTION_RUN_COMMAND -> {
                val cmd = intent.getStringExtra(EXTRA_COMMAND).orEmpty()
                if (cmd.isNotBlank() && !gateActivation(ACTION_RUN_COMMAND, cmd)) {
                    taskFromChat = intent.getBooleanExtra(EXTRA_FROM_CHAT, false)
                    runCommand(cmd)
                }
            }
            ACTION_TRAIN_START -> startTraining(intent.getStringExtra(EXTRA_GOAL).orEmpty())
            ACTION_TRAIN_FINISH -> finishTraining()
            ACTION_LEARN_MODE -> { if (!gateActivation(ACTION_LEARN_MODE, null)) startLearnMode() }
        }
        return START_STICKY
    }

    /** If the owner requires auth and the inactivity window lapsed, bounce activation
     *  through [AuthGateActivity] (which re-dispatches on success). Returns true if it
     *  intercepted (caller should stop). No-op when the security toggle is off. */
    private fun gateActivation(action: String, command: String?): Boolean {
        if (!settings.needsReauth()) return false
        val i = Intent(this, AuthGateActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            .putExtra(AuthGateActivity.EXTRA_PENDING_ACTION, action)
        command?.let { i.putExtra(AuthGateActivity.EXTRA_PENDING_COMMAND, it) }
        try { startActivity(i) } catch (_: Exception) { return false }
        return true
    }

    // --- Vosk voice pipeline ----------------------------------------------

    private fun startVoicePipeline() {
        if (loading || speechService != null) return
        loading = true
        mode = Mode.LOADING
        updateNotification("Preparing voice model…", false)
        thread(name = "vosk-load") {
            try {
                val m = VoskModelManager.loadModel(this) { msg ->
                    handler.post { if (mode == Mode.LOADING) updateNotification(msg, false) }
                }
                handler.post { loading = false; onModelReady(m) }
            } catch (e: Exception) {
                handler.post {
                    loading = false
                    updateNotification("Voice model unavailable — tap the mic to retry.", false)
                }
            }
        }
    }

    private fun onModelReady(m: Model) {
        model = m
        try {
            // Rebuilds on every SpeechRecognizer capture window too, so release the previous Vosk
            // recognizer/mic first to avoid leaking AudioRecords across captures.
            speechService?.let { try { it.stop() } catch (_: Exception) {}; it.shutdown() }
            recognizer?.close()
            val rec = Recognizer(m, SAMPLE_RATE)
            recognizer = rec
            speechService = SpeechService(rec, SAMPLE_RATE).also { it.startListening(this) }
            goIdle()
        } catch (e: Exception) {
            updateNotification("Microphone unavailable.", false)
        }
    }

    /** Stop feeding the mic to Vosk while we speak; resume when done. */
    private fun pauseListening() {
        speechService?.setPause(true)
    }

    private fun resumeListening() {
        speechService?.setPause(false)
    }

    // --- TTS --------------------------------------------------------------

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            val r = tts.setLanguage(Locale.getDefault())
            ttsReady = r != TextToSpeech.LANG_MISSING_DATA && r != TextToSpeech.LANG_NOT_SUPPORTED
            if (ttsReady) defaultVoice = tts.voice
            tts.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) {
                    ttsSpeaking = true
                    handler.post { pauseListening() }
                }
                override fun onDone(utteranceId: String?) { handler.post { onSpeechFinished() } }
                @Deprecated("deprecated") override fun onError(utteranceId: String?) {
                    handler.post { onSpeechFinished() }
                }
                override fun onError(utteranceId: String?, errorCode: Int) {
                    handler.post { onSpeechFinished() }
                }
            })
        }
    }

    private fun onSpeechFinished() {
        ttsSpeaking = false
        handler.removeCallbacks(resumeListeningRunnable)
        // Reset so the tail of our own speech isn't carried into the next utterance.
        recognizer?.reset()
        resumeListening()
    }

    private var lastSpoken = ""
    private var lastSpokenAt = 0L

    // Owner wants RUN-mode tasks to give a VERBAL cue, not just the on-screen status. We speak the
    // meaningful "thinking/planning/re-orienting" beats - but only when the status TEXT changes, so a
    // long run of "Thinking…" says it once rather than chattering. Reset each task so it speaks again.
    private var lastStatusSpoken = ""
    private fun speakStatus(s: String) {
        val clean = s.trim().trimEnd('…', '.', ' ')
        val low = clean.lowercase()
        if (!(low.contains("think") || low.contains("planning") || low.contains("orient") ||
              low.contains("rethink") || low.contains("waiting for the reply"))) return
        if (clean.equals(lastStatusSpoken, ignoreCase = true)) return
        lastStatusSpoken = clean
        speak(clean)
    }

    fun speak(text: String) {
        if (!ttsReady || settings.isSilent()) return
        val t = text.trim()
        // Never read internal diagnostics aloud (this is the "...it only said 'status'..." bug:
        // an engine error string like "Status Code: 3. Message: Input token ids are too long"
        // was being spoken, then QUEUE_FLUSH cut it to the first word each step). Drop those, and
        // de-dupe the same line repeated within a few seconds so it can't stutter.
        if (t.isBlank()) return
        val low = t.lowercase()
        if (low.startsWith("status code") || low.contains("token ids") ||
            low.contains("exceeding the maximum") || low.contains("backend$") || low.contains("litertlm")) return
        val now = System.currentTimeMillis()
        if (t == lastSpoken && now - lastSpokenAt < 6000) return
        lastSpoken = t; lastSpokenAt = now
        applyVoicePrefs()
        ttsSpeaking = true
        pauseListening()
        // Safety net: never stay paused if an utterance callback is missed.
        handler.removeCallbacks(resumeListeningRunnable)
        handler.postDelayed(resumeListeningRunnable, TTS_PAUSE_SAFETY_MS)
        tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "agent")
    }

    /** Pick a real male voice when requested+available; else deepen pitch as fallback. */
    private fun applyVoicePrefs() {
        if (settings.isMaleVoice()) {
            if (!maleVoiceSearched) { maleVoice = findMaleVoice(); maleVoiceSearched = true }
            val v = maleVoice
            if (v != null) {
                try { tts.voice = v } catch (_: Exception) {}
                tts.setPitch(0.92f) // a touch deeper still, for a clearer masculine tone
            } else {
                // No identifiable male voice installed - deepen the pitch noticeably so
                // it at least reads as masculine (0.8 was too subtle to tell apart).
                tts.setPitch(0.7f)
            }
        } else {
            defaultVoice?.let { try { tts.voice = it } catch (_: Exception) {} }
            tts.setPitch(1.0f)
        }
    }

    /**
     * Best-effort male-voice finder. TTS exposes no gender field, and real engines
     * (Google, Samsung) don't put "male" in voice names - they use opaque ids like
     * `en-us-x-iom-local`. So: match an explicit "male" name first, then fall back
     * to known male id fragments for the current language. Voice names are logged
     * once so we can see what a given device actually offers.
     */
    private fun findMaleVoice(): Voice? {
        val lang = Locale.getDefault().language
        val voices = try { tts.voices } catch (_: Exception) { null } ?: return null
        val forLang = voices.filter { it.locale?.language == lang && it.name != null }
        AgentLog.log("voice", "available(${lang}): " +
            forLang.joinToString(", ") { it.name }.take(300))

        forLang.firstOrNull {
            it.name.contains("male", ignoreCase = true) &&
                !it.name.contains("female", ignoreCase = true)
        }?.let { AgentLog.log("voice", "male by name: ${it.name}"); return it }

        // Known male voice id fragments (Google TTS network/local voices, etc.).
        val maleFragments = listOf("iom", "iol", "tpc", "tpd", "-male", "_male", "#male")
        forLang.firstOrNull { v -> maleFragments.any { v.name.contains(it, ignoreCase = true) } }
            ?.let { AgentLog.log("voice", "male by id: ${it.name}"); return it }

        AgentLog.log("voice", "no male voice found; using deepened pitch")
        return null
    }

    /** Short non-verbal "I'm listening" tone - snappier than speaking "Yes?". */
    private fun playListeningCue() {
        try {
            val tg = ToneGenerator(AudioManager.STREAM_MUSIC, 70)
            tg.startTone(ToneGenerator.TONE_PROP_BEEP, 150)
            handler.postDelayed({ try { tg.release() } catch (_: Exception) {} }, 350)
        } catch (_: Exception) {}
    }

    // --- activation -------------------------------------------------------

    /** Floating-button tap when idle: capture a command without the wake word. */
    private fun onListenNow() {
        if (speechService == null) { startVoicePipeline(); return }
        if (isAgentBusy) return
        beginCapture()
    }

    private fun beginCapture() {
        // Hand the COMMAND to Android's SpeechRecognizer (far better than Vosk at free-form dictation -
        // Vosk's mishears are why normalizeHeard/wakeVariants exist). Fall back to the Vosk capture path
        // if SpeechRecognizer isn't available on this device. The wake word stays on Vosk regardless.
        if (srAvailable()) captureWithSpeechRecognizer() else beginCaptureVosk()
    }

    private fun beginCaptureVosk() {
        mode = Mode.CAPTURING
        taskFromChat = false   // a spoken command isn't a chat-initiated task
        if (!settings.isSilent()) playListeningCue()
        updateNotification("Listening… speak your command.", false)
        handler.removeCallbacks(captureTimeout)
        handler.postDelayed(captureTimeout, CAPTURE_TIMEOUT_MS)
    }

    // --- High-accuracy command capture (Android SpeechRecognizer) ----------
    // The always-on wake word stays on local Vosk (low-profile). Once it fires - or the mic button is
    // tapped - we hand the COMMAND to Android's SpeechRecognizer: on-device by default (PREFER_OFFLINE,
    // nothing leaves the phone), or the cloud recognizer if the owner opted in (more accurate, off-device)
    // via the first-run choice / Settings. Vosk and SpeechRecognizer can't share the mic, so we STOP Vosk
    // for the capture window and rebuild it after - they never hold the mic at the same time.
    private var sr: SpeechRecognizer? = null

    private fun srAvailable(): Boolean =
        try { SpeechRecognizer.isRecognitionAvailable(this) } catch (_: Exception) { false }

    private fun captureWithSpeechRecognizer() {
        mode = Mode.CAPTURING
        taskFromChat = false
        if (!settings.isSilent()) playListeningCue()
        updateNotification("Listening… speak your command.", false)
        // Free the mic from Vosk for the capture window (stop, don't pause - SR needs the mic exclusively).
        try { speechService?.stop() } catch (_: Exception) {}
        speechService = null
        val cloud = settings.isCloudSpeech()
        val rec = try {
            if (!cloud && android.os.Build.VERSION.SDK_INT >= 33 &&
                SpeechRecognizer.isOnDeviceRecognitionAvailable(this))
                SpeechRecognizer.createOnDeviceSpeechRecognizer(this)
            else SpeechRecognizer.createSpeechRecognizer(this)
        } catch (_: Exception) { null }
        if (rec == null) { resumeVoskListening(); beginCaptureVosk(); return }
        sr = rec
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault().toString())
            // PRIVACY: on-device mode must NEVER reach the network. Cloud mode (owner opt-in) allows it.
            putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, !cloud)
        }
        rec.setRecognitionListener(object : android.speech.RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {}
            override fun onBeginningOfSpeech() {}
            override fun onRmsChanged(rmsdB: Float) {}
            override fun onBufferReceived(buffer: ByteArray?) {}
            override fun onEndOfSpeech() {}
            override fun onEvent(eventType: Int, params: Bundle?) {}
            override fun onPartialResults(partialResults: Bundle?) {}
            override fun onError(error: Int) { handler.post { finishSrCapture(null) } }
            override fun onResults(results: Bundle?) {
                val spoken = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    ?.firstOrNull().orEmpty()
                handler.post { finishSrCapture(spoken.ifBlank { null }) }
            }
        })
        try { rec.startListening(intent) } catch (_: Exception) { finishSrCapture(null) }
    }

    private fun finishSrCapture(spoken: String?) {
        try { sr?.destroy() } catch (_: Exception) {}
        sr = null
        resumeVoskListening()   // wake word + cancel-listening back online (this also goIdle()s)
        if (!spoken.isNullOrBlank()) {
            AgentLog.log("speech", "command via ${if (settings.isCloudSpeech()) "cloud" else "on-device"} recognizer")
            if (awaitingFollowUp) {
                awaitingFollowUp = false
                if (isNegative(spoken)) { speak("Okay.") } else runCommand(spoken)
            } else runCommand(spoken)
        }
        // No speech / error -> resumeVoskListening already returned us to idle.
    }

    /** Rebuild the Vosk recognizer+mic after a SpeechRecognizer capture window (the model stays loaded,
     *  so this is cheap). onModelReady() ends in goIdle(), so a no-result capture lands back at idle. */
    private fun resumeVoskListening() {
        val m = model
        if (m != null) onModelReady(m) else startVoicePipeline()
    }

    private fun goIdle() {
        handler.removeCallbacks(captureTimeout)
        handler.removeCallbacks(answerTimeout)
        awaitingAnswer = false
        awaitingFollowUp = false
        inputOverlay.dismiss()
        if (isAgentBusy) { mode = Mode.BUSY; return }
        // We're truly idle now, so this command is done: clear the chat-origin flag so it can't
        // leak onto the NEXT task (a deterministic chat command used to leave it set, which made a
        // later non-chat task wrongly post a summary + jump to the chat). The orchestrated path
        // already consumed it in onComplete before reaching here.
        taskFromChat = false
        ActionAccessibilityService.instance?.exploreOnly = false  // Learn mode's hard block is per-task
        mode = Mode.IDLE
        updateNotification("Listening for "${settings.getTriggerWord()}" — or tap the mic.", false)
        // The task is genuinely over -> arm the idle release so RAM goes light. A quick follow-up
        // within the grace window still reuses the warm model; a real emergency frees it via onTrimMemory.
        handler.removeCallbacks(idleRelease)
        handler.postDelayed(idleRelease, IDLE_RELEASE_MS)
    }

    /**
     * The agent asked a clarifying question. Speak it, then listen for the spoken
     * answer - the whole next utterance is taken as the answer (no wake word
     * needed). The orchestrator stays paused until provideAnswer is called, here
     * on the answer or, if none comes, on a timeout that stops the task.
     */
    private fun askUser(question: String) {
        if (!isAgentBusy) return
        awaitingAnswer = true
        mode = Mode.BUSY
        AgentLog.log("ask", question)
        updateNotification("Asked: $question", false)
        speak(question)
        // Owner: clarifying questions (especially data-task parameters - age/sex/criteria) should offer
        // an on-screen TEXT FIELD, not just voice. Show a typed-answer popup over the task; voice still
        // works too, and whichever answers first wins.
        inputOverlay.show(this, question,
            onSubmit = { typed -> deliverAnswer(typed) },
            onCancel = { /* keep waiting - voice and the timeout are still active */ })
        handler.removeCallbacks(answerTimeout)
        handler.postDelayed(answerTimeout, ANSWER_TIMEOUT_MS)
    }

    /** Hand a TYPED answer (from the input popup) back to the paused task - the same path the spoken
     *  answer takes. Guarded so a late tap can't double-answer once voice already replied. */
    private fun deliverAnswer(text: String) {
        if (!awaitingAnswer) return
        awaitingAnswer = false
        handler.removeCallbacks(answerTimeout)
        inputOverlay.dismiss()
        AgentLog.log("cmd", "typed answer: ${text.take(80)}")
        orchestrator.provideAnswer(text)
        updateNotification("Working on: $lastObjective", false)
    }

    /** Compose the return-to-chat SUMMARY: what happened, anything the agent CREATED (files it
     *  saved, logins it recorded), and - if it didn't finish - an explicit offer to resume (the
     *  owner must say yes; we never silently re-attempt). Grounded in real outcome data only. */
    private fun buildChatOutcome(success: Boolean, doneSay: String?): String {
        val artifacts = ActionAccessibilityService.instance?.createdArtifacts?.toList().orEmpty()
        val created = if (artifacts.isEmpty()) "" else
            "\n\nHere's what I saved for you:\n" + artifacts.joinToString("\n") { "• $it" }
        return if (success) {
            val tail = doneSay?.trim()?.takeIf { it.isNotBlank() }?.let { " — $it" } ?: "."
            "Done$tail$created\n\nWhat next?"
        } else {
            val task = lastUnfinishedTask.take(80)
            val far = orchestrator.lastProgress().takeIf { it.isNotBlank() }
                ?.let { "\n\nHow far I got: ${it.take(200)}" } ?: ""
            "I stopped before finishing \"$task\".$far$created\n\nWant me to pick it back up? Say " +
                "\"yes\" or \"continue\" to resume — or just tell me what to do instead."
        }
    }

    /** A short "yes / continue / resume" answer to the resume offer (≤4 words so a real new command
     *  is never mistaken for one). Only matters right after an unfinished task. */
    private fun isResumeAffirmation(text: String): Boolean {
        val l = text.lowercase().trim().trim('.', '!', ',', ' ')
        if (l.isBlank() || l.split(Regex("\\s+")).size > 4) return false
        return l in setOf(
            "yes", "yeah", "yep", "yup", "sure", "ok", "okay", "please", "please do", "yes please",
            "do it", "go ahead", "go for it", "continue", "continue it", "resume", "resume it",
            "keep going", "finish it", "finish that", "pick it back up", "pick it up", "carry on",
            "go on", "yes continue", "yes resume")
    }

    /** Announce completion and listen for a follow-up command (or "no"). */
    private fun completeAndOfferMore(doneSay: String?) {
        val base = doneSay?.trim().takeUnless { it.isNullOrBlank() } ?: "Task complete"
        awaitingFollowUp = true
        mode = Mode.CAPTURING
        handler.removeCallbacks(captureTimeout)
        handler.postDelayed(captureTimeout, CAPTURE_TIMEOUT_MS)
        updateNotification("Done — anything else?", false)
        speak("$base. Anything else?")
    }

    private fun isNegative(text: String): Boolean {
        val l = text.lowercase().trim().trim('.', '!', ' ')
        return l in setOf(
            "no", "nope", "nah", "no thanks", "no thank you", "nothing", "that's all",
            "thats all", "that is all", "i'm good", "im good", "we're good", "all good",
            "no that's all", "that'll be all", "im done", "i'm done"
        )
    }

    private fun acquireWakeLock() {
        handler.removeCallbacks(idleRelease)   // a task is starting - never let the idle release fire now
        try { if (!wakeLock.isHeld) wakeLock.acquire(10 * 60 * 1000L) } catch (_: Exception) {}
    }

    private fun releaseWakeLock() {
        try { if (wakeLock.isHeld) wakeLock.release() } catch (_: Exception) {}
    }

    /** Reason to refuse/abort a task for device safety (low battery / overheating), or null. */
    private fun deviceSafetyReason(): String? {
        val pct = DeviceStats.batteryPercent(applicationContext)
        // More headroom when UNPLUGGED (a near-dead battery drains fast under GPU inference and can
        // die mid-task); an absolute floor even while charging.
        val charging = DeviceStats.isCharging(applicationContext)
        val floor = if (charging) CRITICAL_BATTERY else LOW_BATTERY_FLOOR
        if (pct in 0..floor)
            return "Battery is at $pct percent" + (if (charging) "" else " and not charging") +
                ", so I won't run a task right now — plug in and try again."
        // Heat cutoff is user-configurable (Settings → Heat protection). Default is
        // "minimal": only stop when the phone is critically hot enough to risk damage.
        if (DeviceStats.thermalStatus(applicationContext) >= settings.getThermalCutoff())
            return "Your phone is getting too hot, so I'm stopping to let it cool down."
        return null
    }

    // --- Vosk RecognitionListener ----------------------------------------

    override fun onPartialResult(hypothesis: String?) {
        if (ttsSpeaking) return
        val partial = jsonField(hypothesis, "partial")
        if (partial.isBlank()) return
        handler.post { if (mode == Mode.BUSY && containsCancel(partial)) stopCurrentTask() }
    }

    override fun onResult(hypothesis: String?) {
        val text = jsonField(hypothesis, "text")
        if (text.isBlank() || ttsSpeaking) return
        handler.post { handleUtterance(text) }
    }

    override fun onFinalResult(hypothesis: String?) {}
    override fun onError(e: Exception?) {}
    override fun onTimeout() {}

    private fun handleUtterance(text: String) {
        when (mode) {
            Mode.BUSY -> {
                if (awaitingAnswer) {
                    awaitingAnswer = false
                    handler.removeCallbacks(answerTimeout)
                    inputOverlay.dismiss()   // a spoken answer closes the typed-answer popup
                    if (containsCancel(text) && text.split(" ").size <= 2) {
                        stopCurrentTask()
                    } else {
                        AgentLog.log("cmd", "answer: $text")
                        orchestrator.provideAnswer(text)
                        updateNotification("Working on: $lastObjective", false)
                    }
                    return
                }
                val after = afterWake(text)
                if (after != null) {
                    when {
                        after.isBlank() -> {}
                        containsCancel(after) && after.split(" ").size <= 3 -> stopCurrentTask()
                        else -> orchestrator.addCorrection(after)
                    }
                } else if (containsCancel(text)) stopCurrentTask()
                else maybeLogReaction(text)
            }
            Mode.CAPTURING -> {
                if (awaitingFollowUp) {
                    awaitingFollowUp = false
                    if (isNegative(text)) { speak("Okay."); goIdle() } else runCommand(text)
                } else runCommand(text)
            }
            Mode.IDLE -> {
                val after = afterWake(text)
                if (after != null) {
                    // ALWAYS play the indicator beep on wake (the owner's "that noise isn't playing"
                    // bug): it only fired in beginCapture (the "hey agent" ALONE path), so saying
                    // "hey agent do X" in one breath skipped it. beginCapture plays its own, so only
                    // beep here on the spoken-command path to avoid a double beep.
                    if (after.isNotBlank()) {
                        if (!settings.isSilent()) playListeningCue()
                        runCommand(after)
                    } else beginCapture()
                }
            }
            Mode.LOADING -> {}
        }
    }

    // Vosk mis-transcribes "hey agent" ("hey age", "hey aging", "hey a gent"...), so an EXACT match
    // almost never fired. We accept the common mishears - but EVERY variant must include a deliberate
    // address prefix ("hey"/"ok"/"okay"/"hay"). The bare word "agent" (and "a agent") were REMOVED:
    // they fired on any incidental mention, so the owner "couldn't even say his name around him"
    // (the wake word must be an address, not a topic word). A custom trigger is matched exactly.
    private val wakeVariants = listOf(
        "hey agent", "hey agents", "hay agent", "hey a gent", "hey a agent", "hey aging",
        "hey age and", "hey age", "ok agent", "okay agent", "okay agents", "ok agents")

    /** The command spoken AFTER the wake word, "" if the wake word was said with no command, or
     *  null if no wake word was heard. Fuzzy on the default "hey agent" so mishears still trigger. */
    private fun afterWake(text: String): String? {
        val l = text.lowercase()
        val trigger = settings.getTriggerWord().lowercase().trim()
        l.indexOf(trigger).let { if (it >= 0) return text.substring(it + trigger.length).trim(' ', ',', '.', ':', ';') }
        if (trigger == "hey agent") for (v in wakeVariants) {
            val i = l.indexOf(v)
            if (i >= 0) return text.substring(i + v.length).trim(' ', ',', '.', ':', ';')
        }
        return null
    }

    private fun jsonField(hypothesis: String?, key: String): String {
        if (hypothesis.isNullOrBlank()) return ""
        return try { JSONObject(hypothesis).optString(key).trim() } catch (_: Exception) { "" }
    }

    private fun containsCancel(text: String): Boolean {
        val l = text.lowercase()
        return cancelWords.any { l.contains(it) }
    }

    // Owner's affective feedback heard DURING a task (not a command/correction): specific enough
    // phrases that ambient chatter rarely trips them.
    private val frustrationWords = listOf("that's wrong", "thats wrong", "not that", "why are you",
        "what are you doing", "stop doing that", "don't do that", "dont do that", "you messed",
        "messed up", "that's not right", "thats not right", "come on agent", "ugh agent", "no no no")
    private val praiseWords = listOf("good job", "well done", "nice job", "great job", "perfect",
        "that's perfect", "thats perfect", "good agent", "nicely done", "good boy", "that's right agent")

    /** The owner reacted DURING a task (it wasn't a wake command or a cancel). Log the reaction tied to
     *  what the agent just did - the owner's "log my reaction" / praise. Conservative (specific phrases)
     *  and NON-disruptive: it never alters the running task, only records the signal for review/learning. */
    private fun maybeLogReaction(text: String) {
        val l = text.lowercase()
        val frustrated = frustrationWords.any { l.contains(it) }
        val pleased = praiseWords.any { l.contains(it) }
        val during = if (::orchestrator.isInitialized) orchestrator.lastAction() else "a task"
        when {
            frustrated -> AgentLog.log("react", "owner sounded FRUSTRATED: \"$text\" — just after: $during")
            pleased -> AgentLog.log("react", "owner PLEASED: \"$text\" — just after: $during")
        }
    }

    private fun isCapabilityQuery(command: String): Boolean {
        val l = command.lowercase()
        return l.contains("what can you do") || l.contains("what can i ask") ||
            l.contains("what can i say") || l.contains("what do you do") ||
            l == "help" || l == "help me"
    }

    /** The agent reflects on its recent run and writes a dev-change request to the log. */
    private fun isSelfReportQuery(command: String): Boolean {
        val l = command.lowercase()
        return l.contains("what do you need") || l.contains("what should i change") ||
            l.contains("dev report") || l.contains("self report") ||
            l.contains("what would help you") || l.contains("report what you need") ||
            l.contains("what's wrong with your code") || l.contains("whats wrong with your code")
    }

    private fun announceCapabilities() {
        AgentLog.log("cmd", "capabilities query")
        speak(
            "Say hey agent then a task. I can open apps, search the web, change " +
            "settings, type and send messages, and work through multi-step tasks. " +
            "Say stop any time."
        )
        goIdle()
    }

    /**
     * Deterministic shortcuts for the most common commands - reliable and instant,
     * bypassing the weak on-device model. Returns true if it handled the command.
     */
    private fun tryDeterministic(command: String): Boolean {
        // Memory: "remember (that) my <key> is <value>" and "what is my <key>".
        Regex("""remember(?:\s+that)?\s+(?:my\s+)?(.+?)\s+(?:is|are|=)\s+(.+)""", RegexOption.IGNORE_CASE)
            .find(command)?.let {
                val k = it.groupValues[1].trim(); val v = it.groupValues[2].trim().trimEnd('.', '!')
                if (k.isNotBlank() && v.isNotBlank()) {
                    AgentMemory.setFact(applicationContext, k, v)
                    AgentLog.log("mem", "remember $k = $v"); speak("Got it, I'll remember that."); return true
                }
            }
        Regex("""^what(?:'s| is)\s+my\s+(.+)""", RegexOption.IGNORE_CASE).find(command)?.let {
            val k = it.groupValues[1].trim().trimEnd('?', '.')
            AgentMemory.getFact(applicationContext, k)?.let { v -> speak("Your $k is $v."); return true }
        }
        if (Regex("""favou?rite song""", RegexOption.IGNORE_CASE).containsMatchIn(command)) {
            try {
                val am = getSystemService(AUDIO_SERVICE) as AudioManager
                am.setStreamVolume(AudioManager.STREAM_MUSIC, am.getStreamMaxVolume(AudioManager.STREAM_MUSIC), 0)
            } catch (_: Exception) {}
            openUri("https://www.youtube.com/results?search_query=" + Uri.encode("Special Place Bladee"))
            AgentLog.log("det", "favorite song"); return true
        }
        Regex("""^(?:search(?: the web| online| google)? for|google|look up|search)\s+(.+)""", RegexOption.IGNORE_CASE)
            .find(command)?.let {
                val q = it.groupValues[1].trim().trim('.', '?', '!')
                if (q.isNotBlank()) {
                    webSearch(q)
                    AgentLog.log("det", "web search: $q")
                    speak("Searching for $q.")
                    updateNotification("Searched the web: $q", false)
                    return true
                }
            }
        Regex("""^(?:open|launch|start)\s+(?:the\s+)?(.+?)(?:\s+app)?$""", RegexOption.IGNORE_CASE)
            .find(command)?.let {
                val name = it.groupValues[1].trim()
                if (name.isNotBlank() && !name.contains(" and ") && !name.contains(" then ") && launchApp(name)) {
                    AgentLog.log("det", "open app: $name")
                    speak("Opening $name.")
                    updateNotification("Opened $name", false)
                    return true
                }
            }
        Regex("""^(?:navigate to|directions to|take me to|maps? (?:to|of))\s+(.+)""", RegexOption.IGNORE_CASE)
            .find(command)?.let {
                val place = it.groupValues[1].trim().trim('.', '?', '!')
                if (place.isNotBlank()) {
                    openUri("geo:0,0?q=" + Uri.encode(place))
                    AgentLog.log("det", "maps: $place")
                    speak("Opening directions to $place.")
                    updateNotification("Maps: $place", false)
                    return true
                }
            }
        Regex("""^play\s+(.+?)\s+on\s+you\s?tube""", RegexOption.IGNORE_CASE)
            .find(command)?.let {
                val q = it.groupValues[1].trim()
                if (q.isNotBlank()) {
                    openUri("https://www.youtube.com/results?search_query=" + Uri.encode(q))
                    AgentLog.log("det", "youtube: $q")
                    speak("Searching YouTube for $q.")
                    updateNotification("YouTube: $q", false)
                    return true
                }
            }
        Regex("""(?:set|start)\s+(?:a\s+)?timer\s+(?:for\s+)?(\d+)\s*(sec|second|seconds|min|minute|minutes|hour|hours|hr)""", RegexOption.IGNORE_CASE)
            .find(command)?.let {
                val n = it.groupValues[1].toIntOrNull()
                if (n != null) {
                    val u = it.groupValues[2].lowercase()
                    val secs = when { u.startsWith("sec") -> n; u.startsWith("hour") || u == "hr" -> n * 3600; else -> n * 60 }
                    try {
                        startActivity(Intent(android.provider.AlarmClock.ACTION_SET_TIMER)
                            .putExtra(android.provider.AlarmClock.EXTRA_LENGTH, secs)
                            .putExtra(android.provider.AlarmClock.EXTRA_SKIP_UI, true)
                            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                        AgentLog.log("det", "timer ${secs}s"); speak("Timer set."); updateNotification("Timer set", false)
                        return true
                    } catch (_: Exception) {}
                }
            }
        Regex("""(?:call|dial)\s+([0-9][0-9\s\-()+]{4,})""", RegexOption.IGNORE_CASE)
            .find(command)?.let {
                val num = it.groupValues[1].filter { c -> c.isDigit() || c == '+' }
                if (num.length >= 4) {
                    // Open the dialer pre-filled (does NOT auto-place the call - safer).
                    openUri("tel:$num")
                    AgentLog.log("det", "dial $num"); speak("Opening the dialer."); updateNotification("Dial $num", false)
                    return true
                }
            }
        return false
    }

    private fun openUri(uri: String) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(uri)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        } catch (_: Exception) {}
    }

    private fun webSearch(query: String) {
        val attempts = listOf(
            Intent(Intent.ACTION_WEB_SEARCH).apply { putExtra(SearchManager.QUERY, query) },
            Intent(Intent.ACTION_VIEW, Uri.parse("https://www.google.com/search?q=" + Uri.encode(query)))
        )
        for (i in attempts) {
            try { startActivity(i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); return } catch (_: Exception) {}
        }
    }

    private fun launchApp(name: String): Boolean {
        val pm = packageManager
        // "Gemini" must be the standalone Gemini app, not the Assistant voice overlay.
        if (name.trim().lowercase() == "gemini")
            pm.getLaunchIntentForPackage("com.google.android.apps.bard")?.let {
                startActivity(it.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); return true
            }
        val main = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
        val cands = pm.queryIntentActivities(main, 0)
        val t = name.trim().lowercase()
        val labeled = cands.map { it to it.loadLabel(pm).toString() }
        val m = labeled.firstOrNull { it.second.lowercase() == t }
            ?: labeled.firstOrNull { it.second.lowercase().startsWith(t) }
            ?: labeled.firstOrNull { it.second.contains(name, ignoreCase = true) }
            ?: return false
        val launch = pm.getLaunchIntentForPackage(m.first.activityInfo.packageName) ?: return false
        startActivity(launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        return true
    }

    // --- commands ---------------------------------------------------------

    /** "Learn mode": the agent autonomously EXPLORES apps (safely) to build navigation memory so
     *  later tasks are faster/smarter. Routed through the normal command path so every safety gate
     *  applies (payment/install confirm, risky-actions-off, self-interaction-off); the word "explore"
     *  in the objective puts it in EXPLORER mode. Bounded to a handful of apps, and the owner can stop
     *  it anytime with the floating button. */
    private fun startLearnMode() {
        if (isAgentBusy) { speak("I'm already working on something - stop that first, then start Learn mode."); return }
        speak("Setting myself little practice goals to learn your apps. Tap the floating button to stop me.")
        runCommand(
            "LEARN MODE: teach YOURSELF to use this phone by setting your OWN simple, harmless, ONE-STEP " +
            "goals and completing them - do NOT just wander aimlessly. For each of about 5 DIFFERENT apps: " +
            "open it, then pick ONE concrete thing to LOCATE (e.g. 'where do I compose/create a new item?', " +
            "'where is search?', 'where are the settings?', 'how do I go back/switch tabs?'), and navigate " +
            "until you actually SEE it. When you find it, RECORD what you learned with a {\"action\":\"note\"} " +
            "in TWO forms: the SPECIFIC fact ('in <app>, compose is the + button bottom-right') AND the " +
            "GENERAL pattern it teaches ('compose is usually a + button bottom-right'). Then press home and " +
            "open a DIFFERENT app and set yourself a NEW little goal. This must be completely HARMLESS - ONLY " +
            "open, look, scroll, navigate, and press back/home. Do NOT type into fields, send, post, buy, " +
            "install, uninstall, log in or out, delete or move anything, close or force-stop apps, clear " +
            "data, or change ANY setting. If a screen asks you to confirm or permit something, just go back. " +
            "After about 5 apps with a goal met in each, finish."
        )
    }

    private fun runCommand(commandRaw: String) {
        // Resume gate (ask-before-resume): if a task was left unfinished we ALREADY asked whether to
        // pick it back up. Only an explicit "yes / continue" now resumes it; any other command means
        // the owner moved on, so we drop the pending resume and run what they actually said.
        val pendingResume = lastUnfinishedTask
        val effectiveRaw = if (pendingResume.isBlank()) commandRaw else {
            lastUnfinishedTask = ""
            if (isResumeAffirmation(commandRaw)) {
                AgentLog.log("cmd", "owner OK'd resuming the unfinished task")
                speak("Okay, picking that back up.")
                pendingResume
            } else commandRaw
        }
        // Vosk mis-transcribes common terms badly ("chat gp t", "why fi"); fix the
        // worst offenders deterministically before anything downstream uses the text.
        val command = normalizeHeard(effectiveRaw)
        // Consume the conversation-mode flag now, on every path, so it can't leak to a later
        // command if this one is handled deterministically or cancelled.
        val cont = pendingContinuous; pendingContinuous = false
        val trimmed = command.trim()
        // Only a bare "stop"/"cancel" cancels here - a real prompt may legitimately
        // contain the word (e.g. "don't stop until I say so") and must still run.
        if (trimmed.split(" ").size == 1 && containsCancel(trimmed)) { stopCurrentTask(); return }
        if (isCapabilityQuery(trimmed)) { announceCapabilities(); return }
        if (isSelfReportQuery(trimmed)) {
            AgentLog.log("cmd", command)
            speak("Okay, writing what I need into the debug log.")
            orchestrator.writeSelfReport { speak("Done. It's in the debug log for you to share.") }
            goIdle(); return
        }
        AgentLog.log("cmd", command)
        AgentLog.log("diag", "start :: ${DeviceStats.snapshot(applicationContext)}")
        deviceSafetyReason()?.let { reason ->
            AgentLog.log("safety", "refused at start: $reason")
            speak(reason); goIdle(); return
        }
        // Handle simple, unambiguous single-intent commands (timer, web search, open
        // app, directions, dial) deterministically and INSTANTLY - far more reliable
        // than letting the weak model fumble. Multi-step requests fall through to it.
        if (tryDeterministic(command)) {
            AgentLog.log("diag", "end :: ${DeviceStats.snapshot(applicationContext)}")
            if (lastObjective.isBlank()) lastObjective = command
            TaskHistory.add(applicationContext, command, "finished")
            // If this was launched from chat, resolve the "Thinking…" placeholder there instead of
            // leaving it hanging (the deterministic path skips the orchestrator's chat summary).
            if (taskFromChat) ChatStore.add(applicationContext, "agent", "Done — handled that. What next?")
            goIdle(); return
        }
        lastObjective = command
        // Learn mode is harmless-only: tell the executor to HARD-BLOCK anything destructive for the
        // duration of this task (cleared again in goIdle). False for every normal task.
        ActionAccessibilityService.instance?.exploreOnly = command.contains("LEARN MODE", ignoreCase = true)
        awaitingAnswer = false
        awaitingFollowUp = false
        isAgentBusy = true
        lastStatusSpoken = ""   // fresh verbal status cues for this run
        mode = Mode.BUSY
        // Fresh artifact ledger for THIS task, so the end-of-task chat summary lists only what this
        // run created (files saved, logins recorded).
        ActionAccessibilityService.instance?.createdArtifacts?.clear()
        ActionAccessibilityService.instance?.clearCollected()   // fresh captured-data buffer per task
        // Start loading the model NOW so its cold-start (load + first inference) overlaps with
        // launching the app and reading the first screen, instead of stalling the first "thinking"
        // step. Same model, just warmed sooner - no effect on output quality.
        if (::brain.isInitialized) brain.prewarm()
        acquireWakeLock()
        ensureFloatingButton()   // the overlay is the user's STOP control - keep it up the whole task
        handler.removeCallbacks(captureTimeout)
        // A fuller acknowledgement (vs a clipped "On it.") so the user feels heard.
        speak("Okay, got it — working on that now.")
        updateNotification("Working on: $command", false)
        // Tell the chat we're loading so it doesn't look like a dead home screen during the ~20s
        // model spin-up (the user watches the chat, not a notification).
        if (taskFromChat)
            ChatStore.add(applicationContext, "agent", "Thinking… — reading your screen and planning. Tap the floating button anytime to stop.")
        // Resolve (but HOLD) the app this command implies. The orchestrator opens it once the model
        // is READY (after planning), so the user stays on the chat/loading screen during spin-up
        // instead of being dropped into a half-loaded app. Home logic: only leave our OWN UI when
        // there is NOTHING to preload - if we have a preload app it'll open over us when ready, so a
        // Home press would just be an extra flash.
        // Open the task's FIRST app deterministically even in human-navigation mode (owner: "if it's
        // just going to open_app anyway, don't waste a 13s step reading the home screen - it didn't even
        // manually tap the icon"). Human nav still governs the REST of the task (in-app navigation);
        // this only skips the pointless home-screen read to launch the initial app. Learn mode names no
        // specific app, so resolvePreloadApp returns null there and navigation practice is preserved.
        val preloadName = resolvePreloadApp(command)
        if (preloadName == null && ActionAccessibilityService.instance?.currentPackage() == packageName) {
            ActionAccessibilityService.instance?.performActionJson("{\"action\":\"home\"}", allowGated = true)
        }
        orchestrator.start(command, isContinuousCommand(command) || cont, preloadName)
    }

    // --- teach-by-demonstration (floating Train flow) ---------------------

    /** Start recording the owner's demonstration right where they are, so they can go do the
     *  task without first navigating to a Train screen (which would pollute the captured steps). */
    private fun startTraining(goal: String) {
        val acc = ActionAccessibilityService.instance
        if (acc == null) { speak("Turn on the accessibility service first."); return }
        if (isAgentBusy) { speak("Finish the current task first."); return }
        trainingGoal = goal.trim()
        acc.startDemonstration()
        AgentLog.log("train", "recording demo: ${trainingGoal.ifBlank { "(unspecified)" }}")
        speak(if (trainingGoal.isBlank()) "Recording. Show me, then tap the button to finish."
              else "Recording how to $trainingGoal. Show me, then tap the button to finish.")
    }

    /** Stop recording and learn a generalized skill from what the owner showed. */
    private fun finishTraining() {
        val acc = ActionAccessibilityService.instance ?: return
        if (!acc.recording) return
        val steps = acc.stopDemonstration()
        val goal = trainingGoal; trainingGoal = ""
        if (steps.isEmpty()) { speak("I didn't catch any steps that time."); return }
        val b = brainOrNull()
        if (b == null) {
            AgentMemory.addSkill(applicationContext, goal.ifBlank { "a task you showed me" }, "",
                steps.joinToString("\n") { "- $it" }, "shown")
            speak("Saved your steps."); return
        }
        speak("Got it — learning from what you showed me.")
        b.generalizeDemonstration(goal, steps) { out ->
            val name = if (out.isBlank()) null
                else AgentMemory.addSkillFromModel(applicationContext, out, "shown",
                    goal.ifBlank { "a task you showed me" }, raw = steps.joinToString("\n") { "- $it" })
            if (name != null) {
                AgentMemory.removeUnknownAction(applicationContext, goal)
                handler.post { speak("Learned how to $name.") }
            } else {
                AgentMemory.addSkill(applicationContext, goal.ifBlank { "a task you showed me" }, "",
                    steps.joinToString("\n") { "- $it" }, "shown")
                handler.post { speak("Saved your steps.") }
            }
        }
    }

    /** Resolve (do NOT launch) the app a command implies, so the model can start INSIDE it. The
     *  launch is HELD by the orchestrator until the model is ready, so the user stays on the
     *  chat/loading screen during spin-up instead of staring at a half-loaded app. Returns the app
     *  NAME to open, or null if there's nothing obvious to preload (or it's blacklisted). */
    private fun resolvePreloadApp(command: String): String? {
        val l = command.lowercase()
        // Prefer the FIRST installed app (from the phone SCAN) named in the command, so we open what
        // the task needs FIRST - not an app mentioned LATER ("...then send to Gemini"). Using the
        // real installed list means we never preload a name that isn't actually here.
        val scanned = AgentMemory.deviceApps(applicationContext)
            .filter { it.length >= 3 }
            .mapNotNull { app ->
                Regex("\\b" + Regex.escape(app.lowercase()) + "\\b").find(l)?.let { app to it.range.first }
            }
            .minByOrNull { it.second }?.first
        // An EXPLICITLY named app (open/launch/use/talk to/chat with X).
        val named = Regex("""\b(?:open|launch|start|go to|use|talk to|chat with)\s+(?:the\s+)?([a-z0-9 .'&-]{2,30}?)(?:\s+(?:app|and|then|to|about|please)\b|[.,!?]|$)""")
            .find(l)?.groupValues?.get(1)?.trim()
        val name = when {
            scanned != null -> scanned
            named != null && named.isNotBlank() && named !in setOf("it", "the", "my", "a", "me") -> named
            // Gemini fallback ONLY when the scan didn't catch it (this phone hosts Gemini inside the
            // Google app, so it may not be listed as "Gemini") - and only if no earlier app was found.
            Regex("""\bgemini\b""").containsMatchIn(l) -> "Gemini"
            Regex("""\b(text|sms|imessage)\b""").containsMatchIn(l) -> "Messages"
            Regex("""\bcall\b""").containsMatchIn(l) -> "Phone"
            else -> return null
        }
        // Never preload a blacklisted assistant (ChatGPT/OpenAI) - that's a hard moat.
        if (name.lowercase().let { it.contains("chatgpt") || it.contains("openai") }) return null
        return name
    }

    /** Fix common Vosk mishears so the model/deterministic paths see the real words. */
    private fun normalizeHeard(text: String): String {
        var s = " ${text} "
        val fixes = listOf(
            "\\b(?:chat|church)\\s*g\\s*p\\w{0,4}\\b" to "chatgpt",
            "\\bchat\\s*g\\s*[bp]\\s*t\\b" to "chatgpt",
            "\\bchat\\s*gpt\\b" to "chatgpt",
            "\\byou\\s*tube\\b" to "youtube",
            "\\bjee\\s*mail\\b" to "gmail",
            "\\bg\\s*mail\\b" to "gmail",
            "\\bwhy\\s*fi\\b" to "wifi",
            "\\bwi\\s*fi\\b" to "wifi",
            "\\bwife\\s*i\\b" to "wifi",
            "\\bin\\s*sta\\s*gram\\b" to "instagram",
            "\\bwhat'?s\\s*app\\b" to "whatsapp",
            "\\bblue\\s*tooth\\b" to "bluetooth",
            "\\btik\\s*tok\\b" to "tiktok",
            "\\bsnap\\s*chat\\b" to "snapchat"
        )
        for ((re, rep) in fixes) s = Regex(re, RegexOption.IGNORE_CASE).replace(s, rep)
        return s.trim()
    }

    private fun isContinuousCommand(command: String): Boolean {
        val l = command.lowercase()
        val phrases = listOf(
            "forever", "repeatedly", "over and over", "again and again",
            "keep doing", "keep ", "continuously", "non-stop", "nonstop",
            "in a loop", "until i tell", "until you", "until i stop", "on repeat",
            // "Keep going until I tell you to stop" tasks. NOTE: this flag is only about NEVER
            // auto-stopping - it does NOT unlock chat turn-taking any more. Taking a conversational
            // turn is now the agent's own {"action":"reply"} (it decides when it's in a back-and-
            // forth), so a debate/argument needs no keyword here - the agent drives it via reply.
            // Substrings catch mishears/typos too: "continu"/"contino", "convers" (conversation).
            "continu", "contino", "convers", "back and forth", "back-and-forth", "chat with"
        ).any { l.contains(it) }
        // Explicit repetition the user asked for ("tap 30 times", "do it 50x") is a
        // deliberate instruction, NOT a malfunction - so don't let the same-screen
        // loop breaker or step cap cut it short. Obeying the owner's command IS the
        // success condition. Battery/heat failsafes still apply every step.
        val explicitCount = Regex("""\b(\d{1,4})\s*(?:x|times|more times)\b""")
            .containsMatchIn(l)
        return phrases || explicitCount
    }

    /** Keep the floating overlay button on screen whenever a task runs - the user relies on it as
     *  the STOP control, and a plain background service can be killed under the memory pressure of
     *  loading the model (or simply was never started for a verbal/notification-launched task).
     *  startService is idempotent, so this just guarantees it's present. No-op without the overlay
     *  permission. */
    private fun ensureFloatingButton() {
        if (android.provider.Settings.canDrawOverlays(this)) {
            try { startService(Intent(this, FloatingButtonService::class.java)) } catch (_: Exception) {}
        }
    }

    private fun stopCurrentTask(reason: String = "Stopped.") {
        orchestrator.stop()
        awaitingAnswer = false
        handler.removeCallbacks(answerTimeout)
        confirmationOverlay.dismiss()
        // Capture the plan + steps even on a STOP (these looping tasks are exactly the ones the owner
        // wants to rate per-step), so the task log entry is rateable instead of empty.
        if (isAgentBusy && lastObjective.isNotBlank())
            TaskHistory.add(applicationContext, lastObjective, "stopped",
                plan = orchestrator.lastPlan(), steps = orchestrator.lastSteps())
        isAgentBusy = false
        releaseWakeLock()
        speak(reason)
        goIdle()
    }

    private fun updateNotification(text: String, showResume: Boolean) {
        getSystemService(NotificationManager::class.java).notify(
            NotificationHelper.SERVICE_NOTIFICATION_ID,
            NotificationHelper.buildNotification(this, text, showResume)
        )
    }

    override fun onTaskRemoved(rootIntent: Intent?) {
        // Swiping the app away halts any running task and frees the wake-lock, so it
        // can never keep draining/heating in the background unnoticed.
        if (isAgentBusy) stopCurrentTask("Stopping — you closed the app.")
        else releaseWakeLock()
        super.onTaskRemoved(rootIntent)
    }

    override fun onDestroy() {
        isAgentBusy = false
        instance = null
        releaseWakeLock()
        handler.removeCallbacksAndMessages(null)
        confirmationOverlay.dismiss()
        inputOverlay.dismiss()
        if (::orchestrator.isInitialized) orchestrator.stop()
        speechService?.let { try { it.stop() } catch (_: Exception) {}; it.shutdown() }
        speechService = null
        try { sr?.destroy() } catch (_: Exception) {}; sr = null
        recognizer?.close(); recognizer = null
        model?.close(); model = null
        if (::brain.isInitialized) brain.close()
        if (::tts.isInitialized) { tts.stop(); tts.shutdown() }
        super.onDestroy()
    }

    /** The EMERGENCY unload path (the idle release frees the model when idle; THIS frees it under real
     *  pressure, including MID-TASK, which the idle release never does). For when RAM is genuinely
     *  overloaded and the phone starts glitching. Moderate pressure sheds just the helper submodel for
     *  relief and keeps the big model working; CRITICAL pressure (the OS is about to start killing
     *  background apps - the black wallpaper) frees the big model too, even mid-task, to stay stable. */
    // PUSH-THROUGH (owner): a black wallpaper that recovers is tolerable, and completion beats avoiding
    // it - so we ride out a one-off RAM close call instead of bailing. This stamps the last CRITICAL
    // trim, to tell a single spike (ride it out) from sustained pressure (genuinely about to be killed).
    @Volatile private var lastCriticalTrimAt = 0L

    override fun onTrimMemory(level: Int) {
        super.onTrimMemory(level)
        if (!::brain.isInitialized) return
        when {
            level >= TRIM_MEMORY_RUNNING_CRITICAL -> {
                brain.onMemoryPressure()        // drop the helper first - cheap, always safe
                // PUSH THROUGH the close call. While BUSY, do NOT free the big model on the FIRST
                // critical trim - riding it out usually recovers (the wallpaper may flash black, then
                // the phone comes back) and keeps the task ALIVE, which is what the owner wants. Only
                // free it if criticals keep coming within a few seconds (pressure is NOT easing and a
                // real force-stop is imminent - losing the whole agent is worse than a reload). When
                // IDLE there's no task to protect, so free immediately. closeSafely still defers the
                // close past any in-flight inference so we never tear the engine down mid-decision.
                val now = System.currentTimeMillis()
                val sustained = now - lastCriticalTrimAt < 8000L
                lastCriticalTrimAt = now
                if (!isAgentBusy || sustained) {
                    brain.closeSafely()
                    AgentLog.log("mem", "onTrimMemory($level) ${if (isAgentBusy) "SUSTAINED pressure" else "idle"} -> freed the model")
                } else {
                    AgentLog.log("mem", "onTrimMemory($level) -> riding out the close call (busy); kept the model to finish the task")
                }
            }
            level >= TRIM_MEMORY_RUNNING_LOW -> {
                brain.onMemoryPressure()        // moderate: shed the helper, keep the big model cooking
                AgentLog.log("mem", "onTrimMemory($level) -> released the helper submodel for relief")
            }
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null
}

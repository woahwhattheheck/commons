package com.local.deviceagent

import android.graphics.Typeface
import android.os.Bundle
import android.text.Editable
import android.text.InputType
import android.text.TextWatcher
import android.view.Gravity
import android.view.View
import android.widget.*
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity

/**
 * Dedicated Settings screen. Advanced / power-user options live here so the home
 * screen stays clean and approachable. Everything is backed by [SettingsManager]
 * and takes effect immediately - including for a task already running - so there
 * is no save button.
 */
class SettingsActivity : AppCompatActivity() {

    private lateinit var settings: SettingsManager
    private lateinit var root: LinearLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        settings = SettingsManager(this)
        title = "Settings"

        val scroll = ScrollView(this)
        root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 40, 48, 64)
        }
        scroll.addView(root)
        setContentView(scroll)

        buildActivation()
        buildVoice()
        buildBehavior()
        buildData()
        buildSecurity()
    }

    private fun buildData() {
        sectionHeader("Training data (local)")
        toggle("Capture steps for training", settings.isDataCaptureEnabled()) { settings.setDataCaptureEnabled(it) }
        caption("Saves each step (the screen + the action the agent chose + the outcome) to a private file " +
            "ON THIS DEVICE only — the dataset for measuring success and, later, fine-tuning a model. " +
            "Nothing is sent anywhere. Captured ${TrainingData.count(this)} steps so far.")
        val export = android.widget.Button(this).apply {
            text = "Export training data (to pull off-device)"
            setOnClickListener {
                val dest = try {
                    val src = TrainingData.file(this@SettingsActivity)
                    if (!src.exists() || src.length() == 0L) null
                    else java.io.File(getExternalFilesDir(null), "training_data.jsonl")
                        .also { src.copyTo(it, overwrite = true) }.absolutePath
                } catch (_: Exception) { null }
                val msg = if (dest != null) "Exported to:\n$dest\n(pull via the Files app → Android/data, or USB)"
                    else "Nothing to export yet — run some tasks first."
                android.widget.Toast.makeText(this@SettingsActivity, msg, android.widget.Toast.LENGTH_LONG).show()
            }
        }
        root.addView(export)
        val clear = android.widget.Button(this).apply {
            text = "Clear captured data"
            setOnClickListener {
                TrainingData.clear(this@SettingsActivity)
                android.widget.Toast.makeText(this@SettingsActivity, "Cleared training data.", android.widget.Toast.LENGTH_SHORT).show()
            }
        }
        root.addView(clear)
    }

    private fun buildSecurity() {
        sectionHeader("Security")
        toggle(
            "Require fingerprint / PIN to activate",
            settings.isBiometricRequired()
        ) { settings.setBiometricRequired(it) }
        caption("Off by default while testing. When on, activating the agent after a period of inactivity asks for your device unlock first - prevents someone else (or a malicious prompt) from driving your phone. If you ever share this app, leave this ON.")

        caption("Re-ask after this much inactivity.")
        val mins = listOf(1, 5, 10, 30, 60)
        val labels = mins.map { if (it == 60) "1 hour" else "$it min" }
        spinner(labels, mins.indexOf(settings.getReauthMinutes()).coerceAtLeast(0)) { pos ->
            settings.setReauthMinutes(mins[pos])
        }

        toggleWithWarning(
            "Let the agent use its own app",
            settings.isSelfInteractionAllowed(),
            "Allow the agent to use its own app?",
            "By default the agent is BLOCKED from operating its own app — this chat, the menus, and " +
                "these settings. If it ever lands here it just leaves to the home screen.\n\n" +
                "Turning this ON lets it tap and type inside its own app, which can cause it to loop " +
                "on itself (reading its own messages as new tasks) or change its own settings. Only " +
                "enable this if you specifically need it."
        ) { settings.setSelfInteractionAllowed(it) }
        caption("Off by default (recommended). Keeps the agent from operating its own chat/menus and looping on itself.")
    }

    private fun buildActivation() {
        sectionHeader("Activation")
        caption("Say this word any time, then your command.")
        val field = EditText(this).apply {
            setText(settings.getTriggerWord())
            hint = "hey agent"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
            setSingleLine(true)
            addTextChangedListener(object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
                override fun onTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
                override fun afterTextChanged(s: Editable?) {
                    val w = s?.toString()?.trim().orEmpty()
                    if (w.isNotBlank()) settings.setTriggerWord(w)
                }
            })
        }
        root.addView(field)
    }

    private fun buildVoice() {
        sectionHeader("Voice")
        caption("How much the agent speaks while it works.")
        val modes = listOf("minimal", "explanation", "silent")
        val labels = listOf(
            "Minimal - brief replies",
            "Explanation - narrate reasoning",
            "Silent - no speech"
        )
        spinner(labels, modes.indexOf(settings.getVoiceMode()).coerceAtLeast(0)) { pos ->
            settings.setVoiceMode(modes[pos])
        }
        toggle("Male voice", settings.isMaleVoice()) { settings.setMaleVoice(it) }
        caption("Speech recognition for your spoken commands. On-device is private (nothing leaves the " +
            "phone); cloud is more accurate but sends the command off-device. The wake word stays on-device either way.")
        toggle("Cloud speech (more accurate, off-device)", settings.isCloudSpeech()) {
            settings.setSpeechMode(if (it) "cloud" else "ondevice"); settings.setSpeechChoiceMade(true)
        }
    }

    private fun buildBehavior() {
        sectionHeader("Behavior")
        toggle(
            "Navigate like a human (tap, don't shortcut)",
            settings.isHumanNavigation()
        ) { settings.setHumanNavigation(it) }

        toggle(
            "Double-check actions (verifier)",
            settings.isVerifierEnabled()
        ) { settings.setVerifierEnabled(it) }
        caption("Takes a fast second look at each action before doing it and fixes clear mistakes (wrong app/field, off-goal taps). More reliable, a little slower. Turn off to compare.")

        toggle(
            "Allow the agent to run code (terminals)",
            !settings.isCodeExecutionBlocked()
        ) { settings.setCodeExecutionBlocked(!it) }
        caption("OFF by default and recommended off. While off, the agent is HARD-BLOCKED from opening or operating any terminal / shell / code-runner / remote-desktop app (Termux, Andronix, SSH, VNC, Pydroid, …): it backs out instantly without touching anything, so it cannot execute code on your phone. Turn on only if you deliberately want it to.")

        toggle(
            "Protect the agent's own repo",
            settings.isSelfProtectEnabled()
        ) { settings.setSelfProtectEnabled(it) }
        caption("ON by default. While on, the agent backs out of any screen showing its own source repo (its GitHub page, where Delete/commit buttons could trash the codebase) without touching anything. Turn off only if you deliberately need it to operate the repo.")

        caption("Speed - how long it settles between actions.")
        val speeds = listOf("fast", "balanced", "careful")
        val speedLabels = listOf(
            "Fast - snappier, less settle time",
            "Balanced - recommended",
            "Careful - waits longer on slow screens"
        )
        spinner(speedLabels, speeds.indexOf(settings.getSpeed()).coerceAtLeast(0)) { pos ->
            settings.setSpeed(speeds[pos])
        }

        caption("Heat protection - how soon the agent stops if the phone warms up.")
        val heat = listOf("minimal", "medium", "high")
        val heatLabels = listOf(
            "Minimal - only stop if critically hot (default)",
            "Medium - stop when very hot",
            "High - stop early as it warms up"
        )
        spinner(heatLabels, heat.indexOf(settings.getHeatProtection()).coerceAtLeast(0)) { pos ->
            settings.setHeatProtection(heat[pos])
        }
        caption("Phones run warm under sustained AI work. Minimal keeps the agent going until the phone is genuinely at risk; raise it if you'd rather it cool down sooner.")

        toggle(
            "Allow risky actions (close tabs, change files)",
            settings.isRiskyActionsAllowed()
        ) { settings.setRiskyActionsAllowed(it) }
        caption("Off by default. When on, the agent may close browser tabs/windows and alter files if a task needs it.")

        toggle(
            "Auto-decline incoming calls",
            settings.isAutoDeclineCalls()
        ) { settings.setAutoDeclineCalls(it) }
        caption("Off by default. When on, incoming calls are rejected automatically.")

        toggle(
            "Learn from watching me (passive)",
            settings.isPassiveLearningEnabled()
        ) {
            settings.setPassiveLearningEnabled(it)
            ActionAccessibilityService.instance?.setPassiveLearning(it)
        }
        caption("Off by default. When on, the agent watches how YOU navigate - which taps open which apps - and saves those navigation facts to its memory to reuse later. No screenshots and no model thinking, just compact notes you can review/delete under Agent memory. It does monitor your taps while on, which costs some battery, so turn it off to save power.")

        sectionHeader("Help")
        button("How it works") { IntroDialog.show(this) }
        toggle("Show intro on startup", !settings.isIntroHidden()) { settings.setIntroHidden(!it) }
        caption("A quick overview of what the agent does and how to stay in control. It pops up when you open the app until you turn it off; reopen it anytime with the button above.")
    }

    // --- small view helpers (match MainActivity's code-built UI style) --------

    private fun button(label: String, onClick: () -> Unit) {
        root.addView(Button(this).apply {
            text = label
            setOnClickListener { onClick() }
            Ui.styleButton(this, primary = false)
        })
    }

    private fun sectionHeader(text: String) {
        root.addView(TextView(this).apply {
            this.text = text
            textSize = 18f
            setTypeface(typeface, Typeface.BOLD)
            setPadding(0, 40, 0, 4)
        })
    }

    private fun caption(text: String) {
        root.addView(TextView(this).apply {
            this.text = text
            textSize = 13f
            setTextColor(0xFF888888.toInt())
            setPadding(0, 0, 0, 8)
        })
    }

    private fun toggle(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, 16, 0, 0)
        }
        row.addView(TextView(this).apply {
            text = label
            textSize = 15f
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
        })
        row.addView(Switch(this).apply {
            isChecked = checked
            setOnCheckedChangeListener { _, c -> onChange(c) }
        })
        root.addView(row)
    }

    /** Like [toggle], but turning it ON first asks for confirmation (for risky opt-ins). Cancelling
     *  reverts the switch without firing onChange. Turning it OFF is immediate. */
    private fun toggleWithWarning(
        label: String, checked: Boolean, warnTitle: String, warnMsg: String, onChange: (Boolean) -> Unit
    ) {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, 16, 0, 0)
        }
        row.addView(TextView(this).apply {
            text = label
            textSize = 15f
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
        })
        val sw = Switch(this)
        var suppress = false
        sw.isChecked = checked
        sw.setOnCheckedChangeListener { _, c ->
            if (suppress) return@setOnCheckedChangeListener
            if (c) {
                AlertDialog.Builder(this)
                    .setTitle(warnTitle)
                    .setMessage(warnMsg)
                    .setNegativeButton("Cancel") { _, _ -> suppress = true; sw.isChecked = false; suppress = false }
                    .setOnCancelListener { suppress = true; sw.isChecked = false; suppress = false }
                    .setPositiveButton("Enable") { _, _ -> onChange(true) }
                    .show()
            } else onChange(false)
        }
        row.addView(sw)
        root.addView(row)
    }

    private fun spinner(labels: List<String>, selected: Int, onSelect: (Int) -> Unit) {
        root.addView(Spinner(this).apply {
            adapter = ArrayAdapter(
                this@SettingsActivity,
                android.R.layout.simple_spinner_dropdown_item,
                labels
            )
            setSelection(selected)
            onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                override fun onItemSelected(p: AdapterView<*>?, v: View?, pos: Int, id: Long) = onSelect(pos)
                override fun onNothingSelected(p: AdapterView<*>?) {}
            }
        })
    }
}

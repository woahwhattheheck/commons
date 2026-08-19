package com.local.deviceagent

import android.graphics.Typeface
import android.os.Bundle
import android.view.Gravity
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity

/**
 * Lets the owner review exactly what the agent has stored about them and itself -
 * facts, lessons it has learned, and logins it created - and wipe it. This keeps the
 * self-learning auditable so it can't quietly drift off the rails. Read-only review +
 * a clear button; the agent writes here, the user verifies here.
 */
class MemoryActivity : AppCompatActivity() {

    private lateinit var root: LinearLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        title = "Agent memory"
        val scroll = ScrollView(this)
        root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 40, 48, 64)
        }
        scroll.addView(root)
        setContentView(scroll)
        render()
    }

    private fun render() {
        root.removeAllViews()
        caption("Everything the agent remembers is here — tap any item to edit or delete it.")

        header("Facts it knows")
        val facts = AgentMemory.factsList(this)
        if (facts.isEmpty()) caption("Nothing yet. Say \"remember my … is …\".")
        else facts.forEach { (k, v) -> editableFact(k, v) }

        header("Skills you've taught it")
        val skills = AgentMemory.skills(this)
        if (skills.isEmpty()) caption("None yet. Teach it from the Train screen or the floating button.")
        else skills.forEach { editableSkill(it) }

        header("Learned from watching you")
        val obs = AgentMemory.observations(this)
        if (obs.isEmpty()) caption("Nothing yet. Turn on “Learn from watching me” in Settings, then navigate your phone and it fills in here.")
        else { caption("Navigation it picked up by watching you use the phone."); obs.forEach { o ->
            deletableLine("• $o", "Forget this?") { AgentMemory.removeObservation(this, o); render() }
        } }

        header("Things it couldn't do yet")
        val unknown = AgentMemory.unknownActions(this)
        if (unknown.isEmpty()) caption("Nothing pending.")
        else unknown.forEach { what ->
            deletableLine("• $what", "Remove this?") { AgentMemory.removeUnknownAction(this, what); render() }
        }

        header("Lessons it learned")
        val lessons = AgentMemory.lessons(this)
        if (lessons.isEmpty()) caption("Nothing yet. It records tips when it gets stuck or succeeds after a struggle.")
        else lessons.forEach { editableLesson(it) }

        header("Mistakes it's learning from")
        val bad = AgentMemory.badMemories(this)
        if (bad.isEmpty()) caption("None. When it gets stuck it notes what went wrong + what to do instead, and avoids repeating it.")
        else bad.forEach { (m, b) ->
            deletableLine("• $m${if (b.isNotBlank()) "\n   → better: $b" else ""}", "Forget this?") {
                AgentMemory.removeBadMemory(this, m); render()
            }
        }

        header("Logins it created")
        val logins = AgentMemory.logins(this)
        if (logins.isEmpty()) caption("None. When the agent signs up for a service it records the login here.")
        else logins.forEach { editableLogin(it) }

        header("Send shortcuts it learned")
        val recipes = AgentMemory.sendRecipes(this)
        if (recipes.isEmpty()) caption("None. It records which Send method worked per app.")
        else recipes.forEach { (pkg, strat) ->
            deletableLine("• $pkg → strategy $strat", "Forget this shortcut?") { AgentMemory.removeSendRecipe(this, pkg); render() }
        }

        header("What it knows about your phone")
        val profile = AgentMemory.deviceProfile(this)
        if (profile.isBlank()) caption("Not scanned yet. Use “Re-scan installed apps” on the Train screen.")
        else caption(profile)
        val apps = AgentMemory.deviceApps(this)
        if (apps.isEmpty()) caption("Apps: not scanned yet.")
        else {
            val joined = apps.joinToString(", ")
            caption("${apps.size} apps known: ${joined.take(400)}${if (joined.length > 400) "…" else ""}")
            deletableLine("Clear scanned apps & profile", "Clear what the agent learned about your phone?") {
                AgentMemory.setDeviceApps(this, emptyList()); AgentMemory.setDeviceProfile(this, ""); render()
            }
        }

        val clear = Button(this).apply {
            text = "Clear ALL memory"
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { setMargins(0, 48, 0, 0) }
            setOnClickListener { confirmClear() }
        }
        root.addView(clear)
    }

    /** A taught skill: tap to read its steps, edit them, or delete it. */
    private fun editableSkill(skill: AgentMemory.Skill) = root.addView(TextView(this).apply {
        text = "• ${if (skill.pinned) "📌 " else ""}${skill.name}  (${skill.source})  ✎"
        textSize = 15f
        setPadding(0, 10, 0, 0)
        setOnClickListener {
            val body = (if (skill.app.isBlank()) "" else "App: ${skill.app}\n\n") +
                "WHAT I'LL DO (generalized):\n" + skill.steps +
                (if (skill.raw.isBlank()) "" else "\n\nWHAT I LEARNED IT FROM (recorded):\n" + skill.raw)
            AlertDialog.Builder(this@MemoryActivity)
                .setTitle(skill.name)
                .setMessage(body)
                .setPositiveButton("Edit steps") { _, _ ->
                    val input = EditText(this@MemoryActivity).apply {
                        setText(skill.steps); setSelection(skill.steps.length); minLines = 4; isSingleLine = false
                    }
                    AlertDialog.Builder(this@MemoryActivity)
                        .setTitle("Edit “${skill.name}”")
                        .setView(input)
                        .setPositiveButton("Save") { _, _ ->
                            val nv = input.text.toString().trim()
                            if (nv.isEmpty()) AgentMemory.removeSkill(this@MemoryActivity, skill.name)
                            else AgentMemory.addSkill(this@MemoryActivity, skill.name, skill.app, nv, skill.source)
                            render()
                        }
                        .setNegativeButton("Cancel", null)
                        .show()
                }
                .setNeutralButton("Delete") { _, _ -> AgentMemory.removeSkill(this@MemoryActivity, skill.name); render() }
                // Pin/unpin: a pinned skill is never auto-evicted by the cap. Tap outside to close.
                .setNegativeButton(if (skill.pinned) "Unpin" else "📌 Pin") { _, _ ->
                    AgentMemory.setSkillPinned(this@MemoryActivity, skill.name, !skill.pinned); render()
                }
                .show()
        }
    })

    /** A created login: tap to edit the saved secret or delete the whole entry. */
    private fun editableLogin(login: AgentMemory.Login) = root.addView(TextView(this).apply {
        text = "• ${login.service} — ${login.username} / ${login.secret}  ✎"
        textSize = 15f
        setPadding(0, 10, 0, 0)
        setOnClickListener {
            val input = EditText(this@MemoryActivity).apply { setText(login.secret); setSelection(login.secret.length) }
            AlertDialog.Builder(this@MemoryActivity)
                .setTitle("${login.service} (${login.username})")
                .setView(input)
                .setPositiveButton("Save") { _, _ ->
                    AgentMemory.updateLoginSecret(this@MemoryActivity, login.service, login.username, login.time, input.text.toString().trim())
                    render()
                }
                .setNeutralButton("Delete") { _, _ ->
                    AgentMemory.removeLogin(this@MemoryActivity, login.service, login.username, login.time); render()
                }
                .setNegativeButton("Cancel", null)
                .show()
        }
    })

    /** A line the owner can tap to delete (with a confirm). */
    private fun deletableLine(text: String, confirm: String, onDelete: () -> Unit) = root.addView(TextView(this).apply {
        this.text = text
        textSize = 15f
        setPadding(0, 10, 0, 0)
        setOnClickListener {
            AlertDialog.Builder(this@MemoryActivity)
                .setMessage(confirm)
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Delete") { _, _ -> onDelete() }
                .show()
        }
    })

    private fun confirmClear() {
        AlertDialog.Builder(this)
            .setTitle("Clear all memory?")
            .setMessage("This wipes every fact, lesson, and saved login. Can't be undone.")
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Clear") { _, _ -> AgentMemory.clear(this); render() }
            .show()
    }

    private fun header(text: String) = root.addView(TextView(this).apply {
        this.text = text
        textSize = 18f
        setTypeface(typeface, Typeface.BOLD)
        setPadding(0, 40, 0, 6)
    })

    private fun caption(text: String) = root.addView(TextView(this).apply {
        this.text = text
        textSize = 13f
        setTextColor(0xFF888888.toInt())
        gravity = Gravity.START
        setPadding(0, 0, 0, 4)
    })

    private fun line(text: String) = root.addView(TextView(this).apply {
        this.text = text
        textSize = 15f
        setPadding(0, 6, 0, 0)
    })

    /** A learned lesson the owner can tap to edit (fix a slightly-off one) or delete. */
    private fun editableLesson(text: String) = root.addView(TextView(this).apply {
        this.text = "• $text  ✎"
        textSize = 15f
        setPadding(0, 10, 0, 0)
        setOnClickListener {
            val input = EditText(this@MemoryActivity).apply { setText(text); setSelection(text.length) }
            AlertDialog.Builder(this@MemoryActivity)
                .setTitle("Edit memory")
                .setView(input)
                .setPositiveButton("Save") { _, _ ->
                    val nv = input.text.toString().trim()
                    AgentMemory.removeLesson(this@MemoryActivity, text)
                    if (nv.isNotEmpty()) AgentMemory.addLesson(this@MemoryActivity, nv)
                    render()
                }
                .setNeutralButton("Delete") { _, _ -> AgentMemory.removeLesson(this@MemoryActivity, text); render() }
                .setNegativeButton("Cancel", null)
                .show()
        }
    })

    /** A stored fact the owner can tap to edit its value or delete it. */
    private fun editableFact(k: String, v: String) = root.addView(TextView(this).apply {
        this.text = "• $k = $v  ✎"
        textSize = 15f
        setPadding(0, 10, 0, 0)
        setOnClickListener {
            val input = EditText(this@MemoryActivity).apply { setText(v); setSelection(v.length) }
            AlertDialog.Builder(this@MemoryActivity)
                .setTitle("Edit \"$k\"")
                .setView(input)
                .setPositiveButton("Save") { _, _ ->
                    val nv = input.text.toString().trim()
                    if (nv.isEmpty()) AgentMemory.removeFact(this@MemoryActivity, k)
                    else AgentMemory.setFact(this@MemoryActivity, k, nv)
                    render()
                }
                .setNeutralButton("Delete") { _, _ -> AgentMemory.removeFact(this@MemoryActivity, k); render() }
                .setNegativeButton("Cancel", null)
                .show()
        }
    })
}

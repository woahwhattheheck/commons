package com.local.deviceagent

import android.os.Bundle
import android.text.format.DateUtils
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

/**
 * Per-task detail + PER-STEP rating (the owner's idea): show the task's objective, the PLAN the
 * agent authored, and EACH action it actually took - each with Worked / Failed buttons. A rating is
 * fed straight into durable memory (a worked step -> a confirmed lesson, a failed one -> a "mistake
 * to avoid"), so the owner can teach the agent EXACTLY where a task succeeded or went wrong.
 */
class TaskDetailActivity : AppCompatActivity() {

    companion object { const val EXTRA_TASK_ID = "task_id" }

    private lateinit var container: LinearLayout
    private var taskId: Long = 0L

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        taskId = intent.getLongExtra(EXTRA_TASK_ID, 0L)
        val scroll = ScrollView(this).apply { setBackgroundColor(Ui.BG) }
        container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 32, 32, 120)   // bottom pad clears the ownership stamp
        }
        scroll.addView(container)
        setContentView(scroll)
        render()
    }

    override fun onResume() { super.onResume(); render() }

    private fun render() {
        container.removeAllViews()
        val e = TaskHistory.get(this, taskId)
        if (e == null) {
            container.addView(label("This task is no longer in the log.", Ui.TEXT_DIM, 15f))
            return
        }

        container.addView(label(e.objective.ifBlank { "(no objective)" }, Ui.TEXT, 20f, bold = true))
        container.addView(label("${e.outcome} · ${DateUtils.getRelativeTimeSpanString(e.time)}", Ui.TEXT_DIM, 12f))

        // The plan the agent wrote for itself (read-only context for rating the steps).
        if (e.plan.isNotBlank()) {
            container.addView(label("Plan", Ui.TEXT, 16f, bold = true, topPad = 28))
            container.addView(label(e.plan.trim(), Ui.TEXT_DIM, 13f, topPad = 4))
        }

        // The actions actually taken, each rateable. This is the heart of the screen.
        container.addView(label("Steps it took — rate each", Ui.TEXT, 16f, bold = true, topPad = 28))
        if (e.steps.isEmpty()) {
            container.addView(label("No per-step record for this task (older task, or it ended before acting).",
                Ui.TEXT_DIM, 13f, topPad = 4))
            return
        }
        container.addView(label("Tell me which steps worked and which didn't — I'll remember it for next time.",
            Ui.TEXT_DIM, 12f, topPad = 2))

        e.steps.forEachIndexed { i, step ->
            val rating = e.stepRatings.getOrElse(i) { 0 }
            container.addView(label("${i + 1}. $step", Ui.TEXT, 14f, topPad = 18))
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL; setPadding(0, 6, 0, 0)
            }
            row.addView(rateButton("Worked", selected = rating == 1) { rate(e, i, if (rating == 1) 0 else 1) })
            row.addView(rateButton("Failed", selected = rating == -1) { rate(e, i, if (rating == -1) 0 else -1) })
            container.addView(row)
        }
    }

    /** Persist the per-step rating AND teach memory from it, then refresh the screen. */
    private fun rate(e: TaskHistory.Entry, index: Int, rating: Int) {
        val step = TaskHistory.setStepRating(this, e.id, index, rating)
        // rating 0 = the owner toggled it back off; don't write a memory for "un-rated".
        if (rating != 0 && step != null) AgentMemory.recordStepFeedback(this, e.objective, step, rating)
        render()
    }

    private fun label(text: String, color: Int, size: Float, bold: Boolean = false, topPad: Int = 0) =
        TextView(this).apply {
            this.text = text; textSize = size; setTextColor(color)
            setPadding(0, topPad, 0, 0)
            if (bold) setTypeface(typeface, android.graphics.Typeface.BOLD)
        }

    private fun rateButton(label: String, selected: Boolean, onClick: () -> Unit) = Button(this).apply {
        text = if (selected) "✓ $label" else label
        layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
            .apply { setMargins(0, 0, 12, 0) }
        setOnClickListener { onClick() }
        Ui.styleButton(this, primary = selected)   // the chosen rating is filled
    }
}

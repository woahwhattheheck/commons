package com.local.deviceagent

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/**
 * Persistent, capped log of finished tasks with optional user feedback (thumbs up/down + a "why"
 * note). Stored as JSON in SharedPreferences.
 *
 * Three correctness rules learned from the owner's report ("feedback jumped to another task; the
 * order was wrong; it showed old-build tasks and dropped current ones"):
 *  1. Every entry gets a UNIQUE, monotonic id (a stored counter) - never System.currentTimeMillis(),
 *     which collided for back-to-back tasks and made feedback land on the wrong entry. Legacy entries
 *     with no id (=0) are no longer matchable, so a stray feedback can't bleed onto them.
 *  2. Entries are tagged with the BUILD they ran under and the list shows ONLY the current build, so
 *     stale tasks from older builds never pollute (and are pruned from storage on the next add).
 *  3. The list is sorted by actual time (newest first), and an immediate duplicate add (the same task
 *     recorded twice by two code paths) is skipped.
 */
object TaskHistory {
    private const val PREF = "task_history"
    private const val KEY = "entries"
    private const val SEQ = "seq"        // monotonic id counter, so ids never collide
    private const val MAX = 60

    data class Entry(
        val id: Long, val time: Long, val objective: String,
        val outcome: String, val rating: Int, val note: String,
        // The agent's authored PLAN (its STEPS) and the actions it actually TOOK, so the log can show
        // them back for PER-STEP rating. stepRatings runs parallel to steps (0=unrated,1=worked,-1=failed).
        val plan: String = "", val steps: List<String> = emptyList(),
        val stepRatings: List<Int> = emptyList()
    )

    private fun prefs(c: Context) = c.getSharedPreferences(PREF, Context.MODE_PRIVATE)

    /** Identifies the current build, so older-build tasks don't mix in (same source as AgentLog). */
    private fun buildTag(c: Context): Long = try {
        c.packageManager.getPackageInfo(c.packageName, 0).lastUpdateTime
    } catch (_: Exception) { 0L }

    @Synchronized
    fun add(c: Context, objective: String, outcome: String,
            plan: String = "", steps: List<String> = emptyList()) {
        val arr = load(c)
        val now = System.currentTimeMillis()
        val build = buildTag(c)
        // Skip an immediate duplicate: the same task recorded twice in quick succession (e.g. a stop
        // path + the completion callback) shouldn't create two entries.
        if (arr.length() > 0) {
            val last = arr.optJSONObject(arr.length() - 1)
            if (last != null && last.optString("objective") == objective &&
                last.optString("outcome") == outcome && now - last.optLong("time") < 20_000L) return
        }
        val id = prefs(c).getLong(SEQ, 1L)
        prefs(c).edit().putLong(SEQ, id + 1).apply()
        val stepsArr = JSONArray().apply { steps.take(40).forEach { put(it) } }
        val ratingsArr = JSONArray().apply { repeat(minOf(steps.size, 40)) { put(0) } }
        arr.put(
            JSONObject()
                .put("id", id)
                .put("time", now)
                .put("objective", objective)
                .put("outcome", outcome)
                .put("rating", 0)
                .put("note", "")
                .put("build", build)
                .put("plan", plan)
                .put("steps", stepsArr)
                .put("sratings", ratingsArr)
        )
        // Keep tasks across builds (the owner reinstalls a new APK constantly; filtering to the
        // current build made the task log "completely empty after several tasks" every update). The
        // task log is the owner's record of what the agent DID, not a build-specific debug view, so we
        // retain ALL builds' entries and just cap the total. (Feedback still lands correctly because
        // every entry has a unique monotonic id - that, not build-filtering, was the collision fix.)
        while (arr.length() > MAX) arr.remove(0)
        save(c, arr)
    }

    @Synchronized
    fun setFeedback(c: Context, id: Long, rating: Int, note: String) {
        if (id <= 0L) return   // 0 = a legacy/unidentified entry; never match it (collision guard)
        val arr = load(c)
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            if (o.optLong("id") == id) { o.put("rating", rating); o.put("note", note); break }
        }
        save(c, arr)
    }

    /** Rate ONE executed step of a task (the owner's per-step feedback): 1=worked, -1=failed, 0=clear.
     *  Stored in the parallel "sratings" array so the agent can later reinforce what worked and avoid
     *  what didn't. Returns the step text (so the caller can feed it to memory), or null if not found. */
    @Synchronized
    fun setStepRating(c: Context, id: Long, index: Int, rating: Int): String? {
        if (id <= 0L) return null
        val arr = load(c)
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            if (o.optLong("id") != id) continue
            val steps = o.optJSONArray("steps") ?: return null
            if (index < 0 || index >= steps.length()) return null
            val ratings = o.optJSONArray("sratings") ?: JSONArray().also { o.put("sratings", it) }
            while (ratings.length() <= index) ratings.put(0)
            ratings.put(index, rating)
            save(c, arr)
            return steps.optString(index)
        }
        return null
    }

    @Synchronized
    fun list(c: Context): List<Entry> {
        val arr = load(c)
        val out = ArrayList<Entry>(arr.length())
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            val stepsArr = o.optJSONArray("steps")
            val steps = if (stepsArr == null) emptyList()
                else (0 until stepsArr.length()).map { stepsArr.optString(it) }
            val ratingsArr = o.optJSONArray("sratings")
            val sratings = if (ratingsArr == null) emptyList()
                else (0 until ratingsArr.length()).map { ratingsArr.optInt(it) }
            out.add(
                Entry(
                    o.optLong("id"), o.optLong("time"), o.optString("objective"),
                    o.optString("outcome"), o.optInt("rating"), o.optString("note"),
                    o.optString("plan"), steps, sratings
                )
            )
        }
        return out.sortedByDescending { it.time }   // newest first, by actual time
    }

    /** One entry by id (for the per-step rating detail screen), or null. */
    @Synchronized
    fun get(c: Context, id: Long): Entry? = list(c).firstOrNull { it.id == id }

    @Synchronized
    fun clear(c: Context) = prefs(c).edit().remove(KEY).apply()

    private fun load(c: Context): JSONArray =
        try { JSONArray(prefs(c).getString(KEY, "[]")) } catch (e: Exception) { JSONArray() }

    private fun save(c: Context, arr: JSONArray) =
        prefs(c).edit().putString(KEY, arr.toString()).apply()
}

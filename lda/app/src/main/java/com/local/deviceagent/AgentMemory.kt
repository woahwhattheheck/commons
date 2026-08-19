package com.local.deviceagent

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/**
 * Small, persistent, size-capped memory the agent carries across tasks and reboots.
 * Two kinds of memory, both stored as JSON in SharedPreferences:
 *
 *  - FACTS: a key -> value map of durable user/device facts the agent should know
 *    (e.g. "phone number" -> "555-1234", "home address" -> "..."). Set explicitly
 *    ("remember my number is ...") and recalled when a task needs them.
 *  - LESSONS: a capped, de-duplicated list of short things the agent learned by doing
 *    (e.g. "Block Blast shows only a SurfaceView - play with tap_xy"). This is the
 *    bounded first step toward self-improvement from experience.
 *
 * A compact [forPrompt] block is injected into the action prompt so the model can use
 * what it knows without re-deriving it every time. Everything stays on-device.
 */
object AgentMemory {
    private const val PREF = "agent_memory"
    private const val FACTS = "facts"
    private const val LESSONS = "lessons"
    private const val LOGINS = "logins"
    private const val SENDS = "send_recipes"
    private const val SEND_SKILLS = "send_skills"   // structural: the EXACT field+send control per app
    private const val IDENTITY = "identity"         // the agent's persistent, continuous self
    private const val SKILLS = "skills"
    private const val UNKNOWN = "unknown_actions"
    private const val APPS = "device_apps"
    private const val PROFILE = "device_profile"
    private const val OBS = "observations"
    private const val BAD = "bad_memories"
    private const val MISTAKES = "screen_mistakes"   // per app+screen-signature: actions that did nothing here
    private const val SIGHTINGS = "passive_sightings"
    private const val NAV = "nav_maps"            // per-app accumulated navigation destinations
    private const val MAX_NAV_APPS = 40
    private const val MAX_NAV_DESTS = 16
    private const val SEEN = "seen_screens"       // structural signatures of screens met per app (novelty)
    private const val MAX_SEEN_PER_APP = 60
    private const val MAX_SEEN_APPS = 40
    private const val CHECKPOINT = "task_checkpoint"  // #10: interrupted-task state, to offer a resume
    private const val MAX_LESSONS = 25
    private const val MAX_LESSON_LEN = 160
    private const val MAX_LOGINS = 60
    private const val MAX_SKILLS = 40
    private const val MAX_SKILL_LEN = 1200
    private const val SKILL_PROTECT_AT = 3        // confirmations before an auto-skill becomes pinned
    private const val MAX_UNKNOWN = 30

    private fun prefs(c: Context) = c.getSharedPreferences(PREF, Context.MODE_PRIVATE)

    // --- facts (key -> value) --------------------------------------------------

    @Synchronized
    fun setFact(c: Context, key: String, value: String) {
        val k = key.trim().lowercase()
        if (k.isBlank() || value.isBlank()) return
        val o = facts(c).put(k, value.trim())
        prefs(c).edit().putString(FACTS, o.toString()).apply()
    }

    @Synchronized
    fun getFact(c: Context, key: String): String? =
        facts(c).optString(key.trim().lowercase(), "").ifBlank { null }

    @Synchronized
    fun removeFact(c: Context, key: String) {
        val o = facts(c); o.remove(key.trim().lowercase())
        prefs(c).edit().putString(FACTS, o.toString()).apply()
    }

    @Synchronized
    fun factsList(c: Context): List<Pair<String, String>> {
        val o = facts(c)
        return o.keys().asSequence().map { it to o.optString(it) }.toList()
    }

    private fun facts(c: Context): JSONObject =
        try { JSONObject(prefs(c).getString(FACTS, "{}")!!) } catch (_: Exception) { JSONObject() }

    // --- lessons (capped list) -------------------------------------------------

    @Synchronized
    fun addLesson(c: Context, lesson: String) {
        val t = lesson.trim().take(MAX_LESSON_LEN)
        if (t.length < 4) return
        val arr = lessonsArr(c)
        // De-dupe (case-insensitive) so the same tip isn't stored repeatedly.
        for (i in 0 until arr.length())
            if (arr.optString(i).equals(t, ignoreCase = true)) return
        arr.put(t)
        while (arr.length() > MAX_LESSONS) arr.remove(0)
        prefs(c).edit().putString(LESSONS, arr.toString()).apply()
    }

    @Synchronized
    fun lessons(c: Context): List<String> {
        val arr = lessonsArr(c)
        return (0 until arr.length()).map { arr.optString(it) }
    }

    /** Remove a single learned lesson (so the owner can trim a bad/stale one). */
    @Synchronized
    fun removeLesson(c: Context, lesson: String) {
        val arr = lessonsArr(c)
        val out = JSONArray()
        for (i in 0 until arr.length()) {
            val v = arr.optString(i)
            if (!v.equals(lesson, ignoreCase = true)) out.put(v)
        }
        prefs(c).edit().putString(LESSONS, out.toString()).apply()
    }

    /** General lessons/concepts pulled by RELEVANCE to the current goal (not just the last-N), so
     *  broadly-useful knowledge surfaces exactly when it applies. This is the "general memory
     *  alongside the specific ones, retrieved when needed" the owner asked for: specific navigation
     *  lives in observations (keyed by app), while these are app-agnostic concepts ranked by how
     *  well they match the goal, falling back to the most recent few when nothing matches. */
    @Synchronized
    fun lessonsFor(c: Context, goal: String, max: Int = 6): List<String> {
        val all = lessons(c)
        if (all.isEmpty()) return emptyList()
        val goalWords = keywordsOf(goal)
        if (goalWords.isEmpty()) return all.takeLast(max)
        val ranked = all.mapIndexed { i, t -> Triple(t, goalWords.count { it in keywordsOf(t) }, i) }
            .sortedWith(compareByDescending<Triple<String, Int, Int>> { it.second }.thenByDescending { it.third })
        val matched = ranked.filter { it.second > 0 }.map { it.first }
        return (if (matched.isNotEmpty()) matched else all.takeLast(max)).take(max)
    }

    /** Relevance-pulled general lessons as a planner block (empty if none). */
    @Synchronized
    fun lessonsBlockFor(c: Context, goal: String, max: Int = 6): String {
        val ls = lessonsFor(c, goal, max)
        return if (ls.isEmpty()) "" else "GENERAL LESSONS THAT MAY APPLY:\n" + ls.joinToString("\n") { "- $it" }
    }

    /** STUCK-RECOVERY RETRIEVAL ("try a learned principle when stuck"): pull the ONE stored lesson
     *  most similar to the CURRENT situation - objective AND what's actually on screen, not just the
     *  goal - to offer as a CANDIDATE when the loop is spinning. Matching on the screen text is what
     *  makes it "by similarity to the real situation": the same objective can be stuck on different
     *  screens that each need a different principle. Returns null unless a lesson clears a real bar
     *  (>=2 shared keywords) - we'd rather say nothing than inject noise that pulls a healthy run off
     *  track. Caller decides whether to surface it; this never forces an action. */
    @Synchronized
    fun principleForStuck(c: Context, objective: String, screen: String): String? {
        val all = lessons(c)
        if (all.isEmpty()) return null
        val want = keywordsOf(objective) + keywordsOf(screen.take(1200))
        if (want.isEmpty()) return null
        val best = all
            .map { lesson -> val lk = keywordsOf(lesson); lesson to want.count { it in lk } }
            .filter { it.second >= 2 }
            .maxByOrNull { it.second } ?: return null
        return best.first.take(160)
    }

    // --- logins (credentials the agent created; NEVER injected into the prompt) ----

    data class Login(val service: String, val username: String, val secret: String, val time: Long)

    @Synchronized
    fun addLogin(c: Context, service: String, username: String, secret: String) {
        if (service.isBlank()) return
        val arr = loginsArr(c)
        arr.put(JSONObject()
            .put("service", service.trim())
            .put("user", username.trim())
            .put("secret", secret.trim())
            .put("time", System.currentTimeMillis()))
        while (arr.length() > MAX_LOGINS) arr.remove(0)
        prefs(c).edit().putString(LOGINS, arr.toString()).apply()
    }

    @Synchronized
    fun logins(c: Context): List<Login> {
        val arr = loginsArr(c)
        return (0 until arr.length()).map {
            val o = arr.getJSONObject(it)
            Login(o.optString("service"), o.optString("user"), o.optString("secret"), o.optLong("time"))
        }.asReversed()
    }

    private fun loginsArr(c: Context): JSONArray =
        try { JSONArray(prefs(c).getString(LOGINS, "[]")) } catch (_: Exception) { JSONArray() }

    /** Delete one stored login (matched on service + username + time), so the owner can prune
     *  credentials the agent created. */
    @Synchronized
    fun removeLogin(c: Context, service: String, username: String, time: Long) {
        val arr = loginsArr(c); val out = JSONArray()
        for (i in 0 until arr.length()) {
            val o = arr.optJSONObject(i) ?: continue
            val match = o.optString("service") == service && o.optString("user") == username && o.optLong("time") == time
            if (!match) out.put(o)
        }
        prefs(c).edit().putString(LOGINS, out.toString()).apply()
    }

    /** Update the secret of one stored login (matched as in [removeLogin]). */
    @Synchronized
    fun updateLoginSecret(c: Context, service: String, username: String, time: Long, secret: String) {
        val arr = loginsArr(c)
        for (i in 0 until arr.length()) {
            val o = arr.optJSONObject(i) ?: continue
            if (o.optString("service") == service && o.optString("user") == username && o.optLong("time") == time) {
                o.put("secret", secret.trim())
            }
        }
        prefs(c).edit().putString(LOGINS, arr.toString()).apply()
    }

    // --- per-app send recipes (which Send strategy worked; executor-internal) ------

    @Synchronized
    fun recordSendRecipe(c: Context, pkg: String, strategy: Int) {
        if (pkg.isBlank() || strategy < 0) return
        val o = sendsObj(c).put(pkg, strategy)
        prefs(c).edit().putString(SENDS, o.toString()).apply()
    }

    @Synchronized
    fun getSendRecipe(c: Context, pkg: String): Int =
        if (pkg.isBlank()) -1 else sendsObj(c).optInt(pkg, -1)

    /** All learned per-app send shortcuts (package -> strategy index), for the memory auditor. */
    @Synchronized
    fun sendRecipes(c: Context): List<Pair<String, Int>> {
        val o = sendsObj(c)
        return o.keys().asSequence().map { it to o.optInt(it, -1) }.toList()
    }

    @Synchronized
    fun removeSendRecipe(c: Context, pkg: String) {
        val o = sendsObj(c); o.remove(pkg)
        prefs(c).edit().putString(SENDS, o.toString()).apply()
    }

    private fun sendsObj(c: Context): JSONObject =
        try { JSONObject(prefs(c).getString(SENDS, "{}")!!) } catch (_: Exception) { JSONObject() }

    // --- structural SEND SKILL: the EXACT field + send control per app (not just a strategy index) -
    // The high-priority "persistent send skill" from the backlog. Learned only once a send is
    // CONFIRMED to have landed, and reused verbatim so a repeat send in a known app clicks the precise
    // Send button instead of re-deriving it through the heuristic ladder (which could wander onto the
    // mic). Keyed (like recipes) by package + screen size, so a fold/unfold gets its own entry.

    /** A learned exact send control: the text field's id + the Send button (by id and/or desc). */
    data class SendSkill(val fieldId: String, val sendId: String, val sendDesc: String, val needsExpand: Boolean)

    @Synchronized
    fun recordSendSkill(c: Context, key: String, fieldId: String, sendId: String, sendDesc: String, needsExpand: Boolean) {
        if (key.isBlank() || (sendId.isBlank() && sendDesc.isBlank())) return
        // NEVER persist a voice/mic control as "send" - learning the mic was the documented send bug.
        val low = "$sendId $sendDesc".lowercase()
        if (low.contains("voice") || low.contains("mic") || low.contains("wave")) return
        val o = sendSkillsObj(c).put(key, JSONObject()
            .put("field", fieldId).put("send", sendId).put("desc", sendDesc).put("expand", needsExpand))
        prefs(c).edit().putString(SEND_SKILLS, o.toString()).apply()
    }

    @Synchronized
    fun getSendSkill(c: Context, key: String): SendSkill? {
        val o = sendSkillsObj(c).optJSONObject(key) ?: return null
        return SendSkill(o.optString("field"), o.optString("send"), o.optString("desc"), o.optBoolean("expand"))
    }

    @Synchronized
    fun removeSendSkill(c: Context, key: String) {
        val o = sendSkillsObj(c); o.remove(key)
        prefs(c).edit().putString(SEND_SKILLS, o.toString()).apply()
    }

    private fun sendSkillsObj(c: Context): JSONObject =
        try { JSONObject(prefs(c).getString(SEND_SKILLS, "{}")!!) } catch (_: Exception) { JSONObject() }

    // --- skills (taught procedures the agent can follow itself) ------------------
    //
    // A skill is a GENERALIZED how-to the owner taught the agent - either by describing it
    // ("Train me: how to send a message in Gemini") or by demonstrating it once. We store the
    // model's generalized step list (labels, not coordinates), not a literal tap replay, so the
    // agent learns the METHOD and can adapt it next time. The best-matching skill is injected
    // into the planner for a new task.

    // [raw] is the literal demonstration/source it was learned from (the recorded taps, or the
    // owner's words), kept ALONGSIDE the generalized [steps] so the owner can see exactly what it
    // learned from what it recorded.
    data class Skill(val name: String, val app: String, val steps: String, val source: String, val time: Long, val raw: String = "", val pinned: Boolean = false, val conf: Int = 0)

    @Synchronized
    fun addSkill(c: Context, name: String, app: String, steps: String, source: String, raw: String = "") {
        val n = name.trim().take(80)
        // #6 PARAMETERIZE: a "completed" playbook is a literal replay of one run's exact values (it
        // "typed \"hi mom\""), which would have the agent re-type stale content next time. Turn that
        // content into fill-in slots so the playbook becomes a reusable TEMPLATE. ONLY for playbooks -
        // owner-described/taught skills keep their literal words (the content IS the instruction), and
        // demonstrations are already generalized by the model. The original is preserved in `raw`.
        val s = (if (source == "completed") templatize(steps) else steps).trim().take(MAX_SKILL_LEN)
        if (n.isBlank() || s.length < 4) return
        // Owner-taught skills (shown/described) are pinned the moment they're created - never auto-drop
        // a skill the owner DELIBERATELY taught.
        val ownerTaught = source.lowercase() in setOf("shown", "described", "taught", "demonstrated")
        val arr = skillsArr(c)
        // Replace any existing skill with the same name (newest teaching wins). Preserve the old raw
        // source, the pinned flag, and the confirmation count across the update.
        val out = JSONArray(); var priorRaw = ""; var priorPinned = false; var priorConf = 0
        for (i in 0 until arr.length()) {
            val o = arr.optJSONObject(i) ?: continue
            if (o.optString("name").equals(n, ignoreCase = true)) {
                priorRaw = o.optString("raw"); priorPinned = o.optBoolean("pinned"); priorConf = o.optInt("conf", 0)
            } else out.put(o)
        }
        // PLASTICITY / STABILITY: each re-save of the same skill (it succeeded again / was re-taught) is
        // a CONFIRMATION. A skill becomes PINNED - a stable core the cap can never evict - once it's
        // owner-taught, already pinned, or confirmed enough times. Everything else is a plastic, LRU-
        // evictable scratch layer. So learning new things never costs the agent its proven core.
        val conf = priorConf + 1
        val pinnedNow = ownerTaught || priorPinned || conf >= SKILL_PROTECT_AT
        out.put(JSONObject()
            .put("name", n).put("app", app.trim().take(40))
            .put("steps", s).put("source", source).put("time", System.currentTimeMillis())
            .put("conf", conf).put("pinned", pinnedNow)
            .put("raw", raw.trim().ifBlank { priorRaw }.take(MAX_SKILL_LEN)))
        // Evict the OLDEST UNPINNED skill to honor the cap, keeping the pinned core. Only if EVERY
        // skill is pinned do we drop the oldest outright (the cap is a hard ceiling).
        while (out.length() > MAX_SKILLS) {
            val drop = (0 until out.length()).firstOrNull { out.optJSONObject(it)?.optBoolean("pinned") != true } ?: 0
            out.remove(drop)
        }
        prefs(c).edit().putString(SKILLS, out.toString()).apply()
    }

    /** Owner pin/unpin from the Skills view: a pinned skill is never auto-evicted by the cap. */
    @Synchronized
    fun setSkillPinned(c: Context, name: String, on: Boolean) {
        val arr = skillsArr(c); val out = JSONArray()
        for (i in 0 until arr.length()) {
            val o = arr.optJSONObject(i) ?: continue
            if (o.optString("name").equals(name, ignoreCase = true)) o.put("pinned", on)
            out.put(o)
        }
        prefs(c).edit().putString(SKILLS, out.toString()).apply()
    }

    @Synchronized
    fun skills(c: Context): List<Skill> {
        val arr = skillsArr(c)
        return (0 until arr.length()).mapNotNull {
            val o = arr.optJSONObject(it) ?: return@mapNotNull null
            Skill(o.optString("name"), o.optString("app"), o.optString("steps"),
                o.optString("source"), o.optLong("time"), o.optString("raw"),
                o.optBoolean("pinned"), o.optInt("conf", 0))
        }.asReversed()
    }

    @Synchronized
    fun removeSkill(c: Context, name: String) {
        val arr = skillsArr(c); val out = JSONArray()
        for (i in 0 until arr.length()) {
            val o = arr.optJSONObject(i) ?: continue
            if (!o.optString("name").equals(name, ignoreCase = true)) out.put(o)
        }
        prefs(c).edit().putString(SKILLS, out.toString()).apply()
    }

    /** Parse a model "SKILL:/APP:/STEPS:" reply into a stored skill. Returns the name, or null
     *  if the reply had no usable steps. [fallbackName] is used when the model omits SKILL:. */
    @Synchronized
    fun addSkillFromModel(c: Context, modelText: String, source: String, fallbackName: String, raw: String = ""): String? {
        val lines = modelText.lines()
        var name = ""; var app = ""
        val stepLines = mutableListOf<String>()
        var inSteps = false
        for (raw in lines) {
            val line = raw.trim()
            when {
                line.startsWith("SKILL:", true) -> name = line.substringAfter(':').trim()
                line.startsWith("APP:", true) -> app = line.substringAfter(':').trim()
                line.startsWith("STEPS:", true) -> { inSteps = true; line.substringAfter(':').trim().let { if (it.isNotBlank()) stepLines.add(it) } }
                inSteps && line.isNotBlank() -> stepLines.add(line)
            }
        }
        // Fallback if the model ignored the format: treat any numbered lines as the steps.
        if (stepLines.isEmpty()) lines.map { it.trim() }.filter { it.matches(Regex("^\\d+[.)].*")) }.let { stepLines.addAll(it) }
        if (stepLines.isEmpty()) return null
        if (name.isBlank()) name = fallbackName.trim().take(80).ifBlank { "untitled skill" }
        if (app.equals("any", true)) app = ""
        addSkill(c, name, app, stepLines.joinToString("\n"), source, raw)
        return name
    }

    private fun skillsArr(c: Context): JSONArray =
        try { JSONArray(prefs(c).getString(SKILLS, "[]")) } catch (_: Exception) { JSONArray() }

    /** The skills most relevant to an objective (token overlap on name/app), best first. */
    @Synchronized
    fun skillsForObjective(c: Context, objective: String): List<Skill> {
        val want = tokens(objective)
        if (want.isEmpty()) return emptyList()
        return skills(c).map { it to scoreOverlap(want, tokens(it.name + " " + it.app)) }
            .filter { it.second > 0 }
            .sortedByDescending { it.second }
            .take(2).map { it.first }
    }

    /** Planner block naming the procedure(s) that apply to this task (empty if none). A playbook
     *  auto-saved from a SUCCESSFUL run (source="completed") is PROVEN - we pin it ("this exact
     *  sequence finished the task before"); an owner-taught one is framed as instruction. Both still
     *  say "adapt to the live screen", so pinning never forces a blind, screen-blind replay. */
    @Synchronized
    fun skillsBlockFor(c: Context, objective: String): String {
        val s = skillsForObjective(c, objective)
        if (s.isEmpty()) return ""
        val sb = StringBuilder()
        s.forEach { sk ->
            val header = if (sk.source == "completed")
                "✓ PROVEN PLAYBOOK - this sequence COMPLETED this task before; follow it, adapt only if the screen clearly differs:"
            else "THE OWNER TAUGHT YOU HOW TO DO THIS - follow it (adapt to the live screen):"
            sb.append(header).append("\n[").append(sk.name).append("]\n").append(sk.steps).append('\n')
            // #6: a templated playbook carries {text}/{number} slots - tell the model to FILL them from
            // THIS task, not to type the literal placeholder (so a generalized playbook actually generalizes).
            if (sk.steps.contains("{text}") || sk.steps.contains("{number}"))
                sb.append("(fill {text}/{number} with THIS task's actual message/value - never type the braces.)\n")
        }
        return sb.toString().trim()
    }

    /** #6: replace clearly-variable content in a playbook with fill-in slots, so it's a reusable
     *  template not a one-task replay. Conservative on purpose - only a quoted run (a typed message) and
     *  a long digit run (a phone number) become slots; navigation words are left exactly as they are. */
    private fun templatize(steps: String): String =
        steps.replace(Regex("\"[^\"]{1,200}\""), "{text}")
             .replace(Regex("\\b\\d{7,}\\b"), "{number}")

    private fun tokens(s: String): Set<String> =
        Regex("[a-z0-9]+").findAll(s.lowercase()).map { it.value }.filter { it.length >= 3 }.toSet()

    private fun scoreOverlap(a: Set<String>, b: Set<String>): Int = a.count { it in b }

    // --- "things I can't do yet" (failed tasks the owner can teach) --------------

    @Synchronized
    fun addUnknownAction(c: Context, what: String) {
        val t = what.trim().take(140)
        if (t.length < 4) return
        val arr = unknownArr(c)
        for (i in 0 until arr.length())
            if (arr.optJSONObject(i)?.optString("what").equals(t, ignoreCase = true)) return
        arr.put(JSONObject().put("what", t).put("time", System.currentTimeMillis()))
        while (arr.length() > MAX_UNKNOWN) arr.remove(0)
        prefs(c).edit().putString(UNKNOWN, arr.toString()).apply()
    }

    @Synchronized
    fun unknownActions(c: Context): List<String> {
        val arr = unknownArr(c)
        return (0 until arr.length()).mapNotNull { arr.optJSONObject(it)?.optString("what") }.asReversed()
    }

    @Synchronized
    fun removeUnknownAction(c: Context, what: String) {
        val arr = unknownArr(c); val out = JSONArray()
        for (i in 0 until arr.length()) {
            val o = arr.optJSONObject(i) ?: continue
            if (!o.optString("what").equals(what, ignoreCase = true)) out.put(o)
        }
        prefs(c).edit().putString(UNKNOWN, out.toString()).apply()
    }

    private fun unknownArr(c: Context): JSONArray =
        try { JSONArray(prefs(c).getString(UNKNOWN, "[]")) } catch (_: Exception) { JSONArray() }

    // --- device scan (the apps installed on this phone, a navigation aid) --------

    @Synchronized
    fun setDeviceApps(c: Context, apps: List<String>) {
        // Keep MORE of what's installed (the owner asked the agent to remember as much useful info
        // as it can); the injected line is still capped so the prompt stays lean.
        val arr = JSONArray(); apps.distinct().take(220).forEach { arr.put(it) }
        prefs(c).edit().putString(APPS, arr.toString()).apply()
    }

    @Synchronized
    fun deviceApps(c: Context): List<String> {
        val arr = try { JSONArray(prefs(c).getString(APPS, "[]")) } catch (_: Exception) { JSONArray() }
        return (0 until arr.length()).map { arr.optString(it) }
    }

    /** Compact one-line hint of what's installed, for the planner (empty if not scanned). */
    @Synchronized
    fun deviceAppsLine(c: Context): String {
        val a = deviceApps(c)
        if (a.isEmpty()) return ""
        return "Apps installed on this phone (open these by name): " + a.joinToString(", ").take(900)
    }

    // --- device profile (durable phone facts: model, OS, screen, DEFAULT apps) ----------
    // A compact, stable line the agent should always know so it routes correctly (e.g. uses THIS
    // phone's real default browser/texting app instead of guessing). Re-derived on each scan.

    @Synchronized
    fun setDeviceProfile(c: Context, text: String) {
        val t = text.trim().take(500)
        prefs(c).edit().putString(PROFILE, t).apply()
    }

    @Synchronized
    fun deviceProfile(c: Context): String = prefs(c).getString(PROFILE, "").orEmpty()

    /** The device-profile line for prompts (empty if not scanned yet). */
    @Synchronized
    fun deviceProfileLine(c: Context): String {
        val p = deviceProfile(c)
        return if (p.isBlank()) "" else "This device: $p"
    }

    // --- persistent IDENTITY (the agent's continuous self) -----------------------
    // Created ONCE on first use and surfaced into the agent's context every task, so the agent is the
    // SAME entity across the owner's whole experience - through app restarts, sleep, and emergency
    // stop (none of which touch it; SharedPreferences persists it). Only a full memory wipe (`clear`)
    // resets it, which reincarnates the agent with a fresh birth date. NOT per-session, NOT per-task.

    @Synchronized
    fun identity(c: Context): JSONObject {
        val o = try { JSONObject(prefs(c).getString(IDENTITY, "{}")!!) } catch (_: Exception) { JSONObject() }
        if (!o.has("born")) {   // first ever run on this install (or first after a wipe): give birth
            o.put("name", "Agent").put("born", System.currentTimeMillis()).put("tasks", 0)
            prefs(c).edit().putString(IDENTITY, o.toString()).apply()
        }
        return o
    }

    fun agentName(c: Context): String = identity(c).optString("name", "Agent").ifBlank { "Agent" }

    /** Count one finished task toward the agent's accumulated experience (a continuity signal). */
    @Synchronized
    fun bumpTasksDone(c: Context) {
        val o = identity(c)
        o.put("tasks", o.optInt("tasks", 0) + 1)
        prefs(c).edit().putString(IDENTITY, o.toString()).apply()
    }

    /** #10 RESUMABLE TASKS: persist the live task's state each step so an OS kill (OOM/black wallpaper)
     *  or a force-stop doesn't lose it. A clean finish() CLEARS it; if the process is reaped mid-task the
     *  record survives and the next launch can offer to resume. Stores the objective + the condensed
     *  progress note (what's already been done) + step count + time. */
    @Synchronized
    fun saveCheckpoint(c: Context, objective: String, progress: String, steps: Int) {
        if (objective.isBlank()) return
        val o = JSONObject().put("objective", objective.take(400)).put("progress", progress.take(600))
            .put("steps", steps).put("time", System.currentTimeMillis())
        prefs(c).edit().putString(CHECKPOINT, o.toString()).apply()
    }

    @Synchronized
    fun clearCheckpoint(c: Context) { prefs(c).edit().remove(CHECKPOINT).apply() }

    /** The pending interrupted task, if one was left within the last 6 hours (older = stale, ignored):
     *  (objective, progress-note, steps). Null when there's nothing worth resuming. */
    @Synchronized
    fun getCheckpoint(c: Context): Triple<String, String, Int>? {
        val s = prefs(c).getString(CHECKPOINT, null) ?: return null
        val o = try { JSONObject(s) } catch (_: Exception) { return null }
        if (System.currentTimeMillis() - o.optLong("time", 0) > 6 * 60 * 60 * 1000L) return null
        val obj = o.optString("objective"); if (obj.isBlank()) return null
        return Triple(obj, o.optString("progress"), o.optInt("steps", 0))
    }

    /** One line for the agent's context: who it is + that it persists across sessions (continuity),
     *  so it reasons as the SAME entity that ran before, not a blank slate each launch. */
    @Synchronized
    fun identityLine(c: Context): String {
        val o = identity(c)
        val name = o.optString("name", "Agent").ifBlank { "Agent" }
        val days = ((System.currentTimeMillis() - o.optLong("born", System.currentTimeMillis())) / 86_400_000L).toInt()
        val since = when { days <= 0 -> "today"; days == 1 -> "1 day ago"; else -> "$days days ago" }
        val tasks = o.optInt("tasks", 0)
        return "YOU: $name, this phone's OWN persistent agent - the SAME agent across every session. " +
            "Your memory carries over through restarts, sleep, and stop; you are NOT a blank slate. " +
            "You came online $since" + (if (tasks > 0) " and have completed $tasks tasks for your owner since." else ".")
    }

    // --- passive observations (what it learns by WATCHING the owner navigate) ----
    // Only filled when passive learning is enabled. Compact navigation facts like
    // "In Chrome, tapping 'New tab' opens a new tab". Surfaced in memory and fed to the planner.

    /**
     * Owner's "see it more than once" rule for PASSIVE learning. Counts how many times a
     * candidate navigation (keyed by tap-source + label + destination) has been SEEN and
     * returns true only once it reaches [threshold]. Persisted across sessions/restarts so a
     * path the owner does once per session still accumulates and is eventually learned - this
     * filters one-off coincidences WITHOUT permanently blocking real, repeated navigation
     * (the owner's explicit constraint: don't stop the agent gaining legit memories). Bounded.
     */
    @Synchronized
    fun passiveSightingReached(c: Context, key: String, threshold: Int = 2): Boolean {
        val k = key.trim()
        if (k.isBlank()) return false
        var o = try { JSONObject(prefs(c).getString(SIGHTINGS, "{}")!!) } catch (_: Exception) { JSONObject() }
        val n = o.optInt(k, 0) + 1
        // Cap the store so it can't grow unbounded. If it's huge there's been a lot of churn (mostly
        // one-off coincidences that never reached threshold), so a clean reset is fine - genuinely
        // repeated navigation will simply be re-counted and re-learned.
        if (o.length() > 400) o = JSONObject()
        o.put(k, n)
        prefs(c).edit().putString(SIGHTINGS, o.toString()).apply()
        return n >= threshold
    }

    @Synchronized
    fun addObservation(c: Context, text: String, key: String = "", goal: String = "") {
        val t = text.trim().take(160)
        if (t.length < 6) return
        val arr = obsArr(c)
        // `k` is the SITUATION (the app) and `g` is the GOAL this was learned under, so
        // observationsFor() can surface it again next time we're in the same situation working
        // toward a similar goal - the "made progress -> what caused it -> reuse it here" loop.
        for (i in 0 until arr.length()) {
            val o = arr.optJSONObject(i) ?: continue
            if (o.optString("t").equals(t, ignoreCase = true)) {
                // Worked AGAIN -> reinforce: bump recency, clear the "miss" strikes, count the HIT
                // (confidence), fold in goal. Enough clean hits with no strikes makes it "proven"
                // (isProvenObs) so the planner/action loop can PIN it - apply it directly.
                o.put("time", System.currentTimeMillis())
                o.put("miss", 0)
                o.put("hits", o.optInt("hits", 0) + 1)
                o.put("g", (o.optString("g") + " " + goal.trim()).trim().take(120))
                prefs(c).edit().putString(OBS, arr.toString()).apply()
                return
            }
        }
        arr.put(JSONObject().put("t", t).put("k", key.trim())
            .put("g", goal.trim().take(120)).put("time", System.currentTimeMillis()))
        while (arr.length() > 60) arr.remove(0)
        prefs(c).edit().putString(OBS, arr.toString()).apply()
    }

    @Synchronized
    fun observations(c: Context): List<String> {
        val arr = obsArr(c)
        return (0 until arr.length()).mapNotNull { arr.optJSONObject(it)?.optString("t") }.asReversed()
    }

    @Synchronized
    fun removeObservation(c: Context, text: String) {
        val arr = obsArr(c); val out = JSONArray()
        for (i in 0 until arr.length()) {
            val o = arr.optJSONObject(i) ?: continue
            if (!o.optString("t").equals(text, ignoreCase = true)) out.put(o)
        }
        prefs(c).edit().putString(OBS, out.toString()).apply()
    }

    /** A few most-recent observations for the planner (empty if none). Proven (pinned) ones are
     *  marked ✓ so the plan can pre-fill them with confidence. */
    @Synchronized
    fun observationsHint(c: Context): String {
        val arr = obsArr(c)
        val items = (arr.length() - 1 downTo 0).mapNotNull { arr.optJSONObject(it) }
            .filter { it.optString("t").isNotBlank() }.take(8)
        if (items.isEmpty()) return ""
        val header = if (items.any { isProvenObs(it) })
            "Navigation you've done before (✓ = PROVEN, prefer it; adapt to the live screen):"
        else "Navigation you've seen the owner do (reuse it):"
        return header + "\n" + items.joinToString("\n") { (if (isProvenObs(it)) "✓ " else "- ") + it.optString("t") }
    }

    /** Situation-matched recall: what worked (or what the owner did) in THIS app before, so the
     *  agent reuses it next time it's in the same situation. Matches the stored situation key (the
     *  app package); returns "" when there's nothing for here, so we never dump unrelated tips onto
     *  an unrelated screen. This is the retrieval half of the progress->cause->reuse loop. */
    @Synchronized
    fun observationsFor(c: Context, key: String, goal: String = "", max: Int = 5): String {
        if (key.isBlank()) return ""
        val k = key.trim()
        val goalWords = keywordsOf(goal)
        val arr = obsArr(c)
        // Each candidate carries a PROVEN flag (enough clean hits, no strikes) so we can PIN it -
        // proven items float to the top, get a ✓ marker, and are framed as "apply directly".
        data class Cand(val text: String, val proven: Boolean, val fresh: Boolean, val score: Int, val time: Long)
        val cands = (0 until arr.length()).mapNotNull { arr.optJSONObject(it) }
            .filter { it.optString("k").equals(k, ignoreCase = true) && it.optString("t").isNotBlank() }
            .map { o ->
                // Rank by PINNED (proven AND recently re-confirmed) first, then how well goal+text
                // matches what we're doing NOW, then recency. A proven-but-STALE step is no longer
                // pinned - it drops to a hint to re-verify (confidence decayed with age).
                val score = goalWords.count { it in keywordsOf(o.optString("g") + " " + o.optString("t")) }
                Cand(o.optString("t"), isProvenObs(o), isFresh(o), score, o.optLong("time"))
            }
            .sortedWith(compareByDescending<Cand> { it.proven && it.fresh }.thenByDescending { it.score }.thenByDescending { it.time })
            .distinctBy { it.text }.take(max)
        if (cands.isEmpty()) return ""
        val anyConfident = cands.any { it.proven && it.fresh }
        val anyStale = cands.any { it.proven && !it.fresh }
        val header = when {
            anyConfident -> "WHAT'S WORKED HERE BEFORE (✓ = PROVEN & recent: do it directly, but adapt if the screen looks different" +
                (if (anyStale) "; ⚠ = worked before but NOT lately - re-confirm it still works" else "") + "):"
            anyStale -> "WHAT'S WORKED HERE BEFORE (⚠ = worked before but NOT lately - the UI may have changed, so re-confirm before trusting it):"
            else -> "WHAT'S WORKED HERE BEFORE (reuse it if it fits):"
        }
        return header + "\n" + cands.joinToString("\n") {
            (when { it.proven && it.fresh -> "✓ "; it.proven -> "⚠ "; else -> "- " }) + it.text
        }
    }

    /** Merge the navigation destinations just seen in [app] into its accumulated map. Its OWN storage
     *  (not facts - so it never leaks into every prompt), keyed by app, newest-first, capped. Builds up
     *  an app's full set of "places you can go" across visits so the agent can be reminded of
     *  destinations that aren't on the current screen. No-op when nothing new is seen. */
    @Synchronized
    fun rememberNavDestinations(c: Context, app: String, dests: List<String>) {
        val a = app.trim().lowercase()
        if (a.isBlank() || dests.isEmpty()) return
        val root = try { JSONObject(prefs(c).getString(NAV, "{}") ?: "{}") } catch (_: Exception) { JSONObject() }
        val have = LinkedHashSet<String>()
        root.optJSONArray(a)?.let { for (i in 0 until it.length()) it.optString(i).takeIf { s -> s.isNotBlank() }?.let(have::add) }
        // newest first: the just-seen destinations float to the front, then the ones we already knew.
        val merged = LinkedHashSet<String>()
        dests.forEach { if (it.isNotBlank()) merged.add(it.take(24)) }
        merged.addAll(have)
        if (merged.size == have.size) return            // saw nothing new - skip the write
        val out = JSONArray(); merged.take(MAX_NAV_DESTS).forEach { out.put(it) }
        root.put(a, out)
        if (root.length() > MAX_NAV_APPS) root.keys().asSequence().firstOrNull { it != a }?.let(root::remove)
        prefs(c).edit().putString(NAV, root.toString()).apply()
    }

    /** The accumulated navigation destinations known for [app] (newest first), or empty. */
    @Synchronized
    fun navDestinationsFor(c: Context, app: String): List<String> {
        val a = app.trim().lowercase(); if (a.isBlank()) return emptyList()
        val arr = try { JSONObject(prefs(c).getString(NAV, "{}") ?: "{}").optJSONArray(a) } catch (_: Exception) { null }
            ?: return emptyList()
        return (0 until arr.length()).mapNotNull { arr.optString(it).ifBlank { null } }
    }

    /** NOVELTY (world-state research: "have I seen this state before?"). Records the structural
     *  signature [sig] of a screen met in [app] and returns whether it was ALREADY known. true =
     *  FAMILIAR (seen before, lean on memory); false = NOVEL (first time here, explore carefully).
     *  Durable + capped, newest-first. A blank app/sig returns true so the caller stays silent. */
    @Synchronized
    fun seenScreen(c: Context, app: String, sig: String): Boolean {
        val a = app.trim().lowercase()
        if (a.isBlank() || sig.isBlank()) return true
        val root = try { JSONObject(prefs(c).getString(SEEN, "{}") ?: "{}") } catch (_: Exception) { JSONObject() }
        val arr = root.optJSONArray(a) ?: JSONArray()
        for (i in 0 until arr.length()) if (arr.optString(i) == sig) return true   // familiar
        val out = JSONArray().put(sig)                                              // novel -> record it, newest first
        for (i in 0 until minOf(arr.length(), MAX_SEEN_PER_APP - 1)) out.put(arr.optString(i))
        root.put(a, out)
        if (root.length() > MAX_SEEN_APPS) root.keys().asSequence().firstOrNull { it != a }?.let(root::remove)
        prefs(c).edit().putString(SEEN, root.toString()).apply()
        return false
    }

    /** The live on-screen targets that are PROVEN to work in [app]: the quoted label from a
     *  "clicked X" observation (e.g. "Pen mode"). Lets the action space mark the actual button with a
     *  ✓ - so when the agent peeks at the screen it sees which buttons advanced past tasks here, with
     *  the what-worked memory riding on the button itself instead of in a separate block. */
    @Synchronized
    fun provenTargetsFor(c: Context, app: String): List<String> {
        if (app.isBlank()) return emptyList()
        val arr = obsArr(c)
        val out = LinkedHashSet<String>()
        for (i in 0 until arr.length()) {
            val o = arr.optJSONObject(i) ?: continue
            // Only PINNED (proven AND recently re-confirmed) steps earn the on-button ✓ - a stale
            // one is dropped here so the agent re-verifies it instead of trusting a checkmark on a UI
            // that may have changed since (confidence decays with age).
            if (!o.optString("k").equals(app, ignoreCase = true) || !isProvenObs(o) || !isFresh(o)) continue
            val label = Regex("\"clicked\\s+(.+?)\"").find(o.optString("t"))
                ?.groupValues?.get(1)?.trim()?.removeSurrounding("(", ")")?.trim() ?: continue
            if (label.length in 2..40) out.add(label)
        }
        return out.toList()
    }

    /** PROVEN = the only confidence level we PIN/preload into the agent's actions: re-confirmed
     *  working at least twice with a SPOTLESS record (zero strikes) - effectively 100% in its track
     *  record. Any failure resets hits (see penalizeObservation), so a pin must be earned cleanly,
     *  not flakily. Conservative on purpose - pinning a stale step could break normal adaptation,
     *  and the failsafe (de-pin on the first stall) catches a pull that didn't actually apply. */
    private fun isProvenObs(o: JSONObject): Boolean = o.optInt("hits", 0) >= 2 && o.optInt("miss", 0) == 0

    // CONFIDENCE DECAYS WITH AGE (world-state research: "an old memory can be worse than none; UIs
    // change"). A proven step not re-confirmed in this long is no longer PINNED with confidence: it
    // loses its inline ✓ and is surfaced as a CHALLENGE to re-verify ("worked before, not lately").
    // A fresh hit (addObservation bumps "time") reaffirms it and restores the ✓. So memory ages out
    // of certainty gracefully instead of misleading the agent after the UI it learned has changed.
    private const val OBS_STALE_MS = 21L * 24 * 60 * 60 * 1000   // 21 days without a re-confirmation
    private fun isFresh(o: JSONObject): Boolean =
        System.currentTimeMillis() - o.optLong("time", 0L) <= OBS_STALE_MS

    /** Distinctive words of a phrase for loose goal matching (drops short/filler words). */
    private fun keywordsOf(s: String): Set<String> {
        val stop = setOf("the", "and", "with", "that", "this", "your", "you", "for", "into", "from",
            "please", "want", "need", "like", "just", "then", "will", "would", "should", "have",
            "about", "their", "there", "them", "they", "what", "when", "begin", "start")
        return s.lowercase().split(Regex("[^a-z0-9]+"))
            .filter { it.length >= 4 && it !in stop }.toSet()
    }

    /** Lifecycle "it didn't work here": we recalled a memory for this app and the action it implies
     *  just STALLED, so demote it; after a few strikes it no longer applies and is dropped. This is
     *  the third state the owner described (same screen -> recall -> worked: reinforce / didn't:
     *  doesn't apply). Matched by app + the action text so we only penalize the relevant memory. */
    @Synchronized
    fun penalizeObservation(c: Context, key: String, actionText: String) {
        if (key.isBlank() || actionText.length < 3) return
        val needle = actionText.lowercase()
        val arr = obsArr(c); val out = JSONArray(); var changed = false
        for (i in 0 until arr.length()) {
            val o = arr.optJSONObject(i) ?: continue
            if (o.optString("k").equals(key, true) && o.optString("t").lowercase().contains(needle)) {
                val miss = o.optInt("miss", 0) + 1
                changed = true
                if (miss >= 3) continue        // 3 strikes -> it doesn't apply here; drop it
                o.put("miss", miss)
                // Failsafe for a PINNED memory that didn't actually apply: knock its confidence back
                // so it is no longer "proven" and must FULLY re-earn that status (a couple of clean
                // hits) before it's ever pinned/preloaded again. A flaky step can't stay pinned.
                o.put("hits", 0)
            }
            out.put(o)
        }
        if (changed) prefs(c).edit().putString(OBS, out.toString()).apply()
    }

    /** One-shot cleanup of the JUNK the passive recorder used to capture (typed text / pasted
     *  messages / the agent's own feedback strings stored as "navigation"). Keeps the memory the
     *  owner actually wants to see, and runs cheaply on start so they don't have to hand-delete. */
    @Synchronized
    fun pruneJunkObservations(c: Context) {
        val arr = obsArr(c); val out = JSONArray(); var changed = false
        for (i in 0 until arr.length()) {
            val o = arr.optJSONObject(i) ?: continue
            if (isJunkObservation(o.optString("t"))) { changed = true; continue }
            out.put(o)
        }
        if (changed) prefs(c).edit().putString(OBS, out.toString()).apply()
    }

    /**
     * Owner's "variable vs persistent" distinction for LEARNING. Returns true when an on-screen
     * label is VARIABLE content - a clock time, date/day, count, price, duration - rather than
     * STABLE chrome (Search, Compose, Menu, a tab) that is ALWAYS there. We only want to learn
     * navigation keyed on stable controls; a fact like "tapping '2:45 PM' opens..." is brittle junk.
     * Deliberately HIGH-PRECISION (only flags clearly-variable patterns) so it never blocks a real
     * control and never stops the agent gaining a legit memory - the owner's explicit constraint.
     */
    fun looksLikeVariableContent(label: String): Boolean {
        val l = label.lowercase().trim()
        if (l.isEmpty()) return false
        // money / decimals / counts / durations / any multi-digit number
        if (Regex("""[$€£]|\d+[.,]\d|\d+\s*(notification|unread|message|item|min|hr|hour|day)|\b\d{2,}\b""").containsMatchIn(l)) return true
        // clock times
        if (Regex("""\b\d{1,2}:\d{2}\b|\b\d{1,2}\s?(am|pm)\b""").containsMatchIn(l)) return true
        // relative dates / weekday labels (timeline/list timestamps)
        if (Regex("""\b(today|yesterday|tomorrow|just now|mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)\b""").containsMatchIn(l)) return true
        return false
    }

    private fun isJunkObservation(t: String): Boolean {
        if (t.length > 96 || t.contains("**") || t.contains("#")) return true
        val low = t.lowercase()
        if (low.contains("now send") || low.contains("do not type") || low.contains("don't type") ||
            low.contains("confirming") || low.contains("waiting for the reply") ||
            low.contains("do not type again")) return true
        // Passive-nav noise: the KEYBOARD popping up, the status bar/System UI, or going HOME to the
        // launcher are NOT navigation - these were the bulk of the garbage facts the owner saw.
        if (Regex("""opens (samsung keyboard|.*keyboard|system ui|one ui home|.*launcher)$""").containsMatchIn(low))
            return true
        if (Regex("""^in (samsung keyboard|.*keyboard|system ui),""").containsMatchIn(low)) return true
        // The tapped "label" is dynamic content (price/badge/version) or a system/media control, not a
        // stable navigation button.
        Regex("tapping (.+?) opens ", RegexOption.IGNORE_CASE).find(t)?.let {
            val lbl = it.groupValues[1].trim(); val ll = lbl.lowercase()
            if (lbl.length > 28 || lbl.split(Regex("\\s+")).size > 4) return true
            if (looksLikeVariableContent(lbl)) return true
            if (ll in setOf("pause", "play", "stop", "expand", "collapse", "maximize", "minimize",
                    "close", "back", "home", "forward", "up", "down", "mute", "unmute", "upgrade",
                    "pay", "copy", "paste", "cut", "share", "menu", "settings", "next", "previous",
                    "skip", "done", "cancel")) return true
            if (Regex("""aspect ratio|toolbar function|view details|more options|(pause|play|stop) video""").containsMatchIn(ll))
                return true
        }
        // Active-learning clutter: a GENERIC verb or an UNLABELED click recorded as "→ advanced the
        // task" carries no situational value (the success playbook already keeps the real sequence).
        // Drop "opened app X", "typed the text", "pressed Send", "scrolled ...", "clicked ()"; KEEP a
        // specific named click like "clicked (Pen mode)".
        if (low.contains("advanced the task")) {
            val act = Regex("\"([^\"]*)\"").find(low)?.groupValues?.get(1)?.trim() ?: ""
            if (act.startsWith("opened app") || act == "typed the text" || act == "pressed send" ||
                act.startsWith("scrolled") ||
                (act.startsWith("clicked") && act.removePrefix("clicked").trim().removeSurrounding("(", ")").trim().isBlank()))
                return true
        }
        return false
    }

    private fun obsArr(c: Context): JSONArray =
        try { JSONArray(prefs(c).getString(OBS, "[]")) } catch (_: Exception) { JSONArray() }

    // --- screen-keyed MISTAKE memory (the owner's "stop repeating mistakes" - surfaced, NOT vetoed) ----
    // The negative twin of observations: remember that an action did NOTHING on a given app + screen so the
    // agent is CAUTIONED (a ✗ it reads) next time it's on that screen - it never blocks, and SUCCESS clears
    // it, so a control whose value depends on state (Gemini's Send) is never permanently poisoned. Generic
    // (app + structural signature + action), capped, decays by age.
    private fun mistakesArr(c: Context): JSONArray =
        try { JSONArray(prefs(c).getString(MISTAKES, "[]")) } catch (_: Exception) { JSONArray() }

    /** Structural signature of a screen: its set of element ids (text stripped), so "the same screen" is
     *  recognized across visits even as labels/values change. Falls back to a length bucket for id-less
     *  screens. Mirrors the orchestrator's own signature so note/recall agree on what "this screen" is. */
    private fun sigOf(screen: String): String {
        val ids = Regex("id:(\\S+)").findAll(screen).map { it.groupValues[1] }.toSortedSet()
        return if (ids.isNotEmpty()) ids.joinToString(",").hashCode().toString() else "len${screen.length / 200}"
    }

    @Synchronized
    fun noteMistake(c: Context, app: String, screen: String, action: String) {
        val a = app.trim().lowercase(); val s = sigOf(screen); val act = action.trim().take(80)
        if (a.isBlank() || act.length < 3) return
        val arr = mistakesArr(c)
        for (i in 0 until arr.length()) {
            val o = arr.optJSONObject(i) ?: continue
            if (o.optString("k") == a && o.optString("s") == s && o.optString("a").equals(act, true)) {
                o.put("n", o.optInt("n", 0) + 1).put("time", System.currentTimeMillis())
                prefs(c).edit().putString(MISTAKES, arr.toString()).apply(); return
            }
        }
        arr.put(JSONObject().put("k", a).put("s", s).put("a", act).put("n", 1).put("time", System.currentTimeMillis()))
        while (arr.length() > 80) arr.remove(0)
        prefs(c).edit().putString(MISTAKES, arr.toString()).apply()
    }

    /** SUCCESS clears the ✗: if [action] just worked at this app+screen, drop any mistake against it so a
     *  state-dependent control (advances one moment, not another) is never permanently flagged. */
    @Synchronized
    fun clearMistake(c: Context, app: String, screen: String, action: String) {
        val a = app.trim().lowercase(); val s = sigOf(screen); val act = action.trim().take(80)
        val arr = mistakesArr(c); val out = JSONArray(); var changed = false
        for (i in 0 until arr.length()) {
            val o = arr.optJSONObject(i) ?: continue
            if (o.optString("k") == a && o.optString("s") == s && o.optString("a").equals(act, true)) { changed = true; continue }
            out.put(o)
        }
        if (changed) prefs(c).edit().putString(MISTAKES, out.toString()).apply()
    }

    /** Cautions for THIS app+screen: actions that did nothing here at least twice and recently. A surfaced
     *  reminder the agent READS, never a block; "" when there's nothing. */
    @Synchronized
    fun mistakesFor(c: Context, app: String, screen: String, max: Int = 4): String {
        val a = app.trim().lowercase(); val s = sigOf(screen)
        if (a.isBlank()) return ""
        val now = System.currentTimeMillis()
        val arr = mistakesArr(c)
        val items = (0 until arr.length()).mapNotNull { arr.optJSONObject(it) }
            .filter { it.optString("k") == a && it.optString("s") == s && it.optInt("n") >= 2 &&
                now - it.optLong("time") < 14L * 24 * 3600_000L }   // decay: ignore older than ~2 weeks
            .sortedByDescending { it.optInt("n") }.take(max)
        if (items.isEmpty()) return ""
        return "TRIED HERE & DID NOTHING (✗ - don't recycle these unless the screen clearly changed; pick a DIFFERENT action):\n" +
            items.joinToString("\n") { "✗ ${it.optString("a")} (×${it.optInt("n")})" }
    }

    // --- bad memories (a small, reflective "mistakes I'm learning from" log) -----------------
    // A LIMITED hidden record of times a choice/memory led the agent wrong: what it did wrong and
    // what it should have done. Surfaced (a) to the model as "MISTAKES TO AVOID" so it can learn
    // from them, and (b) in the memory viewer so the owner can read/clear them.

    @Synchronized
    fun addBadMemory(c: Context, mistake: String, better: String) {
        val m = mistake.trim().take(140); val b = better.trim().take(140)
        if (m.length < 6) return
        val arr = badArr(c)
        for (i in 0 until arr.length())
            if (arr.optJSONObject(i)?.optString("m").equals(m, ignoreCase = true)) {
                arr.optJSONObject(i)?.put("time", System.currentTimeMillis()); // reinforce recency
                prefs(c).edit().putString(BAD, arr.toString()).apply(); return
            }
        arr.put(JSONObject().put("m", m).put("b", b).put("time", System.currentTimeMillis()))
        while (arr.length() > 12) arr.remove(0)   // keep it LIMITED but healthy
        prefs(c).edit().putString(BAD, arr.toString()).apply()
    }

    /**
     * Owner's PER-STEP rating from the task log -> durable memory: a step they mark "worked" becomes
     * a confirmed positive lesson, one they mark "failed" becomes a "mistake to avoid", each scoped to
     * the task so later recall stays relevant. This is the owner teaching the agent exactly WHERE a
     * task succeeded or failed ("these actions worked, these didn't"), straight into what it reuses.
     */
    @Synchronized
    fun recordStepFeedback(c: Context, objective: String, step: String, rating: Int) {
        val obj = objective.lineSequence().firstOrNull { it.isNotBlank() }?.trim()?.take(60).orEmpty()
        val s = step.trim().take(90)
        if (s.length < 4) return
        when {
            rating > 0 -> addLesson(c, "For \"$obj\": \"$s\" works - the owner confirmed this step.")
            rating < 0 -> addBadMemory(c, "Doing \"$obj\", this step was WRONG: $s",
                "the owner marked that step a failure - at that point take a DIFFERENT action")
        }
    }

    /** (mistake, what-I-should-have-done) pairs, newest first - for the memory viewer. */
    @Synchronized
    fun badMemories(c: Context): List<Pair<String, String>> {
        val arr = badArr(c)
        return (arr.length() - 1 downTo 0).mapNotNull { arr.optJSONObject(it) }
            .map { it.optString("m") to it.optString("b") }
    }

    @Synchronized
    fun removeBadMemory(c: Context, mistake: String) {
        val arr = badArr(c); val out = JSONArray()
        for (i in 0 until arr.length()) {
            val o = arr.optJSONObject(i) ?: continue
            if (!o.optString("m").equals(mistake, ignoreCase = true)) out.put(o)
        }
        prefs(c).edit().putString(BAD, out.toString()).apply()
    }

    /** A few recent mistakes for the action prompt, so the agent doesn't repeat them. "" if none. */
    @Synchronized
    fun badMemoriesHint(c: Context, max: Int = 4): String {
        val b = badMemories(c).take(max)
        if (b.isEmpty()) return ""
        return "MISTAKES TO AVOID (you did these before - do the better thing):\n" +
            b.joinToString("\n") { "- ${it.first}${if (it.second.isNotBlank()) " → better: ${it.second}" else ""}" }
    }

    private fun badArr(c: Context): JSONArray =
        try { JSONArray(prefs(c).getString(BAD, "[]")) } catch (_: Exception) { JSONArray() }

    /** WIPE the agent's memory - the ONE thing that resets it to a blank slate (a fresh entity with
     *  a new identity born next run). Everything LEARNED goes, including nav-maps, structural send
     *  skills, and the persistent identity itself - so a wipe truly forgets, not half-forgets (those
     *  three were silently surviving wipes before). The device HARDWARE profile is kept (it's the
     *  phone, not learned experience; re-onboarding it is the owner's separate choice). */
    @Synchronized
    fun clear(c: Context) =
        prefs(c).edit().remove(FACTS).remove(LESSONS).remove(LOGINS).remove(SENDS)
            .remove(SEND_SKILLS).remove(NAV).remove(SEEN).remove(IDENTITY)
            .remove(SKILLS).remove(UNKNOWN).remove(APPS).remove(OBS).remove(BAD).apply()

    private fun lessonsArr(c: Context): JSONArray =
        try { JSONArray(prefs(c).getString(LESSONS, "[]")) } catch (_: Exception) { JSONArray() }

    // --- prompt injection ------------------------------------------------------

    /** Compact block of what the agent knows, for the action prompt (empty if nothing). */
    @Synchronized
    fun forPrompt(c: Context): String {
        val f = facts(c)
        val sb = StringBuilder()
        sb.append(identityLine(c)).append('\n')   // who you are + that you persist across sessions
        deviceProfileLine(c).let { if (it.isNotBlank()) sb.append(it).append('\n') }
        if (f.length() > 0) {
            sb.append("Known facts: ")
            sb.append(f.keys().asSequence().joinToString("; ") { "$it = ${f.optString(it)}" })
            sb.append('\n')
        }
        val ls = lessons(c)
        if (ls.isNotEmpty()) {
            sb.append("Lessons from experience:\n")
            ls.takeLast(12).forEach { sb.append("- ").append(it).append('\n') }
        }
        return sb.toString().trim()
    }

    /** Goal-aware variant: facts + device profile + the lessons RELEVANT to [goal] (pulled when
     *  they apply, instead of dumping the last-N). Used in the action loop where we know the task. */
    @Synchronized
    fun forPrompt(c: Context, goal: String): String {
        val f = facts(c)
        val sb = StringBuilder()
        sb.append(identityLine(c)).append('\n')   // who you are + that you persist across sessions
        deviceProfileLine(c).let { if (it.isNotBlank()) sb.append(it).append('\n') }
        if (f.length() > 0) {
            sb.append("Known facts: ")
            sb.append(f.keys().asSequence().joinToString("; ") { "$it = ${f.optString(it)}" })
            sb.append('\n')
        }
        val ls = lessonsFor(c, goal, 8)
        if (ls.isNotEmpty()) {
            sb.append("Lessons that may apply here:\n")
            ls.forEach { sb.append("- ").append(it).append('\n') }
        }
        return sb.toString().trim()
    }
}

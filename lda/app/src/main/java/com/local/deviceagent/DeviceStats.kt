package com.local.deviceagent

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager
import android.os.PowerManager

/**
 * Lightweight device-health readouts (battery + thermal) used for the safety
 * guards and for diagnostics in the debug log. All calls are cheap and safe to
 * poll once per agent step.
 */
object DeviceStats {

    fun batteryPercent(context: Context): Int {
        val bm = context.getSystemService(Context.BATTERY_SERVICE) as? BatteryManager ?: return -1
        val pct = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
        return if (pct in 0..100) pct else -1
    }

    fun isCharging(context: Context): Boolean {
        val i = context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED)) ?: return false
        val status = i.getIntExtra(BatteryManager.EXTRA_STATUS, -1)
        return status == BatteryManager.BATTERY_STATUS_CHARGING ||
            status == BatteryManager.BATTERY_STATUS_FULL
    }

    /** PowerManager thermal status (0 none .. 6 shutdown); -1 if unknown. */
    fun thermalStatus(context: Context): Int {
        val pm = context.getSystemService(Context.POWER_SERVICE) as? PowerManager ?: return -1
        return try { pm.currentThermalStatus } catch (_: Exception) { -1 }
    }

    fun thermalLabel(status: Int): String = when (status) {
        PowerManager.THERMAL_STATUS_NONE -> "none"
        PowerManager.THERMAL_STATUS_LIGHT -> "light"
        PowerManager.THERMAL_STATUS_MODERATE -> "moderate"
        PowerManager.THERMAL_STATUS_SEVERE -> "severe"
        PowerManager.THERMAL_STATUS_CRITICAL -> "critical"
        PowerManager.THERMAL_STATUS_EMERGENCY -> "emergency"
        PowerManager.THERMAL_STATUS_SHUTDOWN -> "shutdown"
        else -> "unknown"
    }

    // --- MEMORY (the owner's #1 failure mode: the RAM ceiling) -----------------

    private fun memInfo(context: Context): android.app.ActivityManager.MemoryInfo? {
        val am = context.getSystemService(Context.ACTIVITY_SERVICE) as? android.app.ActivityManager ?: return null
        val mi = android.app.ActivityManager.MemoryInfo()
        return try { am.getMemoryInfo(mi); mi } catch (_: Exception) { null }
    }

    /** Available / total system RAM in MB (-1 if unknown). availMem is the headroom before the
     *  low-memory killer starts reaping - logging it per step makes the OOM boundary VISIBLE. */
    fun availMemMb(context: Context): Long = memInfo(context)?.let { it.availMem / (1024 * 1024) } ?: -1
    fun totalMemMb(context: Context): Long = memInfo(context)?.let { it.totalMem / (1024 * 1024) } ?: -1
    /** The OS already considers memory low (the killer is active) - a genuine close-call signal. */
    fun lowMemory(context: Context): Boolean = memInfo(context)?.lowMemory ?: false

    /** LIVE memory pressure (re-read each use, NOT cached) - the single signal the adaptive throttle/degrade
     *  reads so the cache, the image rung, and the inter-step pacing all agree. The owner's directive: run on
     *  budget hardware, "throttle so it never crashes but is just slower", and use as little as necessary while
     *  "breathing" when there's juice. NONE = headroom, run full quality/speed. TIGHT = free RAM getting low,
     *  trim the cheap things (cache, pace a little). CRITICAL = the OS is about to start killing - back off hard
     *  (lean image, real pauses) so the loop survives instead of getting OS-reaped mid-task. */
    enum class MemPressure { NONE, TIGHT, CRITICAL }
    fun memPressure(context: Context): MemPressure {
        val mi = memInfo(context) ?: return MemPressure.NONE
        val free = mi.availMem / (1024 * 1024)
        return when {
            mi.lowMemory || free in 1..1200 -> MemPressure.CRITICAL
            free in 1..2400 -> MemPressure.TIGHT
            else -> MemPressure.NONE
        }
    }

    // --- HARDWARE / MODEL DETECTION (drives the adaptive "lighter path") -------

    /** Coarse hardware tier from total RAM, so the SAME agent takes a lighter route on a weak phone
     *  (e.g. a 4GB Galaxy A16) and the rich route on a Fold with 12GB+. This is the detection the owner
     *  wants to "guide the path to completion": one build, many devices (the solutions/business vision). */
    enum class DeviceTier { LEAN, MID, RICH }
    fun deviceTier(context: Context): DeviceTier {
        val gb = totalMemMb(context) / 1024.0
        return when {
            gb <= 0 -> DeviceTier.MID          // unknown -> middle, don't over-degrade a device we can't read
            gb < 4.5 -> DeviceTier.LEAN
            gb < 8.5 -> DeviceTier.MID
            else -> DeviceTier.RICH
        }
    }

    /** Is the imported model a HEAVY one (~E4B, ~4GB+ of weights) vs a light one (~E2B)? Inferred from
     *  the file size - the app can't ask the runtime, but the footprint is what stresses RAM. */
    fun modelIsHeavy(modelPath: String?): Boolean {
        val len = modelPath?.let { try { java.io.File(it).length() } catch (_: Exception) { 0L } } ?: 0L
        return len > 3_500_000_000L
    }

    /** Should perception take the LIGHTER path on THIS device+model? True when the hardware is weak, or a
     *  heavy model is paired with only mid hardware - the combinations where the rich path courts the RAM
     *  ceiling. A strong device (the dev Fold, RICH) returns false, so the OWNER'S TEST DEVICE is never
     *  degraded - it keeps running the full rich path he's tuning against. */
    fun useLeanPath(context: Context, modelPath: String?): Boolean {
        val tier = deviceTier(context)
        return tier == DeviceTier.LEAN || (tier == DeviceTier.MID && modelIsHeavy(modelPath))
    }

    /** One-line device+model identity for the TOP of a task's log - so a log pasted from ANY device is
     *  self-describing: which phone, Android, how much RAM, which model, light/heavy, the chosen path.
     *  Essential once the agent runs on hardware other than the dev Fold (multi-device / customers). */
    fun deviceHeader(context: Context, modelPath: String?, helperOn: Boolean): String {
        val heavy = if (modelIsHeavy(modelPath)) "heavy~E4B" else "light~E2B"
        val model = modelPath?.substringAfterLast('/')?.take(40) ?: "none"
        return "${android.os.Build.MODEL} / Android ${android.os.Build.VERSION.RELEASE} / " +
            "ram ${availMemMb(context)}of${totalMemMb(context)}MB / tier ${deviceTier(context)} / " +
            "model $model[$heavy] / helper ${if (helperOn) "on" else "off"} / " +
            "path ${if (useLeanPath(context, modelPath)) "LEAN" else "rich"}"
    }

    /** MODEL-FITNESS GUARD (the A16 / multi-device / business case): a HEAVY model (~E4B, ~4GB of
     *  weights) simply cannot fit a LEAN device's RAM (a 4GB phone) no matter how light perception gets -
     *  the weights alone overflow, so it OOMs on load every time. Detect that combo so the owner/customer
     *  gets a clear "use a smaller model" signal instead of silent black-wallpaper crashes. Conservative:
     *  only flags the clearly-impossible heavy-on-LEAN pairing, never the dev Fold (RICH) or a light model. */
    fun modelTooHeavy(context: Context, modelPath: String?): Boolean =
        modelIsHeavy(modelPath) && deviceTier(context) == DeviceTier.LEAN

    /** A one-line, human-readable warning when the imported model won't fit this device, else "". */
    fun fitnessWarning(context: Context, modelPath: String?): String =
        if (modelTooHeavy(context, modelPath))
            "This model is too large for this phone's RAM (${totalMemMb(context)}MB) - it will likely crash on load. Import a smaller (E2B) model for reliable use on this device."
        else ""

    /** One-line summary for the debug log. */
    fun snapshot(context: Context): String {
        val t = thermalStatus(context)
        return "battery=${batteryPercent(context)}% charging=${isCharging(context)} " +
            "thermal=${thermalLabel(t)}($t) ram=${availMemMb(context)}of${totalMemMb(context)}MB"
    }
}

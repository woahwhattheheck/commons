package com.local.deviceagent

import android.graphics.Bitmap
import android.graphics.Color

/**
 * Tiny perceptual fingerprint of a screenshot ("pixel map"), so the agent can tell whether the
 * screen ACTUALLY changed after an action - the signal the accessibility tree can't give on a
 * game/canvas (the tree is empty/static there, yet the pixels move). It's an average-hash: downscale
 * to 8x8 grayscale, one bit per cell for above/below the mean -> a 64-bit fingerprint. The Hamming
 * distance between two frames is a cheap "how much did it visibly change" measure (0 = identical,
 * ~64 = totally different). Cheap enough to run every step; robust to minor noise/animation.
 */
object PixelMap {
    private const val N = 8

    fun hash(bmp: Bitmap): Long {
        val small = try { Bitmap.createScaledBitmap(bmp, N, N, true) } catch (_: Exception) { return 0L }
        val lum = IntArray(N * N)
        var sum = 0L
        for (y in 0 until N) for (x in 0 until N) {
            val p = small.getPixel(x, y)
            val l = (Color.red(p) * 299 + Color.green(p) * 587 + Color.blue(p) * 114) / 1000
            lum[y * N + x] = l; sum += l
        }
        if (small !== bmp) small.recycle()
        val mean = sum / (N * N)
        var h = 0L
        for (i in lum.indices) if (lum[i] >= mean) h = h or (1L shl i)
        return h
    }

    /** 0 = identical, up to 64 = completely different. */
    fun distance(a: Long, b: Long): Int = java.lang.Long.bitCount(a xor b)
}

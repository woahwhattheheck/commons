package com.local.deviceagent

import android.content.Context
import android.graphics.PixelFormat
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView

class ConfirmationOverlay {
    private var view: View? = null
    private var wm: WindowManager? = null

    fun show(context: Context, message: String, onYes: () -> Unit, onNo: () -> Unit) {
        dismiss()
        val windowManager = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
        wm = windowManager

        val root = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setBackgroundColor(0x88000000.toInt())
            setPadding(60, 60, 60, 60)
        }
        val card = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(0xFF202020.toInt())
            setPadding(48, 48, 48, 48)
        }
        val title = TextView(context).apply {
            text = "Confirm action"
            textSize = 18f
            setTextColor(0xFFFFFFFF.toInt())
            setPadding(0, 0, 0, 16)
        }
        val msg = TextView(context).apply {
            text = message
            textSize = 15f
            setTextColor(0xFFDDDDDD.toInt())
            setPadding(0, 0, 0, 32)
        }
        val buttons = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.END
        }
        val no = Button(context).apply {
            text = "No, stop"
            setOnClickListener { onNo() }
        }
        val yes = Button(context).apply {
            text = "Yes, allow"
            setOnClickListener { onYes() }
        }
        buttons.addView(no)
        buttons.addView(yes)
        card.addView(title)
        card.addView(msg)
        card.addView(buttons)
        root.addView(card)

        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_DIM_BEHIND,
            PixelFormat.TRANSLUCENT
        ).apply { dimAmount = 0.5f }

        view = root
        try { windowManager.addView(root, params) } catch (_: Exception) {}
    }

    fun dismiss() {
        val v = view ?: return
        try { wm?.removeView(v) } catch (_: Exception) {}
        view = null
    }
}

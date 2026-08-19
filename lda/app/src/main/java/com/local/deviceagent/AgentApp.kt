package com.local.deviceagent

import android.app.Activity
import android.app.Application
import android.os.Bundle

/**
 * App entry point. Its one job today is to stamp EVERY screen with the ownership label (via an
 * activity lifecycle callback) so "Property of Bryce Muhlnickel" is present at all times without
 * having to touch each Activity individually - and any future screen gets it automatically too.
 */
class AgentApp : Application() {
    override fun onCreate() {
        super.onCreate()
        registerActivityLifecycleCallbacks(object : Application.ActivityLifecycleCallbacks {
            override fun onActivityCreated(a: Activity, b: Bundle?) {}
            // After onStart the content view exists, so the stamp lands on top of it. The helper is
            // idempotent (skips if already stamped), so re-entering a screen won't double it.
            override fun onActivityStarted(a: Activity) { Ui.stampBrand(a); Ui.stampBackButton(a) }
            override fun onActivityResumed(a: Activity) { Ui.stampBrand(a); Ui.stampBackButton(a) }
            override fun onActivityPaused(a: Activity) {}
            override fun onActivityStopped(a: Activity) {}
            override fun onActivitySaveInstanceState(a: Activity, b: Bundle) {}
            override fun onActivityDestroyed(a: Activity) {}
        })
    }
}

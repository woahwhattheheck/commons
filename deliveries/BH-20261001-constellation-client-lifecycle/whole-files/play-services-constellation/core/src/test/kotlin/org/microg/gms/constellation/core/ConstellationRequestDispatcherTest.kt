/*
 * SPDX-FileCopyrightText: 2026, microG Project Team
 * SPDX-License-Identifier: Apache-2.0
 */

package org.microg.gms.constellation.core

import android.os.IBinder
import android.os.RemoteException
import com.google.android.gms.constellation.internal.IConstellationCallbacks
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.awaitCancellation
import kotlinx.coroutines.cancel
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.mockito.Mockito

@OptIn(ExperimentalCoroutinesApi::class)
class ConstellationRequestDispatcherTest {

    /** A caller whose callback binder records its death recipients and can be "killed" on demand. */
    private class FakeCaller(linkThrows: Boolean = false) {
        private val recipients = mutableListOf<IBinder.DeathRecipient>()
        val binder: IBinder = Mockito.mock(IBinder::class.java)
        val callbacks: IConstellationCallbacks = Mockito.mock(IConstellationCallbacks::class.java)

        init {
            Mockito.`when`(callbacks.asBinder()).thenReturn(binder)
            if (linkThrows) {
                Mockito.doThrow(Mockito.mock(RemoteException::class.java))
                    .`when`(binder).linkToDeath(Mockito.any(), Mockito.anyInt())
            } else {
                Mockito.doAnswer { invocation ->
                    recipients += invocation.getArgument<IBinder.DeathRecipient>(0)
                    Unit
                }.`when`(binder).linkToDeath(Mockito.any(), Mockito.anyInt())
            }
            Mockito.doAnswer { invocation ->
                recipients.remove(invocation.getArgument<IBinder.DeathRecipient>(0))
            }.`when`(binder).unlinkToDeath(Mockito.any(), Mockito.anyInt())
        }

        fun hasDeathRecipient(): Boolean = recipients.isNotEmpty()

        fun killCaller() = recipients.toList().forEach { it.binderDied() }
    }

    @Test
    fun callerDeath_cancelsTheRunningRequest_andUnlinks() = runTest {
        val scope = CoroutineScope(SupervisorJob() + UnconfinedTestDispatcher(testScheduler))
        try {
            val caller = FakeCaller()
            val dispatcher = ConstellationRequestDispatcher(scope)
            var sawCancellation = false

            val job: Job = dispatcher.dispatch(caller.callbacks, "verifyPhoneNumber") {
                try {
                    awaitCancellation()
                } catch (e: CancellationException) {
                    sawCancellation = true
                    throw e
                }
            }
            // Eager dispatch has already linked death and parked at awaitCancellation().
            assertTrue("request should have linked to caller death", caller.hasDeathRecipient())
            assertFalse(job.isCompleted)

            caller.killCaller()
            advanceUntilIdle()

            assertTrue("request job should be cancelled when caller dies", job.isCancelled)
            assertTrue("request body should observe cancellation", sawCancellation)
            assertFalse("death recipient should be unlinked after completion", caller.hasDeathRecipient())
        } finally {
            scope.cancel()
        }
    }

    @Test
    fun callerAlreadyDead_cancelsRequestImmediately() = runTest {
        val scope = CoroutineScope(SupervisorJob() + UnconfinedTestDispatcher(testScheduler))
        try {
            val caller = FakeCaller(linkThrows = true)
            val dispatcher = ConstellationRequestDispatcher(scope)

            val job = dispatcher.dispatch(caller.callbacks, "verifyPhoneNumber") {
                awaitCancellation()
            }
            advanceUntilIdle()

            assertTrue("request job should be cancelled when the caller is already dead", job.isCancelled)
        } finally {
            scope.cancel()
        }
    }

    @Test
    fun failureInRequest_isContained_notPropagatedAsJobFailure() = runTest {
        val scope = CoroutineScope(SupervisorJob() + UnconfinedTestDispatcher(testScheduler))
        try {
            val caller = FakeCaller()
            val dispatcher = ConstellationRequestDispatcher(scope)

            val job = dispatcher.dispatch(caller.callbacks, "verifyPhoneNumber") {
                throw IllegalStateException("boom")
            }
            advanceUntilIdle()

            assertTrue("request job should complete", job.isCompleted)
            // Contained: a caught failure completes the coroutine normally. If it were NOT contained,
            // the launched coroutine would fail and the job would be in the cancelled state.
            assertFalse("a contained failure must not surface as a job failure", job.isCancelled)
            assertFalse("death recipient should be unlinked after completion", caller.hasDeathRecipient())
        } finally {
            scope.cancel()
        }
    }

    @Test
    fun normalCompletion_unlinksDeathRecipient() = runTest {
        val scope = CoroutineScope(SupervisorJob() + UnconfinedTestDispatcher(testScheduler))
        try {
            val caller = FakeCaller()
            val dispatcher = ConstellationRequestDispatcher(scope)

            val job = dispatcher.dispatch(caller.callbacks, "getIidToken") {
                // completes immediately
            }
            advanceUntilIdle()

            assertTrue(job.isCompleted)
            assertFalse(job.isCancelled)
            assertFalse("death recipient should be unlinked after completion", caller.hasDeathRecipient())
        } finally {
            scope.cancel()
        }
    }
}

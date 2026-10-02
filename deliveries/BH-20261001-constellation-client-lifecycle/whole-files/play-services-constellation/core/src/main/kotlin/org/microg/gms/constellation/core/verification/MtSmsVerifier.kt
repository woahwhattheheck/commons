package org.microg.gms.constellation.core.verification

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.provider.Telephony
import android.telephony.SmsMessage
import android.util.Log
import androidx.core.content.ContextCompat
import kotlinx.coroutines.CancellableContinuation
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeoutOrNull
import org.microg.gms.constellation.core.proto.ChallengeResponse
import org.microg.gms.constellation.core.proto.MTChallenge
import org.microg.gms.constellation.core.proto.MTChallengeResponseData
import java.util.concurrent.TimeUnit
import kotlin.coroutines.AbstractCoroutineContextElement
import kotlin.coroutines.CoroutineContext
import kotlin.coroutines.coroutineContext
import kotlin.coroutines.resume

private const val TAG = "MtSmsVerifier"

suspend fun MTChallenge.verify(
    subId: Int,
    timeoutMillis: Long? = null
): ChallengeResponse? {
    val expectedBody = sms.takeIf { it.isNotEmpty() } ?: return null
    val inbox = MtSmsInboxRegistry.get(subId)
    val effectiveTimeoutMillis = timeoutMillis?.coerceAtLeast(0L) ?: TimeUnit.MINUTES.toMillis(30)

    Log.d(TAG, "Waiting for MT SMS containing challenge string")

    val match = withTimeoutOrNull(effectiveTimeoutMillis) {
        inbox.awaitMatch(expectedBody)
    }

    if (match == null) {
        Log.w(TAG, "Timed out waiting for MT SMS, proceeding with empty response")
    }

    val response = match ?: ReceivedSms(body = "", sender = "")
    return ChallengeResponse(
        mt_response = MTChallengeResponseData(
            sms = response.body,
            sender = response.sender
        )
    )
}

/**
 * Handle to a per-request MT SMS inbox. Extracted as an interface so the request-scoping logic in
 * [MtSmsInboxScope] can be unit tested without registering a real [BroadcastReceiver].
 */
internal interface MtSmsInboxHandle {
    suspend fun awaitMatch(expectedBody: String): ReceivedSms?
    fun dispose()
}

/**
 * Per-request registry for [MtSmsInbox] instances.
 *
 * The inboxes are owned by an [MtSmsInboxScope] carried in the request's coroutine context, which
 * the Constellation service installs when it dispatches a request. Because every request has its
 * own scope, [dispose] only tears down the inboxes of the request that calls it. That is what makes
 * the cleanup safe under concurrency: a slow or cancelled request running its `finally { dispose() }`
 * can never unregister the SMS receivers of a newer request that started in the meantime.
 */
internal object MtSmsInboxRegistry {
    suspend fun prepare(context: Context, subIds: Iterable<Int>) {
        currentScope().prepare(context, subIds)
    }

    suspend fun get(subId: Int): MtSmsInboxHandle = currentScope().get(subId)

    suspend fun dispose() {
        // Null-safe so it is a harmless no-op (never throws) when called from a finally block,
        // including during cancellation unwinding.
        coroutineContext[MtSmsInboxScope]?.dispose()
    }

    private suspend fun currentScope(): MtSmsInboxScope =
        coroutineContext[MtSmsInboxScope] ?: error(
            "No MtSmsInboxScope in the current coroutine context. Constellation requests must be " +
                "dispatched through ConstellationRequestDispatcher so MT SMS inboxes are scoped per request."
        )
}

/**
 * Coroutine-context element that owns the MT SMS inboxes of a single Constellation request.
 *
 * Each dispatched request carries its own instance, so the registry operations above resolve to the
 * inboxes of the calling request only. [inboxFactory] is overridable for tests; production uses the
 * real [MtSmsInbox].
 */
internal class MtSmsInboxScope(
    private val inboxFactory: (Context, Int) -> MtSmsInboxHandle = { context, subId ->
        MtSmsInbox(context, subId)
    }
) : AbstractCoroutineContextElement(MtSmsInboxScope) {
    companion object Key : CoroutineContext.Key<MtSmsInboxScope>

    private val lock = Any()
    private val inboxes = HashMap<Int, MtSmsInboxHandle>()
    private var disposed = false

    fun prepare(context: Context, subIds: Iterable<Int>) {
        val effectiveSubIds = subIds.distinct().ifEmpty { listOf(-1) }
        val replaced: List<MtSmsInboxHandle>
        synchronized(lock) {
            check(!disposed) { "MtSmsInboxScope already disposed" }
            // Only ever touches THIS request's own inboxes.
            replaced = inboxes.values.toList()
            inboxes.clear()
            for (subId in effectiveSubIds) {
                inboxes[subId] = inboxFactory(context, subId)
            }
        }
        replaced.forEach { it.dispose() }
    }

    fun get(subId: Int): MtSmsInboxHandle = synchronized(lock) {
        inboxes[subId] ?: error("MT SMS inbox for subId=$subId was not initialized")
    }

    fun dispose() {
        val current: List<MtSmsInboxHandle>
        synchronized(lock) {
            if (disposed) return
            disposed = true
            current = inboxes.values.toList()
            inboxes.clear()
        }
        current.forEach { it.dispose() }
    }
}

internal data class ReceivedSms(
    val body: String,
    val sender: String
)

private data class PendingMatch(
    val expectedBody: String,
    val continuation: CancellableContinuation<ReceivedSms?>
)

internal class MtSmsInbox(
    context: Context,
    private val subId: Int
) : MtSmsInboxHandle {
    private val context = context.applicationContext
    private val lock = Any()
    private val bufferedMessages = mutableListOf<ReceivedSms>()
    private val pendingMatches = mutableListOf<PendingMatch>()

    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) return

            val receivedSubId = intent.getIntExtra(
                "android.telephony.extra.SUBSCRIPTION_INDEX",
                intent.getIntExtra("subscription", -1)
            )
            if (subId != -1 && receivedSubId != subId) return

            onMessagesReceived(Telephony.Sms.Intents.getMessagesFromIntent(intent))
        }
    }

    init {
        val filter = IntentFilter(Telephony.Sms.Intents.SMS_RECEIVED_ACTION).apply {
            priority = 1000
        }
        ContextCompat.registerReceiver(
            context,
            receiver,
            filter,
            ContextCompat.RECEIVER_EXPORTED
        )
    }

    override suspend fun awaitMatch(expectedBody: String): ReceivedSms? {
        return suspendCancellableCoroutine { continuation ->
            synchronized(lock) {
                bufferedMessages.firstOrNull { it.body.contains(expectedBody) }?.let {
                    continuation.resume(it)
                    return@suspendCancellableCoroutine
                }

                val pendingMatch = PendingMatch(expectedBody, continuation)
                pendingMatches += pendingMatch
                continuation.invokeOnCancellation {
                    synchronized(lock) {
                        pendingMatches.remove(pendingMatch)
                    }
                }
            }
        }
    }

    private fun onMessagesReceived(messages: Array<SmsMessage>) {
        val receivedMessages = messages.mapNotNull { message ->
            val body = message.messageBody ?: return@mapNotNull null
            ReceivedSms(
                body = body,
                sender = message.originatingAddress ?: ""
            )
        }
        if (receivedMessages.isEmpty()) return

        synchronized(lock) {
            bufferedMessages += receivedMessages
            for (receivedMessage in receivedMessages) {
                val iterator = pendingMatches.iterator()
                while (iterator.hasNext()) {
                    val pendingMatch = iterator.next()
                    if (!receivedMessage.body.contains(pendingMatch.expectedBody)) continue

                    iterator.remove()
                    Log.d(TAG, "Matching MT SMS received from ${receivedMessage.sender}")
                    if (pendingMatch.continuation.isActive) {
                        pendingMatch.continuation.resume(receivedMessage)
                    }
                }
            }
        }
    }

    override fun dispose() {
        synchronized(lock) {
            pendingMatches.clear()
            bufferedMessages.clear()
        }
        try {
            context.unregisterReceiver(receiver)
        } catch (_: IllegalArgumentException) {
        }
    }
}

package com.arthurassistant.messaging

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import com.arthurassistant.failure.ArthurFailure
import com.arthurassistant.failure.FailureProtocol
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow

class SmsReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context?, intent: Intent?) {
        if (intent?.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) return
        try {
            val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
            messages?.forEach { smsMessage ->
                val sender = smsMessage.displayOriginatingAddress ?: "Unknown"
                val body = smsMessage.displayMessageBody ?: ""
                if (body.isNotBlank()) {
                    _incoming.tryEmit(IncomingMessage(source = "SMS from $sender", text = body))
                }
            }
        } catch (ex: Exception) {
            failureProtocol?.handle(ArthurFailure(ex.message ?: "sms receive error"))
        }
    }

    data class IncomingMessage(val source: String, val text: String)

    companion object {
        private val _incoming = MutableSharedFlow<IncomingMessage>(extraBufferCapacity = 10)
        val incoming = _incoming.asSharedFlow()
        private var failureProtocol: FailureProtocol? = null
        fun registerFailureProtocol(protocol: FailureProtocol) {
            failureProtocol = protocol
        }
    }
}

package com.arthurassistant.messaging

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.app.Notification
import com.arthurassistant.failure.ArthurFailure
import com.arthurassistant.failure.FailureProtocol
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow

class WhatsAppNotificationListener : NotificationListenerService() {
    override fun onNotificationPosted(sbn: StatusBarNotification) {
        try {
            val packageName = sbn.packageName ?: return
            if (!ALLOWED_PACKAGES.contains(packageName)) return

            val extras = sbn.notification.extras
            val title = extras?.getCharSequence(Notification.EXTRA_TITLE)?.toString()?.takeIf { it.isNotBlank() }
            val text = extras?.getCharSequence(Notification.EXTRA_TEXT)?.toString()?.takeIf { it.isNotBlank() }
            if (!text.isNullOrBlank()) {
                val source = if (!title.isNullOrBlank()) {
                    "WhatsApp ($title)"
                } else {
                    "WhatsApp"
                }
                _previews.tryEmit(SurfaceMessage(source = source, text = text))
            }
        } catch (ex: Exception) {
            failureProtocol?.handle(ArthurFailure(ex.message ?: "whatsapp preview error"))
        }
    }

    data class SurfaceMessage(val source: String, val text: String)

    companion object {
        private val ALLOWED_PACKAGES = setOf("com.whatsapp", "com.whatsapp.w4b")
        private val _previews = MutableSharedFlow<SurfaceMessage>(extraBufferCapacity = 10)
        val previews = _previews.asSharedFlow()
        private var failureProtocol: FailureProtocol? = null
        fun registerFailureProtocol(protocol: FailureProtocol) {
            failureProtocol = protocol
        }
    }
}

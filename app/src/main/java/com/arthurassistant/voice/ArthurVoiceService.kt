package com.arthurassistant.voice

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.arthurassistant.failure.ArthurFailure
import com.arthurassistant.failure.BackoffPolicy
import com.arthurassistant.failure.FailureProtocol
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class ArthurVoiceService : Service(), RecognitionListener {
    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private val backoffPolicy = BackoffPolicy()
    private var restartAttempts = 0
    private var userRequestedListening = false
    private var speechRecognizer: SpeechRecognizer? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification())
        userRequestedListening = true
        startListeningSession()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            val reason = intent.getStringExtra(EXTRA_REASON) ?: "Stopped"
            userRequestedListening = false
            stopListening(reason)
            stopSelf()
            return START_NOT_STICKY
        }
        userRequestedListening = true
        if (!_listening.value) {
            startListeningSession()
        }
        return START_STICKY
    }

    override fun onDestroy() {
        stopListening("Service destroyed")
        serviceScope.coroutineContext.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?) = null

    private fun startListeningSession() {
        if (!userRequestedListening) return
        try {
            if (!SpeechRecognizer.isRecognitionAvailable(this)) {
                onListeningError("Speech recognition unavailable")
                return
            }
            speechRecognizer?.destroy()
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this).apply {
                setRecognitionListener(this@ArthurVoiceService)
            }
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            }
            _pauseReason.value = null
            _listening.value = true
            restartAttempts = 0
            speechRecognizer?.startListening(intent)
        } catch (ex: Exception) {
            failureProtocol?.handle(ArthurFailure(ex.message ?: "listen init failed"))
            onListeningError("Recognizer init error")
        }
    }

    private fun stopListening(reason: String) {
        _listening.value = false
        _pauseReason.value = reason
        speechRecognizer?.cancel()
        speechRecognizer?.destroy()
        speechRecognizer = null
        stopForeground(STOP_FOREGROUND_REMOVE)
    }

    private fun scheduleRestart() {
        val delayMs = backoffPolicy.nextDelay(restartAttempts++)
        serviceScope.launch {
            delay(delayMs)
            if (userRequestedListening) {
                startForeground(NOTIFICATION_ID, buildNotification())
                startListeningSession()
            }
        }
    }

    private fun onListeningError(reason: String) {
        _listening.value = false
        _pauseReason.value = reason
        failureProtocol?.handle(ArthurFailure(reason))
        if (userRequestedListening) {
            scheduleRestart()
        }
    }

    override fun onReadyForSpeech(params: Bundle?) {
        _listening.value = true
        _pauseReason.value = null
    }

    override fun onBeginningOfSpeech() {
        _listening.value = true
    }

    override fun onRmsChanged(rmsdB: Float) {
        // no-op
    }

    override fun onBufferReceived(buffer: ByteArray?) {
        // no-op; audio is not stored or forwarded.
    }

    override fun onEndOfSpeech() {
        _listening.value = false
    }

    override fun onError(error: Int) {
        val reason = when (error) {
            SpeechRecognizer.ERROR_NETWORK_TIMEOUT -> "Network timeout"
            SpeechRecognizer.ERROR_NETWORK -> "Network error"
            SpeechRecognizer.ERROR_AUDIO -> "Audio error"
            SpeechRecognizer.ERROR_SERVER -> "Server error"
            SpeechRecognizer.ERROR_CLIENT -> "Client error"
            SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "Speech timeout"
            SpeechRecognizer.ERROR_NO_MATCH -> "No match"
            SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "Recognizer busy"
            SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Insufficient permissions"
            else -> "Unknown error $error"
        }
        onListeningError(reason)
    }

    override fun onResults(results: Bundle?) {
        _listening.value = false
        val texts = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
        val text = texts?.firstOrNull()
        if (!text.isNullOrBlank()) {
            _transcripts.tryEmit(text)
        }
        if (userRequestedListening) {
            startListeningSession()
        }
    }

    override fun onPartialResults(partialResults: Bundle?) {
        val texts = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
        val text = texts?.firstOrNull()
        if (!text.isNullOrBlank()) {
            _transcripts.tryEmit(text)
        }
    }

    override fun onEvent(eventType: Int, params: Bundle?) {
        // no-op
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Arthur Listening",
                NotificationManager.IMPORTANCE_LOW
            )
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Arthur is listening")
            .setContentText("Foreground listening active")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setOngoing(true)
            .build()
    }

    companion object {
        private const val CHANNEL_ID = "arthur_listening_channel"
        private const val NOTIFICATION_ID = 1001
        private const val ACTION_STOP = "com.arthurassistant.voice.ACTION_STOP"
        private const val EXTRA_REASON = "extra_reason"

        private val _transcripts = MutableSharedFlow<String>(extraBufferCapacity = 10)
        val transcripts: SharedFlow<String> = _transcripts

        private val _listening = MutableStateFlow(false)
        val listening: StateFlow<Boolean> = _listening

        private val _pauseReason = MutableStateFlow<String?>(null)
        val pauseReason: StateFlow<String?> = _pauseReason

        private var failureProtocol: FailureProtocol? = null

        fun registerFailureProtocol(protocol: FailureProtocol) {
            failureProtocol = protocol
        }

        fun start(context: Context) {
            val intent = Intent(context, ArthurVoiceService::class.java)
            ContextCompat.startForegroundService(context, intent)
        }

        fun stop(context: Context, reason: String = "Stopped by user") {
            val intent = Intent(context, ArthurVoiceService::class.java).apply {
                action = ACTION_STOP
                putExtra(EXTRA_REASON, reason)
            }
            ContextCompat.startForegroundService(context, intent)
        }
    }
}

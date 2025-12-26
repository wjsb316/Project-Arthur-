package com.arthurassistant.voice

import android.content.Context
import android.speech.tts.TextToSpeech
import com.arthurassistant.failure.ArthurFailure
import com.arthurassistant.failure.FailureProtocol
import com.arthurassistant.policy.PolicyEngine
import java.util.Locale

class ArthurSpeaker(
    context: Context,
    private val policyEngine: PolicyEngine,
    private val failureProtocol: FailureProtocol,
    private val sensitivityClassifier: SensitivityClassifier = SensitivityClassifier()
) : TextToSpeech.OnInitListener {

    private var textToSpeech: TextToSpeech? = TextToSpeech(context.applicationContext, this)
    @Volatile
    private var initialized = false

    override fun onInit(status: Int) {
        initialized = status == TextToSpeech.SUCCESS
        if (initialized) {
            textToSpeech?.language = Locale.US
        } else {
            failureProtocol.handle(ArthurFailure("tts init failed"))
        }
    }

    fun speak(text: String): Boolean {
        val sensitivity = sensitivityClassifier.classify(text)
        val decision = policyEngine.decideSpeech(
            PolicyEngine.SpeechRequest(
                text = text,
                sensitive = sensitivity == SensitivityClassifier.SensitivityLevel.SENSITIVE
            )
        )
        if (decision is PolicyEngine.PolicyDecision.Blocked) {
            return false
        }

        if (!initialized) {
            failureProtocol.handle(ArthurFailure("tts not ready"))
            return false
        }

        return try {
            textToSpeech?.speak(text, TextToSpeech.QUEUE_ADD, null, "arthur_say")
            true
        } catch (ex: Exception) {
            failureProtocol.handle(ArthurFailure(ex.message ?: "tts failure"))
            false
        }
    }

    fun shutdown() {
        textToSpeech?.stop()
        textToSpeech?.shutdown()
    }
}

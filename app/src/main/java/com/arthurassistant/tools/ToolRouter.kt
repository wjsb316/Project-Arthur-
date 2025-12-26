package com.arthurassistant.tools

import android.content.Context
import android.content.Intent
import androidx.core.content.ContextCompat
import com.arthurassistant.failure.ArthurFailure
import com.arthurassistant.failure.FailureProtocol
import com.arthurassistant.lockout.LockoutManager
import com.arthurassistant.messaging.SmsHandler
import com.arthurassistant.notes.NotesRepository
import com.arthurassistant.policy.BatmanOverrideController
import com.arthurassistant.policy.HipaaModeController
import com.arthurassistant.policy.PolicyEngine
import com.arthurassistant.policy.StealthModeController
import com.arthurassistant.status.StatusExplainer
import com.arthurassistant.voice.SensitivityClassifier
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

data class ToolCall(val name: String, val args: Map<String, Any?> = emptyMap())

sealed class ToolResult {
    data class Success(val payload: Any? = null) : ToolResult()
    data class Blocked(val reason: String) : ToolResult()
    data class Failure(val message: String) : ToolResult()
}

class ToolRouter(
    private val context: Context,
    private val policyEngine: PolicyEngine,
    private val failureProtocol: FailureProtocol,
    private val notesRepository: NotesRepository,
    private val lockoutManager: LockoutManager,
    private val batmanOverrideController: BatmanOverrideController,
    private val stealthModeController: StealthModeController,
    private val hipaaModeController: HipaaModeController,
    private val statusExplainer: StatusExplainer,
    private val smsHandler: SmsHandler,
    private val sensitivityClassifier: SensitivityClassifier = SensitivityClassifier()
) {
    sealed class BatmanEvent {
        data class Challenge(val message: String, val uiOnly: Boolean) : BatmanEvent()
        object RequestPin : BatmanEvent()
        data class Cleared(val message: String) : BatmanEvent()
        data class PinFailed(val message: String) : BatmanEvent()
    }

    sealed class UiMessage {
        data class Speak(val text: String) : UiMessage()
        data class UiOnly(val text: String) : UiMessage()
    }

    private val _batmanEvents = MutableSharedFlow<BatmanEvent>(extraBufferCapacity = 10)
    val batmanEvents: SharedFlow<BatmanEvent> = _batmanEvents

    private val _uiMessages = MutableSharedFlow<UiMessage>(extraBufferCapacity = 10)
    val uiMessages: SharedFlow<UiMessage> = _uiMessages

    private val batmanScope = CoroutineScope(Dispatchers.Default)

    init {
        batmanScope.launch {
            batmanOverrideController.uiEvents.collect { event ->
                when (event) {
                    is BatmanOverrideController.UiEvent.Challenge ->
                        _batmanEvents.tryEmit(BatmanEvent.Challenge(event.message, event.uiOnly))
                    BatmanOverrideController.UiEvent.RequestPin ->
                        _batmanEvents.tryEmit(BatmanEvent.RequestPin)
                    is BatmanOverrideController.UiEvent.Cleared ->
                        _batmanEvents.tryEmit(BatmanEvent.Cleared(event.message))
                    is BatmanOverrideController.UiEvent.PinFailed ->
                        _batmanEvents.tryEmit(BatmanEvent.PinFailed(event.message))
                }
            }
        }
    }

    suspend fun handle(toolCall: ToolCall): ToolResult = withContext(Dispatchers.IO) {
        try {
            when (toolCall.name) {
                "create_note" -> {
                    val text = toolCall.args["text"] as? String
                    if (text.isNullOrBlank()) {
                        failureProtocol.handle(ArthurFailure("create_note missing text"))
                        return@withContext ToolResult.Failure("invalid text")
                    }
                    val decision = policyEngine.decideToolCall(PolicyEngine.ToolRequest(toolCall.name))
                    if (decision is PolicyEngine.PolicyDecision.Blocked) {
                        return@withContext ToolResult.Blocked(decision.reason)
                    }
                    val id = notesRepository.createNote(text)
                    ToolResult.Success(mapOf("id" to id))
                }

                "search_notes" -> {
                    val query = toolCall.args["query"] as? String ?: ""
                    val decision = policyEngine.decideToolCall(PolicyEngine.ToolRequest(toolCall.name))
                    if (decision is PolicyEngine.PolicyDecision.Blocked) {
                        return@withContext ToolResult.Blocked(decision.reason)
                    }
                    val results = notesRepository.searchNotes(query)
                    ToolResult.Success(results)
                }

                "delete_note" -> {
                    val id = (toolCall.args["id"] as? Number)?.toLong()
                    if (id == null) {
                        failureProtocol.handle(ArthurFailure("delete_note missing id"))
                        return@withContext ToolResult.Failure("invalid id")
                    }
                    val decision = policyEngine.decideToolCall(PolicyEngine.ToolRequest(toolCall.name))
                    if (decision is PolicyEngine.PolicyDecision.Blocked) {
                        return@withContext ToolResult.Blocked(decision.reason)
                    }
                    notesRepository.deleteNote(id)
                    ToolResult.Success()
                }

                "send_sms" -> {
                    val phone = toolCall.args["phone"] as? String
                    val text = toolCall.args["text"] as? String
                    if (phone.isNullOrBlank() || text.isNullOrBlank()) {
                        failureProtocol.handle(ArthurFailure("send_sms missing phone or text"))
                        return@withContext ToolResult.Failure("invalid sms args")
                    }
                    val sensitivity = sensitivityClassifier.classify(text)
                    val decision = policyEngine.decideToolCall(
                        PolicyEngine.ToolRequest(toolCall.name, sensitive = sensitivity == SensitivityClassifier.SensitivityLevel.SENSITIVE)
                    )
                    if (decision is PolicyEngine.PolicyDecision.Blocked) {
                        return@withContext ToolResult.Blocked(decision.reason)
                    }
                    if (hipaaModeController.hipaa.value && sensitivity == SensitivityClassifier.SensitivityLevel.SENSITIVE) {
                        val reason = "sms blocked: sensitive content in hipaa mode"
                        failureProtocol.handleBlock(reason)
                        return@withContext ToolResult.Blocked(reason)
                    }

                    val confirmed = toolCall.args["confirmed"] as? Boolean ?: false
                    if (!confirmed) {
                        _uiMessages.tryEmit(UiMessage.UiOnly("Confirm SMS to $phone: \"$text\""))
                        failureProtocol.handleBlock("sms confirmation required")
                        return@withContext ToolResult.Blocked("confirmation required")
                    }

                    if (!smsHandler.hasPermission()) {
                        failureProtocol.handle(ArthurFailure("sms permission missing"))
                        _uiMessages.tryEmit(UiMessage.UiOnly("SMS permission required to send."))
                        return@withContext ToolResult.Blocked("permission missing")
                    }

                    val sent = smsHandler.sendSms(phone, text)
                    if (sent) {
                        ToolResult.Success()
                    } else {
                        ToolResult.Failure("sms send failed")
                    }
                }

                "send_whatsapp_intent" -> {
                    val phone = toolCall.args["phoneOrJid"] as? String
                    val text = toolCall.args["text"] as? String
                    if (phone.isNullOrBlank() || text.isNullOrBlank()) {
                        failureProtocol.handle(ArthurFailure("send_whatsapp_intent missing args"))
                        return@withContext ToolResult.Failure("invalid whatsapp args")
                    }
                    val sensitivity = sensitivityClassifier.classify(text)
                    val decision = policyEngine.decideToolCall(
                        PolicyEngine.ToolRequest(toolCall.name, sensitive = sensitivity == SensitivityClassifier.SensitivityLevel.SENSITIVE)
                    )
                    if (decision is PolicyEngine.PolicyDecision.Blocked) {
                        return@withContext ToolResult.Blocked(decision.reason)
                    }
                    if (hipaaModeController.hipaa.value && sensitivity == SensitivityClassifier.SensitivityLevel.SENSITIVE) {
                        val reason = "whatsapp intent blocked: sensitive content in hipaa mode"
                        failureProtocol.handleBlock(reason)
                        return@withContext ToolResult.Blocked(reason)
                    }

                    val intent = Intent(Intent.ACTION_SEND).apply {
                        type = "text/plain"
                        putExtra(Intent.EXTRA_TEXT, text)
                        `package` = "com.whatsapp"
                        putExtra("jid", phone)
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    }
                    return@withContext try {
                        ContextCompat.startActivity(context, intent, null)
                        ToolResult.Success()
                    } catch (ex: Exception) {
                        failureProtocol.handle(ArthurFailure(ex.message ?: "whatsapp intent failed"))
                        ToolResult.Failure("unable to open whatsapp")
                    }
                }

                else -> {
                    failureProtocol.handle(ArthurFailure("unknown tool ${toolCall.name}"))
                    ToolResult.Failure("unknown tool")
                }
            }
        } catch (ex: Exception) {
            failureProtocol.handle(ArthurFailure(ex.message ?: "tool failure"))
            ToolResult.Failure("exception")
        }
    }

    suspend fun interceptTranscript(transcript: String) {
        withContext(Dispatchers.Default) {
            try {
                val normalized = transcript.trim().lowercase()

                if (handleStealthEntry(normalized)) {
                    return@withContext
                }

                handleStealthExitIfQuestion(normalized)

                if (handleExplain(normalized)) {
                    return@withContext
                }

                if (normalized.contains(TRIGGER_PHRASE)) {
                    batmanOverrideController.onTriggerPhrase()
                    return@withContext
                }

                if (normalized.contains(AUTH_PHRASE)) {
                    batmanOverrideController.onAuthorizationPhrase()
                }
            } catch (ex: Exception) {
                failureProtocol.handle(ArthurFailure(ex.message ?: "transcript intercept failure"))
            }
        }
    }

    fun clearLockouts() {
        lockoutManager.clearAll()
    }

    companion object {
        private const val TRIGGER_PHRASE = "arthur, undo all standing lockouts system wide"
        private const val AUTH_PHRASE = "do it, because i am batman"
        private val QUESTION_STARTERS = listOf(
            "what", "why", "how", "can you", "could you", "would you", "when", "where", "who", "is", "are", "do", "did", "does", "will", "should"
        )
        private val EXPLAIN_COMMANDS = listOf(
            "arthur, status", "arthur, explain", "arthur, why are you quiet"
        )
    }

    private fun handleStealthEntry(normalized: String): Boolean {
        val triggers = listOf("arthur, hush", "arthur, shut up", "arthur, shup up")
        val matched = triggers.any { normalized.startsWith(it) }
        if (matched && !stealthModeController.stealth.value) {
            val decision = policyEngine.decideSpeech(PolicyEngine.SpeechRequest("Alright."))
            if (decision is PolicyEngine.PolicyDecision.Allowed) {
                _uiMessages.tryEmit(UiMessage.Speak("Alright."))
            }
            stealthModeController.setStealth(true)
            return true
        }
        return matched
    }

    private fun handleStealthExitIfQuestion(normalized: String) {
        if (!stealthModeController.stealth.value) return
        val prefix = "arthur "
        if (!normalized.startsWith(prefix)) return
        val questionPortion = normalized.removePrefix(prefix).trim()
        if (questionPortion.contains("?")) {
            stealthModeController.setStealth(false)
            _uiMessages.tryEmit(UiMessage.UiOnly("Stealth disabled after question."))
            return
        }
        val starterMatch = QUESTION_STARTERS.any { questionPortion.startsWith(it) }
        if (starterMatch) {
            stealthModeController.setStealth(false)
            _uiMessages.tryEmit(UiMessage.UiOnly("Stealth disabled after question."))
        }
    }

    private fun handleExplain(normalized: String): Boolean {
        val matched = EXPLAIN_COMMANDS.any { normalized.startsWith(it) }
        if (!matched) return false
        val explanation = statusExplainer.explainLatest()
        return if (stealthModeController.stealth.value) {
            _uiMessages.tryEmit(UiMessage.UiOnly(explanation))
            true
        } else {
            val decision = policyEngine.decideSpeech(PolicyEngine.SpeechRequest(explanation))
            if (decision is PolicyEngine.PolicyDecision.Allowed) {
                _uiMessages.tryEmit(UiMessage.Speak(explanation))
            }
            true
        }
    }
}

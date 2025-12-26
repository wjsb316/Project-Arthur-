package com.arthurassistant.policy

import com.arthurassistant.failure.ArthurFailure
import com.arthurassistant.failure.FailureProtocol
import com.arthurassistant.lockout.LockoutManager
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow

class BatmanOverrideController(
    private val lockoutManager: LockoutManager,
    private val policyEngine: PolicyEngine,
    private val failureProtocol: FailureProtocol,
    private val pinVerifier: (String) -> Boolean = { it == "0000" }
) {
    sealed class State {
        object Idle : State()
        object Challenged : State()
        object AwaitingPin : State()
    }

    sealed class UiEvent {
        data class Challenge(val message: String, val uiOnly: Boolean) : UiEvent()
        object RequestPin : UiEvent()
        data class Cleared(val message: String) : UiEvent()
        data class PinFailed(val message: String) : UiEvent()
    }

    private val _state = MutableStateFlow<State>(State.Idle)
    val state: StateFlow<State> = _state

    private val _uiEvents = MutableSharedFlow<UiEvent>(extraBufferCapacity = 5)
    val uiEvents: SharedFlow<UiEvent> = _uiEvents

    private val _logs = MutableSharedFlow<String>(extraBufferCapacity = 5)
    val logs: SharedFlow<String> = _logs

    fun onTriggerPhrase() {
        if (_state.value != State.Idle) return
        _state.value = State.Challenged
        val challenge = "That will require the proper authorization phrase."
        val decision = policyEngine.decideSpeech(PolicyEngine.SpeechRequest(challenge))
        val uiOnly = decision is PolicyEngine.PolicyDecision.Blocked
        _uiEvents.tryEmit(UiEvent.Challenge(challenge, uiOnly))
        _logs.tryEmit("batman_challenge")
    }

    fun onAuthorizationPhrase() {
        if (_state.value != State.Challenged) return
        _state.value = State.AwaitingPin
        _uiEvents.tryEmit(UiEvent.RequestPin)
        _logs.tryEmit("batman_request_pin")
    }

    fun confirmPin(pin: String): Boolean {
        if (_state.value != State.AwaitingPin) return false
        val verified = runCatching { pinVerifier(pin) }.getOrElse { ex ->
            failureProtocol.handle(ArthurFailure(ex.message ?: "pin check failed"))
            return false
        }
        return if (verified) {
            lockoutManager.clearAll()
            _state.value = State.Idle
            _uiEvents.tryEmit(UiEvent.Cleared("All lockouts cleared."))
            _logs.tryEmit("batman_cleared")
            true
        } else {
            _uiEvents.tryEmit(UiEvent.PinFailed("Authorization failed."))
            _logs.tryEmit("batman_pin_failed")
            false
        }
    }

    fun reset() {
        _state.value = State.Idle
    }
}

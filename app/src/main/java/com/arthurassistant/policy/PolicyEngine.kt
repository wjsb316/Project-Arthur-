package com.arthurassistant.policy

import com.arthurassistant.failure.FailureProtocol

class PolicyEngine(
    private val stealthModeController: StealthModeController,
    private val hipaaModeController: HipaaModeController,
    private val publicModeController: PublicModeController,
    private val failureProtocol: FailureProtocol
) {
    data class SpeechRequest(val text: String, val sensitive: Boolean = false)
    data class ToolRequest(val name: String, val sensitive: Boolean = false)

    sealed class PolicyDecision(val reason: String) {
        class Allowed(reason: String = "allowed") : PolicyDecision(reason)
        class Blocked(reason: String) : PolicyDecision(reason)
    }

    fun decideSpeech(request: SpeechRequest): PolicyDecision {
        val stealth = stealthModeController.stealth.value
        val hipaa = hipaaModeController.hipaa.value
        val public = publicModeController.publicMode.value

        val decision = when {
            stealth -> PolicyDecision.Blocked("speech blocked: stealth mode active")
            hipaa && public && request.sensitive -> PolicyDecision.Blocked("sensitive speech blocked in hipaa+public mode")
            else -> PolicyDecision.Allowed()
        }

        if (decision is PolicyDecision.Blocked) {
            failureProtocol.handleBlock(decision.reason)
        }
        return decision
    }

    fun decideToolCall(request: ToolRequest): PolicyDecision {
        val stealth = stealthModeController.stealth.value
        val hipaa = hipaaModeController.hipaa.value
        val decision = when {
            stealth -> PolicyDecision.Blocked("tool blocked: stealth mode active")
            hipaa && request.sensitive -> PolicyDecision.Blocked("sensitive tool blocked in hipaa mode")
            else -> PolicyDecision.Allowed()
        }

        if (decision is PolicyDecision.Blocked) {
            failureProtocol.handleBlock(decision.reason)
        }
        return decision
    }
}

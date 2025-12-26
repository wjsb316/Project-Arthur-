package com.arthurassistant.failure

import com.arthurassistant.status.StatusExplainer
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow

class FailureProtocol(
    private val statusExplainer: StatusExplainer
) {
    private val _uiEvents = MutableSharedFlow<String>(extraBufferCapacity = 10)
    val uiEvents = _uiEvents.asSharedFlow()

    private val _lastBlockedReason = MutableStateFlow<String?>(null)
    val lastBlockedReason: StateFlow<String?> = _lastBlockedReason

    fun handle(failure: ArthurFailure) {
        recordBlock(failure.message, prefix = "failure")
    }

    fun handleBlock(reason: String) {
        recordBlock(reason, prefix = "blocked")
    }

    private fun recordBlock(reason: String, prefix: String) {
        _lastBlockedReason.value = reason
        statusExplainer.recordBlock(reason)
        _uiEvents.tryEmit("$prefix:$reason")
        clearPendingActions()
    }

    private fun clearPendingActions() {
        // Placeholder for clearing pending actions safely.
    }
}

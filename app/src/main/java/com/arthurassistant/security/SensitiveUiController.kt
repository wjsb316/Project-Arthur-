package com.arthurassistant.security

import com.arthurassistant.status.SystemStatusController
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.flow.onEach

class SensitiveUiController(
    private val scope: CoroutineScope = CoroutineScope(Dispatchers.Main)
) {
    fun observe(stateFlow: kotlinx.coroutines.flow.StateFlow<SystemStatusController.StatusState>, onSecureChanged: (Boolean) -> Unit) {
        stateFlow.onEach { state ->
            val status = state.status.value
            onSecureChanged(status.hipaaMode || status.highRisk)
        }.launchIn(scope)
    }
}

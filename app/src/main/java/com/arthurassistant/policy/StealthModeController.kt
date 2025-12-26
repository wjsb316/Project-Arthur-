package com.arthurassistant.policy

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

class StealthModeController {
    private val _stealth = MutableStateFlow(false)
    val stealth: StateFlow<Boolean> = _stealth

    fun setStealth(enabled: Boolean) {
        _stealth.value = enabled
    }
}

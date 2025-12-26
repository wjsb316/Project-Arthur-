package com.arthurassistant.policy

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

class HipaaModeController {
    private val _hipaa = MutableStateFlow(false)
    val hipaa: StateFlow<Boolean> = _hipaa

    fun setHipaa(enabled: Boolean) {
        _hipaa.value = enabled
    }
}

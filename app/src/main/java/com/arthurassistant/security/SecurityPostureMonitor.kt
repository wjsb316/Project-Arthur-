package com.arthurassistant.security

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

class SecurityPostureMonitor {
    private val _highRisk = MutableStateFlow(false)
    val highRisk: StateFlow<Boolean> = _highRisk

    fun setHighRisk(value: Boolean) {
        _highRisk.value = value
    }
}

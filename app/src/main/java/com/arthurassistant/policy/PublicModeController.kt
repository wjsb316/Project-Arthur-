package com.arthurassistant.policy

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

class PublicModeController {
    private val _public = MutableStateFlow(false)
    val publicMode: StateFlow<Boolean> = _public

    fun setPublic(enabled: Boolean) {
        _public.value = enabled
    }
}

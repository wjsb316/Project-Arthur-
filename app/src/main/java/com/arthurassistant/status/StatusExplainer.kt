package com.arthurassistant.status

class StatusExplainer {
    private var lastBlockReason: String? = null

    fun recordBlock(reason: String) {
        lastBlockReason = reason
    }

    fun explainLatest(): String = lastBlockReason ?: "No blocks recorded"
}

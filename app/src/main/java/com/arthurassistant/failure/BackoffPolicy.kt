package com.arthurassistant.failure

class BackoffPolicy(private val baseMillis: Long = 1000L) {
    fun nextDelay(attempt: Int): Long = baseMillis * (attempt + 1)
}

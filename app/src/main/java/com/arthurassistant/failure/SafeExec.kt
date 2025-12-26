package com.arthurassistant.failure

class SafeExec(private val failureProtocol: FailureProtocol) {
    fun <T> runOrHandle(block: () -> T): T? {
        return try {
            block()
        } catch (ex: Exception) {
            failureProtocol.handle(ArthurFailure(ex.message ?: "unknown error"))
            null
        }
    }
}

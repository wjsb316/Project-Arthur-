package com.arthurassistant.status

class ExplainCommandParser {
    fun parse(command: String): String {
        return if (command.startsWith("explain")) {
            command.removePrefix("explain").trim().ifEmpty { "Explain latest" }
        } else {
            "Unsupported command"
        }
    }
}

package com.arthurassistant.voice

class SensitivityClassifier {
    enum class SensitivityLevel { LOW, PERSONAL, SENSITIVE }

    fun classify(text: String): SensitivityLevel {
        val normalized = text.lowercase()
        if (containsSensitiveKeywords(normalized) || containsLikelyCodes(normalized)) {
            return SensitivityLevel.SENSITIVE
        }
        return SensitivityLevel.PERSONAL
    }

    private fun containsSensitiveKeywords(normalized: String): Boolean {
        val keywords = listOf(
            "2fa", "two-factor", "verification code", "auth code", "one-time password", "otp", "password", "passcode", "pin code",
            "diagnosis", "medical", "hipaa", "blood", "lab result", "prescription"
        )
        return keywords.any { normalized.contains(it) }
    }

    private fun containsLikelyCodes(normalized: String): Boolean {
        val codePattern = Regex("\\b\\d{6,8}\\b")
        return codePattern.containsMatchIn(normalized)
    }
}

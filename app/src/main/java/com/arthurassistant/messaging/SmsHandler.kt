package com.arthurassistant.messaging

import android.content.Context
import android.telephony.SmsManager
import androidx.core.content.ContextCompat
import com.arthurassistant.failure.ArthurFailure
import com.arthurassistant.failure.FailureProtocol

class SmsHandler(
    private val context: Context,
    private val failureProtocol: FailureProtocol
) {
    fun hasPermission(): Boolean {
        val sendPermission = android.Manifest.permission.SEND_SMS
        val receivePermission = android.Manifest.permission.RECEIVE_SMS
        val readPermission = android.Manifest.permission.READ_SMS
        return ContextCompat.checkSelfPermission(context, sendPermission) == android.content.pm.PackageManager.PERMISSION_GRANTED &&
            ContextCompat.checkSelfPermission(context, receivePermission) == android.content.pm.PackageManager.PERMISSION_GRANTED &&
            ContextCompat.checkSelfPermission(context, readPermission) == android.content.pm.PackageManager.PERMISSION_GRANTED
    }

    fun sendSms(phone: String, text: String): Boolean {
        return try {
            val smsManager = SmsManager.getDefault()
            smsManager.sendTextMessage(phone, null, text, null, null)
            true
        } catch (ex: Exception) {
            failureProtocol.handle(ArthurFailure(ex.message ?: "sms send error"))
            false
        }
    }
}

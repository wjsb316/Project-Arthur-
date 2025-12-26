package com.arthurassistant.network

import android.content.Context
import com.arthurassistant.failure.ArthurFailure
import com.arthurassistant.failure.FailureProtocol
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import okhttp3.CertificatePinner
import okhttp3.ConnectionSpec
import okhttp3.OkHttpClient
import java.io.File
import java.io.FileInputStream
import java.security.KeyStore
import javax.inject.Named
import javax.net.ssl.KeyManager
import javax.net.ssl.KeyManagerFactory
import javax.net.ssl.SSLContext
import javax.net.ssl.SSLSocketFactory
import javax.net.ssl.TrustManagerFactory
import javax.net.ssl.X509TrustManager

class SecureHttpClientModule(
    private val context: Context,
    private val failureProtocol: FailureProtocol
) {
    companion object {
        private const val GATEWAY_HOST = "YOUR_DOMAIN"
        private const val ANDROID_KEYSTORE = "AndroidKeyStore"
        private const val GATEWAY_KEY_ALIAS = "gateway_client"
        private const val DEV_PKCS12_FILE = "gateway-dev-keystore.p12"
    }

    private val _pinnedConfigured = MutableStateFlow(false)
    val pinnedConfigured: StateFlow<Boolean> = _pinnedConfigured

    private val _pinningFailureReason = MutableStateFlow<String?>(null)
    val pinningFailureReason: StateFlow<String?> = _pinningFailureReason

    private val certificatePinner: CertificatePinner? = buildCertificatePinner()

    @Named("gatewayOkHttp")
    fun gatewayOkHttp(): OkHttpClient {
        val builder = OkHttpClient.Builder()
        certificatePinner?.let { builder.certificatePinner(it) }
        configureMtls(builder)
        builder.connectionSpecs(listOf(ConnectionSpec.RESTRICTED_TLS, ConnectionSpec.MODERN_TLS))
        return builder.build()
    }

    @Named("defaultOkHttp")
    fun defaultOkHttp(): OkHttpClient = OkHttpClient.Builder().build()

    private fun buildCertificatePinner(): CertificatePinner? {
        return try {
            CertificatePinner.Builder()
                .add(GATEWAY_HOST, "sha256/PLACEHOLDER_PIN_1")
                .add(GATEWAY_HOST, "sha256/PLACEHOLDER_PIN_2")
                .build()
                .also { _pinnedConfigured.value = true }
        } catch (ex: Exception) {
            val reason = "Pinning config error: ${ex.message}"
            _pinnedConfigured.value = false
            _pinningFailureReason.value = reason
            failureProtocol.handle(ArthurFailure(reason))
            null
        }
    }

    private fun configureMtls(builder: OkHttpClient.Builder) {
        val trustManager = defaultTrustManager() ?: return
        val keyManagers = clientKeyManagers(trustManager)
        if (keyManagers != null) {
            try {
                val sslContext = SSLContext.getInstance("TLS")
                sslContext.init(keyManagers, arrayOf(trustManager), null)
                val socketFactory: SSLSocketFactory = sslContext.socketFactory
                builder.sslSocketFactory(socketFactory, trustManager)
            } catch (ex: Exception) {
                failureProtocol.handle(ArthurFailure("mTLS setup error: ${ex.message}"))
            }
        } else {
            builder.sslSocketFactory(defaultSslContext(trustManager).socketFactory, trustManager)
        }
    }

    private fun defaultTrustManager(): X509TrustManager? {
        return try {
            val factory = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm())
            factory.init(null as KeyStore?)
            factory.trustManagers.filterIsInstance<X509TrustManager>().firstOrNull()
        } catch (ex: Exception) {
            failureProtocol.handle(ArthurFailure("Trust manager error: ${ex.message}"))
            null
        }
    }

    private fun clientKeyManagers(trustManager: X509TrustManager): Array<KeyManager>? {
        return keystoreKeyManagers(trustManager) ?: pkcs12KeyManagers(trustManager)
    }

    private fun keystoreKeyManagers(trustManager: X509TrustManager): Array<KeyManager>? {
        return try {
            val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
            if (!keyStore.containsAlias(GATEWAY_KEY_ALIAS)) return null
            val kmf = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm())
            kmf.init(keyStore, null)
            kmf.keyManagers
        } catch (_: Exception) {
            null
        }
    }

    private fun pkcs12KeyManagers(trustManager: X509TrustManager): Array<KeyManager>? {
        val pkcsFile = File(context.filesDir, DEV_PKCS12_FILE)
        if (!pkcsFile.exists()) return null
        return try {
            val keyStore = KeyStore.getInstance("PKCS12")
            FileInputStream(pkcsFile).use { input ->
                keyStore.load(input, "TODO_PKCS12_PASSWORD".toCharArray())
            }
            val kmf = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm())
            kmf.init(keyStore, "TODO_PKCS12_PASSWORD".toCharArray())
            kmf.keyManagers
        } catch (ex: Exception) {
            failureProtocol.handle(ArthurFailure("PKCS12 load error: ${ex.message}"))
            null
        }
    }

    private fun defaultSslContext(trustManager: X509TrustManager): SSLContext {
        val sslContext = SSLContext.getInstance("TLS")
        sslContext.init(null, arrayOf(trustManager), null)
        return sslContext
    }
}

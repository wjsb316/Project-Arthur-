package com.arthurassistant.network

import okhttp3.OkHttpClient
import javax.inject.Named

class TokenProvider(
    @Named("gatewayOkHttp") private val okHttpClient: OkHttpClient
) {
    fun client(): OkHttpClient = okHttpClient
}

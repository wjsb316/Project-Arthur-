package com.arthurassistant.status

import com.arthurassistant.failure.FailureProtocol
import com.arthurassistant.policy.HipaaModeController
import com.arthurassistant.policy.PublicModeController
import com.arthurassistant.policy.StealthModeController
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.SharingStarted

class SystemStatusController(
    private val scope: CoroutineScope = CoroutineScope(Dispatchers.Default),
    private val stealthModeController: StealthModeController = StealthModeController(),
    private val hipaaModeController: HipaaModeController = HipaaModeController(),
    private val publicModeController: PublicModeController = PublicModeController(),
    val statusExplainer: StatusExplainer = StatusExplainer(),
    private val failureProtocol: FailureProtocol = FailureProtocol(statusExplainer),
    private val listeningFlow: StateFlow<Boolean> = MutableStateFlow(false),
    private val listeningPauseReason: StateFlow<String?> = MutableStateFlow(null),
    private val pinnedTlsConfigured: StateFlow<Boolean> = MutableStateFlow(false),
    private val pinningFailureReason: StateFlow<String?> = MutableStateFlow(null)
) {
    data class SystemStatus(
        val listeningActive: Boolean,
        val listeningPauseReason: String?,
        val networkAvailable: Boolean,
        val stealth: Boolean,
        val publicMode: Boolean,
        val hipaaMode: Boolean,
        val highRisk: Boolean,
        val lastBlock: String?,
        val pinnedTlsConfigured: Boolean,
        val pinningFailureReason: String?
    )

    data class StatusState(
        val status: StateFlow<SystemStatus>,
        val statusExplainer: StatusExplainer,
        val refreshRequested: MutableStateFlow<Int>
    )

    private val networkFlow = MutableStateFlow(true)
    private val highRiskFlow = MutableStateFlow(false)
    private val refreshFlow = MutableStateFlow(0)

    private val statusFlow: StateFlow<SystemStatus> = combine(
        listeningFlow,
        listeningPauseReason,
        networkFlow,
        stealthModeController.stealth,
        publicModeController.publicMode,
        hipaaModeController.hipaa,
        highRiskFlow,
        failureProtocol.lastBlockedReason,
        pinnedTlsConfigured,
        pinningFailureReason
    ) { listening, pauseReason, network, stealth, public, hipaa, highRisk, lastBlock, pinned, pinFailure ->
        SystemStatus(
            listeningActive = listening,
            listeningPauseReason = pauseReason,
            networkAvailable = network,
            stealth = stealth,
            publicMode = public,
            hipaaMode = hipaa,
            highRisk = highRisk,
            lastBlock = lastBlock,
            pinnedTlsConfigured = pinned,
            pinningFailureReason = pinFailure
        )
    }.stateIn(scope, SharingStarted.WhileSubscribed(5000), SystemStatus(false, null, true, false, false, false, false, null, false, null))

    val state: StatusState = StatusState(statusFlow, statusExplainer, refreshFlow)
}

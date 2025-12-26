package com.arthurassistant

import android.Manifest
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedTextField
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.room.Room
import com.arthurassistant.failure.FailureProtocol
import com.arthurassistant.lockout.LockoutManager
import com.arthurassistant.messaging.SmsHandler
import com.arthurassistant.messaging.SmsReceiver
import com.arthurassistant.messaging.WhatsAppNotificationListener
import com.arthurassistant.notes.NotesDatabase
import com.arthurassistant.notes.NotesRepository
import com.arthurassistant.network.SecureHttpClientModule
import com.arthurassistant.network.TokenProvider
import com.arthurassistant.policy.BatmanOverrideController
import com.arthurassistant.policy.HipaaModeController
import com.arthurassistant.policy.PolicyEngine
import com.arthurassistant.policy.PublicModeController
import com.arthurassistant.policy.StealthModeController
import com.arthurassistant.security.SensitiveUiController
import com.arthurassistant.status.StatusExplainer
import com.arthurassistant.status.SystemStatusController
import com.arthurassistant.tools.ToolCall
import com.arthurassistant.tools.ToolRouter
import com.arthurassistant.ui.composables.NotesSection
import com.arthurassistant.ui.composables.SystemStatusCard
import com.arthurassistant.voice.ArthurVoiceService
import com.arthurassistant.voice.ArthurSpeaker
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    private val stealthModeController = StealthModeController()
    private val hipaaModeController = HipaaModeController()
    private val publicModeController = PublicModeController()
    private val lockoutManager = LockoutManager()
    private val statusExplainer = StatusExplainer()
    private val failureProtocol = FailureProtocol(statusExplainer)
    private lateinit var secureHttpClientModule: SecureHttpClientModule
    private val sensitiveUiController = SensitiveUiController()
    private lateinit var systemStatusController: SystemStatusController
    private lateinit var notesRepository: NotesRepository
    private lateinit var toolRouter: ToolRouter
    private lateinit var arthurSpeaker: ArthurSpeaker
    private lateinit var smsHandler: SmsHandler

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val notesDatabase = Room.databaseBuilder(
            applicationContext,
            NotesDatabase::class.java,
            "notes.db"
        ).build()
        notesRepository = NotesRepository(notesDatabase.noteDao())
        smsHandler = SmsHandler(applicationContext, failureProtocol)
        secureHttpClientModule = SecureHttpClientModule(applicationContext, failureProtocol)
        val tokenProvider = TokenProvider(secureHttpClientModule.gatewayOkHttp())

        val policyEngine = PolicyEngine(
            stealthModeController,
            hipaaModeController,
            publicModeController,
            failureProtocol
        )
        val batmanOverrideController = BatmanOverrideController(lockoutManager, policyEngine, failureProtocol)
        SmsReceiver.registerFailureProtocol(failureProtocol)
        WhatsAppNotificationListener.registerFailureProtocol(failureProtocol)
        toolRouter = ToolRouter(
            context = applicationContext,
            policyEngine = policyEngine,
            failureProtocol = failureProtocol,
            notesRepository = notesRepository,
            lockoutManager = lockoutManager,
            batmanOverrideController = batmanOverrideController,
            stealthModeController = stealthModeController,
            hipaaModeController = hipaaModeController,
            statusExplainer = statusExplainer,
            smsHandler = smsHandler
        )
        arthurSpeaker = ArthurSpeaker(applicationContext, policyEngine, failureProtocol)
        ArthurVoiceService.registerFailureProtocol(failureProtocol)
        systemStatusController = SystemStatusController(
            stealthModeController = stealthModeController,
            hipaaModeController = hipaaModeController,
            publicModeController = publicModeController,
            failureProtocol = failureProtocol,
            statusExplainer = statusExplainer,
            listeningFlow = ArthurVoiceService.listening,
            listeningPauseReason = ArthurVoiceService.pauseReason,
            pinnedTlsConfigured = secureHttpClientModule.pinnedConfigured,
            pinningFailureReason = secureHttpClientModule.pinningFailureReason
        )

        setContent {
            App(
                statusState = systemStatusController.state,
                toolRouter = toolRouter,
                notesRepository = notesRepository,
                batmanOverrideController = batmanOverrideController,
                arthurSpeaker = arthurSpeaker
            )
        }

        sensitiveUiController.observe(systemStatusController.state) { shouldSecure ->
            if (shouldSecure) {
                window.setFlags(
                    WindowManager.LayoutParams.FLAG_SECURE,
                    WindowManager.LayoutParams.FLAG_SECURE
                )
            } else {
                window.clearFlags(WindowManager.LayoutParams.FLAG_SECURE)
            }
        }
    }

    override fun onDestroy() {
        arthurSpeaker.shutdown()
        super.onDestroy()
    }
}

@Composable
fun App(
    statusState: SystemStatusController.StatusState,
    toolRouter: ToolRouter,
    notesRepository: NotesRepository,
    batmanOverrideController: BatmanOverrideController,
    arthurSpeaker: ArthurSpeaker
) {
    val recentNotes by notesRepository.recentNotes().collectAsState(initial = emptyList())
    val scope = rememberCoroutineScope()
    val batmanState by batmanOverrideController.state.collectAsState()
    val feedMessages = remember { mutableStateListOf<String>() }
    var batmanMessage by remember { mutableStateOf<String?>(null) }
    var showPinDialog by remember { mutableStateOf(false) }
    var pinEntry by remember { mutableStateOf("") }
    var pinError by remember { mutableStateOf<String?>(null) }
    val context = LocalContext.current
    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { }
    val appendToFeed: (String) -> Unit = { text ->
        feedMessages.add(text)
        if (feedMessages.size > 20) {
            feedMessages.removeAt(0)
        }
    }

    MaterialTheme {
        Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
            Column {
                BatmanBanner(state = batmanState, message = batmanMessage)
                SystemStatusCard(
                    statusState = statusState,
                    onRequestPermissions = {
                        permissionLauncher.launch(
                            arrayOf(
                                Manifest.permission.SEND_SMS,
                                Manifest.permission.RECEIVE_SMS,
                                Manifest.permission.READ_SMS
                            )
                        )
                    },
                    onOpenNotificationSettings = {
                        context.startActivity(
                            Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS).apply {
                                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                            }
                        )
                    },
                    onRefresh = { statusState.refreshRequested.value = statusState.refreshRequested.value + 1 },
                    onExplain = { statusState.statusExplainer.explainLatest() },
                    onStartListening = { ArthurVoiceService.start(context) },
                    onStopListening = { ArthurVoiceService.stop(context) }
                )
                NotesSection(
                    notes = recentNotes,
                    onAddNote = { text ->
                        scope.launch {
                            toolRouter.handle(ToolCall(name = "create_note", args = mapOf("text" to text)))
                        }
                    },
                    onDeleteNote = { id ->
                        scope.launch {
                            toolRouter.handle(ToolCall(name = "delete_note", args = mapOf("id" to id)))
                        }
                    }
                )

                LaunchedEffect(toolRouter, "transcripts") {
                    ArthurVoiceService.transcripts.collect { transcript ->
                        toolRouter.interceptTranscript(transcript)
                    }
                }

                LaunchedEffect(toolRouter, "uiMessages") {
                    toolRouter.uiMessages.collect { message ->
                        val text = when (message) {
                            is ToolRouter.UiMessage.Speak -> message.text
                            is ToolRouter.UiMessage.UiOnly -> message.text
                        }
                        when (message) {
                            is ToolRouter.UiMessage.Speak -> arthurSpeaker.speak(text)
                            is ToolRouter.UiMessage.UiOnly -> false
                        }
                        appendToFeed(text)
                    }
                }

                LaunchedEffect("incomingSms") {
                    SmsReceiver.incoming.collect { incoming ->
                        appendToFeed("${incoming.source}: ${incoming.text}")
                    }
                }

                LaunchedEffect("whatsappPreviews") {
                    WhatsAppNotificationListener.previews.collect { preview ->
                        appendToFeed("${preview.source}: ${preview.text}")
                    }
                }

                LaunchedEffect(toolRouter, "batmanEvents") {
                    toolRouter.batmanEvents.collect { event ->
                        when (event) {
                            is ToolRouter.BatmanEvent.Challenge -> {
                                batmanMessage = event.message
                            }

                            ToolRouter.BatmanEvent.RequestPin -> {
                                batmanMessage = "Batman override pending PIN."
                                showPinDialog = true
                                pinError = null
                                pinEntry = ""
                            }

                            is ToolRouter.BatmanEvent.Cleared -> {
                                batmanMessage = event.message
                                showPinDialog = false
                                pinEntry = ""
                                pinError = null
                            }

                            is ToolRouter.BatmanEvent.PinFailed -> {
                                pinError = event.message
                                showPinDialog = true
                            }
                        }
                    }
                }

                Feed(messages = feedMessages)

                if (showPinDialog && batmanState is BatmanOverrideController.State.AwaitingPin) {
                    AlertDialog(
                        onDismissRequest = { showPinDialog = false },
                        confirmButton = {
                            Button(onClick = {
                                val success = batmanOverrideController.confirmPin(pinEntry)
                                if (success) {
                                    showPinDialog = false
                                    pinEntry = ""
                                    pinError = null
                                } else {
                                    pinError = "Incorrect PIN"
                                }
                            }) {
                                Text("Confirm")
                            }
                        },
                        dismissButton = {
                            Button(onClick = { showPinDialog = false }) { Text("Cancel") }
                        },
                        title = { Text("Batman Override Authorization") },
                        text = {
                            Column {
                                OutlinedTextField(
                                    value = pinEntry,
                                    onValueChange = { pinEntry = it },
                                    label = { Text("Enter PIN") },
                                    visualTransformation = PasswordVisualTransformation()
                                )
                                if (pinError != null) {
                                    Text(pinError!!)
                                }
                            }
                        }
                    )
                }
            }
        }
    }
}

@Composable
private fun BatmanBanner(state: BatmanOverrideController.State, message: String?) {
    if (state is BatmanOverrideController.State.Idle && message == null) return
    val statusText = when (state) {
        is BatmanOverrideController.State.Challenged -> "Batman override challenge active"
        is BatmanOverrideController.State.AwaitingPin -> "Batman override awaiting PIN"
        else -> message ?: "Batman override"
    }
    Surface(modifier = Modifier.fillMaxWidth()) {
        Column {
            Text(text = statusText)
            if (message != null) {
                Text(text = message)
            }
        }
    }
}

@Composable
private fun Feed(messages: List<String>) {
    Column(modifier = Modifier.fillMaxWidth()) {
        Text(text = "Feed")
        messages.asReversed().forEach { entry ->
            Text(text = entry)
        }
    }
}

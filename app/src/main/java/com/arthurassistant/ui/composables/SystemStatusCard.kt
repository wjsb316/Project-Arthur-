package com.arthurassistant.ui.composables

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.arthurassistant.status.SystemStatusController

@Composable
fun SystemStatusCard(
    statusState: SystemStatusController.StatusState,
    onRequestPermissions: () -> Unit,
    onOpenNotificationSettings: () -> Unit,
    onRefresh: () -> Unit,
    onExplain: () -> Unit,
    onStartListening: () -> Unit,
    onStopListening: () -> Unit
) {
    val status = statusState.status.value
    Card(modifier = Modifier.fillMaxWidth().padding(16.dp)) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(text = "Listening: ${status.listeningActive}")
            status.listeningPauseReason?.let { reason ->
                Text(text = "Listening paused: $reason")
            }
            Text(text = "Network: ${status.networkAvailable}")
            Text(text = "Stealth: ${status.stealth}")
            Text(text = "Public: ${status.publicMode}")
            Text(text = "HIPAA: ${status.hipaaMode}")
            Text(text = "High Risk: ${status.highRisk}")
            Text(text = "Last Block: ${status.lastBlock ?: "None"}")
            val pinStatus = if (status.pinnedTlsConfigured) "yes" else "no"
            val pinFailure = status.pinningFailureReason
            Text(text = "Pinned TLS configured: $pinStatus" + (pinFailure?.let { " ($it)" } ?: ""))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onRequestPermissions) { Text("App permissions") }
                Button(onClick = onOpenNotificationSettings) { Text("Notification listener settings") }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onRefresh) { Text("Refresh") }
                Button(onClick = onExplain) { Text("Explain") }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onStartListening) { Text("Start Listening") }
                Button(onClick = onStopListening) { Text("Stop Listening") }
            }
        }
    }
}

package com.waha.apk

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.annotation.RawRes
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.ExperimentalMaterialApi
import androidx.compose.material.pullrefresh.PullRefreshIndicator
import androidx.compose.material.pullrefresh.pullRefresh
import androidx.compose.material.pullrefresh.rememberPullRefreshState
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.SupportAgent
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.ImageLoader
import coil.compose.AsyncImage
import coil.decode.GifDecoder
import coil.decode.ImageDecoderDecoder
import coil.request.ImageRequest
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import com.google.gson.annotations.SerializedName
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch
import kotlin.math.roundToInt
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Url
import retrofit2.HttpException
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.width
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ButtonDefaults
import androidx.compose.ui.window.Dialog
import androidx.compose.material3.TextButton
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.IntOffset
import java.net.URI

private val ComponentActivity.dataStore by preferencesDataStore(name = "monitor_settings")

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        createNotificationChannel(this)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1001)
            }
        }
        val prefs = AppPreferences(dataStore)
        setContent {
            MaterialTheme(colorScheme = androidx.compose.material3.darkColorScheme(
                primary = Color(0xFF58A6FF),
                secondary = Color(0xFF39D2C0),
                background = Color(0xFF0D1117),
                surface = Color(0xFF161B22),
                onBackground = Color(0xFFE6EDF3),
                onSurface = Color(0xFFE6EDF3)
            )) {
                val vm: MonitorViewModel = viewModel(factory = MonitorViewModelFactory(prefs))
                MonitorApp(vm)
            }
        }
    }
}

enum class TabItem(val label: String) {
    Dashboard("Dashboard"),
    Cases("Cases"),
    Staff("Super Staff"),
    Cron("Cron"),
    Settings("Settings")
}

@Composable
private fun MonitorApp(vm: MonitorViewModel) {
    val state by vm.uiState.collectAsState()
    var tab by remember { mutableStateOf(TabItem.Dashboard) }
    var caseFormTarget by remember { mutableStateOf<SessionDto?>(null) }
    val snack = remember { SnackbarHostState() }

    LaunchedEffect(state.notice) {
        state.notice?.let {
            snack.showSnackbar(it)
            vm.clearNotice()
        }
    }

    LaunchedEffect(tab) {
        caseFormTarget = null
    }

    val notifContext = LocalContext.current
    LaunchedEffect(state.notificationEvent) {
        state.notificationEvent?.let { event ->
            postAndroidNotification(notifContext, event)
            vm.clearNotificationEvent()
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snack) },
        bottomBar = {
            NavigationBar {
                NavigationBarItem(tab == TabItem.Dashboard, { tab = TabItem.Dashboard }, { Icon(Icons.Filled.Dashboard, null) }, label = { Text("Dashboard") })
                NavigationBarItem(tab == TabItem.Cases, { tab = TabItem.Cases }, { Icon(Icons.AutoMirrored.Filled.List, null) }, label = { Text("Cases") })
                NavigationBarItem(tab == TabItem.Staff, { tab = TabItem.Staff }, { Icon(Icons.Filled.SupportAgent, null) }, label = { Text("Staff") })
                NavigationBarItem(tab == TabItem.Cron, { tab = TabItem.Cron }, { Icon(Icons.Filled.Build, null) }, label = { Text("Cron") })
                NavigationBarItem(tab == TabItem.Settings, { tab = TabItem.Settings }, { Icon(Icons.Filled.Settings, null) }, label = { Text("Settings") })
            }
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .background(Color(0xFF0D1117))
        ) {
            Row(
                modifier = Modifier.fillMaxWidth().padding(12.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(state.bossName.ifBlank { "MyDora Monitor" }, fontWeight = FontWeight.Bold)
                if (caseFormTarget != null) {
                    IconButton(onClick = { caseFormTarget = null }) {
                        Box(
                            modifier = Modifier
                                .background(Color(0xFFF85149), CircleShape)
                                .padding(8.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(Icons.Filled.Clear, contentDescription = "Close", tint = Color.White, modifier = Modifier.size(18.dp))
                        }
                    }
                } else {
                    IconButton(onClick = vm::refreshAll) {
                        Icon(Icons.Filled.Refresh, contentDescription = "Refresh")
                    }
                }
            }

            when (tab) {
                TabItem.Dashboard -> DashboardScreen(state, vm::refreshAll)
                TabItem.Cases -> CasesScreen(state, vm, vm::refreshAll, caseFormTarget) { caseFormTarget = it }
                TabItem.Staff -> StaffScreen(state, vm::refreshAll)
                TabItem.Cron -> CronScreen(state, vm, vm::refreshAll)
                TabItem.Settings -> SettingsScreen(state, vm, vm::refreshAll)
            }
        }

        if (state.loading) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
        }
    }
}

@Composable
private fun DashboardScreen(state: UiState, onRefresh: () -> Unit) {
    PullToRefreshContainer(isRefreshing = state.loading, onRefresh = onRefresh) {
        LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = 12.dp)) {
            item {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                    StatCard("Cases", state.sessions.size.toString(), Modifier.weight(1f))
                    StatCard("Staff", state.staff.size.toString(), Modifier.weight(1f))
                    StatCard("CPU", state.summary.cpuLabel, Modifier.weight(1f))
                }
                Spacer(Modifier.height(12.dp))
                OfficeStrip(state.sessions, state.staff)
                Spacer(Modifier.height(12.dp))
                Text("Cases", fontWeight = FontWeight.SemiBold)
            }
            items(state.sessions.take(10)) { SessionCard(it) }
            item { Spacer(Modifier.height(64.dp)) }
        }
    }
}

@Composable
private fun OfficeStrip(sessions: List<SessionDto>, staff: List<StaffDto>) {
    val context = LocalContext.current
    val gifImageLoader = rememberGifImageLoader(context)
    val runningStates = setOf("running-tools")
    val discussingStates = setOf("thinking")
    val runningSessions = sessions.filter { it.state in runningStates }
    val discussingSessions = sessions.filter { it.state in discussingStates }

    Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF161B22))) {
        Column(modifier = Modifier.fillMaxWidth().padding(10.dp)) {
            Text("Live Activity", color = Color(0xFF8B949E), style = MaterialTheme.typography.bodySmall)
            Spacer(Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                if (runningSessions.isNotEmpty()) {
                    runningSessions.take(2).forEach { session ->
                        val gifRes = resolveWorkingGif(session, staff)
                        AsyncImage(
                            model = ImageRequest.Builder(context).data(rawResUri(context, gifRes)).build(),
                            imageLoader = gifImageLoader,
                            contentDescription = session.title,
                            modifier = Modifier.size(96.dp),
                            contentScale = ContentScale.Crop
                        )
                    }
                } else {
                    AsyncImage(
                        model = ImageRequest.Builder(context).data(rawResUri(context, R.raw.working_staff_loop)).build(),
                        imageLoader = gifImageLoader,
                        contentDescription = "Working",
                        modifier = Modifier.size(96.dp),
                        contentScale = ContentScale.Crop
                    )
                }

                if (discussingSessions.isNotEmpty()) {
                    AsyncImage(
                        model = ImageRequest.Builder(context).data(rawResUri(context, R.raw.discuss_group_loop)).build(),
                        imageLoader = gifImageLoader,
                        contentDescription = "Discussion",
                        modifier = Modifier.size(96.dp),
                        contentScale = ContentScale.Crop
                    )
                }
            }
        }
    }
}

private fun resolveWorkingGif(session: SessionDto, staff: List<StaffDto>): Int {
    val title = session.title.lowercase()
    val matched = staff.firstOrNull { s ->
        s.name.isNotBlank() && title.contains(s.name.lowercase())
    }
    return if ((matched?.gender ?: "").lowercase() == "female") {
        R.raw.working_staff_loop_female
    } else {
        R.raw.working_staff_loop
    }
}

@Composable
private fun rememberGifImageLoader(context: Context): ImageLoader {
    return remember(context) {
        ImageLoader.Builder(context)
            .components {
                if (Build.VERSION.SDK_INT >= 28) {
                    add(ImageDecoderDecoder.Factory())
                } else {
                    add(GifDecoder.Factory())
                }
            }
            .build()
    }
}

private fun rawResUri(context: Context, @RawRes resId: Int): String {
    return "android.resource://${context.packageName}/$resId"
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CasesScreen(state: UiState, vm: MonitorViewModel, onRefresh: () -> Unit, formTarget: SessionDto? = null, onFormTargetChange: (SessionDto?) -> Unit = {}) {
    val sessionOptions = sessionDropdownList(state)
    var sessionSearch by remember { mutableStateOf("") }
    var viewTarget by remember { mutableStateOf<SessionDto?>(null) }
    var renameTarget by remember { mutableStateOf<SessionDto?>(null) }
    var stopTarget by remember { mutableStateOf<SessionDto?>(null) }

    val filteredSessionOptions = remember(sessionOptions, sessionSearch) {
        sessionOptions.filter { it.matchesSessionFilter(sessionSearch) }
    }

    PullToRefreshContainer(isRefreshing = state.loading, onRefresh = onRefresh) {
        if (formTarget != null) {
            CaseFormScreen(formTarget, state, vm) { onFormTargetChange(null) }
        } else {
            LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = 12.dp)) {
                item {
                    OutlinedTextField(
                        value = sessionSearch,
                        onValueChange = { sessionSearch = it },
                        label = { Text("Search") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    Spacer(Modifier.height(8.dp))
                }
                items(filteredSessionOptions) { session ->
                    SwipeableCaseItem(session, isActive = session.state == "thinking" || session.state == "running-tools",
                        onSelect = { onFormTargetChange(session) },
                        onView = { viewTarget = session },
                        onRename = { renameTarget = session },
                        onStop = { stopTarget = session }
                    ) { SessionCard(session) }
                }
                item { Spacer(Modifier.height(64.dp)) }
            }
        }
    }
    viewTarget?.let { ViewCaseDialog(it) { viewTarget = null } }
    renameTarget?.let { RenameCaseDialog(it, vm) { renameTarget = null } }
    stopTarget?.let { StopConfirmDialog(it, vm) { stopTarget = null } }
}

@Composable
private fun StaffScreen(state: UiState, onRefresh: () -> Unit) {
    PullToRefreshContainer(isRefreshing = state.loading, onRefresh = onRefresh) {
        LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = 12.dp)) {
            items(state.staff) { s ->
                Card(modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp), colors = CardDefaults.cardColors(containerColor = Color(0xFF161B22))) {
                    Column(Modifier.padding(12.dp)) {
                        Text(s.name, fontWeight = FontWeight.SemiBold)
                        Text("${s.gender ?: "-"} • ${s.mode ?: "default"} • ${s.model?.takeIf { it.isNotBlank() } ?: "default model"}", color = Color(0xFF8B949E))
                        if (!s.description.isNullOrBlank()) {
                            Text(s.description ?: "", maxLines = 2, overflow = TextOverflow.Ellipsis)
                        }
                    }
                }
            }
            item { Spacer(Modifier.height(64.dp)) }
        }
    }
}

@Composable
private fun CronScreen(state: UiState, vm: MonitorViewModel, onRefresh: () -> Unit) {
    PullToRefreshContainer(isRefreshing = state.loading, onRefresh = onRefresh) {
        LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = 12.dp)) {
            items(state.cronJobs) { c ->
                Card(modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp), colors = CardDefaults.cardColors(containerColor = Color(0xFF161B22))) {
                    Column(Modifier.padding(12.dp)) {
                        Text(c.name ?: "Cron job", fontWeight = FontWeight.SemiBold)
                        Text("Every ${c.intervalSec ?: 0}s", color = Color(0xFF8B949E))
                        Text("Last run: ${formatTimestamp(c.lastRun)}  -  Next run: ${c.nextRunDisplay()}", color = Color(0xFF8B949E), style = MaterialTheme.typography.bodySmall)
                        val countdown = formatCountdown(c.lastRun, c.intervalSec)
                        if (countdown.isNotBlank()) {
                            Text("Time to next run: $countdown", color = Color(0xFFD29922), style = MaterialTheme.typography.bodySmall)
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Button(onClick = { c.id?.let(vm::toggleCron) }) { Text("Toggle") }
                            Button(onClick = { c.id?.let(vm::runCron) }) { Text("Run") }
                        }
                    }
                }
            }
            item { Spacer(Modifier.height(64.dp)) }
        }
    }
}

@Composable
private fun SettingsScreen(state: UiState, vm: MonitorViewModel, onRefresh: () -> Unit) {
    val tabs = listOf("Connections", "Services", "Others")
    var selectedTab by remember { mutableStateOf(0) }
    var baseUrl by remember(state.baseUrl) { mutableStateOf(state.baseUrl) }
    var apiKey by remember(state.apiKey) { mutableStateOf(state.apiKey) }
    var bossName by remember(state.bossName) { mutableStateOf(state.bossName) }

    PullToRefreshContainer(isRefreshing = state.loading, onRefresh = onRefresh) {
        Column(modifier = Modifier.fillMaxSize().padding(12.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                tabs.forEachIndexed { i, label ->
                    val selected = selectedTab == i
                    TextButton(
                        onClick = { selectedTab = i },
                        colors = ButtonDefaults.textButtonColors(
                            containerColor = if (selected) Color(0xFF30363D) else Color.Transparent,
                            contentColor = if (selected) Color.White else Color(0xFF8B949E)
                        ),
                        shape = RoundedCornerShape(6.dp)
                    ) { Text(label, fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal) }
                }
            }
            Spacer(Modifier.height(12.dp))
            when (selectedTab) {
                0 -> {
                    OutlinedTextField(value = baseUrl, onValueChange = { baseUrl = it }, label = { Text("Base URL") }, modifier = Modifier.fillMaxWidth())
                    Spacer(Modifier.height(8.dp))
                    OutlinedTextField(value = apiKey, onValueChange = { apiKey = it }, label = { Text("API key") }, modifier = Modifier.fillMaxWidth())
                    Spacer(Modifier.height(8.dp))
                    Button(onClick = { vm.saveSettings(baseUrl, apiKey) }) { Text("Save") }
                }
                1 -> {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = vm::restartDaemon) { Text("Restart Daemon") }
                        Button(onClick = vm::killDaemon) { Text("Kill Daemon") }
                    }
                }
                2 -> {
                    OutlinedTextField(value = bossName, onValueChange = { bossName = it }, label = { Text("Boss Name") }, modifier = Modifier.fillMaxWidth())
                    Spacer(Modifier.height(8.dp))
                    Button(onClick = { vm.saveBossName(bossName) }) { Text("Save") }
                }
            }
        }
    }
}

@Composable
@OptIn(ExperimentalMaterialApi::class)
private fun PullToRefreshContainer(
    isRefreshing: Boolean,
    onRefresh: () -> Unit,
    content: @Composable () -> Unit
) {
    val pullState = rememberPullRefreshState(refreshing = isRefreshing, onRefresh = onRefresh)
    Box(
        modifier = Modifier
            .fillMaxSize()
            .pullRefresh(pullState)
    ) {
        content()
        PullRefreshIndicator(
            refreshing = isRefreshing,
            state = pullState,
            modifier = Modifier.align(Alignment.TopCenter)
        )
    }
}

@Composable
private fun SessionCard(session: SessionDto) {
    val stateColor = when (session.state) {
        "thinking" -> Color(0xFFD29922)
        "running-tools" -> Color(0xFF58A6FF)
        "complete" -> Color(0xFF3FB950)
        "error" -> Color(0xFFF85149)
        else -> Color(0xFF8B949E)
    }
    Card(modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp), colors = CardDefaults.cardColors(containerColor = Color(0xFF161B22))) {
        Column(Modifier.padding(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(modifier = Modifier.size(10.dp).background(stateColor, RoundedCornerShape(16.dp)))
                Spacer(Modifier.size(8.dp))
                Text(session.title.ifBlank { "Untitled case" }, fontWeight = FontWeight.SemiBold)
            }
            if (!session.lastText.isNullOrBlank()) {
                Spacer(Modifier.height(4.dp))
                Text(session.lastText ?: "", maxLines = 2, overflow = TextOverflow.Ellipsis, color = Color(0xFF8B949E))
            }
            if (!session.id.isNullOrBlank()) {
                Spacer(Modifier.height(4.dp))
                Text(session.id ?: "", color = Color(0xFF58A6FF), style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun SwipeableCaseItem(
    session: SessionDto,
    isActive: Boolean,
    onSelect: () -> Unit,
    onView: () -> Unit,
    onRename: () -> Unit,
    onStop: () -> Unit,
    content: @Composable () -> Unit
) {
    val scope = rememberCoroutineScope()
    val density = LocalDensity.current
    val revealWidthPx = with(density) { 300.dp.toPx() }
    val offsetX = remember { Animatable(0f) }

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clipToBounds()
    ) {
        Row(
            modifier = Modifier
                .align(Alignment.CenterEnd)
                .height(IntrinsicSize.Min)
                .background(Color(0xFF0D1117), RoundedCornerShape(topStart = 10.dp, bottomStart = 10.dp)),
            horizontalArrangement = Arrangement.End
        ) {
            val btnMod = Modifier.width(100.dp).fillMaxHeight().padding(vertical = 6.dp)
            SwipeActionButton("View", Icons.Filled.Visibility, Color(0xFF58A6FF), btnMod) {
                scope.launch { offsetX.animateTo(0f, tween(150)) }
                onView()
            }
            SwipeActionButton("Rename", Icons.Filled.Edit, Color(0xFFD29922), btnMod) {
                scope.launch { offsetX.animateTo(0f, tween(150)) }
                onRename()
            }
            if (isActive) {
                SwipeActionButton("Stop", Icons.Filled.Stop, Color(0xFFF85149), btnMod) {
                    scope.launch { offsetX.animateTo(0f, tween(150)) }
                    onStop()
                }
            }
        }

        Box(
            modifier = Modifier
                .offset { IntOffset(offsetX.value.roundToInt(), 0) }
                .pointerInput(Unit) {
                    detectHorizontalDragGestures(
                        onDragEnd = {
                            scope.launch {
                                val target = if (offsetX.value < -revealWidthPx * 0.4f) -revealWidthPx else 0f
                                offsetX.animateTo(target, tween(200))
                            }
                        },
                        onHorizontalDrag = { _, dragAmount ->
                            scope.launch {
                                offsetX.snapTo((offsetX.value + dragAmount).coerceIn(-revealWidthPx, 0f))
                            }
                        }
                    )
                }
                .pointerInput(Unit) {
                    detectTapGestures(
                        onTap = {
                            if (offsetX.value < 0f) {
                                scope.launch { offsetX.animateTo(0f, tween(150)) }
                            } else {
                                onSelect()
                            }
                        }
                    )
                }
        ) {
            content()
        }
    }
}

@Composable
private fun SwipeActionButton(label: String, icon: ImageVector, color: Color, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Box(
        modifier = modifier
            .background(color)
            .clickable(
                interactionSource = remember { MutableInteractionSource() },
                indication = null,
                onClick = onClick
            ),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(icon, contentDescription = label, tint = Color.White, modifier = Modifier.size(24.dp))
            Spacer(Modifier.height(4.dp))
            Text(label, color = Color.White, fontWeight = FontWeight.SemiBold, fontSize = MaterialTheme.typography.labelSmall.fontSize)
        }
    }
}

@Composable
private fun ViewCaseDialog(session: SessionDto, onDismiss: () -> Unit) {
    val stateColor = when (session.state) {
        "thinking" -> Color(0xFFD29922)
        "running-tools" -> Color(0xFF58A6FF)
        "complete" -> Color(0xFF3FB950)
        "error" -> Color(0xFFF85149)
        else -> Color(0xFF8B949E)
    }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Case Details") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Row(Modifier.fillMaxWidth()) { Text("State: ", color = Color(0xFF8B949E)); Text(session.state ?: "active", color = stateColor) }
                Row(Modifier.fillMaxWidth()) { Text("Slug: ", color = Color(0xFF8B949E)); Text(session.slug ?: "\u2014") }
                Row(Modifier.fillMaxWidth()) { Text("Model: ", color = Color(0xFF8B949E)); Text(session.modelId ?: "\u2014") }
                Row(Modifier.fillMaxWidth()) { Text("Cost: ", color = Color(0xFF8B949E)); Text(if (session.cost != null) "$${String.format("%.4f", session.cost)}" else "\u2014") }
                Row(Modifier.fillMaxWidth()) { Text("Tokens: ", color = Color(0xFF8B949E)); Text(session.tokens?.toString() ?: "\u2014") }
                if (!session.lastMode.isNullOrBlank()) Row(Modifier.fillMaxWidth()) { Text("Last Mode: ", color = Color(0xFF8B949E)); Text(session.lastMode) }
                Row(Modifier.fillMaxWidth()) { Text("Directory: ", color = Color(0xFF8B949E)); Text(session.directory ?: "\u2014", maxLines = 2, overflow = TextOverflow.Ellipsis) }
            }
        },
        confirmButton = { TextButton(onClick = onDismiss) { Text("Close") } }
    )
}

@Composable
private fun RenameCaseDialog(session: SessionDto, vm: MonitorViewModel, onDismiss: () -> Unit) {
    var newTitle by remember { mutableStateOf(session.title) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Rename Case") },
        text = {
            OutlinedTextField(
                value = newTitle,
                onValueChange = { newTitle = it },
                label = { Text("New Title") },
                modifier = Modifier.fillMaxWidth()
            )
        },
        confirmButton = {
            Button(onClick = {
                if (newTitle.isNotBlank()) {
                    vm.renameSession(session.id ?: "", newTitle)
                    onDismiss()
                }
            }) { Text("Save") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } }
    )
}

@Composable
private fun StopConfirmDialog(session: SessionDto, vm: MonitorViewModel, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Stop this case?") },
        text = { Text("Are you sure you want to stop \"${session.title}\"?") },
        confirmButton = {
            Button(
                onClick = {
                    vm.stopSession(session.id ?: "", session.directory)
                    onDismiss()
                },
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFF85149))
            ) { Text("Stop") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } }
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CaseFormScreen(session: SessionDto, state: UiState, vm: MonitorViewModel, onBack: () -> Unit) {
    var instruction by remember { mutableStateOf("") }
    var selectedMode by remember { mutableStateOf(session.staffMode ?: session.lastMode ?: "build") }
    var selectedModel by remember { mutableStateOf((session.staffModel ?: session.modelId).orEmpty()) }
    var modeMenuOpen by remember { mutableStateOf(false) }
    var modelMenuOpen by remember { mutableStateOf(false) }
    var fork by remember { mutableStateOf(false) }
    var isSending by remember { mutableStateOf(false) }
    var showResponseDialog by remember { mutableStateOf(false) }
    var showInstructionDialog by remember { mutableStateOf(false) }

    LaunchedEffect(state.notice) {
        if (isSending) isSending = false
    }

    val selectedStaff = findStaffByModeName(selectedMode, state.staff)

    LaunchedEffect(selectedMode, session, state.staff, state.availableModels) {
        if (selectedStaff != null) {
            selectedModel = selectedStaff.model.orEmpty()
        } else if (selectedModel.isBlank()) {
            selectedModel = defaultModelForSession(session, state.availableModels)
        }
    }

    Column(Modifier.fillMaxSize().padding(horizontal = 12.dp).verticalScroll(rememberScrollState())) {
        Text(session.displayLabel(), fontWeight = FontWeight.SemiBold)
        Spacer(Modifier.height(12.dp))
        ExposedDropdownMenuBox(
            expanded = modeMenuOpen,
            onExpandedChange = { modeMenuOpen = !modeMenuOpen }
        ) {
            OutlinedTextField(
                value = modeLabel(selectedMode),
                onValueChange = {},
                readOnly = true,
                label = { Text("Mode") },
                modifier = Modifier.fillMaxWidth().menuAnchor(),
                trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = modeMenuOpen) }
            )
            DropdownMenu(
                expanded = modeMenuOpen,
                onDismissRequest = { modeMenuOpen = false }
            ) {
                buildModeOptions(state.staff).forEach { mode ->
                    DropdownMenuItem(
                        text = { Text(modeLabel(mode)) },
                        onClick = {
                            selectedMode = mode
                            if (findStaffByModeName(mode, state.staff) == null && selectedModel.isBlank()) {
                                selectedModel = defaultModelForSession(session, state.availableModels)
                            }
                            modeMenuOpen = false
                        }
                    )
                }
            }
        }
        Spacer(Modifier.height(8.dp))
        ExposedDropdownMenuBox(
            expanded = modelMenuOpen,
            onExpandedChange = { if (selectedStaff == null) modelMenuOpen = !modelMenuOpen }
        ) {
            OutlinedTextField(
                value = selectedModel.ifBlank { "Default model" },
                onValueChange = {},
                readOnly = true,
                enabled = selectedStaff == null,
                label = { Text("Model") },
                modifier = Modifier.fillMaxWidth().menuAnchor(),
                trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = modelMenuOpen) }
            )
            DropdownMenu(
                expanded = modelMenuOpen && selectedStaff == null,
                onDismissRequest = { modelMenuOpen = false }
            ) {
                if (state.availableModels.isEmpty()) {
                    DropdownMenuItem(
                        text = { Text("Default model") },
                        onClick = {
                            selectedModel = ""
                            modelMenuOpen = false
                        }
                    )
                } else {
                    state.availableModels.forEach { model ->
                        DropdownMenuItem(
                            text = { Text(model.label()) },
                            onClick = {
                                selectedModel = model.id.orEmpty()
                                modelMenuOpen = false
                            }
                        )
                    }
                }
            }
        }
        if (session.lastText != null || session.lastUserPrompt != null) {
            Spacer(Modifier.height(8.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (!session.lastText.isNullOrBlank()) {
                    Button(
                        onClick = { showResponseDialog = true },
                        modifier = Modifier.weight(1f),
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF21262D)),
                        shape = RoundedCornerShape(6.dp)
                    ) { Text("Last response", color = Color(0xFF8B949E)) }
                }
                if (!session.lastUserPrompt.isNullOrBlank()) {
                    Button(
                        onClick = { showInstructionDialog = true },
                        modifier = Modifier.weight(1f),
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF21262D)),
                        shape = RoundedCornerShape(6.dp)
                    ) { Text("Last instruction", color = Color(0xFF8B949E)) }
                }
            }
        }
        Spacer(Modifier.height(8.dp))
        OutlinedTextField(value = instruction, onValueChange = { instruction = it }, label = { Text("Instruction") }, modifier = Modifier.fillMaxWidth())
        Spacer(Modifier.height(8.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Checkbox(checked = fork, onCheckedChange = { fork = it })
            Spacer(Modifier.width(4.dp))
            Text("Start new conversation", color = Color(0xFF8B949E), style = MaterialTheme.typography.bodySmall)
        }
        Spacer(Modifier.height(8.dp))
        Button(
            onClick = {
                if (instruction.isBlank()) {
                    vm.showNotice("Enter an instruction first")
                    return@Button
                }
                val finalInstruction = if (selectedStaff != null && !selectedStaff.description.isNullOrBlank()) {
                    "${selectedStaff.description}\n\nInstruction: $instruction"
                } else {
                    instruction
                }
                val requestMode = selectedStaff?.mode?.takeIf { it.isNotBlank() } ?: selectedMode
                val requestModel = if (selectedStaff != null) {
                    selectedStaff.model?.takeIf { it.isNotBlank() } ?: ""
                } else {
                    selectedModel
                }
                isSending = true
                vm.sendInstruction(session.id ?: "", finalInstruction, session.directory, requestMode, requestModel, fork = fork)
                instruction = ""
            },
            enabled = !isSending,
            modifier = Modifier.fillMaxWidth()
        ) { Text(if (isSending) "Sending\u2026" else "Send") }
        Spacer(Modifier.height(64.dp))
    }
    if (showResponseDialog && session.lastText != null) {
        AlertDialog(
            onDismissRequest = { showResponseDialog = false },
            title = { Text("Last response") },
            text = {
                Box(Modifier.heightIn(max = 400.dp).verticalScroll(rememberScrollState())) {
                    Text(session.lastText ?: "", color = Color(0xFF8B949E))
                }
            },
            confirmButton = { TextButton(onClick = { showResponseDialog = false }) { Text("Close") } }
        )
    }
    if (showInstructionDialog && session.lastUserPrompt != null) {
        AlertDialog(
            onDismissRequest = { showInstructionDialog = false },
            title = { Text("Last instruction") },
            text = {
                Box(Modifier.heightIn(max = 400.dp).verticalScroll(rememberScrollState())) {
                    Text(session.lastUserPrompt ?: "", color = Color(0xFF8B949E))
                }
            },
            confirmButton = { TextButton(onClick = { showInstructionDialog = false }) { Text("Close") } }
        )
    }
}

@Composable
private fun StatCard(label: String, value: String, modifier: Modifier = Modifier) {
    Card(modifier = modifier, colors = CardDefaults.cardColors(containerColor = Color(0xFF161B22))) {
        Column(Modifier.padding(10.dp)) {
            Text(label, style = MaterialTheme.typography.bodySmall, color = Color(0xFF8B949E))
            Text(value, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        }
    }
}

data class NotificationEvent(
    val type: String,
    val title: String,
    val body: String,
    val sessionId: String? = null
)

data class UiState(
    val loading: Boolean = false,
    val notice: String? = null,
    val baseUrl: String = "https://mydora.brandon.my/",
    val apiKey: String = "",
    val bossName: String = "Brandon",
    val sessions: List<SessionDto> = emptyList(),
    val allSessions: List<SessionDto> = emptyList(),
    val staff: List<StaffDto> = emptyList(),
    val availableModels: List<ModelOption> = emptyList(),
    val cronJobs: List<CronJobDto> = emptyList(),
    val summary: SummaryDto = SummaryDto(),
    val notificationEvent: NotificationEvent? = null
)

data class StatusPayload(
    val sessions: List<SessionDto>? = null,
    @SerializedName("all_sessions") val allSessions: List<SessionDto>? = null,
    val summary: SummaryDto? = null,
    @SerializedName("available_models") val availableModels: List<ModelOption>? = null,
    @SerializedName("boss_name") val bossName: String? = null
)
data class SummaryDto(val cpu_percent: Double? = null) { val cpuLabel: String get() = "${(cpu_percent ?: 0.0).toInt()}%" }
data class SessionDto(
    val id: String? = null,
    val title: String = "",
    val state: String? = null,
    val slug: String? = null,
    val cost: Double? = null,
    val tokens: Long? = null,
    val updated: Long? = null,
    @SerializedName("last_text") val lastText: String? = null,
    @SerializedName("last_mode") val lastMode: String? = null,
    @SerializedName("model_id") val modelId: String? = null,
    @SerializedName("assigned_staff") val assignedStaff: String? = null,
    @SerializedName("staff_mode") val staffMode: String? = null,
    @SerializedName("staff_model") val staffModel: String? = null,
    @SerializedName("last_user_prompt") val lastUserPrompt: String? = null,
    val directory: String? = null
)
data class StaffDto(
    val name: String = "",
    val description: String? = null,
    val gender: String? = null,
    val mode: String? = null,
    val model: String? = null
)
data class ModelOption(val id: String? = null, val provider: String? = null) { fun label(): String = if (provider.isNullOrBlank()) id.orEmpty() else "$provider · ${id.orEmpty()}" }
data class CronJobDto(
    val id: String? = null,
    val name: String? = null,
    val interval_sec: Int? = null,
    val enabled: Boolean? = null,
    @SerializedName("last_run") val lastRun: Long? = null,
    @SerializedName("last_status") val lastStatus: String? = null
) {
    val intervalSec: Int? get() = interval_sec
    fun nextRunDisplay(): String {
        if (enabled == false) return "\u2014"
        val last = lastRun ?: return "\u2014"
        val interval = interval_sec ?: return "\u2014"
        val next = last + interval
        return if (next <= System.currentTimeMillis() / 1000L) "Due now" else formatTimestamp(next)
    }
}

private fun formatTimestamp(epochSec: Long?): String {
    if (epochSec == null || epochSec == 0L) return "Never"
    val sdf = java.text.SimpleDateFormat("dd MMM hh:mm a", java.util.Locale.getDefault())
    return sdf.format(java.util.Date(epochSec * 1000))
}

private fun formatCountdown(lastRun: Long?, intervalSec: Int?): String {
    if (lastRun == null || intervalSec == null) return ""
    val next = lastRun + intervalSec
    val diff = next - System.currentTimeMillis() / 1000L
    if (diff <= 0) return "Due now"
    val h = diff / 3600
    val m = (diff % 3600) / 60
    val s = diff % 60
    return "${h}h ${m}m ${s}s"
}

interface DashboardApi {
    @GET suspend fun getStatusFile(@Url url: String): StatusPayload
    @GET suspend fun getJson(@Url url: String): JsonObject
    @GET suspend fun getStatusGet(@Url url: String): StatusPayload
    @POST suspend fun getStatus(@Url url: String, @Body body: JsonObject): StatusPayload
    @POST suspend fun postJson(@Url url: String, @Body body: JsonObject): JsonObject
}

class AppPreferences(private val store: androidx.datastore.core.DataStore<Preferences>) {
    private val baseUrlKey = stringPreferencesKey("base_url")
    private val apiKeyKey = stringPreferencesKey("api_key")
    val baseUrl: Flow<String> = store.data.map { it[baseUrlKey] ?: "https://mydora.brandon.my/" }
    val apiKey: Flow<String> = store.data.map { it[apiKeyKey] ?: "" }

    suspend fun save(baseUrl: String, apiKey: String) {
        store.edit {
            it[baseUrlKey] = normalizeBaseUrl(baseUrl)
            it[apiKeyKey] = apiKey
        }
    }
}

class MonitorViewModel(private val prefs: AppPreferences) : ViewModel() {
    private val _uiState = MutableStateFlow(UiState())
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()
    private var prevSessions: Map<String?, SessionDto> = emptyMap()

    init {
        viewModelScope.launch { prefs.baseUrl.collect { _uiState.value = _uiState.value.copy(baseUrl = it) } }
        viewModelScope.launch { prefs.apiKey.collect { _uiState.value = _uiState.value.copy(apiKey = it) } }
        refreshAll()
    }

    fun clearNotice() { _uiState.value = _uiState.value.copy(notice = null) }

    fun clearNotificationEvent() { _uiState.value = _uiState.value.copy(notificationEvent = null) }

    fun showNotice(message: String) {
        _uiState.value = _uiState.value.copy(notice = message)
    }

    fun refreshAll() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true)
            val api = createApi(_uiState.value.apiKey)
            val base = _uiState.value.baseUrl.trimEnd('/')
            val status = runCatching {
                api.getStatus("$base/api/status", JsonObject())
            }.recoverCatching {
                api.getStatusGet("$base/api/status")
            }.recoverCatching {
                api.getStatusFile("$base/data/status.json")
            }.recoverCatching {
                api.getStatusFile("$base/status.json")
            }.getOrElse {
                _uiState.value = _uiState.value.copy(loading = false, notice = it.message ?: "Refresh failed")
                return@launch
            }

            val staff = runCatching {
                api.getJson("$base/api/super-staff").toStaffList()
            }.getOrDefault(emptyList())
            val cron = runCatching {
                api.getJson("$base/api/cron-jobs").toCronList()
            }.getOrDefault(emptyList())
            val models = collectModels(status, staff)
            _uiState.value = _uiState.value.copy(
                loading = false,
                sessions = status.sessions ?: emptyList(),
                allSessions = status.allSessions ?: emptyList(),
                summary = status.summary ?: SummaryDto(),
                staff = staff,
                availableModels = models,
                cronJobs = cron,
                bossName = status.bossName?.takeIf { it.isNotBlank() } ?: _uiState.value.bossName
            )
            val newList = status.allSessions ?: status.sessions ?: emptyList()
            if (prevSessions.isNotEmpty()) {
                detectSessionChanges(prevSessions, newList).firstOrNull()?.let { ch ->
                    _uiState.value = _uiState.value.copy(
                        notificationEvent = NotificationEvent(
                            type = ch.type, title = ch.title.ifBlank { "Case" },
                            body = when (ch.type) {
                                "state_change" -> "${ch.title}: ${ch.oldState} → ${ch.newState}"
                                "new" -> "New case: ${ch.title}"
                                "complete" -> "Case completed: ${ch.title}"
                                else -> "${ch.title} updated"
                            },
                            sessionId = ch.id
                        )
                    )
                }
            }
            prevSessions = newList.associateBy { it.id }
        }
    }

    fun saveSettings(baseUrl: String, apiKey: String) {
        viewModelScope.launch {
            prefs.save(baseUrl, apiKey)
            _uiState.value = _uiState.value.copy(notice = "Settings saved")
            refreshAll()
        }
    }

    fun sendInstruction(sessionId: String, message: String, directory: String? = null, mode: String? = null, model: String? = null, fork: Boolean = false) {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                val api = createApi(_uiState.value.apiKey)
                val payload = JsonObject().apply {
                    addProperty("id", sessionId)
                    addProperty("message", message)
                    if (!directory.isNullOrBlank()) addProperty("directory", directory)
                    if (!mode.isNullOrBlank()) addProperty("mode", mode)
                    if (!model.isNullOrBlank()) addProperty("model", model)
                    addProperty("fork", fork)
                }
                val resp = sendQueued(api, base, "session-instruct", payload)
                val ok = resp.get("ok")?.asBoolean ?: false
                val msg = resp.get("message")?.asString ?: "Instruction sent"
                _uiState.value = _uiState.value.copy(notice = if (ok) msg else "Error: $msg")
            }.onFailure {
                _uiState.value = _uiState.value.copy(notice = it.message ?: "Request failed")
            }
            refreshAll()
        }
    }

    fun renameSession(id: String, title: String) {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                val api = createApi(_uiState.value.apiKey)
                sendQueued(api, base, "rename-session", JsonObject().apply {
                    addProperty("id", id)
                    addProperty("title", title)
                })
                _uiState.value = _uiState.value.copy(notice = "Case renamed")
            }.onFailure {
                _uiState.value = _uiState.value.copy(notice = it.message ?: "Request failed")
            }
            refreshAll()
        }
    }

    fun stopSession(id: String, directory: String?) {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                val api = createApi(_uiState.value.apiKey)
                sendQueued(api, base, "stop-session", JsonObject().apply {
                    addProperty("id", id)
                    if (!directory.isNullOrBlank()) addProperty("directory", directory)
                })
                _uiState.value = _uiState.value.copy(notice = "Session stopped")
            }.onFailure {
                _uiState.value = _uiState.value.copy(notice = it.message ?: "Request failed")
            }
            refreshAll()
        }
    }

    fun toggleCron(id: String) {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                val api = createApi(_uiState.value.apiKey)
                sendQueued(api, base, "cron-jobs/toggle", JsonObject().apply { addProperty("id", id) })
                _uiState.value = _uiState.value.copy(notice = "Cron toggled")
            }.onFailure {
                _uiState.value = _uiState.value.copy(notice = it.message ?: "Request failed")
            }
            refreshAll()
        }
    }

    fun runCron(id: String) {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                val api = createApi(_uiState.value.apiKey)
                sendQueued(api, base, "cron-jobs/run", JsonObject().apply { addProperty("id", id) })
                _uiState.value = _uiState.value.copy(notice = "Cron run triggered")
            }.onFailure {
                _uiState.value = _uiState.value.copy(notice = it.message ?: "Request failed")
            }
            refreshAll()
        }
    }

    fun restartDaemon() {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                val api = createApi(_uiState.value.apiKey)
                sendQueued(api, base, "restart-daemon", JsonObject())
                _uiState.value = _uiState.value.copy(notice = "Daemon restarted")
            }.onFailure {
                _uiState.value = _uiState.value.copy(notice = it.message ?: "Request failed")
            }
        }
    }

    fun killDaemon() {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                val api = createApi(_uiState.value.apiKey)
                sendQueued(api, base, "kill-daemon", JsonObject())
                _uiState.value = _uiState.value.copy(notice = "Daemon killed")
            }.onFailure {
                _uiState.value = _uiState.value.copy(notice = it.message ?: "Request failed")
            }
        }
    }

    fun saveBossName(name: String) {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                val api = createApi(_uiState.value.apiKey)
                sendQueued(api, base, "save-boss-name", JsonObject().apply { addProperty("name", name) })
                _uiState.value = _uiState.value.copy(notice = "Boss name saved", bossName = name)
            }.onFailure {
                _uiState.value = _uiState.value.copy(notice = it.message ?: "Request failed")
            }
            refreshAll()
        }
    }
}

private suspend fun postJsonFlexible(api: DashboardApi, url: String): JsonObject {
    return try {
        api.postJson(url, JsonObject())
    } catch (e: HttpException) {
        if (e.code() == 405) api.getJson(url) else throw e
    }
}

private suspend fun sendQueued(api: DashboardApi, baseUrl: String, type: String, payload: JsonObject): JsonObject {
    val queueResp = api.postJson("$baseUrl/api/queue", JsonObject().apply {
        addProperty("type", type)
        add("payload", payload)
    })
    val queueId = queueResp.get("queueId")?.asString ?: throw Exception("Queue rejected: ${queueResp.get("message")?.asString ?: "unknown"}")
    while (true) {
        kotlinx.coroutines.delay(2000)
        val pollResp = api.getJson("$baseUrl/api/queue/$queueId")
        when (pollResp.get("status")?.asString) {
            "done" -> return pollResp.get("result")?.asJsonObject ?: JsonObject()
            "failed" -> throw Exception(pollResp.get("error")?.asString ?: "Queue failed")
        }
    }
}

private fun collectModels(status: StatusPayload, staff: List<StaffDto>): List<ModelOption> {
    val models = linkedMapOf<String, ModelOption>()
    status.availableModels.orEmpty().forEach { model ->
        model.id?.let { models[it] = model }
    }
    status.sessions.orEmpty().forEach { session ->
        session.modelId?.let { models.putIfAbsent(it, ModelOption(id = it)) }
        session.staffModel?.let { models.putIfAbsent(it, ModelOption(id = it)) }
    }
    staff.forEach { item ->
        item.model?.let { models.putIfAbsent(it, ModelOption(id = it)) }
    }
    return models.values.toList()
}

private fun sessionDropdownList(state: UiState): List<SessionDto> {
    val primary = if (state.allSessions.isNotEmpty()) state.allSessions else state.sessions
    return primary.distinctBy { it.id ?: it.title }
}

private fun SessionDto.displayLabel(): String {
    return title.ifBlank { id.orEmpty() }
}

private fun SessionDto.matchesSessionFilter(query: String): Boolean {
    if (query.isBlank()) return true
    val needle = query.trim().lowercase()
    return title.lowercase().contains(needle) || (id ?: "").lowercase().contains(needle)
}

private fun modeLabel(mode: String): String {
    return when (mode) {
        "build" -> "Build"
        "plan" -> "Plan"
        else -> mode
    }
}

private fun buildModeOptions(staff: List<StaffDto>): List<String> {
    return buildList {
        add("build")
        add("plan")
        staff.mapNotNull { it.name.takeIf { name -> name.isNotBlank() } }
            .distinct()
            .forEach { add(it) }
    }
}

private fun findStaffByModeName(modeName: String, staff: List<StaffDto>): StaffDto? {
    if (modeName == "build" || modeName == "plan" || modeName.isBlank()) return null
    return staff.firstOrNull { it.name.equals(modeName, ignoreCase = true) }
}

private fun defaultModelForSession(session: SessionDto?, models: List<ModelOption>): String {
    val sessionModel = session?.modelId?.takeIf { it.isNotBlank() }
    if (sessionModel != null) {
        val exact = models.firstOrNull { it.id == sessionModel }
        if (exact != null) return exact.id.orEmpty()
        val prefixed = models.firstOrNull { it.id?.endsWith("/$sessionModel") == true }
        if (prefixed != null) return prefixed.id.orEmpty()
        return sessionModel
    }
    val staffModel = session?.staffModel?.takeIf { it.isNotBlank() }
    return models.firstOrNull()?.id.orEmpty()
}

private fun resolveRequestMode(selectedMode: String, session: SessionDto?): String? {
    return when (selectedMode) {
        "build", "plan" -> selectedMode.takeIf { it.isNotBlank() }
        else -> selectedMode.takeIf { it.isNotBlank() }
    }
}

private fun resolveRequestModel(selectedMode: String, session: SessionDto?, selectedModel: String, staff: List<StaffDto>): String? {
    return when (selectedMode) {
        "build", "plan" -> selectedModel.takeIf { it.isNotBlank() }
        else -> findStaffByModeName(selectedMode, staff)?.model?.takeIf { it.isNotBlank() }
    }
}

private data class SessionChange(
    val type: String, val id: String?, val title: String,
    val oldState: String? = null, val newState: String? = null
)

private fun detectSessionChanges(prev: Map<String?, SessionDto>, current: List<SessionDto>): List<SessionChange> {
    val changes = mutableListOf<SessionChange>()
    current.forEach { cs ->
        val p = prev[cs.id]
        if (p != null && p.state != cs.state) {
            changes.add(SessionChange("state_change", cs.id, cs.title, p.state, cs.state))
        } else if (p == null && cs.state == "complete") {
            changes.add(SessionChange("complete", cs.id, cs.title, newState = cs.state))
        } else if (p == null) {
            changes.add(SessionChange("new", cs.id, cs.title, newState = cs.state))
        }
    }
    return changes
}

class MonitorViewModelFactory(private val prefs: AppPreferences) : ViewModelProvider.Factory {
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        @Suppress("UNCHECKED_CAST")
        return MonitorViewModel(prefs) as T
    }
}

private fun createApi(apiKey: String): DashboardApi {
    val logging = HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BASIC }
    val client = OkHttpClient.Builder()
        .addInterceptor { chain ->
            val req = chain.request().newBuilder().apply {
                if (apiKey.isNotBlank()) addHeader("X-API-Key", apiKey)
            }.build()
            chain.proceed(req)
        }
        .addInterceptor(logging)
        .build()

    return Retrofit.Builder()
        .baseUrl("https://mydora.brandon.my/")
        .client(client)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(DashboardApi::class.java)
}

private fun createNotificationChannel(context: Context) {
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
        val channel = NotificationChannel("case_updates", "Case Updates", NotificationManager.IMPORTANCE_DEFAULT).apply {
            description = "Notifications for case status changes"
        }
        context.getSystemService(Context.NOTIFICATION_SERVICE)?.let { svc ->
            (svc as? NotificationManager)?.createNotificationChannel(channel)
        }
    }
}

private fun postAndroidNotification(context: Context, event: NotificationEvent) {
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) return
    }
    val id = event.sessionId?.hashCode() ?: System.currentTimeMillis().toInt()
    val notification = NotificationCompat.Builder(context, "case_updates")
        .setSmallIcon(android.R.drawable.ic_dialog_info)
        .setContentTitle(event.title)
        .setContentText(event.body)
        .setPriority(NotificationCompat.PRIORITY_DEFAULT)
        .setAutoCancel(true)
        .build()
    NotificationManagerCompat.from(context).notify(id, notification)
}

private fun normalizeBaseUrl(input: String): String {
    val trimmed = input.trim()
    if (trimmed.isBlank()) return "https://mydora.brandon.my/"
    val withScheme = if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) trimmed else "https://$trimmed"
    return runCatching {
        val uri = URI(withScheme)
        val scheme = uri.scheme ?: "https"
        val host = uri.host ?: uri.authority ?: "mydora.brandon.my"
        "$scheme://$host/"
    }.getOrElse {
        if (withScheme.endsWith('/')) withScheme else "$withScheme/"
    }
}

private fun JsonObject.toStaffList(): List<StaffDto> {
    val arr = getAsJsonArray("staff") ?: getAsJsonArray("data") ?: return emptyList()
    return arr.mapNotNull {
        runCatching {
            val o = it.asJsonObject
            StaffDto(
                name = o.get("name")?.asString ?: "",
                description = o.get("description")?.asString,
                gender = o.get("gender")?.asString,
                mode = o.get("mode")?.asString,
                model = o.get("model")?.asString
            )
        }.getOrNull()
    }
}

private fun JsonObject.toCronList(): List<CronJobDto> {
    val arr = getAsJsonArray("jobs") ?: getAsJsonArray("data") ?: return emptyList()
    return arr.mapNotNull {
        runCatching {
            val o = it.asJsonObject
            CronJobDto(
                id = o.get("id")?.asString ?: o.get("id")?.asInt?.toString(),
                name = o.get("name")?.asString,
                interval_sec = o.get("interval_sec")?.asInt,
                enabled = o.get("enabled")?.asBoolean,
                lastRun = o.get("last_run")?.asLong,
                lastStatus = o.get("last_status")?.asString
            )
        }.getOrNull()
    }
}

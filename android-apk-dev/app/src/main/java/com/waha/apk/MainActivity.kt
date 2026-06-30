package com.waha.apk

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.ClipData
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
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
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
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.DropdownMenu
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AccountTree
import androidx.compose.material.icons.filled.Article
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.QuestionAnswer
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.TaskAlt
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
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.Divider
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.ModalDrawerSheet
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.NavigationDrawerItem
import androidx.compose.material3.rememberDrawerState
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.OpenWith
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
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
import com.google.gson.Gson
import com.google.gson.JsonElement
import com.google.gson.annotations.SerializedName
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.delay
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
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.PaddingValues
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
import androidx.compose.ui.viewinterop.AndroidView
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
    Tasks("Tasks"),
    Cron("Cron"),
    Workflows("Workflows"),
    Notifications("Notifications"),
    Logs("Logs"),
    Settings("Settings")
}

@Composable
private fun MonitorApp(vm: MonitorViewModel) {
    val state by vm.uiState.collectAsState()
    var tab by remember { mutableStateOf(TabItem.Dashboard) }
    var caseFormTarget by remember { mutableStateOf<SessionDto?>(null) }
    var showNewCaseDialog by remember { mutableStateOf(false) }
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

    LaunchedEffect(Unit) {
        while (true) {
            delay(5000)
            vm.pollNotifications()
        }
    }

    val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)
    val scope = rememberCoroutineScope()

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet {
                Text("Menu", fontWeight = FontWeight.SemiBold, modifier = Modifier.padding(16.dp))
                Divider()
                NavigationDrawerItem(icon = { Icon(Icons.Filled.AccountTree, null) }, label = { Text("Workflows") }, selected = tab == TabItem.Workflows, onClick = { tab = TabItem.Workflows; scope.launch { drawerState.close() } })
                NavigationDrawerItem(icon = { Icon(Icons.Filled.Build, null) }, label = { Text("Cron") }, selected = tab == TabItem.Cron, onClick = { tab = TabItem.Cron; scope.launch { drawerState.close() } })
                NavigationDrawerItem(icon = { Icon(Icons.Filled.Notifications, null) }, label = { Text("Notifications") }, selected = tab == TabItem.Notifications, onClick = { tab = TabItem.Notifications; scope.launch { drawerState.close() } })
                NavigationDrawerItem(icon = { Icon(Icons.Filled.Article, null) }, label = { Text("Logs") }, selected = tab == TabItem.Logs, onClick = { tab = TabItem.Logs; scope.launch { drawerState.close() } })
                NavigationDrawerItem(icon = { Icon(Icons.Filled.Settings, null) }, label = { Text("Settings") }, selected = tab == TabItem.Settings, onClick = { tab = TabItem.Settings; scope.launch { drawerState.close() } })
            }
        }
    ) {
        Scaffold(
        snackbarHost = { SnackbarHost(snack) },
        bottomBar = {
            NavigationBar {
                NavigationBarItem(tab == TabItem.Dashboard, { tab = TabItem.Dashboard }, { Icon(Icons.Filled.Dashboard, null) }, label = { Text("Dashboard") })
                NavigationBarItem(tab == TabItem.Cases, { tab = TabItem.Cases }, { Icon(Icons.AutoMirrored.Filled.List, null) }, label = { Text("Cases") })
                NavigationBarItem(tab == TabItem.Staff, { tab = TabItem.Staff }, { Icon(Icons.Filled.SupportAgent, null) }, label = { Text("Staff") })
                NavigationBarItem(tab == TabItem.Tasks, { tab = TabItem.Tasks }, { Icon(Icons.Filled.TaskAlt, null) }, label = { Text("Tasks") })
            }
        },
        floatingActionButton = {
            if (tab == TabItem.Cases && caseFormTarget == null) {
                FloatingActionButton(
                    onClick = { showNewCaseDialog = true },
                    containerColor = Color(0xFF58A6FF)
                ) {
                    Icon(Icons.Filled.Add, contentDescription = "New Case")
                }
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
                Spacer(Modifier.weight(1f))
                IconButton(onClick = { scope.launch { drawerState.open() } }) {
                    Icon(Icons.Filled.Menu, contentDescription = "Menu")
                }
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

            state.remoteNotifications.firstOrNull()?.let { ntf ->
                var visible by remember(ntf.id) { mutableStateOf(true) }
                LaunchedEffect(ntf.id) {
                    delay(5000)
                    visible = false
                    vm.dismissNotification(ntf.id)
                }
                AnimatedVisibility(
                    visible = visible,
                    enter = slideInVertically { -it },
                    exit = slideOutVertically { -it }
                ) {
                    val bg = when (ntf.type) {
                        "error" -> Color(0xFFF85149)
                        "warning" -> Color(0xFFD29922)
                        "success" -> Color(0xFF3FB950)
                        else -> Color(0xFF58A6FF)
                    }
                    Row(
                        modifier = Modifier.fillMaxWidth().background(bg).padding(horizontal = 12.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(ntf.message, color = Color.White, modifier = Modifier.weight(1f), fontSize = MaterialTheme.typography.bodySmall.fontSize)
                        IconButton(onClick = { visible = false; vm.dismissNotification(ntf.id) }, modifier = Modifier.size(24.dp)) {
                            Icon(Icons.Filled.Clear, contentDescription = "Dismiss", tint = Color.White, modifier = Modifier.size(16.dp))
                        }
                    }
                }
            }

            when (tab) {
                TabItem.Dashboard -> DashboardScreen(state, vm, vm::refreshAll, caseFormTarget) { caseFormTarget = it }
                TabItem.Cases -> CasesScreen(state, vm, vm::refreshAll, caseFormTarget) { caseFormTarget = it }
                TabItem.Staff -> StaffScreen(state, vm, vm::refreshAll)
                TabItem.Tasks -> TasksScreen(state, vm, vm::refreshAll)
                TabItem.Cron -> CronScreen(state, vm, vm::refreshAll)
                TabItem.Workflows -> WorkflowsScreen(state, vm, vm::refreshAll)
                TabItem.Notifications -> NotificationsScreen(state, vm, vm::refreshAll)
                TabItem.Logs -> LogsScreen(state, vm, vm::refreshAll)
                TabItem.Settings -> SettingsScreen(state, vm, vm::refreshAll)
            }
        }

        if (state.loading) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
        }  // closes if
        }  // closes Scaffold
    }  // closes ModalNavigationDrawer
}  // closes MonitorApp

    if (showNewCaseDialog) {
        NewCaseFormDialog(state, vm) { showNewCaseDialog = false }
    }
}

@Composable
private fun DashboardScreen(state: UiState, vm: MonitorViewModel, onRefresh: () -> Unit, formTarget: SessionDto? = null, onFormTargetChange: (SessionDto?) -> Unit = {}) {
    var viewTarget by remember { mutableStateOf<SessionDto?>(null) }
    var renameTarget by remember { mutableStateOf<SessionDto?>(null) }
    var stopTarget by remember { mutableStateOf<SessionDto?>(null) }
    var questionsTarget by remember { mutableStateOf<SessionDto?>(null) }

    PullToRefreshContainer(isRefreshing = state.loading, onRefresh = onRefresh) {
        if (formTarget != null) {
            CaseFormScreen(formTarget, state, vm) { onFormTargetChange(null) }
        } else {
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
                items(state.sessions.take(10)) { session ->
                    SwipeableCaseItem(session, isActive = session.state == "thinking" || session.state == "running-tools",
                        onSelect = { onFormTargetChange(session) },
                        onView = { viewTarget = session },
                        onQuestions = { questionsTarget = session },
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
    questionsTarget?.let { QuestionsDialog(it) { questionsTarget = null } }
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
                } else {
                    Image(
                        painter = painterResource(R.drawable.discuss_empty),
                        contentDescription = "Discussion idle",
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
    var questionsTarget by remember { mutableStateOf<SessionDto?>(null) }

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
                        onQuestions = { questionsTarget = session },
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
    questionsTarget?.let { QuestionsDialog(it) { questionsTarget = null } }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun StaffScreen(state: UiState, vm: MonitorViewModel, onRefresh: () -> Unit) {
    var formTarget by remember { mutableStateOf<StaffDto?>(null) }
    var viewTarget by remember { mutableStateOf<StaffDto?>(null) }
    var deleteTarget by remember { mutableStateOf<StaffDto?>(null) }

    PullToRefreshContainer(isRefreshing = state.loading, onRefresh = onRefresh) {
        LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = 12.dp)) {
            item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Text("Staff", fontWeight = FontWeight.SemiBold)
                    Button(onClick = { formTarget = StaffDto() }) { Text("+ New") }
                }
                Spacer(Modifier.height(8.dp))
            }
            items(state.staff) { s ->
                SwipeableStaffItem(
                    staff = s,
                    onView = { viewTarget = s },
                    onEdit = { formTarget = s },
                    onDelete = { deleteTarget = s }
                ) {
                    Card(modifier = Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = Color(0xFF161B22))) {
                        Column(Modifier.padding(12.dp)) {
                            Text(s.name, fontWeight = FontWeight.SemiBold)
                            Text("${s.gender ?: "-"} • ${s.mode ?: "default"} • ${s.model?.takeIf { it.isNotBlank() } ?: "default model"}", color = Color(0xFF8B949E))
                            if (!s.description.isNullOrBlank()) {
                                Text(s.description ?: "", maxLines = 2, overflow = TextOverflow.Ellipsis)
                            }
                        }
                    }
                }
            }
            item { Spacer(Modifier.height(64.dp)) }
        }
    }
    formTarget?.let { StaffFormDialog(it, state, vm) { formTarget = null } }
    viewTarget?.let { AssignCasesDialog(it, state, vm) { viewTarget = null } }
    deleteTarget?.let { s ->
        AlertDialog(
            onDismissRequest = { deleteTarget = null },
            title = { Text("Delete staff?") },
            text = { Text("Are you sure you want to delete \"${s.name}\"?") },
            confirmButton = { Button(colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFF85149)), onClick = { vm.deleteStaff(s.name); deleteTarget = null }) { Text("Delete") } },
            dismissButton = { TextButton(onClick = { deleteTarget = null }) { Text("Cancel") } }
        )
    }
}

@Composable
private fun SwipeableStaffItem(staff: StaffDto, onView: () -> Unit, onEdit: () -> Unit, onDelete: () -> Unit, content: @Composable () -> Unit) {
    val scope = rememberCoroutineScope()
    val density = LocalDensity.current
    val revealWidthPx = with(density) { 300.dp.toPx() }
    val offsetX = remember { Animatable(0f) }

    Box(modifier = Modifier.fillMaxWidth().clipToBounds().padding(vertical = 6.dp)) {
        Row(modifier = Modifier.align(Alignment.CenterEnd).height(IntrinsicSize.Min).background(Color(0xFF0D1117), RoundedCornerShape(topStart = 10.dp, bottomStart = 10.dp)), horizontalArrangement = Arrangement.End) {
            val btnMod = Modifier.width(100.dp).fillMaxHeight().padding(vertical = 14.dp)
            SwipeActionButton("View", Icons.Filled.Visibility, Color(0xFF58A6FF), btnMod) {
                scope.launch { offsetX.animateTo(0f, tween(150)) }; onView()
            }
            SwipeActionButton("Edit", Icons.Filled.Edit, Color(0xFFD29922), btnMod) {
                scope.launch { offsetX.animateTo(0f, tween(150)) }; onEdit()
            }
            SwipeActionButton("Delete", Icons.Filled.Delete, Color(0xFFF85149), btnMod) {
                scope.launch { offsetX.animateTo(0f, tween(150)) }; onDelete()
            }
        }
        Box(modifier = Modifier
            .offset { IntOffset(offsetX.value.roundToInt(), 0) }
            .pointerInput(Unit) {
                detectHorizontalDragGestures(
                    onDragEnd = { scope.launch { offsetX.animateTo(if (offsetX.value < -revealWidthPx * 0.4f) -revealWidthPx else 0f, tween(200)) } },
                    onHorizontalDrag = { _, dragAmount -> scope.launch { offsetX.snapTo((offsetX.value + dragAmount).coerceIn(-revealWidthPx, 0f)) } }
                )
            }
            .pointerInput(Unit) {
                detectTapGestures(onTap = { if (offsetX.value < 0f) scope.launch { offsetX.animateTo(0f, tween(150)) } })
            }
        ) { content() }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun StaffFormDialog(staff: StaffDto, state: UiState, vm: MonitorViewModel, onDismiss: () -> Unit) {
    val isNew = staff.name.isBlank()
    var name by remember { mutableStateOf(staff.name) }
    var description by remember { mutableStateOf(staff.description ?: "") }
    var gender by remember { mutableStateOf(staff.gender ?: "male") }
    var mode by remember { mutableStateOf(staff.mode ?: "build") }
    var model by remember { mutableStateOf(staff.model ?: "") }
    var genderMenuOpen by remember { mutableStateOf(false) }
    var modeMenuOpen by remember { mutableStateOf(false) }
    var modelMenuOpen by remember { mutableStateOf(false) }

    Dialog(onDismissRequest = onDismiss) {
        Card(modifier = Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = Color(0xFF161B22))) {
            Column(Modifier.padding(16.dp).verticalScroll(rememberScrollState())) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Text(if (isNew) "New Staff" else "Edit Staff", fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                    IconButton(onClick = onDismiss) { Icon(Icons.Filled.Clear, contentDescription = "Close", tint = Color(0xFFF85149)) }
                }
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("Name") }, modifier = Modifier.fillMaxWidth())
                Spacer(Modifier.height(8.dp))
                ExposedDropdownMenuBox(expanded = genderMenuOpen, onExpandedChange = { genderMenuOpen = !genderMenuOpen }) {
                    OutlinedTextField(value = gender.replaceFirstChar { it.uppercase() }, onValueChange = {}, readOnly = true, label = { Text("Gender") }, modifier = Modifier.fillMaxWidth().menuAnchor(), trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = genderMenuOpen) })
                    DropdownMenu(expanded = genderMenuOpen, onDismissRequest = { genderMenuOpen = false }) {
                        DropdownMenuItem(text = { Text("Male") }, onClick = { gender = "male"; genderMenuOpen = false })
                        DropdownMenuItem(text = { Text("Female") }, onClick = { gender = "female"; genderMenuOpen = false })
                    }
                }
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(value = description, onValueChange = { description = it }, label = { Text("Roles & Scope") }, modifier = Modifier.fillMaxWidth(), minLines = 3)
                Spacer(Modifier.height(8.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    ExposedDropdownMenuBox(expanded = modeMenuOpen, onExpandedChange = { modeMenuOpen = !modeMenuOpen }, modifier = Modifier.weight(1f)) {
                        OutlinedTextField(value = modeLabel(mode), onValueChange = {}, readOnly = true, label = { Text("Mode") }, modifier = Modifier.fillMaxWidth().menuAnchor(), trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = modeMenuOpen) })
                        DropdownMenu(expanded = modeMenuOpen, onDismissRequest = { modeMenuOpen = false }) {
                            DropdownMenuItem(text = { Text("Build") }, onClick = { mode = "build"; modeMenuOpen = false })
                            DropdownMenuItem(text = { Text("Plan") }, onClick = { mode = "plan"; modeMenuOpen = false })
                        }
                    }
                    ExposedDropdownMenuBox(expanded = modelMenuOpen, onExpandedChange = { modelMenuOpen = !modelMenuOpen }, modifier = Modifier.weight(1f)) {
                        OutlinedTextField(value = model.ifBlank { "Default model" }, onValueChange = {}, readOnly = true, label = { Text("Model") }, modifier = Modifier.fillMaxWidth().menuAnchor(), trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = modelMenuOpen) })
                        DropdownMenu(expanded = modelMenuOpen, onDismissRequest = { modelMenuOpen = false }) {
                            if (state.availableModels.isEmpty()) {
                                DropdownMenuItem(text = { Text("Default model") }, onClick = { model = ""; modelMenuOpen = false })
                            } else {
                                state.availableModels.forEach { m ->
                                    DropdownMenuItem(text = { Text(m.label()) }, onClick = { model = m.id.orEmpty(); modelMenuOpen = false })
                                }
                            }
                        }
                    }
                }
                Spacer(Modifier.height(12.dp))
                Button(onClick = {
                    if (name.isBlank()) { vm.showNotice("Name is required"); return@Button }
                    val path = staff.path ?: "~"
                    if (isNew) vm.createStaff(name, description, gender, mode, model, path)
                    else vm.updateStaff(staff.name, name, description, gender, mode, model, path)
                    onDismiss()
                }, modifier = Modifier.fillMaxWidth()) { Text(if (isNew) "Create" else "Save") }
            }
        }
    }
}

@Composable
private fun AssignCasesDialog(staff: StaffDto, state: UiState, vm: MonitorViewModel, onDismiss: () -> Unit) {
    val allSessions = state.allSessions.takeIf { it.isNotEmpty() } ?: state.sessions
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("${staff.name} — Assigned Cases") },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState())) {
                if (allSessions.isEmpty()) {
                    Text("No cases available", color = Color(0xFF8B949E))
                } else {
                    allSessions.forEach { session ->
                        val isAssigned = session.assignedStaff == staff.name
                        val otherStaff = session.assignedStaff?.takeIf { it != staff.name }
                        Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                            Checkbox(
                                checked = isAssigned,
                                onCheckedChange = { checked ->
                                    if (checked) vm.assignStaff(session.id ?: "", staff.name)
                                    else vm.assignStaff(session.id ?: "", "")
                                }
                            )
                            Spacer(Modifier.width(4.dp))
                            Column(Modifier.weight(1f)) {
                                Text(session.title.ifBlank { "Untitled" }, fontSize = MaterialTheme.typography.bodySmall.fontSize)
                                if (otherStaff != null) Text("Assigned: $otherStaff", color = Color(0xFFD29922), fontSize = MaterialTheme.typography.labelSmall.fontSize)
                            }
                        }
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = onDismiss) { Text("Close") } }
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun NewCaseFormDialog(state: UiState, vm: MonitorViewModel, onDismiss: () -> Unit) {
    var title by remember { mutableStateOf("") }
    var message by remember { mutableStateOf("") }
    var selectedMode by remember { mutableStateOf("build") }
    var selectedModel by remember { mutableStateOf("") }
    var workspace by remember { mutableStateOf("") }
    var modeMenuOpen by remember { mutableStateOf(false) }
    var modelMenuOpen by remember { mutableStateOf(false) }
    var workspaceMenuOpen by remember { mutableStateOf(false) }

    val selectedStaff = findStaffByModeName(selectedMode, state.staff)

    val workspaceOptions = remember(state.allSessions, state.sessions) {
        val sessions = state.allSessions.takeIf { it.isNotEmpty() } ?: state.sessions
        listOf("") + sessions.mapNotNull { it.directory?.takeIf { d -> d.isNotBlank() } }.distinct().sorted()
    }

    Dialog(onDismissRequest = onDismiss) {
        Card(modifier = Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = Color(0xFF161B22))) {
            Column(Modifier.padding(16.dp).verticalScroll(rememberScrollState())) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Text("New Case", fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                    IconButton(onClick = onDismiss) { Icon(Icons.Filled.Clear, contentDescription = "Close", tint = Color(0xFFF85149)) }
                }
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(value = title, onValueChange = { title = it }, label = { Text("Title") }, modifier = Modifier.fillMaxWidth())
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(value = message, onValueChange = { message = it }, label = { Text("Message") }, modifier = Modifier.fillMaxWidth(), minLines = 3)
                Spacer(Modifier.height(8.dp))
                ExposedDropdownMenuBox(expanded = modeMenuOpen, onExpandedChange = { modeMenuOpen = !modeMenuOpen }) {
                    OutlinedTextField(value = modeLabel(selectedMode), onValueChange = {}, readOnly = true, label = { Text("Mode") }, modifier = Modifier.fillMaxWidth().menuAnchor(), trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = modeMenuOpen) })
                    DropdownMenu(expanded = modeMenuOpen, onDismissRequest = { modeMenuOpen = false }) {
                        buildModeOptions(state.staff).forEach { mode ->
                            DropdownMenuItem(text = { Text(modeLabel(mode)) }, onClick = {
                                selectedMode = mode
                                val staffModel = findStaffByModeName(mode, state.staff)?.model?.takeIf { it.isNotBlank() }
                                selectedModel = staffModel ?: ""
                                modeMenuOpen = false
                            })
                        }
                    }
                }
                Spacer(Modifier.height(8.dp))
                ExposedDropdownMenuBox(expanded = modelMenuOpen && selectedStaff == null, onExpandedChange = { if (selectedStaff == null) modelMenuOpen = !modelMenuOpen }) {
                    OutlinedTextField(value = selectedModel.ifBlank { "Default model" }, onValueChange = {}, readOnly = true, enabled = selectedStaff == null, label = { Text("Model") }, modifier = Modifier.fillMaxWidth().menuAnchor(), trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = modelMenuOpen) })
                    DropdownMenu(expanded = modelMenuOpen && selectedStaff == null, onDismissRequest = { modelMenuOpen = false }) {
                        if (state.availableModels.isEmpty()) {
                            DropdownMenuItem(text = { Text("Default model") }, onClick = { selectedModel = ""; modelMenuOpen = false })
                        } else {
                            state.availableModels.forEach { m ->
                                DropdownMenuItem(text = { Text(m.label()) }, onClick = { selectedModel = m.id.orEmpty(); modelMenuOpen = false })
                            }
                        }
                    }
                }
                Spacer(Modifier.height(8.dp))
                ExposedDropdownMenuBox(expanded = workspaceMenuOpen, onExpandedChange = { workspaceMenuOpen = !workspaceMenuOpen }) {
                    OutlinedTextField(value = if (workspace.isBlank()) "Default (home)" else workspace.split("/").lastOrNull() ?: workspace, onValueChange = {}, readOnly = true, label = { Text("Workspace") }, modifier = Modifier.fillMaxWidth().menuAnchor(), trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = workspaceMenuOpen) })
                    DropdownMenu(expanded = workspaceMenuOpen, onDismissRequest = { workspaceMenuOpen = false }) {
                        workspaceOptions.forEach { dir ->
                            DropdownMenuItem(text = { Text(if (dir.isBlank()) "Default (home)" else dir, maxLines = 1, overflow = TextOverflow.Ellipsis) }, onClick = { workspace = dir; workspaceMenuOpen = false })
                        }
                    }
                }
                Spacer(Modifier.height(12.dp))
                Button(onClick = {
                    if (title.isBlank()) { vm.showNotice("Title is required"); return@Button }
                    if (message.isBlank()) { vm.showNotice("Message is required"); return@Button }
                    val staff = selectedStaff
                    val finalMessage = if (staff != null && !staff.description.isNullOrBlank()) "${staff.description}\n\n$message" else message
                    val finalMode = staff?.mode?.takeIf { it.isNotBlank() } ?: selectedMode
                    val finalModel = if (staff != null) (staff.model?.takeIf { it.isNotBlank() } ?: "") else selectedModel
                    vm.createSession(title, finalMessage, finalMode, finalModel, workspace)
                    onDismiss()
                }, modifier = Modifier.fillMaxWidth()) { Text("Create") }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CronScreen(state: UiState, vm: MonitorViewModel, onRefresh: () -> Unit) {
    val allSessions = state.allSessions.takeIf { it.isNotEmpty() } ?: state.sessions
    var cronFormTarget by remember { mutableStateOf<CronJobDto?>(null) }
    var deleteTarget by remember { mutableStateOf<CronJobDto?>(null) }

    PullToRefreshContainer(isRefreshing = state.loading, onRefresh = onRefresh) {
        LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = 12.dp)) {
            item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Text("Scheduled Jobs", fontWeight = FontWeight.SemiBold)
                    Button(onClick = { cronFormTarget = CronJobDto() }) { Text("+ New") }
                }
                Spacer(Modifier.height(8.dp))
            }
            items(state.cronJobs) { c ->
                Card(modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp), colors = CardDefaults.cardColors(containerColor = Color(0xFF161B22))) {
                    Column(Modifier.padding(12.dp)) {
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                            Text(c.name ?: "Cron job", fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                            Switch(checked = c.enabled != false, onCheckedChange = { c.id?.let(vm::toggleCron) })
                        }
                        Spacer(Modifier.height(4.dp))
                        Text("Every ${c.intervalSec ?: 0}s", color = Color(0xFF8B949E))
                        Text("Last run: ${formatTimestamp(c.lastRun)}  -  Next run: ${c.nextRunDisplay()}", color = Color(0xFF8B949E), style = MaterialTheme.typography.bodySmall)
                        val countdown = formatCountdown(c.lastRun, c.intervalSec)
                        if (countdown.isNotBlank()) {
                            Text("Time to next run: $countdown", color = Color(0xFFD29922), style = MaterialTheme.typography.bodySmall)
                        }
                        if (c.lastStatus != null) {
                            Text("Status: ${c.lastStatus}", color = if (c.lastStatus?.startsWith("fail") == true) Color(0xFFF85149) else Color(0xFF3FB950), style = MaterialTheme.typography.bodySmall)
                        }
                        Spacer(Modifier.height(6.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            Button(onClick = { c.id?.let(vm::runCron) }, contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp)) { Text("Run", fontSize = MaterialTheme.typography.bodySmall.fontSize) }
                            Button(onClick = { cronFormTarget = c }, contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp)) { Text("Edit", fontSize = MaterialTheme.typography.bodySmall.fontSize) }
                            Button(onClick = { deleteTarget = c }, colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFF85149)), contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp)) { Text("Delete", fontSize = MaterialTheme.typography.bodySmall.fontSize) }
                        }
                    }
                }
            }
            item { Spacer(Modifier.height(64.dp)) }
        }
    }
    cronFormTarget?.let { CronFormDialog(it, state, vm, allSessions) { cronFormTarget = null } }
    deleteTarget?.let { c ->
        AlertDialog(
            onDismissRequest = { deleteTarget = null },
            title = { Text("Delete cron job?") },
            text = { Text("Are you sure you want to delete \"${c.name}\"?") },
            confirmButton = {
                Button(colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFF85149)), onClick = { c.id?.let(vm::deleteCronJob); deleteTarget = null }) { Text("Delete") }
            },
            dismissButton = { TextButton(onClick = { deleteTarget = null }) { Text("Cancel") } }
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CronFormDialog(job: CronJobDto, state: UiState, vm: MonitorViewModel, allSessions: List<SessionDto>, onDismiss: () -> Unit) {
    val isNew = job.id.isNullOrBlank()
    var name by remember { mutableStateOf(job.name ?: "") }
    var intervalMin by remember { mutableStateOf(((job.interval_sec ?: 300) / 60).toString()) }
    var type by remember { mutableStateOf(job.actionType ?: "session") }
    var message by remember { mutableStateOf(job.actionMessage ?: "") }
    var sessionId by remember { mutableStateOf(job.actionSessionId ?: "") }
    var fork by remember { mutableStateOf(job.actionFork ?: false) }
    var directory by remember { mutableStateOf(job.actionDirectory ?: "") }
    var selectedMode by remember { mutableStateOf(job.actionMode ?: "build") }
    var selectedModel by remember { mutableStateOf(job.actionModel ?: "") }
    var typeMenuOpen by remember { mutableStateOf(false) }
    var modeMenuOpen by remember { mutableStateOf(false) }
    var modelMenuOpen by remember { mutableStateOf(false) }
    var sessionMenuOpen by remember { mutableStateOf(false) }

    val selectedStaff = findStaffByModeName(selectedMode, state.staff)

    Dialog(onDismissRequest = onDismiss) {
        Card(modifier = Modifier.fillMaxWidth().fillMaxHeight(0.9f), colors = CardDefaults.cardColors(containerColor = Color(0xFF161B22))) {
            Column(Modifier.padding(16.dp).verticalScroll(rememberScrollState())) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Text(if (isNew) "New Cron Job" else "Edit Cron Job", fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                    IconButton(onClick = onDismiss) { Icon(Icons.Filled.Clear, contentDescription = "Close", tint = Color(0xFFF85149)) }
                }
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("Name") }, modifier = Modifier.fillMaxWidth())
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(value = intervalMin, onValueChange = { intervalMin = it.filter { c -> c.isDigit() } }, label = { Text("Interval (minutes)") }, modifier = Modifier.fillMaxWidth())
                Spacer(Modifier.height(8.dp))
                ExposedDropdownMenuBox(expanded = typeMenuOpen, onExpandedChange = { typeMenuOpen = !typeMenuOpen }) {
                    OutlinedTextField(value = if (type == "session") "Continue Existing Case" else "New Case", onValueChange = {}, readOnly = true, label = { Text("Type") }, modifier = Modifier.fillMaxWidth().menuAnchor(), trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = typeMenuOpen) })
                    DropdownMenu(expanded = typeMenuOpen, onDismissRequest = { typeMenuOpen = false }) {
                        DropdownMenuItem(text = { Text("Continue Existing Case") }, onClick = { type = "session"; typeMenuOpen = false })
                        DropdownMenuItem(text = { Text("New Case") }, onClick = { type = "workspace"; typeMenuOpen = false })
                    }
                }
                if (type == "session") {
                    Spacer(Modifier.height(8.dp))
                    ExposedDropdownMenuBox(expanded = sessionMenuOpen, onExpandedChange = { sessionMenuOpen = !sessionMenuOpen }) {
                        OutlinedTextField(value = allSessions.firstOrNull { it.id == sessionId }?.displayLabel() ?: sessionId, onValueChange = {}, readOnly = true, label = { Text("Case") }, modifier = Modifier.fillMaxWidth().menuAnchor(), trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = sessionMenuOpen) })
                        DropdownMenu(expanded = sessionMenuOpen, onDismissRequest = { sessionMenuOpen = false }) {
                            allSessions.forEach { s ->
                                DropdownMenuItem(text = { Text(s.displayLabel()) }, onClick = { sessionId = s.id.orEmpty(); sessionMenuOpen = false })
                            }
                        }
                    }
                    Spacer(Modifier.height(4.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(checked = fork, onCheckedChange = { fork = it })
                        Spacer(Modifier.width(4.dp))
                        Text("Start new conversation", color = Color(0xFF8B949E), style = MaterialTheme.typography.bodySmall)
                    }
                }
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(value = message, onValueChange = { message = it }, label = { Text("Message") }, modifier = Modifier.fillMaxWidth(), minLines = 2)
                Spacer(Modifier.height(8.dp))
                ExposedDropdownMenuBox(expanded = modeMenuOpen, onExpandedChange = { modeMenuOpen = !modeMenuOpen }) {
                    OutlinedTextField(value = modeLabel(selectedMode), onValueChange = {}, readOnly = true, label = { Text("Mode") }, modifier = Modifier.fillMaxWidth().menuAnchor(), trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = modeMenuOpen) })
                    DropdownMenu(expanded = modeMenuOpen, onDismissRequest = { modeMenuOpen = false }) {
                        buildModeOptions(state.staff).forEach { mode ->
                            DropdownMenuItem(text = { Text(modeLabel(mode)) }, onClick = {
                                selectedMode = mode
                                val staffModel = findStaffByModeName(mode, state.staff)?.model?.takeIf { it.isNotBlank() }
                                selectedModel = staffModel ?: ""
                                modeMenuOpen = false
                            })
                        }
                    }
                }
                Spacer(Modifier.height(8.dp))
                ExposedDropdownMenuBox(expanded = modelMenuOpen && selectedStaff == null, onExpandedChange = { if (selectedStaff == null) modelMenuOpen = !modelMenuOpen }) {
                    OutlinedTextField(value = selectedModel.ifBlank { "Default model" }, onValueChange = {}, readOnly = true, enabled = selectedStaff == null, label = { Text("Model") }, modifier = Modifier.fillMaxWidth().menuAnchor(), trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = modelMenuOpen) })
                    DropdownMenu(expanded = modelMenuOpen && selectedStaff == null, onDismissRequest = { modelMenuOpen = false }) {
                        if (state.availableModels.isEmpty()) {
                            DropdownMenuItem(text = { Text("Default model") }, onClick = { selectedModel = ""; modelMenuOpen = false })
                        } else {
                            state.availableModels.forEach { model ->
                                DropdownMenuItem(text = { Text(model.label()) }, onClick = { selectedModel = model.id.orEmpty(); modelMenuOpen = false })
                            }
                        }
                    }
                }
                Spacer(Modifier.height(12.dp))
                Button(onClick = {
                    if (name.isBlank() || message.isBlank()) { vm.showNotice("Name and message required"); return@Button }
                    val intervalSec = (intervalMin.toIntOrNull() ?: 5) * 60
                    val staff = selectedStaff
                    val action = JsonObject().apply {
                        addProperty("type", type)
                        addProperty("message", message)
                        if (staff != null) { addProperty("staff", staff.name); addProperty("mode", staff.mode ?: ""); addProperty("model", staff.model ?: "") }
                        else { addProperty("mode", selectedMode); addProperty("model", selectedModel) }
                        if (type == "session") { addProperty("session_id", sessionId); addProperty("fork", fork) }
                        else { addProperty("directory", directory) }
                    }
                    if (isNew) vm.createCronJob(name, intervalSec, action) else vm.updateCronJob(job.id!!, name, intervalSec, action)
                    onDismiss()
                }, modifier = Modifier.fillMaxWidth()) { Text(if (isNew) "Create" else "Save") }
            }
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
private fun TasksScreen(state: UiState, vm: MonitorViewModel, onRefresh: () -> Unit) {
    val sessionsWithTodos = (state.allSessions.takeIf { it.isNotEmpty() } ?: state.sessions).filter { it.todos?.isNotEmpty() == true }
    var selectedSession by remember { mutableStateOf<SessionDto?>(null) }

    PullToRefreshContainer(isRefreshing = state.loading, onRefresh = onRefresh) {
        LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = 12.dp)) {
            item {
                Text("Tasks", fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.height(8.dp))
            }
            if (sessionsWithTodos.isEmpty()) {
                item {
                    Box(Modifier.fillMaxWidth().height(200.dp), contentAlignment = Alignment.Center) {
                        Text("No tasks found", color = Color(0xFF8B949E))
                    }
                }
            } else {
                items(sessionsWithTodos) { session ->
                    Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp), colors = CardDefaults.cardColors(containerColor = Color(0xFF161B22)), onClick = { selectedSession = session }) {
                        Column(Modifier.padding(12.dp)) {
                            Text(session.title.ifBlank { "Untitled" }, fontWeight = FontWeight.SemiBold)
                            Spacer(Modifier.height(4.dp))
                            Text("${session.todos?.size ?: 0} task(s)", color = Color(0xFF8B949E), fontSize = MaterialTheme.typography.bodySmall.fontSize)
                        }
                    }
                }
            }
            item { Spacer(Modifier.height(64.dp)) }
        }
    }
    selectedSession?.let { session ->
        AlertDialog(
            onDismissRequest = { selectedSession = null },
            title = { Text(session.title.ifBlank { "Tasks" }) },
            text = {
                Column {
                    session.todos?.forEach { todo ->
                        Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                            Box(Modifier.size(8.dp).background(if (todo.status == "done") Color(0xFF3FB950) else if (todo.status == "pending") Color(0xFFD29922) else Color(0xFF8B949E), CircleShape))
                            Spacer(Modifier.width(8.dp))
                            Column(Modifier.weight(1f)) {
                                Text(todo.content, fontSize = MaterialTheme.typography.bodySmall.fontSize)
                                Text("${todo.status}${todo.priority?.let { " · $it" } ?: ""}", color = Color(0xFF8B949E), fontSize = MaterialTheme.typography.labelSmall.fontSize)
                            }
                        }
                    }
                }
            },
            confirmButton = { TextButton(onClick = { selectedSession = null }) { Text("Close") } }
        )
    }
}

@Composable
private fun NotificationsScreen(state: UiState, vm: MonitorViewModel, onRefresh: () -> Unit) {
    PullToRefreshContainer(isRefreshing = state.loading, onRefresh = onRefresh) {
        LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = 12.dp)) {
            item {
                Text("Notifications", fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.height(8.dp))
            }
            if (state.remoteNotifications.isEmpty()) {
                item {
                    Box(Modifier.fillMaxWidth().height(200.dp), contentAlignment = Alignment.Center) {
                        Text("No notifications", color = Color(0xFF8B949E))
                    }
                }
            } else {
                items(state.remoteNotifications) { ntf ->
                    Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp), colors = CardDefaults.cardColors(containerColor = Color(0xFF161B22))) {
                        Row(Modifier.fillMaxWidth().padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                            val ntfColor = when (ntf.type) { "error" -> Color(0xFFF85149); "warning" -> Color(0xFFD29922); "success" -> Color(0xFF3FB950); else -> Color(0xFF58A6FF) }
                            Box(Modifier.size(8.dp).background(ntfColor, CircleShape))
                            Spacer(Modifier.width(8.dp))
                            Text(ntf.message, color = Color.White, modifier = Modifier.weight(1f), fontSize = MaterialTheme.typography.bodySmall.fontSize)
                            IconButton(onClick = { vm.dismissNotification(ntf.id) }, modifier = Modifier.size(24.dp)) {
                                Icon(Icons.Filled.Clear, contentDescription = "Dismiss", tint = Color(0xFF8B949E), modifier = Modifier.size(16.dp))
                            }
                        }
                    }
                }
            }
            item { Spacer(Modifier.height(64.dp)) }
        }
    }
}

@Composable
private fun LogsScreen(state: UiState, vm: MonitorViewModel, onRefresh: () -> Unit) {
    var searchQuery by remember { mutableStateOf("") }
    var logLines by remember { mutableStateOf<List<String>>(vm.cachedLogs) }
    var loaded by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        vm.fetchLogs()
        delay(1000)
        logLines = vm.cachedLogs
        loaded = true
    }

    PullToRefreshContainer(isRefreshing = state.loading, onRefresh = onRefresh) {
        Column(Modifier.fillMaxSize().padding(horizontal = 12.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Text("Logs", fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                OutlinedTextField(value = searchQuery, onValueChange = { searchQuery = it }, placeholder = { Text("Search") }, modifier = Modifier.width(200.dp), singleLine = true, textStyle = MaterialTheme.typography.bodySmall)
            }
            Spacer(Modifier.height(8.dp))
            val filtered = if (searchQuery.isBlank()) logLines else logLines.filter { it.contains(searchQuery, ignoreCase = true) }
            LazyColumn(modifier = Modifier.fillMaxWidth()) {
                if (filtered.isEmpty()) {
                    item { Text("No log entries", color = Color(0xFF8B949E), modifier = Modifier.padding(16.dp)) }
                } else {
                    items(filtered) { line ->
                        val match = Regex("""\[(\d{2}:\d{2}:\d{2})\]\s*(.*)""").find(line)
                        val display = if (match != null) "[${match.groupValues[1]}] ${match.groupValues[2]}" else line
                        Text(display, fontSize = MaterialTheme.typography.labelSmall.fontSize, fontFamily = FontFamily.Monospace, color = Color(0xFF8B949E), modifier = Modifier.padding(vertical = 1.dp))
                    }
                }
                item { Spacer(Modifier.height(64.dp)) }
            }
        }
    }
}

@Composable
@OptIn(ExperimentalMaterial3Api::class, ExperimentalMaterialApi::class)
private fun WorkflowsScreen(state: UiState, vm: MonitorViewModel, onRefresh: () -> Unit) {
    var editingWf by remember { mutableStateOf<WorkflowDto?>(null) }
    var editingNodes by remember { mutableStateOf<List<WorkflowNodeDto>>(emptyList()) }
    var editingEdges by remember { mutableStateOf<List<WorkflowEdgeDto>>(emptyList()) }
    var wfName by remember { mutableStateOf("") }
    var selectedNodeId by remember { mutableStateOf<String?>(null) }
    var showNodeEditor by remember { mutableStateOf(false) }
    var draggingFrom by remember { mutableStateOf<String?>(null) }
    var dragPointer by remember { mutableStateOf(Offset.Zero) }
    var pendingDeleteEdge by remember { mutableStateOf<WorkflowEdgeDto?>(null) }
    var connectingFrom by remember { mutableStateOf<String?>(null) }
    var showEdgeList by remember { mutableStateOf(false) }
    var zoom by remember { mutableStateOf(1f) }
    var panX by remember { mutableStateOf(0f) }
    var panY by remember { mutableStateOf(0f) }
    val staff = state.staff

    fun Float.toCanvas(scale: Float, pan: Float) = (this - pan) / scale

    PullToRefreshContainer(isRefreshing = state.loading, onRefresh = onRefresh) {
        if (editingWf != null) {

            // Auto-fit on entry
            LaunchedEffect(editingWf?.id) {
                if (editingNodes.isNotEmpty()) {
                    val minX = editingNodes.minOf { it.x }; val minY = editingNodes.minOf { it.y }
                    val maxX = editingNodes.maxOf { it.x + NODE_W }; val maxY = editingNodes.maxOf { it.y + NODE_H }
                    zoom = minOf(1f, 300f / (maxX - minX + 100)).coerceIn(0.5f, 1.5f)
                    panX = 20f; panY = 20f
                } else { zoom = 1f; panX = 0f; panY = 0f }
            }

            Column(Modifier.fillMaxSize().padding(8.dp)) {
                // Toolbar
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp), verticalAlignment = Alignment.CenterVertically) {
                    TextButton(onClick = { editingWf = null }, contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp)) { Text("←") }
                    OutlinedTextField(value = wfName, onValueChange = { wfName = it }, modifier = Modifier.weight(1f), singleLine = true, textStyle = MaterialTheme.typography.bodySmall, placeholder = { Text("Name") })
                    TextButton(onClick = {
                        if (wfName.isBlank()) vm.showNotice("Enter a workflow name")
                        else if (editingNodes.none { it.type == "start" }) vm.showNotice("Add at least one Start node")
                        else if (editingNodes.none { it.type == "end" }) vm.showNotice("Add at least one End node")
                        else vm.saveWorkflow(WorkflowDto(id = editingWf?.id ?: "wf_${System.currentTimeMillis()}", name = wfName, nodes = editingNodes.toList(), edges = editingEdges.toList()))
                    }, contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp)) { Text("Save", fontSize = MaterialTheme.typography.labelSmall.fontSize) }
                }
                Spacer(Modifier.height(4.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp), verticalAlignment = Alignment.CenterVertically) {
                    Button(onClick = {
                        val nid = "n${System.currentTimeMillis()}"; val cnt = editingNodes.count { it.type == "start" }
                        editingNodes = editingNodes + WorkflowNodeDto(id = nid, name = "Start${if (cnt > 0) " ${cnt + 1}" else ""}", type = "start", x = 40f + (editingNodes.size % 3) * 220f, y = 40f + (editingNodes.size / 3) * 120f)
                    }, contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp), colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2EA043))) { Text("+ Start", fontSize = MaterialTheme.typography.labelSmall.fontSize, color = Color.White) }
                    Button(onClick = {
                        val nid = "n${System.currentTimeMillis()}"; val cnt = editingNodes.count { it.type == "io" }
                        editingNodes = editingNodes + WorkflowNodeDto(id = nid, name = "Stage${if (cnt > 0) " ${cnt + 1}" else ""}", type = "io", x = 40f + (editingNodes.size % 3) * 220f, y = 40f + (editingNodes.size / 3) * 120f)
                    }, contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp), colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1F6FEB))) { Text("+ I/O", fontSize = MaterialTheme.typography.labelSmall.fontSize, color = Color.White) }
                    Button(onClick = {
                        val nid = "n${System.currentTimeMillis()}"; val cnt = editingNodes.count { it.type == "end" }
                        editingNodes = editingNodes + WorkflowNodeDto(id = nid, name = "End${if (cnt > 0) " ${cnt + 1}" else ""}", type = "end", x = 40f + (editingNodes.size % 3) * 220f, y = 40f + (editingNodes.size / 3) * 120f)
                    }, contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp), colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFDA3633))) { Text("+ End", fontSize = MaterialTheme.typography.labelSmall.fontSize, color = Color.White) }
                    Spacer(Modifier.width(4.dp))
                    TextButton(onClick = { showEdgeList = !showEdgeList }, contentPadding = PaddingValues(horizontal = 6.dp, vertical = 4.dp)) { Text("📋", fontSize = MaterialTheme.typography.labelSmall.fontSize) }
                    Spacer(Modifier.weight(1f))
                    TextButton(onClick = { zoom = (zoom - 0.1f).coerceIn(0.5f, 2f) }, contentPadding = PaddingValues(horizontal = 6.dp, vertical = 4.dp)) { Text("−", fontSize = MaterialTheme.typography.labelMedium.fontSize) }
                    Text("${(zoom * 100).toInt()}%", fontSize = MaterialTheme.typography.labelSmall.fontSize, color = Color(0xFF8B949E))
                    TextButton(onClick = { zoom = (zoom + 0.1f).coerceIn(0.5f, 2f) }, contentPadding = PaddingValues(horizontal = 6.dp, vertical = 4.dp)) { Text("+", fontSize = MaterialTheme.typography.labelMedium.fontSize) }
                    TextButton(onClick = { zoom = 1f; panX = 0f; panY = 0f }, contentPadding = PaddingValues(horizontal = 6.dp, vertical = 4.dp)) { Text("↺", fontSize = MaterialTheme.typography.labelSmall.fontSize) }
                }

                // Canvas
                val NODE_W = 200f; val NODE_H = 80f; val PORT_R = 6f
                val typeColors = mapOf("start" to Color(0xFF2EA043), "io" to Color(0xFF1F6FEB), "end" to Color(0xFFDA3633))
                val typeLabels = mapOf("start" to "start", "io" to "io", "end" to "end")
                Box(
                    modifier = Modifier.weight(1f).fillMaxWidth()
                        .background(Color(0xFF0D1117), RoundedCornerShape(8.dp))
                        .pointerInput(Unit) {
                            detectTapGestures { offset ->
                                val cx = (offset.x - panX) / zoom; val cy = (offset.y - panY) / zoom
                                val edgeHit = editingEdges.find { edge ->
                                    val from = editingNodes.find { it.id == edge.from }; val to = editingNodes.find { it.id == edge.to }
                                    if (from != null && to != null) {
                                        val mx = ((from.x + NODE_W / 2 + to.x + NODE_W / 2) / 2); val my = ((from.y + NODE_H + to.y) / 2)
                                        kotlin.math.sqrt((cx - mx) * (cx - mx) + (cy - my) * (cy - my)) < 30f
                                    } else false
                                }
                                if (edgeHit != null) { pendingDeleteEdge = edgeHit; return@detectTapGestures }
                                // Check if tap is on an output port (right side connector)
                                val portTap = editingNodes.findLast { n ->
                                    val px = n.x + NODE_W; val py = n.y + NODE_H / 2
                                    kotlin.math.sqrt((cx - px) * (cx - px) + (cy - py) * (cy - py)) < PORT_R + 6f
                                }
                                if (portTap != null && editingNodes.any { it.id != portTap.id }) {
                                    connectingFrom = portTap.id; return@detectTapGestures
                                }
                                val tapped = editingNodes.findLast { n -> cx in n.x..(n.x + NODE_W) && cy in n.y..(n.y + NODE_H) }
                                if (tapped != null) selectedNodeId = tapped.id else selectedNodeId = null
                            }
                        }
                        .pointerInput(Unit) {
                            detectDragGestures(
                                onDragStart = { offset ->
                                    val cx = (offset.x - panX) / zoom; val cy = (offset.y - panY) / zoom
                                    val dragged = editingNodes.findLast { n -> cx in n.x..(n.x + NODE_W) && cy in n.y..(n.y + NODE_H) }
                                    if (dragged != null) {
                                        val portX = dragged.x + NODE_W; val portY = dragged.y + NODE_H / 2
                                        if (kotlin.math.sqrt((cx - portX) * (cx - portX) + (cy - portY) * (cy - portY)) < PORT_R + 6f) {
                                            draggingFrom = dragged.id; dragPointer = Offset(cx, cy); return@detectDragGestures
                                        }
                                        selectedNodeId = dragged.id
                                    }
                                },
                                onDrag = { change, dragAmount ->
                                    change.consume()
                                    val scaled = Offset(dragAmount.x / zoom, dragAmount.y / zoom)
                                    if (draggingFrom != null) { dragPointer = Offset(dragPointer.x + scaled.x, dragPointer.y + scaled.y) }
                                    else selectedNodeId?.let { id ->
                                        val idx = editingNodes.indexOfFirst { it.id == id }
                                        if (idx >= 0) { val n = editingNodes[idx]
                                            editingNodes = editingNodes.toMutableList().apply { set(idx, n.copy(x = (n.x + scaled.x).coerceAtLeast(0f), y = (n.y + scaled.y).coerceAtLeast(0f))) }
                                        }
                                    }
                                },
                                onDragEnd = {
                                    draggingFrom?.let { fromId ->
                                        val target = editingNodes.findLast { n ->
                                            val px = n.x; val py = n.y + NODE_H / 2
                                            kotlin.math.sqrt((dragPointer.x - px) * (dragPointer.x - px) + (dragPointer.y - py) * (dragPointer.y - py)) < PORT_R + 10f
                                        }
                                        if (target != null && target.id != fromId && editingEdges.none { it.from == fromId && it.to == target.id })
                                            editingEdges = editingEdges + WorkflowEdgeDto(from = fromId, to = target.id)
                                    }
                                    draggingFrom = null
                                }
                            )
                        }
                ) {
                    // Canvas for edges
                    Canvas(Modifier.fillMaxSize()) {
                        for (edge in editingEdges) {
                            val from = editingNodes.find { it.id == edge.from }; val to = editingNodes.find { it.id == edge.to }
                            if (from != null && to != null) {
                                val x1 = (from.x + NODE_W / 2) * zoom + panX; val y1 = (from.y + NODE_H) * zoom + panY
                                val x2 = (to.x + NODE_W / 2) * zoom + panX; val y2 = to.y * zoom + panY
                                val cy = (y1 + y2) / 2
                                val path = androidx.compose.ui.graphics.Path().apply { moveTo(x1, y1); cubicTo(x1, cy, x2, cy, x2, y2) }
                                drawPath(path, color = Color(0xFF58A6FF), style = Stroke(width = 2f))
                                val angle = kotlin.math.atan2(y2 - cy, x2 - x1)
                                val ax = x2 - 8f * kotlin.math.cos(angle); val ay = y2 - 8f * kotlin.math.sin(angle)
                                val arrow = androidx.compose.ui.graphics.Path().apply {
                                    moveTo(x2, y2); lineTo(ax - 4f * kotlin.math.sin(angle), ay + 4f * kotlin.math.cos(angle))
                                    lineTo(ax + 4f * kotlin.math.sin(angle), ay - 4f * kotlin.math.cos(angle)); close()
                                }
                                drawPath(arrow, color = Color(0xFF58A6FF))
                            }
                        }
                        draggingFrom?.let { fromId ->
                            val from = editingNodes.find { it.id == fromId }
                            if (from != null) {
                                val x1 = (from.x + NODE_W / 2) * zoom + panX; val y1 = (from.y + NODE_H) * zoom + panY
                                val dx = dragPointer.x * zoom + panX; val dy = dragPointer.y * zoom + panY
                                val path = androidx.compose.ui.graphics.Path().apply { moveTo(x1, y1); cubicTo(x1, (y1 + dy) / 2, dx, (y1 + dy) / 2, dx, dy) }
                                drawPath(path, color = Color(0xAA58A6FF), style = Stroke(width = 2f, pathEffect = androidx.compose.ui.graphics.PathEffect.dashPathEffect(floatArrayOf(8f, 4f))))
                            }
                        }
                    }
                    // Nodes
                    editingNodes.forEach { n ->
                        val isSel = n.id == selectedNodeId; val borderColor = typeColors[n.type] ?: Color(0xFF58A6FF)
                        val chipColor = typeColors[n.type] ?: Color(0xFF8B949E)
                        Box(modifier = Modifier.offset { IntOffset(((n.x * zoom) + panX).roundToInt(), ((n.y * zoom) + panY).roundToInt()) }.width((NODE_W * zoom).dp).height((NODE_H * zoom).dp)) {
                            // Input port (left exterior)
                            Box(Modifier.align(Alignment.CenterStart).offset(x = (-PORT_R * zoom).dp).size((PORT_R * 2 * zoom).dp).background(if (editingEdges.any { it.to == n.id }) Color(0xFF58A6FF) else Color(0xFF30363D), CircleShape))
                            // Output port (right exterior)
                            Box(Modifier.align(Alignment.CenterEnd).offset(x = (PORT_R * zoom).dp).size((PORT_R * 2 * zoom).dp).background(if (editingEdges.any { it.from == n.id }) Color(0xFF58A6FF) else Color(0xFF30363D), CircleShape))
                            Card(modifier = Modifier.fillMaxSize().border(if (isSel) 2.dp else 1.dp, if (isSel) borderColor else Color(0xFF30363D), RoundedCornerShape(8.dp)), colors = CardDefaults.cardColors(containerColor = Color(0xFF161B22)), shape = RoundedCornerShape(8.dp)) {
                                Column(Modifier.padding(4.dp)) {
                                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                                        Icon(Icons.Filled.OpenWith, contentDescription = "Drag", tint = Color(0xFF8B949E), modifier = Modifier.size(14.dp))
                                        Spacer(Modifier.width(2.dp))
                                        Text(n.name.ifBlank { "Untitled" }, fontWeight = FontWeight.SemiBold, fontSize = MaterialTheme.typography.labelSmall.fontSize, color = if (isSel) borderColor else Color.White, modifier = Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis)
                                        Box(Modifier.padding(horizontal = 4.dp, vertical = 1.dp).background(chipColor.copy(alpha = 0.2f), RoundedCornerShape(4.dp)).padding(horizontal = 4.dp, vertical = 1.dp)) {
                                            Text(typeLabels[n.type] ?: "io", fontSize = MaterialTheme.typography.labelSmall.fontSize, color = chipColor, maxLines = 1)
                                        }
                                        IconButton(onClick = { selectedNodeId = n.id; showNodeEditor = true }, modifier = Modifier.size(18.dp)) {
                                            Icon(Icons.Filled.Edit, contentDescription = "Edit", tint = Color(0xFF8B949E), modifier = Modifier.size(12.dp))
                                        }
                                    }
                                    Text(n.staffIc ?: "No staff", fontSize = MaterialTheme.typography.labelSmall.fontSize, color = Color(0xFF8B949E), maxLines = 1, overflow = TextOverflow.Ellipsis)
                                }
                            }
                        }
                    }
                }
            }

            // Connection modal
            connectingFrom?.let { fromId ->
                val fromNode = editingNodes.find { it.id == fromId }
                AlertDialog(
                    onDismissRequest = { connectingFrom = null },
                    title = { Text("Connect from \"${fromNode?.name ?: ""}\"") },
                    text = {
                        Column { editingNodes.filter { it.id != fromId }.forEach { n ->
                            TextButton(onClick = {
                                if (editingEdges.none { it.from == fromId && it.to == n.id }) editingEdges = editingEdges + WorkflowEdgeDto(from = fromId, to = n.id)
                                connectingFrom = null
                            }) { Text("→ ${n.name}  (${n.type})") }
                        } }
                    },
                    confirmButton = { TextButton(onClick = { connectingFrom = null }) { Text("Cancel") } }
                )
            }

            // Edge deletion confirmation
            if (pendingDeleteEdge != null) {
                AlertDialog(
                    onDismissRequest = { pendingDeleteEdge = null },
                    title = { Text("Remove this connection?") },
                    text = {
                        val from = editingNodes.find { it.id == pendingDeleteEdge?.from }; val to = editingNodes.find { it.id == pendingDeleteEdge?.to }
                        Text("\"${from?.name ?: "?"}\" → \"${to?.name ?: "?"}\"")
                    },
                    confirmButton = { Button(colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFF85149)), onClick = { editingEdges = editingEdges.filter { it != pendingDeleteEdge }; pendingDeleteEdge = null }) { Text("Remove") } },
                    dismissButton = { TextButton(onClick = { pendingDeleteEdge = null }) { Text("Cancel") } }
                )
            }

            // Edge list panel
            if (showEdgeList) {
                Box(Modifier.fillMaxSize()) {
                    Card(modifier = Modifier.align(Alignment.TopStart).padding(4.dp).width(280.dp), colors = CardDefaults.cardColors(containerColor = Color(0xFF161B22))) {
                        Column(Modifier.padding(8.dp)) {
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                                Text("Edges (${editingEdges.size})", fontWeight = FontWeight.SemiBold)
                                TextButton(onClick = { showEdgeList = false }, contentPadding = PaddingValues(0.dp)) { Text("Hide", fontSize = MaterialTheme.typography.labelSmall.fontSize) }
                            }
                            if (editingEdges.isEmpty()) Text("No edges", color = Color(0xFF8B949E), fontSize = MaterialTheme.typography.labelSmall.fontSize)
                            else editingEdges.forEach { edge ->
                                val from = editingNodes.find { it.id == edge.from }; val to = editingNodes.find { it.id == edge.to }
                                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                                    Text("${from?.name ?: "?"} → ${to?.name ?: "?"}", fontSize = MaterialTheme.typography.labelSmall.fontSize, modifier = Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis, color = Color(0xFF8B949E))
                                    IconButton(onClick = { editingEdges = editingEdges.filter { it != edge } }, modifier = Modifier.size(20.dp)) { Icon(Icons.Filled.Clear, contentDescription = "Remove", tint = Color(0xFFF85149), modifier = Modifier.size(14.dp)) }
                                }
                            }
                        }
                    }
                }
            }

            // Node editor dialog
            if (showNodeEditor && selectedNodeId != null) {
                val node = editingNodes.find { it.id == selectedNodeId }
                if (node != null) {
                    var editName by remember(node.id) { mutableStateOf(node.name) }
                    var editType by remember(node.id) { mutableStateOf(node.type) }
                    var editInstr by remember(node.id) { mutableStateOf(node.instructions) }
                    var editStaff by remember(node.id) { mutableStateOf(node.staffIc ?: "") }
                    var editMode by remember(node.id) { mutableStateOf(node.mode ?: "") }
                    var editModel by remember(node.id) { mutableStateOf(node.model ?: "") }
                    var typeExp by remember { mutableStateOf(false) }; var staffExp by remember { mutableStateOf(false) }
                    var modeExp by remember { mutableStateOf(false) }; var modelExp by remember { mutableStateOf(false) }
                    val selectedStaff = staff.firstOrNull { it.name == editStaff }

                    LaunchedEffect(editStaff) { val s = staff.firstOrNull { it.name == editStaff }; if (s != null) { editMode = s.mode ?: ""; editModel = s.model ?: "" } }

                    AlertDialog(
                        onDismissRequest = { showNodeEditor = false },
                        title = { Text("Edit Stage") },
                        text = {
                            Column(Modifier.verticalScroll(rememberScrollState())) {
                                OutlinedTextField(value = editName, onValueChange = { editName = it }, label = { Text("Name") }, modifier = Modifier.fillMaxWidth())
                                Spacer(Modifier.height(8.dp))
                                ExposedDropdownMenuBox(expanded = typeExp, onExpandedChange = { typeExp = it }) {
                                    OutlinedTextField(value = editType.replaceFirstChar { it.uppercase() }, onValueChange = {}, readOnly = true, label = { Text("Type") }, trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(typeExp) }, modifier = Modifier.menuAnchor().fillMaxWidth())
                                    ExposedDropdownMenu(expanded = typeExp, onDismissRequest = { typeExp = false }) {
                                        listOf("start", "io", "end").forEach { t -> DropdownMenuItem(text = { Text(t.replaceFirstChar { it.uppercase() }) }, onClick = { editType = t; typeExp = false }) }
                                    }
                                }
                                Spacer(Modifier.height(8.dp))
                                OutlinedTextField(value = editInstr, onValueChange = { editInstr = it }, label = { Text("Instructions") }, modifier = Modifier.fillMaxWidth(), minLines = 3)
                                Spacer(Modifier.height(8.dp))
                                ExposedDropdownMenuBox(expanded = staffExp, onExpandedChange = { staffExp = it }) {
                                    OutlinedTextField(value = editStaff.ifBlank { "— None —" }, onValueChange = {}, readOnly = true, label = { Text("Staff IC") }, trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(staffExp) }, modifier = Modifier.menuAnchor().fillMaxWidth())
                                    ExposedDropdownMenu(expanded = staffExp, onDismissRequest = { staffExp = false }) {
                                        DropdownMenuItem(text = { Text("— None —") }, onClick = { editStaff = ""; staffExp = false })
                                        staff.forEach { s -> DropdownMenuItem(text = { Text(s.name) }, onClick = { editStaff = s.name; staffExp = false }) }
                                    }
                                }
                                Spacer(Modifier.height(8.dp))
                                val staffMode = selectedStaff?.mode?.takeIf { it.isNotBlank() }; val staffModel = selectedStaff?.model?.takeIf { it.isNotBlank() }
                                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    ExposedDropdownMenuBox(expanded = modeExp, onExpandedChange = { if (selectedStaff == null) modeExp = it }, modifier = Modifier.weight(1f)) {
                                        OutlinedTextField(value = if (staffMode != null) modeLabel(staffMode) else editMode.ifBlank { "Select mode" }, onValueChange = {}, readOnly = true, enabled = selectedStaff == null, label = { Text(if (selectedStaff == null) "Mode *" else "Mode") }, trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(modeExp) }, modifier = Modifier.menuAnchor().fillMaxWidth())
                                        ExposedDropdownMenu(expanded = modeExp && selectedStaff == null, onDismissRequest = { modeExp = false }) { listOf("build", "plan").forEach { m -> DropdownMenuItem(text = { Text(modeLabel(m)) }, onClick = { editMode = m; modeExp = false }) } }
                                    }
                                    ExposedDropdownMenuBox(expanded = modelExp, onExpandedChange = { if (selectedStaff == null) modelExp = it }, modifier = Modifier.weight(1f)) {
                                        OutlinedTextField(value = if (staffModel != null) staffModel else editModel.ifBlank { "Default model" }, onValueChange = {}, readOnly = true, enabled = selectedStaff == null, label = { Text(if (selectedStaff == null) "Model *" else "Model") }, trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(modelExp) }, modifier = Modifier.menuAnchor().fillMaxWidth())
                                        ExposedDropdownMenu(expanded = modelExp && selectedStaff == null, onDismissRequest = { modelExp = false }) {
                                            if (state.availableModels.isEmpty()) DropdownMenuItem(text = { Text("Default model") }, onClick = { editModel = ""; modelExp = false })
                                            else state.availableModels.forEach { m -> DropdownMenuItem(text = { Text(m.label()) }, onClick = { editModel = m.id.orEmpty(); modelExp = false }) }
                                        }
                                    }
                                }
                            }
                        },
                        confirmButton = {
                            TextButton(onClick = {
                                val idx = editingNodes.indexOfFirst { it.id == node.id }
                                if (idx >= 0) {
                                    val s = staff.firstOrNull { it.name == editStaff }
                                    editingNodes = editingNodes.toMutableList().apply {
                                        set(idx, node.copy(name = editName, type = editType, instructions = editInstr, staffIc = editStaff.ifBlank { null },
                                            mode = if (s != null) (s.mode?.takeIf { it.isNotBlank() } ?: editMode) else editMode,
                                            model = if (s != null) (s.model?.takeIf { it.isNotBlank() } ?: editModel) else editModel))
                                    }
                                }
                                showNodeEditor = false
                            }) { Text("Done") }
                        },
                        dismissButton = { TextButton(onClick = { showNodeEditor = false }) { Text("Cancel") } }
                    )
                }
            }
        } else {
            // List View
            LazyColumn(Modifier.fillMaxSize().padding(8.dp)) {
                item {
                    Text("🔁 Workflows", style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(8.dp))
                }
                if (state.workflows.isEmpty()) {
                    item {
                        Box(Modifier.fillMaxWidth().height(200.dp), contentAlignment = Alignment.Center) {
                            Text("No workflows defined", color = Color(0xFF8B949E))
                        }
                    }
                } else {
                    items(state.workflows) { wf ->
                        Card(
                            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                            colors = CardDefaults.cardColors(containerColor = Color(0xFF161B22))
                        ) {
                            Row(Modifier.fillMaxWidth().padding(12.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                                Column(Modifier.weight(1f)) {
                                    Text(wf.name, fontWeight = FontWeight.SemiBold)
                                    Text("${wf.nodes.size} stages", fontSize = MaterialTheme.typography.bodySmall.fontSize, color = Color(0xFF8B949E))
                                }
                                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                    Button(onClick = {
                                        editingNodes = wf.nodes.map { it.copy() }
                                        editingEdges = wf.edges.map { it.copy() }
                                        wfName = wf.name
                                        selectedNodeId = null
                                        editingWf = wf
                                    }, contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp)) { Text("Edit", fontSize = MaterialTheme.typography.labelSmall.fontSize) }
                                    TextButton(onClick = { vm.deleteWorkflow(wf.id) }, contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp)) {
                                        Text("Delete", fontSize = MaterialTheme.typography.labelSmall.fontSize, color = Color(0xFFF85149))
                                    }
                                }
                            }
                        }
                    }
                }
                item { Spacer(Modifier.height(8.dp)) }
                item {
                    Button(onClick = {
                        editingWf = WorkflowDto(id = "wf_${System.currentTimeMillis()}", name = "")
                        editingNodes = emptyList()
                        editingEdges = emptyList()
                        wfName = ""
                        selectedNodeId = null
                    }, modifier = Modifier.fillMaxWidth()) { Text("+ New Workflow") }
                }
            }
        }
    }
}

private const val NODE_W = 200f
private const val NODE_H = 80f

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
    onQuestions: () -> Unit,
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
            val btnMod = Modifier.width(100.dp).fillMaxHeight().padding(vertical = 14.dp)
            SwipeActionButton("View", Icons.Filled.Visibility, Color(0xFF58A6FF), btnMod) {
                scope.launch { offsetX.animateTo(0f, tween(150)) }
                onView()
            }
            SwipeActionButton("Questions", Icons.Filled.QuestionAnswer, Color(0xFF8B949E), btnMod) {
                scope.launch { offsetX.animateTo(0f, tween(150)) }
                onQuestions()
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

@Composable
private fun QuestionsDialog(session: SessionDto, onDismiss: () -> Unit) {
    val questions = session.pendingQuestions ?: emptyList()
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Questions — ${session.title.ifBlank { "Case" }}") },
        text = {
            if (questions.isEmpty()) {
                Text("No pending questions", color = Color(0xFF8B949E))
            } else {
                Column {
                    questions.forEach { q ->
                        Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp), colors = CardDefaults.cardColors(containerColor = Color(0xFF161B22))) {
                            Column(Modifier.padding(8.dp)) {
                                if (!q.header.isNullOrBlank()) Text(q.header, fontWeight = FontWeight.SemiBold, fontSize = MaterialTheme.typography.bodySmall.fontSize)
                                Text(q.question, fontSize = MaterialTheme.typography.bodySmall.fontSize, color = Color(0xFF8B949E))
                                q.options?.forEachIndexed { i, opt ->
                                    val selected = q.selectedIndices?.contains(i) == true
                                    val label = if (opt.isJsonObject) opt.asJsonObject.get("label")?.asString ?: opt.asJsonObject.get("value")?.asString ?: opt.toString() else opt.asString ?: opt.toString()
                                    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(top = 2.dp)) {
                                        Box(Modifier.size(12.dp).background(if (selected) Color(0xFF58A6FF) else Color(0xFF30363D), CircleShape))
                                        Spacer(Modifier.width(6.dp))
                                        Text(label, color = if (selected) Color(0xFF58A6FF) else Color(0xFF8B949E), fontSize = MaterialTheme.typography.labelSmall.fontSize)
                                    }
                                }
                                if (q.answered) Text("✓ Answered", color = Color(0xFF3FB950), fontSize = MaterialTheme.typography.labelSmall.fontSize)
                            }
                        }
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = onDismiss) { Text("Close") } }
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
        OutlinedTextField(value = instruction, onValueChange = { instruction = it }, label = { Text("Instruction") }, modifier = Modifier.fillMaxWidth(), enabled = !isSending)
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
                vm.sendInstruction(session.id ?: "", finalInstruction, session.directory, requestMode, requestModel, fork = fork, onSuccess = { instruction = "" })
            },
            enabled = !isSending,
            modifier = Modifier.fillMaxWidth()
        ) { Text(if (isSending) "Sending\u2026" else "Send") }
        Spacer(Modifier.height(64.dp))
    }
    if (showResponseDialog && session.lastText != null) {
        val respContext = LocalContext.current
        AlertDialog(
            onDismissRequest = { showResponseDialog = false },
            title = { Text("Last response") },
            text = {
                Box(Modifier.heightIn(max = 400.dp).verticalScroll(rememberScrollState())) {
                    AndroidView(factory = { ctx ->
                        android.widget.TextView(ctx).apply {
                            isVerticalScrollBarEnabled = true
                            io.noties.markwon.Markwon.builder(ctx).usePlugin(io.noties.markwon.ext.tables.TablePlugin.create(ctx)).build().setMarkdown(this, session.lastText ?: "")
                        }
                    }, modifier = Modifier.fillMaxWidth())
                }
            },
            dismissButton = {
                TextButton(onClick = {
                    val clip = android.content.ClipData.newPlainText("response", session.lastText)
                    (respContext.getSystemService(android.content.Context.CLIPBOARD_SERVICE) as? android.content.ClipboardManager)?.setPrimaryClip(clip)
                }) { Text("Copy") }
            },
            confirmButton = { TextButton(onClick = { showResponseDialog = false }) { Text("Close") } }
        )
    }
    if (showInstructionDialog && session.lastUserPrompt != null) {
        val instrContext = LocalContext.current
        AlertDialog(
            onDismissRequest = { showInstructionDialog = false },
            title = { Text("Last instruction") },
            text = {
                Box(Modifier.heightIn(max = 400.dp).verticalScroll(rememberScrollState())) {
                    AndroidView(factory = { ctx ->
                        android.widget.TextView(ctx).apply {
                            isVerticalScrollBarEnabled = true
                            io.noties.markwon.Markwon.builder(ctx).usePlugin(io.noties.markwon.ext.tables.TablePlugin.create(ctx)).build().setMarkdown(this, session.lastUserPrompt ?: "")
                        }
                    }, modifier = Modifier.fillMaxWidth())
                }
            },
            dismissButton = {
                TextButton(onClick = {
                    val clip = android.content.ClipData.newPlainText("instruction", session.lastUserPrompt)
                    (instrContext.getSystemService(android.content.Context.CLIPBOARD_SERVICE) as? android.content.ClipboardManager)?.setPrimaryClip(clip)
                }) { Text("Copy") }
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

data class RemoteNotification(
    val id: String,
    val message: String,
    val type: String
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
    val workflows: List<WorkflowDto> = emptyList(),
    val summary: SummaryDto = SummaryDto(),
    val notificationEvent: NotificationEvent? = null,
    val remoteNotifications: List<RemoteNotification> = emptyList()
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
    val directory: String? = null,
    @SerializedName("pending_questions") val pendingQuestions: List<QuestionDto>? = null,
    @SerializedName("todos") val todos: List<TodoDto>? = null
)

data class QuestionDto(
    val question: String = "",
    val header: String? = null,
    val options: List<JsonElement>? = null,
    @SerializedName("selected_indices") val selectedIndices: List<Int>? = null,
    val answered: Boolean = false
)

data class TodoDto(
    val content: String = "",
    val status: String = "",
    val priority: String? = null
)
data class StaffDto(
    val name: String = "",
    val description: String? = null,
    val gender: String? = null,
    val mode: String? = null,
    val model: String? = null,
    val path: String? = null
)
data class ModelOption(val id: String? = null, val provider: String? = null) { fun label(): String = if (provider.isNullOrBlank()) id.orEmpty() else "$provider · ${id.orEmpty()}" }
data class CronJobDto(
    val id: String? = null,
    val name: String? = null,
    val interval_sec: Int? = null,
    val enabled: Boolean? = null,
    @SerializedName("last_run") val lastRun: Long? = null,
    @SerializedName("last_status") val lastStatus: String? = null,
    @SerializedName("action_type") val actionType: String? = null,
    @SerializedName("action_message") val actionMessage: String? = null,
    @SerializedName("action_staff") val actionStaff: String? = null,
    @SerializedName("action_mode") val actionMode: String? = null,
    @SerializedName("action_model") val actionModel: String? = null,
    @SerializedName("action_session_id") val actionSessionId: String? = null,
    @SerializedName("action_fork") val actionFork: Boolean? = null,
    @SerializedName("action_directory") val actionDirectory: String? = null
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

data class WorkflowNodeDto(
    val id: String = "",
    val name: String = "",
    val type: String = "io",
    val instructions: String = "",
    @SerializedName("staff_ic") val staffIc: String? = null,
    val mode: String? = null,
    val model: String? = null,
    val x: Float = 0f,
    val y: Float = 0f
)
data class WorkflowEdgeDto(
    val from: String = "",
    val to: String = ""
)
data class WorkflowDto(
    val id: String = "",
    val name: String = "",
    val nodes: List<WorkflowNodeDto> = emptyList(),
    val edges: List<WorkflowEdgeDto> = emptyList()
)
data class WorkflowInstanceDto(
    @SerializedName("session_id") val sessionId: String = "",
    @SerializedName("workflow_id") val workflowId: String = "",
    val status: String = "",
    val paused: Boolean = false,
    @SerializedName("current_node") val currentNode: String? = null,
    @SerializedName("node_states") val nodeStates: Map<String, NodeStateDto>? = null
)
data class NodeStateDto(
    val status: String = "",
    @SerializedName("completed_at") val completedAt: Long? = null
)

private fun JsonObject.toWorkflowList(): List<WorkflowDto> {
    val arr = getAsJsonArray("workflows") ?: return emptyList()
    return arr.mapNotNull {
        runCatching {
            val o = it.asJsonObject
            val nodes = o.getAsJsonArray("nodes")?.mapNotNull { n ->
                runCatching {
                    val no = n.asJsonObject
                    WorkflowNodeDto(
                        id = no.get("id")?.asString ?: "",
                        name = no.get("name")?.asString ?: "",
                        type = no.get("type")?.asString ?: "io",
                        instructions = no.get("instructions")?.asString ?: "",
                        staffIc = no.get("staff_ic")?.asString,
                        mode = no.get("mode")?.asString,
                        model = no.get("model")?.asString,
                        x = no.get("x")?.asFloat ?: 0f,
                        y = no.get("y")?.asFloat ?: 0f
                    )
                }.getOrNull()
            } ?: emptyList()
            val edges = o.getAsJsonArray("edges")?.mapNotNull { e ->
                runCatching {
                    val eo = e.asJsonObject
                    WorkflowEdgeDto(
                        from = eo.get("from")?.asString ?: "",
                        to = eo.get("to")?.asString ?: ""
                    )
                }.getOrNull()
            } ?: emptyList()
            WorkflowDto(
                id = o.get("id")?.asString ?: "",
                name = o.get("name")?.asString ?: "",
                nodes = nodes,
                edges = edges
            )
        }.getOrNull()
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
                api.getStatusGet("$base/api/status")
            }.getOrElse {
                val msg = try { val e = it as? retrofit2.HttpException; if (e != null) "HTTP ${e.code()} ${e.response()?.raw()?.request?.url}" else it.message } catch (_: Exception) { null } ?: it.message ?: "Failed"
                android.util.Log.e("MyDora", "Status fetch error: $msg")
                _uiState.value = _uiState.value.copy(loading = false, notice = msg)
                return@launch
            }

            val staff = runCatching {
                api.getJson("$base/api/super-staff").toStaffList()
            }.getOrDefault(emptyList())
            val cron = runCatching {
                api.getJson("$base/api/cron-jobs").toCronList()
            }.getOrDefault(emptyList())
            val workflows = runCatching {
                api.getJson("$base/api/workflows").toWorkflowList()
            }.getOrDefault(emptyList())
            val models = collectModels(status, staff)
            val remoteNotifs = runCatching {
                val resp = api.getJson("$base/api/notifications/messages")
                val arr = resp?.getAsJsonArray("notifications") ?: return@runCatching emptyList<RemoteNotification>()
                arr.mapNotNull { it?.asJsonObject?.let { obj ->
                    val id = obj.get("id")?.asString ?: return@mapNotNull null
                    val msg = obj.get("message")?.asString ?: return@mapNotNull null
                    val typ = obj.get("type")?.asString ?: "info"
                    RemoteNotification(id, msg, typ)
                }}
            }.getOrDefault(emptyList())
            _uiState.value = _uiState.value.copy(
                loading = false,
                sessions = status.sessions ?: emptyList(),
                allSessions = status.allSessions ?: emptyList(),
                summary = status.summary ?: SummaryDto(),
                staff = staff,
                availableModels = models,
                cronJobs = cron,
                workflows = workflows,
                bossName = status.bossName?.takeIf { it.isNotBlank() } ?: _uiState.value.bossName,
                remoteNotifications = remoteNotifs
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

    fun sendInstruction(sessionId: String, message: String, directory: String? = null, mode: String? = null, model: String? = null, fork: Boolean = false, onSuccess: (() -> Unit)? = null) {
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
                if (ok) onSuccess?.invoke()
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

    fun createSession(title: String, message: String, mode: String, model: String, directory: String) {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                val api = createApi(_uiState.value.apiKey)
                sendQueued(api, base, "new-session", JsonObject().apply {
                    addProperty("title", title)
                    addProperty("message", message)
                    addProperty("mode", mode)
                    addProperty("model", model)
                    addProperty("directory", directory)
                    addProperty("fresh", true)
                })
                _uiState.value = _uiState.value.copy(notice = "New case started")
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

    fun createCronJob(name: String, intervalSec: Int, action: JsonObject) {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                val api = createApi(_uiState.value.apiKey)
                sendQueued(api, base, "cron-jobs/create", JsonObject().apply {
                    addProperty("name", name)
                    addProperty("interval_sec", intervalSec)
                    add("action", action)
                })
                _uiState.value = _uiState.value.copy(notice = "Cron job created")
            }.onFailure {
                _uiState.value = _uiState.value.copy(notice = it.message ?: "Request failed")
            }
            refreshAll()
        }
    }

    fun updateCronJob(id: String, name: String, intervalSec: Int, action: JsonObject) {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                val api = createApi(_uiState.value.apiKey)
                sendQueued(api, base, "cron-jobs/update", JsonObject().apply {
                    addProperty("id", id)
                    addProperty("name", name)
                    addProperty("interval_sec", intervalSec)
                    add("action", action)
                })
                _uiState.value = _uiState.value.copy(notice = "Cron job updated")
            }.onFailure {
                _uiState.value = _uiState.value.copy(notice = it.message ?: "Request failed")
            }
            refreshAll()
        }
    }

    fun deleteCronJob(id: String) {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                val api = createApi(_uiState.value.apiKey)
                sendQueued(api, base, "cron-jobs/delete", JsonObject().apply { addProperty("id", id) })
                _uiState.value = _uiState.value.copy(notice = "Cron job deleted")
            }.onFailure {
                _uiState.value = _uiState.value.copy(notice = it.message ?: "Request failed")
            }
            refreshAll()
        }
    }

    fun saveWorkflow(wf: WorkflowDto) {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                val api = createApi(_uiState.value.apiKey)
                sendQueued(api, base, "workflow-save", JsonObject().apply {
                    add("workflow", Gson().toJsonTree(wf))
                })
                _uiState.value = _uiState.value.copy(notice = "Workflow saved")
            }.onFailure {
                _uiState.value = _uiState.value.copy(notice = it.message ?: "Request failed")
            }
            refreshAll()
        }
    }

    fun deleteWorkflow(id: String) {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                val api = createApi(_uiState.value.apiKey)
                sendQueued(api, base, "workflow-delete", JsonObject().apply { addProperty("id", id) })
                _uiState.value = _uiState.value.copy(notice = "Workflow deleted")
            }.onFailure {
                _uiState.value = _uiState.value.copy(notice = it.message ?: "Request failed")
            }
            refreshAll()
        }
    }

    fun attachWorkflow(sessionId: String, workflowId: String) {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                val api = createApi(_uiState.value.apiKey)
                sendQueued(api, base, "workflow-attach", JsonObject().apply {
                    addProperty("session_id", sessionId)
                    addProperty("workflow_id", workflowId)
                })
                _uiState.value = _uiState.value.copy(notice = "Workflow attached")
            }.onFailure {
                _uiState.value = _uiState.value.copy(notice = it.message ?: "Request failed")
            }
            refreshAll()
        }
    }

    fun advanceWorkflow(sessionId: String) {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                val api = createApi(_uiState.value.apiKey)
                sendQueued(api, base, "workflow-advance", JsonObject().apply { addProperty("session_id", sessionId) })
                _uiState.value = _uiState.value.copy(notice = "Workflow advanced")
            }.onFailure {
                _uiState.value = _uiState.value.copy(notice = it.message ?: "Request failed")
            }
            refreshAll()
        }
    }

    fun pauseWorkflow(sessionId: String) {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                val api = createApi(_uiState.value.apiKey)
                sendQueued(api, base, "workflow-pause", JsonObject().apply { addProperty("session_id", sessionId) })
                _uiState.value = _uiState.value.copy(notice = "Workflow paused/resumed")
            }.onFailure {
                _uiState.value = _uiState.value.copy(notice = it.message ?: "Request failed")
            }
            refreshAll()
        }
    }

    fun createStaff(name: String, description: String, gender: String, mode: String, model: String, path: String) {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                val api = createApi(_uiState.value.apiKey)
                sendQueued(api, base, "super-staff-create", JsonObject().apply {
                    addProperty("name", name); addProperty("description", description); addProperty("gender", gender)
                    addProperty("mode", mode); addProperty("model", model); addProperty("path", path)
                })
                _uiState.value = _uiState.value.copy(notice = "Staff created")
            }.onFailure {
                _uiState.value = _uiState.value.copy(notice = it.message ?: "Request failed")
            }
            refreshAll()
        }
    }

    fun updateStaff(originalName: String, name: String, description: String, gender: String, mode: String, model: String, path: String) {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                val api = createApi(_uiState.value.apiKey)
                sendQueued(api, base, "super-staff-update", JsonObject().apply {
                    addProperty("originalName", originalName); addProperty("name", name); addProperty("description", description)
                    addProperty("gender", gender); addProperty("mode", mode); addProperty("model", model); addProperty("path", path)
                })
                _uiState.value = _uiState.value.copy(notice = "Staff updated")
            }.onFailure {
                _uiState.value = _uiState.value.copy(notice = it.message ?: "Request failed")
            }
            refreshAll()
        }
    }

    fun deleteStaff(name: String) {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                val api = createApi(_uiState.value.apiKey)
                sendQueued(api, base, "super-staff-delete", JsonObject().apply { addProperty("name", name) })
                _uiState.value = _uiState.value.copy(notice = "Staff deleted")
            }.onFailure {
                _uiState.value = _uiState.value.copy(notice = it.message ?: "Request failed")
            }
            refreshAll()
        }
    }

    fun assignStaff(sessionId: String, staffName: String) {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                val api = createApi(_uiState.value.apiKey)
                sendQueued(api, base, "super-staff-assign", JsonObject().apply {
                    addProperty("sessionId", sessionId)
                    addProperty("staffName", staffName)
                })
                _uiState.value = _uiState.value.copy(notice = if (staffName.isNotBlank()) "Staff assigned" else "Staff unassigned")
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

    fun pollNotifications() {
        viewModelScope.launch {
            val base = _uiState.value.baseUrl.trimEnd('/')
            if (base.isBlank()) return@launch
            val api = createApi(_uiState.value.apiKey)
            val remoteNotifs = runCatching {
                val resp = api.getJson("$base/api/notifications/messages")
                val arr = resp?.getAsJsonArray("notifications") ?: return@runCatching emptyList<RemoteNotification>()
                arr.mapNotNull { it?.asJsonObject?.let { obj ->
                    val id = obj.get("id")?.asString ?: return@mapNotNull null
                    val msg = obj.get("message")?.asString ?: return@mapNotNull null
                    val typ = obj.get("type")?.asString ?: "info"
                    RemoteNotification(id, msg, typ)
                }}
            }.getOrDefault(emptyList())
            _uiState.value = _uiState.value.copy(remoteNotifications = remoteNotifs)
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

    fun dismissNotification(id: String) {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                val api = createApi(_uiState.value.apiKey)
                sendQueued(api, base, "notifications-dismiss", JsonObject().apply { addProperty("id", id) })
            }
            val updated = _uiState.value.remoteNotifications.filter { it.id != id }
            _uiState.value = _uiState.value.copy(remoteNotifications = updated)
        }
    }

    var cachedLogs: List<String> = emptyList()
    fun fetchLogs() {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                val api = createApi(_uiState.value.apiKey)
                val resp = api.getJson("$base/api/logs")
                val arr = resp?.getAsJsonArray("lines") ?: return@launch
                cachedLogs = arr.mapNotNull { it?.asString }
            }
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
                model = o.get("model")?.asString,
                path = o.get("path")?.asString
            )
        }.getOrNull()
    }
}

private fun JsonObject.toCronList(): List<CronJobDto> {
    val arr = getAsJsonArray("jobs") ?: getAsJsonArray("data") ?: return emptyList()
    return arr.mapNotNull {
        runCatching {
            val o = it.asJsonObject
            val action = o.getAsJsonObject("action")
            CronJobDto(
                id = o.get("id")?.asString ?: o.get("id")?.asInt?.toString(),
                name = o.get("name")?.asString,
                interval_sec = o.get("interval_sec")?.asInt,
                enabled = o.get("enabled")?.asBoolean,
                lastRun = o.get("last_run")?.asLong,
                lastStatus = o.get("last_status")?.asString,
                actionType = action?.get("type")?.asString,
                actionMessage = action?.get("message")?.asString,
                actionStaff = action?.get("staff")?.asString,
                actionMode = action?.get("mode")?.asString,
                actionModel = action?.get("model")?.asString,
                actionSessionId = action?.get("session_id")?.asString,
                actionFork = action?.get("fork")?.asBoolean,
                actionDirectory = action?.get("directory")?.asString
            )
        }.getOrNull()
    }
}

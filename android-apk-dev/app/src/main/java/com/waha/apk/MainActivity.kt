package com.waha.apk

import android.content.Context
import android.os.Build
import android.os.Bundle
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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.ExperimentalMaterialApi
import androidx.compose.material.pullrefresh.PullRefreshIndicator
import androidx.compose.material.pullrefresh.pullRefresh
import androidx.compose.material.pullrefresh.rememberPullRefreshState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.SupportAgent
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
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
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Url
import retrofit2.HttpException
import java.net.URI

private val ComponentActivity.dataStore by preferencesDataStore(name = "monitor_settings")

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
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
    val snack = remember { SnackbarHostState() }

    LaunchedEffect(state.notice) {
        state.notice?.let {
            snack.showSnackbar(it)
            vm.clearNotice()
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
                IconButton(onClick = vm::refreshAll) {
                    Icon(Icons.Filled.Refresh, contentDescription = "Refresh")
                }
            }

            when (tab) {
                TabItem.Dashboard -> DashboardScreen(state, vm::refreshAll)
                TabItem.Cases -> CasesScreen(state, vm, vm::refreshAll)
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
                Text("Recent Cases", fontWeight = FontWeight.SemiBold)
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

@Composable
private fun CasesScreen(state: UiState, vm: MonitorViewModel, onRefresh: () -> Unit) {
    var sessionId by remember { mutableStateOf("") }
    var instruction by remember { mutableStateOf("") }

    PullToRefreshContainer(isRefreshing = state.loading, onRefresh = onRefresh) {
        LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = 12.dp)) {
            item {
                OutlinedTextField(value = sessionId, onValueChange = { sessionId = it }, label = { Text("Case ID") }, modifier = Modifier.fillMaxWidth())
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(value = instruction, onValueChange = { instruction = it }, label = { Text("Instruction") }, modifier = Modifier.fillMaxWidth())
                Spacer(Modifier.height(8.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = { vm.sendInstruction(sessionId, instruction) }) { Text("Send") }
                    Button(onClick = { vm.stopSession(sessionId) }) { Text("Stop") }
                }
                Spacer(Modifier.height(12.dp))
            }
            items(state.sessions) { SessionCard(it) }
            item { Spacer(Modifier.height(64.dp)) }
        }
    }
}

@Composable
private fun StaffScreen(state: UiState, onRefresh: () -> Unit) {
    PullToRefreshContainer(isRefreshing = state.loading, onRefresh = onRefresh) {
        LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = 12.dp)) {
            items(state.staff) { s ->
                Card(modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp), colors = CardDefaults.cardColors(containerColor = Color(0xFF161B22))) {
                    Column(Modifier.padding(12.dp)) {
                        Text(s.name, fontWeight = FontWeight.SemiBold)
                        Text("${s.gender ?: "-"} • ${s.mode ?: "default"}", color = Color(0xFF8B949E))
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
    var baseUrl by remember(state.baseUrl) { mutableStateOf(state.baseUrl) }
    var apiKey by remember(state.apiKey) { mutableStateOf(state.apiKey) }

    PullToRefreshContainer(isRefreshing = state.loading, onRefresh = onRefresh) {
        Column(modifier = Modifier.fillMaxSize().padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(value = baseUrl, onValueChange = { baseUrl = it }, label = { Text("Base URL") }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(value = apiKey, onValueChange = { apiKey = it }, label = { Text("API key") }, modifier = Modifier.fillMaxWidth())
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = { vm.saveSettings(baseUrl, apiKey) }) { Text("Save") }
                Button(onClick = vm::restartDaemon) { Text("Restart Daemon") }
                Button(onClick = vm::killDaemon) { Text("Kill Daemon") }
            }
            Image(painter = painterResource(R.drawable.homescreen_apps_mock), contentDescription = null, modifier = Modifier.fillMaxWidth().height(180.dp), contentScale = ContentScale.Crop)
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
private fun StatCard(label: String, value: String, modifier: Modifier = Modifier) {
    Card(modifier = modifier, colors = CardDefaults.cardColors(containerColor = Color(0xFF161B22))) {
        Column(Modifier.padding(10.dp)) {
            Text(label, style = MaterialTheme.typography.bodySmall, color = Color(0xFF8B949E))
            Text(value, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        }
    }
}

data class UiState(
    val loading: Boolean = false,
    val notice: String? = null,
    val baseUrl: String = "https://mydora.brandon.my/",
    val apiKey: String = "",
    val bossName: String = "Brandon",
    val sessions: List<SessionDto> = emptyList(),
    val staff: List<StaffDto> = emptyList(),
    val cronJobs: List<CronJobDto> = emptyList(),
    val summary: SummaryDto = SummaryDto()
)

data class StatusPayload(val sessions: List<SessionDto>? = null, val summary: SummaryDto? = null)
data class SummaryDto(val cpu_percent: Double? = null) { val cpuLabel: String get() = "${(cpu_percent ?: 0.0).toInt()}%" }
data class SessionDto(val id: String? = null, val title: String = "", val state: String? = null, val last_text: String? = null) { val lastText: String? get() = last_text }
data class StaffDto(val name: String = "", val description: String? = null, val gender: String? = null, val mode: String? = null)
data class CronJobDto(val id: String? = null, val name: String? = null, val interval_sec: Int? = null, val enabled: Boolean? = null) { val intervalSec: Int? get() = interval_sec }

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
    private val bossNameKey = stringPreferencesKey("boss_name")

    val baseUrl: Flow<String> = store.data.map { it[baseUrlKey] ?: "https://mydora.brandon.my/" }
    val apiKey: Flow<String> = store.data.map { it[apiKeyKey] ?: "" }
    val bossName: Flow<String> = store.data.map { it[bossNameKey] ?: "Brandon" }

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

    init {
        viewModelScope.launch { prefs.baseUrl.collect { _uiState.value = _uiState.value.copy(baseUrl = it) } }
        viewModelScope.launch { prefs.apiKey.collect { _uiState.value = _uiState.value.copy(apiKey = it) } }
        viewModelScope.launch { prefs.bossName.collect { _uiState.value = _uiState.value.copy(bossName = it) } }
        refreshAll()
    }

    fun clearNotice() { _uiState.value = _uiState.value.copy(notice = null) }

    fun refreshAll() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true)
            runCatching {
                val api = createApi(_uiState.value.apiKey)
                val base = _uiState.value.baseUrl.trimEnd('/')
                val status = runCatching {
                    api.getStatus("$base/api/status", JsonObject())
                }.recoverCatching {
                    api.getStatusGet("$base/api/status")
                }.recoverCatching {
                    api.getStatusFile("$base/data/status.json")
                }.getOrElse {
                    api.getStatusFile("$base/status.json")
                }
                val staff = runCatching {
                    postJsonFlexible(api, "$base/api/super-staff").toStaffList()
                }.getOrDefault(emptyList())
                val cron = runCatching {
                    postJsonFlexible(api, "$base/api/cron-jobs").toCronList()
                }.getOrDefault(emptyList())
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    sessions = status.sessions ?: emptyList(),
                    summary = status.summary ?: SummaryDto(),
                    staff = staff,
                    cronJobs = cron
                )
            }.onFailure {
                _uiState.value = _uiState.value.copy(loading = false, notice = it.message ?: "Refresh failed")
            }
        }
    }

    fun saveSettings(baseUrl: String, apiKey: String) {
        viewModelScope.launch {
            prefs.save(baseUrl, apiKey)
            _uiState.value = _uiState.value.copy(notice = "Settings saved")
            refreshAll()
        }
    }

    fun sendInstruction(sessionId: String, message: String) = postAction(
        path = "/api/session-instruct",
        body = JsonObject().apply {
            addProperty("id", sessionId)
            addProperty("message", message)
        },
        success = "Instruction sent"
    )

    fun stopSession(sessionId: String) = postAction(
        path = "/api/stop-session",
        body = JsonObject().apply { addProperty("id", sessionId) },
        success = "Session stopped"
    )

    fun toggleCron(id: String) = postAction(
        path = "/api/cron-jobs/toggle",
        body = JsonObject().apply { addProperty("id", id) },
        success = "Cron toggled"
    )

    fun runCron(id: String) = postAction(
        path = "/api/cron-jobs/run",
        body = JsonObject().apply { addProperty("id", id) },
        success = "Cron run triggered"
    )

    fun restartDaemon() = postAction("/api/restart-daemon", JsonObject(), "Daemon restarted")
    fun killDaemon() = postAction("/api/kill-daemon", JsonObject(), "Daemon killed")

    private fun postAction(path: String, body: JsonObject, success: String) {
        viewModelScope.launch {
            runCatching {
                val base = _uiState.value.baseUrl.trimEnd('/')
                createApi(_uiState.value.apiKey).postJson("$base$path", body)
            }.onSuccess {
                _uiState.value = _uiState.value.copy(notice = success)
                refreshAll()
            }.onFailure {
                _uiState.value = _uiState.value.copy(notice = it.message ?: "Request failed")
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
                mode = o.get("mode")?.asString
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
                enabled = o.get("enabled")?.asBoolean
            )
        }.getOrNull()
    }
}

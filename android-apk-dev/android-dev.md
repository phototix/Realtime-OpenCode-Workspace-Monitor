# Android App Development Guide

This document is a developer-facing guide for building an Android APK for API-driven products similar to this project. It is intended for teams that already have a working web app built with basic HTML, JavaScript, and HTTP requests, and now need an Android application that can be built locally with `./gradlew assembleDebug`.

## Goal

Build a native Android app that:

- Uses the same backend APIs as the existing web app.
- Is implemented with Kotlin and Jetpack Compose.
- Produces a debug APK with Gradle.
- Can be extended with offline cache, background sync, camera/QR features, and local persistence.

## Required Local Environment

The current project is configured for the following toolchain:

- macOS, Windows, or Linux
- Java 17
- Android SDK Platform 35
- Android Build Tools for API 35
- Gradle 8.7 via the included Gradle wrapper
- Android Gradle Plugin 8.5.2
- Kotlin 2.0.21

Recommended local tools:

- Android Studio
- Android SDK Command-line Tools
- Git

## Required Setup

### 1. Install Java 17

On macOS with Homebrew:

```bash
brew install openjdk@17
export JAVA_HOME="$(brew --prefix openjdk@17)/libexec/openjdk.jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"
java -version
```

The build should report Java 17.

### 2. Install Android SDK Components

Install at minimum:

- Android SDK Platform 35
- Android SDK Build-Tools 35.x
- Android SDK Command-line Tools
- Android Emulator optional
- Platform Tools

If `sdkmanager` is available:

```bash
sdkmanager "platforms;android-35" "build-tools;35.0.0" "platform-tools" "cmdline-tools;latest"
```

### 3. Create local.properties

Create `local.properties` in the project root:

```properties
sdk.dir=/Users/<your-user>/Library/Android/sdk
```

On Windows, use the local SDK path format expected by Android Studio.

### 4. Ensure Gradle Wrapper Is Executable

```bash
chmod +x gradlew
```

## Build Commands

Primary commands for developers:

```bash
./gradlew --version
./gradlew clean
./gradlew assembleDebug
```

Useful additional commands:

```bash
./gradlew tasks
./gradlew dependencies
./gradlew assembleRelease
./gradlew installDebug
```

Expected debug APK output:

```text
app/build/outputs/apk/debug/app-debug.apk
```

## Project Build Configuration

This repository currently builds with:

- App module: `:app`
- Namespace: `com.waha.apk`
- Application ID: `com.waha.apk`
- `compileSdk = 35`
- `minSdk = 26`
- `targetSdk = 35`
- `sourceCompatibility = JavaVersion.VERSION_17`
- `targetCompatibility = JavaVersion.VERSION_17`
- `jvmTarget = "17"`

Top-level Gradle plugin versions:

- `com.android.application` 8.5.2
- `org.jetbrains.kotlin.android` 2.0.21
- `org.jetbrains.kotlin.plugin.compose` 2.0.21
- `com.google.devtools.ksp` 2.0.21-1.0.26

Gradle wrapper version:

- Gradle 8.7

## Android Libraries To Use

These are the libraries already used by this project and should be the baseline for similar Android APK work.

### Core Android

- `androidx.core:core-ktx:1.13.1`
- `androidx.lifecycle:lifecycle-runtime-ktx:2.8.6`
- `androidx.activity:activity-compose:1.9.2`

### Jetpack Compose UI

- `androidx.compose:compose-bom:2024.09.00`
- `androidx.compose.ui:ui`
- `androidx.compose.ui:ui-tooling-preview`
- `androidx.compose.material3:material3`
- `androidx.compose.material:material-icons-extended`
- `androidx.navigation:navigation-compose:2.8.2`
- `androidx.lifecycle:lifecycle-viewmodel-compose:2.8.6`

### Local Persistence

- `androidx.room:room-runtime:2.6.1`
- `androidx.room:room-ktx:2.6.1`
- `androidx.room:room-compiler:2.6.1` via KSP
- `androidx.datastore:datastore-preferences:1.1.1`

### Networking

- `com.squareup.retrofit2:retrofit:2.11.0`
- `com.squareup.retrofit2:converter-gson:2.11.0`
- `com.squareup.okhttp3:okhttp:4.12.0`
- `com.squareup.okhttp3:logging-interceptor:4.12.0`

### Background Work

- `androidx.work:work-runtime-ktx:2.9.1`

### Refresh, Media, and QR Features

- `androidx.swiperefreshlayout:swiperefreshlayout:1.1.0`
- `androidx.camera:camera-core:1.3.4`
- `androidx.camera:camera-camera2:1.3.4`
- `androidx.camera:camera-lifecycle:1.3.4`
- `androidx.camera:camera-view:1.3.4`
- `com.google.mlkit:barcode-scanning:17.3.0`
- `com.google.zxing:core:3.5.3`

### Image Loading

- `io.coil-kt:coil-compose:2.7.0`

### Debug Dependencies

- `androidx.compose.ui:ui-tooling`
- `androidx.compose.ui:ui-test-manifest`

## Recommended Architecture For HTML/JS API-Based Apps

If the existing product is a basic web app that mostly does API calls, the Android version should map into these layers:

- `ui`: Jetpack Compose screens, navigation, reusable components
- `data.remote`: Retrofit API interfaces and DTOs
- `data.local`: Room entities, DAOs, local cache
- `data.repository`: repository implementations combining API and cache
- `feature/*`: screen-specific ViewModels and UI state
- `core/*`: shared constants, design system, utility helpers

Suggested package structure:

```text
app/navigation
core/common
core/designsystem
data/local
data/remote
data/repository
feature/session
feature/chats
feature/groups
feature/me
feature/settings
```

## How To Translate A Basic Web App Into Android

If the current web app is HTML and JavaScript with HTTP requests, the Android equivalent usually maps as follows:

- HTML pages become Compose screens.
- JavaScript fetch logic becomes Retrofit service calls.
- Browser local storage becomes DataStore or Room.
- Client-side state becomes immutable UI state in ViewModels.
- Polling or periodic refresh becomes WorkManager.
- Image URLs and media previews become Coil image loading.
- Camera-based QR flows become CameraX plus ML Kit.

## Screen and Feature Requirements

For a project like this one, the minimum Android scope should include:

- Splash screen
- Session picker for first launch
- Bottom navigation with Chats, Groups, Apps, Settings
- Chat list screen
- Chat detail screen with message bubbles
- Group list screen
- Profile or Me screen
- Settings screen with session info and screenshot preview
- Optional QR screen with scan and personal QR modes

## State Management Requirement

Use one ViewModel per screen with immutable UI state classes.

Each UI state should generally include:

- `isLoading`
- `errorMessage`
- data payload for the screen

Typical ViewModels:

- `SessionPickerViewModel`
- `ChatListViewModel`
- `ChatDetailViewModel`
- `MeViewModel`
- `SettingsViewModel`

## API Integration Requirement

The Android app should not hardcode API calls inside composables. The expected flow is:

1. Retrofit interface defines the endpoint.
2. Repository wraps the API call.
3. ViewModel calls the repository.
4. Compose screen observes state from the ViewModel.

Use OkHttp interceptors for:

- API key headers
- logging in debug builds
- timeout settings
- retry strategy if needed

For API-driven apps similar to this repo, the developer should provide:

- base URL configuration
- API key configuration
- endpoint DTO models
- repository methods for each screen flow

## Local Storage Requirement

Use local storage when the app needs persistent state.

Recommended split:

- DataStore for lightweight values such as selected session, base URL, or API key
- Room for structured cached data such as chats, messages, profiles, or other API entities

## Versioning Requirement

This project reads the app version from `app-version.txt`.

Expected format:

```text
version:YYYY-MM-DD-BUILD-###
```

Example:

```text
version:2026-06-14-BUILD-001
```

The build logic extracts the numeric build value and uses it as `versionCode`, while the full string after `version:` becomes `versionName`.

## Security Requirement

Do not treat the current hardcoded `BuildConfig` API values as a best practice for production. For new Android projects, prefer:

- local developer config for debug values
- CI/CD secret injection for release values
- encrypted local storage if secrets must remain on device

At minimum, the developer should avoid committing production credentials.

## Developer Checklist

Before implementing the Android app, the developer should confirm:

- Final API base URL
- Authentication model
- Required endpoints per screen
- Data models for chats, messages, user profile, settings, and session state
- Empty, loading, and error states
- Offline or cache requirements
- Minimum Android version support
- APK signing strategy for release builds

## Build Validation Checklist

Before handing over a debug APK, verify:

- `java -version` reports Java 17
- `local.properties` points to a valid Android SDK
- Gradle sync succeeds
- `./gradlew assembleDebug` succeeds
- APK exists at `app/build/outputs/apk/debug/app-debug.apk`
- App launches on emulator or device
- Main API flows work against the target backend

## Suggested Implementation Order

1. Set up Gradle, Android SDK config, and dependencies.
2. Create app theme and navigation shell.
3. Implement API client and base repository structure.
4. Add DataStore for lightweight persisted config.
5. Add Room for cached entities if the product needs offline or sync support.
6. Build the first critical user flow end to end.
7. Add background sync, QR, media, or camera features only after the core flow is stable.
8. Validate with `./gradlew assembleDebug` before feature handoff.

## Minimum Handover Output Expected From Developer

The developer should deliver:

- Android source code in a Gradle project
- correct `local.properties` instructions
- complete dependency list in Gradle
- clear environment requirements
- working debug build through `./gradlew assembleDebug`
- resulting debug APK path
- short run instructions for emulator or device testing

## One-Line Build Target

The final acceptance target for this kind of Android conversion project is:

```bash
./gradlew assembleDebug
```

If that command fails on a clean machine with Java 17 and Android SDK 35 installed, the project handoff is incomplete.
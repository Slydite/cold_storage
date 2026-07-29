# Android Capacitor App Documentation

This guide describes how to configure, build, and sign the packaged Android app for the Cold Storage WMS.

---

## 1. Backend CORS Configuration

Because the native Android WebView hosts assets under the origin `http://localhost` (and iOS uses `capacitor://localhost`), the Django backend must allow cross-origin requests from these origins.

### Configuration Steps
1. Open the `.env` file on the production VM.
2. Find the `DJANGO_CORS_ALLOWED_ORIGINS` variable.
3. Append `,http://localhost,capacitor://localhost` to the list of allowed origins.
   *Example:*
   ```env
   DJANGO_CORS_ALLOWED_ORIGINS=https://cold.crystalcubes.in,http://localhost,capacitor://localhost
   ```
4. Restart the Django/Gunicorn backend service (e.g., `docker compose restart backend`).

---

## 2. Release-Signing Steps

To distribute the app via Google Play or install it securely on devices, you must build a signed Android App Bundle (`.aab`) or APK.

> [!WARNING]
> **CRITICAL SECURITY WARNING:**
> The release keystore file and its passwords are **UNRECOVERABLE**. If you lose the keystore, its password, or the alias password, you will **never** be able to update your Google Play listing. You must back up the keystore file and its passwords securely outside of this machine (e.g., in a secure password manager or offline backup).

### Step 2.1: Generate a Keystore File
Generate a secure keystore file using `keytool` (comes with JDK):

```bash
keytool -genkey -v -keystore cold-storage-release.keystore -alias cold-storage-alias -keyalg RSA -keysize 2048 -validity 10000
```
This command will prompt you to enter keystore passwords, organization information, and key passwords.

### Step 2.2: Configure Gradle Signing
Place the generated keystore file in the `android/app/` folder (which is ignored by Git via `*.keystore` pattern in `.gitignore`), and update `frontend/android/app/build.gradle` to define the signing configurations.

Inside `android/app/build.gradle`, add a `signingConfigs` block inside the `android` block, and reference it in the `buildTypes.release`:

```groovy
android {
    ...
    signingConfigs {
        release {
            storeFile file("cold-storage-release.keystore")
            storePassword System.getenv("ANDROID_KEYSTORE_PASSWORD") ?: "YOUR_STORE_PASSWORD"
            keyAlias "cold-storage-alias"
            keyPassword System.getenv("ANDROID_KEY_PASSWORD") ?: "YOUR_KEY_PASSWORD"
        }
    }

    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
}
```

### Step 2.3: Generate the Release Bundle (.aab)
To build the signed release bundle:
1. Open the Android project in Android Studio or run Gradle from the command line:
   ```bash
   cd android
   ./gradlew bundleRelease
   ```
2. The output `.aab` file will be located at `android/app/build/outputs/bundle/release/app-release.aab`.

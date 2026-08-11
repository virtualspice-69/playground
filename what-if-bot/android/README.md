# $IF Studio — Android

WebView shell around `studio/if-studio.html`. Same UI as the browser version,
installable as a real app.

- **Min Android:** 6.0 (API 23) — covers ~99% of devices
- **Size:** ~65 KB
- **Permissions:** internet only
- **Signing:** debug-style keystore generated on first build (`build/signing.keystore`)

## Install

Transfer `build/IF-Studio.apk` to the phone and tap it. Android will ask you to
allow "Install unknown apps" for whatever app you opened it from — that prompt
is expected for any APK not from the Play Store.

Via USB instead: `adb install -r build/IF-Studio.apk`

## Build

```bash
apt-get install -y aapt android-sdk-build-tools android-sdk-platform-23 default-jdk
./build.sh
```

`dx` is fetched from Maven Central on first run. No Android Studio, no Gradle,
no Google SDK download required — which matters because `dl.google.com` is
often blocked on locked-down networks.

To regenerate the launcher icon after changing the mark: `python make_icon.py`

## Notes on the build

- Compiles against the API 23 `android.jar` but declares `targetSdkVersion 34`,
  so modern Android doesn't show the "built for an older version" warning.
  Nothing in `MainActivity` calls an API newer than 23.
- Dexed with legacy `dx`, which cannot desugar Java 8 language features —
  so `MainActivity.java` is deliberately written in Java 7 style (no lambdas,
  no method references). Keep it that way or the dex step will fail.
- The page runs from `file:///android_asset/`, so `localStorage` (where the A/B
  training data lives) is enabled via `setDomStorageEnabled(true)`.
- Export uses the `IFBridge` JavaScript interface rather than a blob download,
  since a blob has nowhere to land in a WebView. Files go to the app-specific
  external dir, so no storage permission is needed.

## Updating the UI

The APK bundles a copy of the HTML at build time. After editing
`studio/if-studio.html`, re-run `./build.sh` to pick up the changes.

## Signing for real distribution

The generated keystore is fine for sideloading and for handing the APK around
the community. If you ever want Play Store distribution, generate your own
keystore, keep it somewhere safe (losing it means you can never update the
listing), and point `KEYSTORE`/`STOREPASS` in `build.sh` at it.
